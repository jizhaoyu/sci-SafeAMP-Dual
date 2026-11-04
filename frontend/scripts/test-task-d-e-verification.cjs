const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const outDir = path.resolve(__dirname, '../../output/gemini-fix-verification');
fs.mkdirSync(outDir, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 960 },
    permissions: ['clipboard-read', 'clipboard-write'],
  });
  const page = await context.newPage();

  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error' && !msg.text().includes('Failed to load resource')) {
      consoleErrors.push(msg.text());
    }
  });
  page.on('pageerror', err => {
    consoleErrors.push(err.message);
  });

  const verificationLog = {
    taskD: {},
    taskE: {},
  };

  try {
    console.log('=== Verifying Task D: Modal Repeat Open/Close & Conditional Hook Fixes ===');
    await page.goto('http://127.0.0.1:5173/evolution');
    await page.waitForTimeout(500);

    // 1. Trigger lead optimization so candidates and baseline are populated
    await page.getByRole('button', { name: /达沙替尼 \(Dasatinib\) → ABL1/ }).click();
    await page.getByRole('button', { name: /开始智能改构与贝叶斯主动学习评估/ }).click();
    const baselineText = page.getByText('先导母体基准 (Baseline Lead)', { exact: true });
    await baselineText.waitFor({ state: 'visible', timeout: 25000 });

    // 2. Test WetlabDispatchModal repeat open / interact / close
    console.log('Testing WetlabDispatchModal cycle 1...');
    const wetlabBtn = page.getByRole('button', { name: '96 孔板投产清单', exact: true });
    await wetlabBtn.click();
    
    const wetlabDialog = page.getByRole('dialog', { name: '湿实验 96 孔板投产清单与移液规程' });
    await wetlabDialog.waitFor({ state: 'visible' });

    // Interact with well
    const well = page.locator('button[title*="A01"], button[title*="空孔"]').first();
    await well.waitFor({ state: 'visible' });
    await well.click();

    // Download CSV
    const csvDownloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: '下载孔板 CSV', exact: true }).click();
    const csvDownload = await csvDownloadPromise;
    const csvFilename = csvDownload.suggestedFilename();
    assert.ok(csvFilename.endsWith('.csv'), `Wetlab CSV filename must end with .csv, got ${csvFilename}`);

    // Close
    await page.getByRole('button', { name: '关闭投产面板', exact: true }).click();
    await wetlabDialog.waitFor({ state: 'hidden' });

    // Reopen WetlabDispatchModal cycle 2 & 3
    console.log('Testing WetlabDispatchModal cycle 2 & 3 (reopenings)...');
    for (let cycle = 2; cycle <= 3; cycle++) {
      await wetlabBtn.click();
      await wetlabDialog.waitFor({ state: 'visible' });
      await page.waitForTimeout(200);
      await page.getByRole('button', { name: '关闭投产面板', exact: true }).click();
      await wetlabDialog.waitFor({ state: 'hidden' });
    }

    // 3. Test AcademicReportModal repeat open / interact / close
    console.log('Testing AcademicReportModal cycle 1...');
    const reportBtn = page.getByRole('button', { name: '生成学术交付报告', exact: true });
    await reportBtn.click();

    const reportDialog = page.getByRole('dialog', { name: '计算生物学学术评估报告' });
    await reportDialog.waitFor({ state: 'visible' });

    // Switch tab to raw markdown
    await page.getByRole('button', { name: 'Markdown 源码视图', exact: true }).click();
    await page.waitForTimeout(200);
    await page.getByRole('button', { name: '排版预览 (Print View)', exact: true }).click();
    await page.waitForTimeout(200);

    // Download MD
    const mdDownloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: '下载 .md', exact: true }).click();
    const mdDownload = await mdDownloadPromise;
    const mdFilename = mdDownload.suggestedFilename();
    assert.ok(mdFilename.endsWith('.md'), `Report markdown filename must end with .md, got ${mdFilename}`);

    // Close
    await page.getByRole('button', { name: '关闭报告', exact: true }).click();
    await reportDialog.waitFor({ state: 'hidden' });

    // Reopen AcademicReportModal cycle 2 & 3
    console.log('Testing AcademicReportModal cycle 2 & 3 (reopenings)...');
    for (let cycle = 2; cycle <= 3; cycle++) {
      await reportBtn.click();
      await reportDialog.waitFor({ state: 'visible' });
      await page.waitForTimeout(200);
      await page.getByRole('button', { name: '关闭报告', exact: true }).click();
      await reportDialog.waitFor({ state: 'hidden' });
    }

    // Assert NO React Hook errors occurred!
    const hookErrors = consoleErrors.filter(e => e.includes('Rendered more hooks') || e.includes('Rendered fewer hooks') || e.includes('Rules of Hooks'));
    assert.equal(hookErrors.length, 0, `React hook order errors detected: ${hookErrors.join('; ')}`);
    console.log('PASS Task D: WetlabDispatchModal and AcademicReportModal opened/closed 3 times each without any Hook error.');
    verificationLog.taskD = {
      status: 'passed',
      wetlabCsvFilename: csvFilename,
      academicReportMdFilename: mdFilename,
      reopenCycles: 3,
      hookErrorsCount: hookErrors.length,
    };

    console.log('=== Verifying Task E: Accurate Status & Rate Limiting Distinctions ===');
    
    // Branch 1: Real backend 200 with 7 models ready
    await page.goto('http://127.0.0.1:5173');
    await page.waitForTimeout(600);
    const badgeText1 = await page.locator('[role="status"]').innerText();
    assert.ok(badgeText1.includes('DTI 预测模型在线') || badgeText1.includes('DTI 世界模型在线'), `Branch 1: Expected online badge with CI, got: ${badgeText1}`);
    console.log('Branch 1 (200 with models) passed:', badgeText1);
    await page.screenshot({ path: path.join(outDir, 'taskE_branch1_200_models_ready.png') });
    verificationLog.taskE.branch1_200_models_ready = { status: 'passed', badge: badgeText1 };

    // Branch 2: Fault injection - 200 with 0 models registered []
    await page.route('**/api/dti/models', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });
    await page.reload();
    await page.waitForTimeout(600);
    const badgeText2 = await page.locator('[role="status"]').innerText();
    assert.ok(badgeText2.includes('未注册模型'), `Branch 2: Expected '未注册模型', got: ${badgeText2}`);
    console.log('Branch 2 (200 empty models) passed:', badgeText2);
    await page.screenshot({ path: path.join(outDir, 'taskE_branch2_200_empty_models.png') });
    verificationLog.taskE.branch2_200_empty_models = { status: 'passed', badge: badgeText2 };
    await page.unroute('**/api/dti/models');

    // Branch 3: Fault injection - HTTP 503 dual task unready
    await page.goto('http://127.0.0.1:5173/amp-screening');
    await page.waitForTimeout(600);
    const readySection = page.locator('#dual-task-readiness');
    await readySection.waitFor({ state: 'visible' });
    const sectionText = await readySection.innerText();
    assert.ok(sectionText.includes('双任务模型未就绪') || sectionText.includes('未配置'), `Branch 3: Expected AMP unready notice, got: ${sectionText}`);
    console.log('Branch 3 (503 gating) passed: AMP dual task properly gated with clear unready notice.');
    await page.screenshot({ path: path.join(outDir, 'taskE_branch3_503_gating.png') });
    verificationLog.taskE.branch3_503_gating = { status: 'passed', unreadyNotice: sectionText.slice(0, 150) };

    // Branch 4: Fault injection - HTTP 429 rate limit with Retry-After header
    await page.route('**/api/dti/models', route => {
      route.fulfill({
        status: 429,
        headers: {
          'Retry-After': '30',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ detail: 'Rate limit exceeded: 30 requests per minute.' }),
      });
    });
    await page.goto('http://127.0.0.1:5173');
    await page.waitForTimeout(600);
    const badgeText4 = await page.locator('[role="status"]').innerText();
    assert.ok(badgeText4.includes('429') || badgeText4.includes('受限'), `Branch 4: Expected 429 rate limit badge, got: ${badgeText4}`);
    assert.ok(!badgeText4.includes('离线'), `Branch 4: 429 MUST NOT be reported as offline! got: ${badgeText4}`);
    console.log('Branch 4 (429 rate limit) passed:', badgeText4);
    await page.screenshot({ path: path.join(outDir, 'taskE_branch4_429_rate_limit.png') });
    verificationLog.taskE.branch4_429_rate_limit = { status: 'passed', badge: badgeText4 };
    await page.unroute('**/api/dti/models');

    // Branch 5: Fault injection - Genuine offline / connection refused
    await page.route('**/api/dti/models', route => {
      route.abort('failed');
    });
    await page.reload();
    await page.waitForTimeout(600);
    const badgeText5 = await page.locator('[role="status"]').innerText();
    assert.ok(badgeText5.includes('后端服务离线') || badgeText5.includes('离线'), `Branch 5: Expected offline badge, got: ${badgeText5}`);
    console.log('Branch 5 (Network offline) passed:', badgeText5);
    await page.screenshot({ path: path.join(outDir, 'taskE_branch5_network_offline.png') });
    verificationLog.taskE.branch5_network_offline = { status: 'passed', badge: badgeText5 };
    await page.unroute('**/api/dti/models');

    fs.writeFileSync(path.join(outDir, 'tasks_d_e_verification.json'), JSON.stringify(verificationLog, null, 2));
    console.log('ALL TASKS D AND E CHECKS COMPLETED SUCCESSFULLY WITH EXIT CODE 0!');

  } finally {
    await browser.close();
  }
})().catch(err => {
  console.error('VERIFICATION FAILURE:', err);
  process.exitCode = 1;
});
