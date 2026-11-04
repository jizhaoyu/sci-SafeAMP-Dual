const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const outDir = path.resolve(__dirname, '../../output/gemini-fix-verification');
const legacyDir = path.resolve(__dirname, '../../output/function-audit-20261008');
fs.mkdirSync(outDir, { recursive: true });
fs.mkdirSync(legacyDir, { recursive: true });

const EXPECTED_PRESETS = [
  {
    name: '达沙替尼',
    labelMatch: /达沙替尼 → ABL1p/,
    expectedTargetId: 'ABL1p',
    isAvailable: true,
  },
  {
    name: '普纳替尼',
    labelMatch: /普纳替尼 → ABL1-T315I/,
    expectedTargetId: '',
    isAvailable: false,
    reasonMatch: /未包含 ABL1-T315I|未收录/,
  },
  {
    name: '奥希替尼',
    labelMatch: /奥希替尼 → EGFR-T790M/,
    expectedTargetId: 'EGFR(T790M)',
    isAvailable: true,
  },
  {
    name: '吉非替尼',
    labelMatch: /吉非替尼 → EGFR/,
    expectedTargetId: '',
    isAvailable: false,
    reasonMatch: /未收录野生型 EGFR|未收录/,
  },
  {
    name: '洛拉替尼',
    labelMatch: /洛拉替尼 → ALK-G1202R/,
    expectedTargetId: '',
    isAvailable: false,
    reasonMatch: /未收录 ALK-G1202R|未收录/,
  },
  {
    name: '吡妥布替尼',
    labelMatch: /吡妥布替尼 → BTK-C481S/,
    expectedTargetId: '',
    isAvailable: false,
    reasonMatch: /未收录 BTK-C481S|未收录/,
  },
  {
    name: '维莫非尼',
    labelMatch: /维莫非尼 → BRAF-V600E/,
    expectedTargetId: 'BRAF(V600E)',
    isAvailable: true,
  },
  {
    name: '帕博西尼',
    labelMatch: /帕博西尼 → CDK4/,
    expectedTargetId: 'CDK4-cyclinD3',
    isAvailable: true,
  },
];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const presetResults = [];

  try {
    console.log('--- Step 1: Auditing 8 Clinical / Benchmark Presets on Home Page ---');
    await page.goto('http://127.0.0.1:5173');
    await page.waitForFunction(() => document.querySelector('textarea')?.value.length > 0);

    // Expand all 8 presets
    const expandBtn = page.getByRole('button', { name: '浏览全部 8 款经典对', exact: true });
    await expandBtn.waitFor({ state: 'visible' });
    await expandBtn.click();

    for (const item of EXPECTED_PRESETS) {
      console.log(`Checking preset: ${item.name} (expected available: ${item.isAvailable})...`);
      
      // Before clicking, record previous state
      const prevSequence = await page.getByRole('textbox', { name: '靶点氨基酸序列' }).inputValue();

      // Click the preset button
      const presetBtn = page.locator('button').filter({ hasText: item.labelMatch }).first();
      await presetBtn.waitFor({ state: 'visible' });
      await presetBtn.click();

      // Give state time to settle
      await page.waitForTimeout(300);

      const actualSmiles = await page.getByRole('textbox', { name: '分子 SMILES' }).inputValue();
      const actualSequence = await page.getByRole('textbox', { name: '靶点氨基酸序列' }).inputValue();
      const actualTargetId = await page.getByRole('combobox', { name: '选择基准靶点' }).inputValue();

      assert.ok(actualSmiles.length > 0, `Preset ${item.name} must populate drug SMILES`);

      if (item.isAvailable) {
        // Assert sequence is populated
        assert.ok(actualSequence.length > 10, `Preset ${item.name} must populate a valid kinase sequence (>10 aa)`);
        // Assert selected target matches expected benchmark ID exactly
        assert.equal(actualTargetId, item.expectedTargetId, `Preset ${item.name} target ID mismatch: expected ${item.expectedTargetId}, got ${actualTargetId}`);
        presetResults.push({
          name: item.name,
          isAvailable: true,
          targetId: actualTargetId,
          sequenceLength: actualSequence.length,
          status: 'passed',
        });
      } else {
        // Assert sequence is CLEARED (not retaining old sequence!)
        assert.equal(actualSequence, '', `Preset ${item.name} is unavailable and MUST clear sequence, but got length ${actualSequence.length}`);
        // Assert target combobox is custom or empty
        assert.ok(actualTargetId === 'custom' || actualTargetId === '', `Preset ${item.name} target ID should be custom or empty, got ${actualTargetId}`);
        
        // Assert alert / error message explains why it cannot run
        const alertText = await page.locator('[role="alert"]').innerText().catch(() => '');
        assert.ok(item.reasonMatch.test(alertText), `Preset ${item.name} alert must explain why it is unavailable, got: ${alertText}`);

        presetResults.push({
          name: item.name,
          isAvailable: false,
          targetId: actualTargetId,
          sequenceLength: 0,
          reason: alertText,
          status: 'passed',
        });
      }
    }

    console.log('--- Step 2: Testing Sequence Clearing When Switching From Available to Unavailable ---');
    // Select Dasatinib (available) first
    await page.locator('button').filter({ hasText: /达沙替尼 → ABL1p/ }).first().click();
    await page.waitForTimeout(300);
    const dasatinibSeq = await page.getByRole('textbox', { name: '靶点氨基酸序列' }).inputValue();
    assert.ok(dasatinibSeq.length > 0, 'Dasatinib must populate sequence');

    // Now select Ponatinib (unavailable)
    await page.locator('button').filter({ hasText: /普纳替尼 → ABL1-T315I/ }).first().click();
    await page.waitForTimeout(300);
    const ponatinibSeq = await page.getByRole('textbox', { name: '靶点氨基酸序列' }).inputValue();
    assert.equal(ponatinibSeq, '', 'Switching to Ponatinib (ABL1-T315I) MUST clear sequence rather than retaining Dasatinib ABL1p sequence!');
    console.log('Sequence clearing verified: sequence was properly cleared to empty string.');

    console.log('--- Step 3: Evolution Page & Cart CSV Export ---');
    await page.goto('http://127.0.0.1:5173/evolution');
    await page.waitForTimeout(500);
    await page.getByRole('button', { name: /达沙替尼 \(Dasatinib\) → ABL1/ }).click();
    await page.getByRole('button', { name: /开始智能改构与贝叶斯主动学习评估/ }).click();
    
    const saveBtn = page.getByRole('button', { name: '存入分子库', exact: true }).first();
    await saveBtn.waitFor({ state: 'visible', timeout: 15000 });
    await saveBtn.click();

    await page.getByRole('button', { name: /分子库/ }).first().click();
    const downloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: /导出为 CSV/ }).click();
    const download = await downloadPromise;
    const filename = download.suggestedFilename();
    assert.ok(filename.endsWith('.csv'), `Cart export filename must end with .csv, got ${filename}`);

    const outputPayload = {
      timestamp: new Date().toISOString(),
      presets: presetResults,
      cart_csv_download: filename,
      allPassed: true,
    };

    fs.writeFileSync(path.join(outDir, 'preset-audit-results.json'), JSON.stringify(outputPayload, null, 2));
    fs.writeFileSync(path.join(legacyDir, 'preset-and-cart.json'), JSON.stringify(outputPayload, null, 2));

    console.log('ALL PRESET AND CART TESTS PASSED! Output written to output directories.');
  } finally {
    await browser.close();
  }
})().catch(err => {
  console.error('AUDIT FAILURE:', err);
  process.exitCode = 1;
});
