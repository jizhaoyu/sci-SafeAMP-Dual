// Real local API/model smoke check. Only ancillary biophysics views are suppressed.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const directory = path.resolve(__dirname, '../../output/dti-real-inference-smoke-20261011');
  const original = JSON.parse(fs.readFileSync(path.join(directory, 'real-inference-results.json'), 'utf8'));
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  const blocked = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route(/^http:\/\/127\.0\.0\.1:5177\/api\/dti\/(?:biophysics|pocket_structure)/, route => {
    blocked.push(route.request().url());
    return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Ancillary structure analysis outside this inference smoke check' }) });
  });
  const results = [];
  try {
    await page.goto('http://127.0.0.1:5177');
    const panel = page.getByRole('region', { name: '研究证据状态' });
    await panel.getByText('独立外部评价尚未完成', { exact: true }).waitFor();
    for (const recorded of original.predictions) {
      await page.getByRole('textbox', { name: '分子 SMILES', exact: true }).fill(recorded.sample.drug_smiles);
      await page.getByRole('textbox', { name: '靶点氨基酸序列', exact: true }).fill(recorded.sample.target_sequence);
      const [response] = await Promise.all([
        page.waitForResponse(response => new URL(response.url()).pathname === '/api/dti/predict' && response.request().method() === 'POST'),
        page.getByRole('button', { name: '开始预测', exact: true }).first().click(),
      ]);
      assert.equal(response.status(), 200);
      const result = await response.json();
      assert.equal(result.predicted_pkd, recorded.response.predicted_pkd);
      assert.equal(result.model_used, 'f1_ridge');
      assert.equal(result.provenance.model_sha256, recorded.response.provenance.model_sha256);
      assert.equal(result.research_evidence.external_evaluation_completed, false);
      await page.getByRole('button', { name: '导出预测 JSON' }).waitFor();
      await page.locator('#prediction-results').getByText(result.predicted_pkd.toFixed(3), { exact: true }).waitFor();
      const downloadEvent = page.waitForEvent('download');
      await page.getByRole('button', { name: '导出预测 JSON' }).click();
      const download = await downloadEvent;
      const saved = path.join(directory, `browser-${recorded.sample.target_id.replace(/[^A-Za-z0-9_-]/g, '_')}.json`);
      await download.saveAs(saved);
      const exported = JSON.parse(fs.readFileSync(saved, 'utf8'));
      assert.equal(exported.predicted_pkd, result.predicted_pkd);
      assert.equal(exported.research_evidence.admitted_count, 0);
      assert.match(exported.research_use, /独立外部评价尚未完成/);
      results.push({ sample: recorded.sample.name, model: result.model_used, pkd: result.predicted_pkd, kd_nM: result.predicted_kd_nM, http_status: response.status() });
    }
    await page.locator('#prediction-results').screenshot({ path: path.join(directory, 'real-prediction-result.png') });
    await page.getByRole('button', { name: '激酶选择性谱 (Kinome Panel)', exact: true }).click();
    const [profileResponse] = await Promise.all([
      page.waitForResponse(response => new URL(response.url()).pathname === '/api/dti/profile_panel' && response.request().method() === 'POST'),
      page.getByRole('button', { name: '重新测定谱系' }).click(),
    ]);
    assert.equal(profileResponse.status(), 200);
    const profile = await profileResponse.json();
    assert.equal(profile.length, original.kinase_panel.length);
    await page.getByRole('button', { name: '导出 CSV', exact: true }).waitFor();
    const csvDownload = page.waitForEvent('download');
    await page.getByRole('button', { name: '导出 CSV', exact: true }).click();
    const file = await csvDownload;
    await file.saveAs(path.join(directory, 'real-browser-kinase-panel.csv'));
    const csv = fs.readFileSync(path.join(directory, 'real-browser-kinase-panel.csv'), 'utf8');
    assert.match(csv, /"f1_ridge","not_completed","false","0","2026-10-11","not_evaluated"/);
    await page.getByRole('link', { name: /先导分子优化/ }).click();
    await page.waitForURL('**/evolution');
    const modelSelect = page.getByRole('combobox', { name: '亲和力定量打分基准模型', exact: true });
    await modelSelect.waitFor();
    assert.equal(await modelSelect.inputValue(), 'f1_ridge');
    assert.equal(await modelSelect.locator('option').count(), original.model_catalog.length);
    assert.equal(errors.length, 0, errors.join('\n'));
    fs.writeFileSync(path.join(directory, 'real-browser-verification.json'), JSON.stringify({ passed: true, api_fixtures: false, core_api_and_models: 'real_local_backend', single_predictions: results, kinase_panel_rows: profile.length, optimizer_model_options: await modelSelect.locator('option').count(), runtime_errors: errors, ancillary_requests_suppressed: blocked }, null, 2));
    console.log('PASS: three real browser predictions, matching JSON exports, real kinase profile/CSV, live optimizer catalog; no runtime errors.');
  } catch (error) {
    console.error(errors);
    console.error((await page.locator('body').innerText()).slice(-1000));
    await page.screenshot({ path: path.join(directory, 'browser-failure.png'), fullPage: true });
    throw error;
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
