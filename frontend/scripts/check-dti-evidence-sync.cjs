// Real browser interaction with isolated API fixtures. No inference or external messages.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const root = path.resolve(__dirname, '../..');
  const directory = path.join(root, 'output/dti-purpose-tightening-20261011');
  const evidence = { ...JSON.parse(fs.readFileSync(path.join(root, '05_web_server/data/dti_external_evidence.json'), 'utf8')), status: 'available', external_metrics: { mae: null, rmse: null, ci: null } };
  const models = [{ id: 'f1_ridge', name: 'F1 Ridge', is_recommended: true, badge: '默认', desc: '历史基准', badge_color: 'blue', train_ci: 0.8, cold_target_ci: 0.7, cold_drug_ci: 0.7 }, { id: 'ridge', name: 'Legacy Ridge', badge: '历史', desc: '历史基准', train_ci: 0.7 }];
  const prediction = { predicted_pkd: 7, predicted_kd_nM: 100, model_used: 'f1_ridge', affinity_tier: '高活性（测试旧标签）', affinity_tier_code: 'high_affinity', domain: 'cold_both', domain_label: '历史基准域', max_drug_similarity_to_train: 0.3, max_target_similarity_to_train: 0.3, domain_benchmark_metrics: {}, target_length: 240, provenance: { protocol: 'UI fixture only', benchmark: 'fixture', training_run: 'fixture' }, warning: '测试数据，不是科学预测', research_evidence: evidence };
  const candidate = { id: 'test-1', name: 'Candidate "A", test', smiles: 'CCN', modification_type: '测试', rationale: '测试数据', predicted_pkd: 7.2, predicted_kd_nM: 63.1, delta_pkd: 0.2, fold_change: 1.58, affinity_tier: '计算候选', affinity_tier_code: 'moderate_affinity', domain: 'cold_both', status: '计算候选', status_code: 'improved' };
  const alCandidate = { name: candidate.name, smiles: candidate.smiles, mean_pkd: 7.2, uncertainty_sigma: 0.3, expected_improvement: 0.1, ucb_score: 7.5, quadrant: 'confident_hit', quadrant_label: '高置信度领头物', recommendation_reason: '测试, "候选"说明' };
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
  const errors = [];
  const calls = [];
  let evidenceMode = 'available';
  let predictionHash = evidence.model_diagnostics.f1_ridge.model_sha256;
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => { Object.defineProperty(navigator, 'clipboard', { value: { writeText: async text => { window.__copiedText = text; } } }); });
  await page.route(/^http:\/\/127\.0\.0\.1:5177\/api\//, route => {
    const pathname = new URL(route.request().url()).pathname;
    calls.push(pathname);
    let payload;
    if (pathname.endsWith('/models')) payload = models;
    else if (pathname.endsWith('/drugs')) payload = [{ id: '1', name: 'Dasatinib', smiles: 'CCO', fold: 1, is_test: false }];
    else if (pathname.endsWith('/targets')) payload = [{ id: 'ABL1', sequence: 'ACDEFGHIKLMNPQRSTVWY'.repeat(12), length: 240, fold: 1, is_test: false }];
    else if (pathname.endsWith('/evidence_status') && evidenceMode !== 'error') payload = evidenceMode === 'malformed' ? { ...evidence, reviewed_count: 99 } : evidence;
    else if (pathname.endsWith('/predict')) payload = { ...prediction, provenance: { ...prediction.provenance, model_sha256: predictionHash } };
    else if (pathname.endsWith('/profile_panel')) payload = [{ ...prediction, kinase_name: 'ABL1', length: 240 }];
    else if (pathname.endsWith('/optimize_lead') || pathname.endsWith('/optimize-lead')) {
      assert.equal(route.request().postDataJSON().model_name, 'f1_ridge');
      payload = { mode: 'heuristic_fallback', target_name: 'ABL1', model_used: 'f1_ridge', baseline: { ...prediction, smiles: 'CCO' }, candidates: [candidate], summary: { candidates_evaluated: 1, best_candidate: candidate.name, max_affinity_gain_pkd: 0.2, best_kd_nM: 63.1 }, research_evidence: evidence };
    } else if (pathname.endsWith('/active_learning')) payload = { target_name: 'ABL1', total_evaluated: 1, y_best_reference: 7, confident_hits: [alCandidate], breakthrough_hypotheses: [], high_information_gain_blindspots: [], known_inactives: [], markdown_summary: '# 高置信度领头物\n\n测试总结', research_evidence: evidence };
    else if (pathname.endsWith('/academic_report')) {
      assert.equal(route.request().postDataJSON().model_used, 'f1_ridge');
      payload = { target_name: 'ABL1', generated_at: 'fixture', research_evidence: evidence, markdown_report: '# 待复核草稿\n\n独立外部评价尚未完成。模型：f1_ridge。测试模板', html_report: '<html><body><aside>独立外部评价尚未完成</aside></body></html>' };
    }
    return route.fulfill({ status: payload ? 200 : 503, contentType: 'application/json', body: JSON.stringify(payload ?? { message: 'UI fixture: unavailable' }) });
  });
  const panel = () => page.getByRole('region', { name: '研究证据状态' });
  const downloadText = async name => {
    await page.getByRole('button', { name, exact: true }).waitFor();
    const event = page.waitForEvent('download');
    await page.getByRole('button', { name, exact: true }).click();
    const downloaded = await event;
    const saved = path.join(directory, downloaded.suggestedFilename());
    await downloaded.saveAs(saved);
    return fs.readFileSync(saved, 'utf8');
  };
  try {
    await page.goto('http://127.0.0.1:5177');
    await panel().getByText('独立外部评价尚未完成', { exact: true }).waitFor();
    assert.deepEqual(await panel().locator('dd').allTextContents(), ['8条', '5条', '0条']);
    await panel().locator('summary').filter({ hasText: '查看复核范围' }).click();
    assert.equal(await panel().locator('li').count(), 8);
    assert.equal(await panel().getByRole('button').count(), 1, 'Pending records must not have quick-run actions');
    await panel().locator('summary').filter({ hasText: '查看复核范围' }).click();
    for (const mode of ['error', 'malformed']) {
      evidenceMode = mode;
      await panel().getByRole('button', { name: '刷新证据状态' }).click();
      await panel().getByText('研究证据状态无法确认', { exact: true }).waitFor();
      assert.equal(await panel().locator('dd').count(), 0);
      await page.getByRole('textbox', { name: '分子 SMILES', exact: true }).fill('CCO');
      await page.getByRole('textbox', { name: '靶点氨基酸序列', exact: true }).fill('ACDEFGHIKLMNPQRSTVWY'.repeat(12));
      assert(await page.getByRole('button', { name: '开始预测', exact: true }).first().isEnabled());
    }
    evidenceMode = 'available';
    await panel().getByRole('button', { name: '刷新证据状态' }).click();
    await panel().getByText('独立外部评价尚未完成', { exact: true }).waitFor();
    await page.getByRole('button', { name: '开始预测', exact: true }).first().click();
    await page.getByRole('button', { name: '导出预测 JSON' }).waitFor();
    const result = JSON.parse(await downloadText('导出预测 JSON'));
    await page.locator('#prediction-results').getByText('预测分数区间', { exact: true }).waitFor();
    assert.doesNotMatch(await page.locator('#prediction-results').innerText(), /亲和力活性分级|高活性（测试旧标签）|ΔG°/);
    const scoreCard = page.getByRole('region', { name: '预测分数与用途限制' });
    await scoreCard.getByLabel('F1模型使用限制').waitFor();
    await scoreCard.screenshot({ path: path.join(directory, 'prediction-score-and-limits.png') });
    assert.equal(result.prediction_score_band, 'pKd ≥ 7');
    assert.equal(result.affinity_tier, undefined);
    assert.equal(result.model_used, 'f1_ridge');
    assert.equal(result.research_evidence.external_evaluation_completed, false);
    assert.equal(result.research_evidence.external_metrics.mae, null);
    assert.match(result.model_limitations, /缺少药物—靶点交互项/);
    predictionHash = 'f'.repeat(64);
    await page.getByRole('button', { name: '开始预测', exact: true }).first().click();
    await page.locator('#prediction-results').getByText('当前F1模型版本与已有诊断不一致，诊断限制的适用性尚未确认。', { exact: true }).waitFor();
    assert.equal(await page.locator('#prediction-results').getByText('查看F1诊断依据', { exact: true }).count(), 0);
    const differentVersion = JSON.parse(await downloadText('导出预测 JSON'));
    assert.match(differentVersion.model_limitations, /版本与已有诊断不一致/);
    assert.doesNotMatch(differentVersion.model_limitations, /620|系统性低估/);
    predictionHash = evidence.model_diagnostics.f1_ridge.model_sha256;
    await page.getByRole('button', { name: '开始预测', exact: true }).first().click();
    await page.locator('#prediction-results').getByText('查看F1诊断依据', { exact: true }).waitFor();
    await panel().getByText('F1 Ridge · 已记录的模型使用限制', { exact: true }).waitFor();
    await panel().getByText('查看F1诊断依据', { exact: true }).click();
    assert.match(await panel().innerText(), /620个参考pKd/);
    await panel().getByText('查看F1诊断依据', { exact: true }).click();
    assert.match(result.research_use, /研究探索/);
    await page.getByRole('button', { name: '激酶选择性谱 (Kinome Panel)', exact: true }).click();
    await page.getByRole('button', { name: '重新测定谱系' }).click();
    const csv = await downloadText('导出 CSV');
    assert.match(csv, /External_MAE/);
    assert.match(csv, /"false","0","2026-10-11","not_evaluated"/);
    assert.match(csv, /f1_ridge/);
    assert.match(csv, /Model_Limitations/);
    assert.match(csv, /Prediction_Score_Band/);
    assert.doesNotMatch(csv, /高活性（测试旧标签）/);
    assert.match(csv, /高亲和力系统性低估/);
    await page.getByRole('button', { name: '亲和力预测', exact: true }).click();
    const themeBackgrounds = [];
    for (const dark of [false, true]) {
      if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== dark) await page.getByRole('button', { name: '切换日间/夜间模式', exact: true }).click();
      assert.equal(await page.locator('html').evaluate(el => el.classList.contains('dark')), dark);
      themeBackgrounds.push(await panel().evaluate(el => getComputedStyle(el).backgroundColor));
      for (const width of [375, 768, 1024, 1440]) {
        await page.setViewportSize({ width, height: 960 });
        await page.evaluate(() => window.scrollTo(0, 0));
        await page.waitForTimeout(100);
        assert(await panel().evaluate(el => el.getBoundingClientRect().right <= innerWidth), `Evidence panel overflow at ${width}`);
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `Page overflow at ${width}`);
        await page.screenshot({ path: path.join(directory, `dti-${dark ? 'dark' : 'light'}-${width}.png`) });
      }
    }
    assert.notEqual(themeBackgrounds[0], themeBackgrounds[1], 'Theme must change actual panel colors');
    await page.getByRole('link', { name: /先导分子优化/ }).click();
    await page.waitForURL('**/evolution');
    await panel().waitFor();
    const select = page.getByRole('combobox', { name: '亲和力定量打分基准模型', exact: true });
    await select.waitFor();
    assert.equal(await select.inputValue(), 'f1_ridge');
    assert.equal(await select.locator('option').count(), 2);
    await select.selectOption('ridge');
    assert.equal(await panel().getByLabel('F1模型使用限制').count(), 0, 'F1 limitations must not be applied to other models');
    await panel().getByRole('button', { name: '刷新证据状态' }).click();
    assert.equal(await select.inputValue(), 'ridge', 'Evidence refresh must preserve model selection');
    await select.selectOption('f1_ridge');
    await panel().getByLabel('F1模型使用限制').waitFor();
    evidenceMode = 'error';
    await panel().getByRole('button', { name: '刷新证据状态' }).click();
    await panel().getByText('研究证据状态无法确认', { exact: true }).waitFor();
    assert(await page.getByRole('button', { name: /开始智能改构/ }).isEnabled());
    evidenceMode = 'available';
    await panel().getByRole('button', { name: '刷新证据状态' }).click();
    await panel().getByText('独立外部评价尚未完成', { exact: true }).waitFor();
    await page.getByRole('button', { name: /开始智能改构/ }).click();
    await page.getByRole('button', { name: /贝叶斯主动学习探索\/利用矩阵/ }).click();
    await page.getByRole('button', { name: '导出验证清单 (CSV)' }).waitFor();
    const alCSV = await downloadText('导出验证清单 (CSV)');
    assert.match(alCSV, /Active_Learning_Model_ID/);
    assert.match(alCSV, /"f1_ridge","not_reported"/);
    assert.match(alCSV, /Candidate ""A"", test/);
    assert.doesNotMatch(alCSV, /高置信度领头物/);
    assert.match(alCSV, /高亲和力系统性低估/);
    await page.getByRole('button', { name: '复制学术总结' }).click();
    const markdown = await page.evaluate(() => window.__copiedText);
    assert.match(markdown, /独立外部评价尚未完成/);
    assert.doesNotMatch(markdown, /高置信度领头物/);
    assert.match(markdown, /缺少药物—靶点交互项/);
    await page.getByRole('button', { name: '生成学术交付报告' }).click();
    const dialog = page.getByRole('dialog', { name: '计算生物学学术评估报告' });
    await dialog.getByText('待人工与实验复核', { exact: true }).waitFor();
    const reportMarkdown = await downloadText('下载 .md');
    assert.match(reportMarkdown, /独立外部评价尚未完成/);
    await dialog.getByRole('button', { name: '排版预览 (Print View)' }).click();
    await page.frameLocator('iframe[title="Print Preview"]').getByText('独立外部评价尚未完成').waitFor();
    await dialog.getByRole('button', { name: '关闭报告' }).click();
    for (const dark of [false, true]) {
      if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== dark) await page.getByRole('button', { name: '切换日间/夜间模式', exact: true }).click();
      for (const width of [375, 768, 1024, 1440]) {
        await page.setViewportSize({ width, height: 960 });
        await page.evaluate(() => window.scrollTo(0, 0));
        assert(await panel().evaluate(el => el.getBoundingClientRect().right <= innerWidth));
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `Optimizer overflow at ${width}`);
        await page.screenshot({ path: path.join(directory, `optimizer-${dark ? 'dark' : 'light'}-${width}.png`) });
      }
    }
    await page.setViewportSize({ width: 375, height: 960 });
    await panel().screenshot({ path: path.join(directory, 'optimizer-evidence-mobile.png') });
    assert.equal(errors.length, 0, errors.join('\n'));
    fs.writeFileSync(path.join(directory, 'browser-verification.json'), JSON.stringify({ passed: true, fixture_only: true, runtime_errors: errors, viewport_widths: [375, 768, 1024, 1440], checks: ['scope counts/details', 'HTTP failure and malformed data', 'refresh recovery', 'prediction and optimization runtime independent of evidence', 'JSON/CSV/Markdown exports', 'academic report download and HTML preview', 'dynamic model options and preserved selection', 'F1 diagnosis visible and exported', 'other model does not inherit F1 diagnosis', 'different model hash does not inherit frozen diagnosis', 'both themes and full page viewport overflow'], intercepted_api_paths: [...new Set(calls)] }, null, 2));
    console.log('PASS: research evidence states, exports, model directory, responsive layout, no browser runtime errors. API fixtures only.');
  } catch (error) {
    console.error('Runtime errors:', errors);
    console.error('Overflow:', await page.evaluate(() => [...document.querySelectorAll('body *')].filter(el => el.getBoundingClientRect().right > innerWidth + 1 && el.getBoundingClientRect().width > 0).slice(0, 15).map(el => ({ tag: el.tagName, class: el.className, right: el.getBoundingClientRect().right, text: el.textContent.slice(0, 80) }))));
    console.error((await page.locator('body').innerText()).slice(-2000));
    await page.screenshot({ path: path.join(directory, 'failure.png'), fullPage: true });
    throw error;
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
