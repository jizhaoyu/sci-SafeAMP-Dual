const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  // UI checks use deterministic local catalog fixtures; no scientific inference is run.
  await page.route(/^http:\/\/127\.0\.0\.1:5173\/api\//, route => {
    const url = new URL(route.request().url());
    const payload = url.pathname.endsWith('/drugs')
      ? [{ id: '1', name: 'Dasatinib', smiles: 'CCO', fold: 1, is_test: false }]
      : url.pathname.endsWith('/targets')
        ? [{ id: 'ABL1', sequence: 'ACDEFGHIKLMNPQRSTVWY'.repeat(12), length: 240, fold: 1, is_test: false }]
        : url.pathname.endsWith('/models')
          ? [{ id: 'worldmodel_stacked_ensemble', name: 'WorldModel', is_recommended: true, train_ci: 0.865 }]
          : null;
    return route.fulfill({ status: payload ? 200 : 503, contentType: 'application/json', body: JSON.stringify(payload || { message: 'UI fixture: service unavailable' }) });
  });
  const directory = path.resolve(__dirname, '../../output/ui-usability');
  fs.mkdirSync(directory, { recursive: true });
  try {
    await page.goto('http://127.0.0.1:5173');
    const smiles = page.getByRole('textbox', { name: '分子 SMILES', exact: true });
    await smiles.waitFor();
    const tools = page.locator('details').filter({ hasText: '更多研究工具' });
    assert.equal(await tools.getAttribute('open'), null);
    await tools.locator('summary').click();
    await page.getByRole('button', { name: /超大虚拟海选/ }).waitFor();
    await tools.locator('summary').click();
    await page.getByRole('link', { name: '填写分子', exact: true }).click();
    await smiles.fill('CCN');
    await page.getByRole('link', { name: '选择靶点', exact: true }).click();
    await page.getByRole('textbox', { name: '靶点氨基酸序列', exact: true }).fill('ACDEFGHIKLMNPQRSTVWY'.repeat(12));
    await page.getByRole('link', { name: '查看结果', exact: true }).click();
    assert.equal(await smiles.inputValue(), 'CCN', 'Section navigation must retain edits');
    await page.getByRole('textbox', { name: '搜索药物' }).fill('not-in-catalog');
    await page.getByText('未找到匹配的小分子药物', { exact: true }).waitFor({ state: 'attached' });
    await page.getByRole('button', { name: '清空', exact: true }).first().click();
    await page.setViewportSize({ width: 1440, height: 960 });
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: path.join(directory, 'overview.png') });
    await page.getByRole('button', { name: '开始预测', exact: true }).first().click();
    await page.getByRole('alert').waitFor();
    for (const width of [375, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: 960 });
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForTimeout(150);
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), `Horizontal overflow at ${width}px`);
      await page.screenshot({ path: path.join(directory, `light-${width}.png`), fullPage: true });
    }
    await page.getByRole('button', { name: '切换日间/夜间模式', exact: true }).click();
    assert(await page.locator('html').evaluate(el => el.classList.contains('dark')));
    await page.screenshot({ path: path.join(directory, 'dark-1440.png'), fullPage: true });
    await page.getByRole('link', { name: /先导分子优化/ }).click();
    await page.waitForURL('**/evolution');
    assert.equal(errors.length, 0, errors.join('\n'));
    console.log('PASS: section navigation, retained input, filtering, prediction error feedback, 4 viewport widths, theme and optimizer navigation');
  } catch (error) {
    console.error('Runtime errors:', errors);
    console.error((await page.locator('body').innerText()).slice(-1200));
    await page.screenshot({ path: path.join(directory, 'failure.png'), fullPage: true });
    throw error;
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
