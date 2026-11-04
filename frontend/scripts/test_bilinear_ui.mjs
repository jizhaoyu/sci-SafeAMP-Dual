import { chromium } from 'playwright';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const OUTPUT_DIR = path.resolve(__dirname, '../../output/playwright');

if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

async function runBilinearUITest() {
  console.log('[Playwright] Launching browser...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  console.log('[Playwright] Navigating to http://127.0.0.1:18180/dti ...');
  await page.goto('http://127.0.0.1:18180/dti', { waitUntil: 'networkidle', timeout: 30000 });

  // 1. Wait for page title and main container
  await page.waitForSelector('text=AI药物靶点亲和力预测平台', { timeout: 15000 });
  console.log('[Playwright] DTI Studio loaded.');
  await page.waitForTimeout(1000);

  // 2. Expand model configuration
  const switchModelBtn = page.locator('button:has-text("切换对比模型")');
  await switchModelBtn.waitFor({ state: 'visible', timeout: 10000 });
  await switchModelBtn.click();
  console.log('[Playwright] Clicked "切换对比模型".');
  await page.waitForTimeout(800);

  // 3. Select Bilinear ESM-2 model
  const bilinearBtn = page.locator('button:has-text("Bilinear ESM-2")');
  await bilinearBtn.waitFor({ state: 'visible', timeout: 5000 });
  await bilinearBtn.click();
  console.log('[Playwright] Selected Bilinear ESM-2 model.');
  await page.waitForTimeout(800);

  // Take screenshot of model selection
  const modelScreenshot = path.join(OUTPUT_DIR, '01_bilinear_model_selected.png');
  await page.screenshot({ path: modelScreenshot, fullPage: false });
  console.log(`[Playwright] Model selection screenshot saved to ${modelScreenshot}`);

  // 4. Click "开始预测" (Predict affinity)
  const predictBtn = page.locator('#prediction-controls button:has-text("开始预测")');
  await predictBtn.click();
  console.log('[Playwright] Clicked "开始预测", waiting for result...');

  // Wait for result display
  await page.waitForSelector('text=预测推断与结合评分', { timeout: 15000 });
  await page.waitForTimeout(1000);

  // Take screenshot of prediction result
  const predScreenshot = path.join(OUTPUT_DIR, '02_bilinear_prediction_result.png');
  await page.screenshot({ path: predScreenshot, fullPage: false });
  console.log(`[Playwright] Prediction result screenshot saved to ${predScreenshot}`);

  // 5. Click "激酶谱选择性分析" (Profiling)
  const profileBtn = page.locator('#prediction-controls button:has-text("激酶谱选择性分析")');
  await profileBtn.click();
  console.log('[Playwright] Clicked "激酶谱选择性分析", waiting for profiling results...');

  // Wait for profiling tab active
  await page.waitForTimeout(3000);

  // Take screenshot of kinome profiling
  const profileScreenshot = path.join(OUTPUT_DIR, '03_bilinear_kinome_profile.png');
  await page.screenshot({ path: profileScreenshot, fullPage: false });
  console.log(`[Playwright] Kinome profiling screenshot saved to ${profileScreenshot}`);

  console.log('[Playwright] All UI tests completed successfully!');
  await browser.close();
}

runBilinearUITest().catch(err => {
  console.error('[Playwright Error]:', err);
  process.exit(1);
});
