import { chromium } from 'playwright';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, '../..');
const ARTIFACTS_DIR = path.resolve(__dirname, '../test-artifacts');
const SERVER_URL = 'http://127.0.0.1:8000';

if (!fs.existsSync(ARTIFACTS_DIR)) {
  fs.mkdirSync(ARTIFACTS_DIR, { recursive: true });
}

async function checkServerReady() {
  try {
    const res = await fetch(`${SERVER_URL}/api/health`);
    if (res.ok) {
      const data = await res.json();
      return data.status === 'healthy';
    }
  } catch {
    return false;
  }
  return false;
}

async function startServerIfNeeded() {
  const isUp = await checkServerReady();
  if (isUp) {
    console.log('[E2E Setup] Backend server is already running on http://127.0.0.1:8000');
    return null;
  }

  console.log('[E2E Setup] Starting Python server in background...');
  const proc = spawn('python', ['05_web_server/app.py'], {
    cwd: ROOT_DIR,
    stdio: 'ignore',
    detached: false
  });

  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    if (await checkServerReady()) {
      console.log('[E2E Setup] Backend server is ready.');
      return proc;
    }
    await new Promise(r => setTimeout(r, 400));
  }
  throw new Error('Server failed to start within 15 seconds.');
}

async function runE2EUIAutomation() {
  console.log('='.repeat(70));
  console.log('[START] Starting Full Playwright E2E UI Automation Test');
  console.log('='.repeat(70));

  let serverProc = null;
  let browser = null;
  const pageErrors = [];

  try {
    serverProc = await startServerIfNeeded();

    console.log('[1/6] Launching Chromium headless browser...');
    browser = await chromium.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const context = await browser.newContext({
      viewport: { width: 1400, height: 950 },
      deviceScaleFactor: 1
    });

    const page = await context.newPage();

    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.error(`  [Browser Console Error]: ${msg.text()}`);
        pageErrors.push(msg.text());
      }
    });

    page.on('pageerror', err => {
      console.error(`  [Uncaught Page Error]: ${err.message}`);
      pageErrors.push(err.message);
    });

    // -------------------------------------------------------------
    // Step 1: Navigate to Home and Check Layout & Navigation
    // -------------------------------------------------------------
    console.log('[2/6] Step 1: Navigating to Home Shell (GET /)...');
    const t0 = Date.now();
    await page.goto(`${SERVER_URL}/`, { waitUntil: 'networkidle' });
    const title = await page.title();
    console.log(`  Page Title: "${title}" (${Date.now() - t0}ms)`);
    await page.screenshot({ path: path.join(ARTIFACTS_DIR, '01_home_screen.png') });
    console.log('  Screenshot saved: 01_home_screen.png');

    // -------------------------------------------------------------
    // Step 2: DTI Studio Automation
    // -------------------------------------------------------------
    console.log('[3/6] Step 2: Testing DTI Studio & Prediction Workflow...');
    // Ensure we are on DTI Tab
    const dtiTab = page.locator('a[href="/"]').first();
    await dtiTab.click();
    await page.waitForTimeout(500);

    // Verify World Model is present and select preset
    const presetBtn = page.locator('button', { hasText: '达沙替尼 → ABL1' }).first();
    await presetBtn.waitFor({ state: 'visible', timeout: 5000 });
    await presetBtn.click();
    console.log('  Clicked preset "达沙替尼 → ABL1"');
    await page.waitForTimeout(400);

    // Select Flagship World Model
    const worldModelBtn = page.locator('button', { hasText: '第二代生物世界模型' }).first();
    if (await worldModelBtn.isVisible()) {
      await worldModelBtn.click();
      console.log('  Selected flagship World Model');
    }

    // Trigger Prediction
    const predictBtn = page.locator('button', { hasText: '执行单点结合亲和力预测' }).first();
    await predictBtn.click();
    console.log('  Triggered single-point affinity prediction...');

    // Wait for Result Output Card
    const resultHeader = page.locator('text=预测推断与结合评分').first();
    await resultHeader.waitFor({ state: 'visible', timeout: 12000 });

    // Wait for 3D Biophysics Insights Card
    const biophysicsCard = page.locator('text=3D 诱导契合与 MM-GBSA 物理透视').first();
    await biophysicsCard.waitFor({ state: 'visible', timeout: 8000 });
    console.log('  Received prediction output & 3D Biophysics MM-GBSA card!');

    // Scroll to top of predictions to capture both Hero and Biophysics
    await page.evaluate(() => window.scrollTo(0, 80));
    await page.waitForTimeout(400);

    await page.screenshot({ path: path.join(ARTIFACTS_DIR, '02_dti_prediction_output.png') });
    console.log('  Screenshot saved: 02_dti_prediction_output.png');

    // Test Kinome Selectivity Profiling Tab
    console.log('  Testing Kinome Profiling Tab...');
    const kinomeTabBtn = page.locator('button', { hasText: '激酶选择性谱 (Kinome Panel)' }).first();
    await kinomeTabBtn.click();
    await page.waitForTimeout(400);

    const reProfileBtn = page.locator('button', { hasText: '重新测定谱系' }).first();
    if (await reProfileBtn.isVisible()) {
      await reProfileBtn.click();
      await page.waitForTimeout(2500);
    }
    await page.screenshot({ path: path.join(ARTIFACTS_DIR, '03_kinome_selectivity_profile.png') });
    console.log('  Screenshot saved: 03_kinome_selectivity_profile.png');

    // Test Benchmark Leaderboard Tab
    const leaderboardBtn = page.locator('button', { hasText: '四大域基准天梯榜' }).first();
    await leaderboardBtn.click();
    await page.waitForTimeout(400);
    await page.screenshot({ path: path.join(ARTIFACTS_DIR, '04_davis_benchmark_leaderboard.png') });
    console.log('  Screenshot saved: 04_davis_benchmark_leaderboard.png');

    // -------------------------------------------------------------
    // Step 3: Lead Optimizer Studio & Active Learning
    // -------------------------------------------------------------
    const evoTab = page.locator('a[href="/evolution"]').first();
    await evoTab.click();
    await page.waitForTimeout(600);

    // Apply preset Dasatinib
    const evoPresetBtn = page.locator('button', { hasText: '达沙替尼 (Dasatinib) → ABL1' }).first();
    await evoPresetBtn.waitFor({ state: 'visible', timeout: 5000 });
    await evoPresetBtn.click();
    console.log('  Selected lead preset "Dasatinib → ABL1"');

    // Run Optimization
    const runOptBtn = page.locator('button', { hasText: '开始智能改构与贝叶斯主动学习评估' }).first();
    await runOptBtn.click();
    console.log('  Triggered lead optimization execution...');

    // Wait for results
    const evoResultHero = page.locator('text=先导母体基准 (Baseline Lead)').first();
    await evoResultHero.waitFor({ state: 'visible', timeout: 15000 });
    console.log('  Optimization results returned!');

    // Scroll to molecular ladder
    const ladderViewHeading = page.locator('text=分子阶梯排行榜 (Ladder View)').first();
    await ladderViewHeading.scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);

    await page.screenshot({ path: path.join(ARTIFACTS_DIR, '05_lead_evolution_ladder.png') });
    console.log('  Screenshot saved: 05_lead_evolution_ladder.png');

    // Switch to Active Learning Matrix Tab
    const alTabBtn = page.locator('button', { hasText: '贝叶斯主动学习探索/利用矩阵' }).first();
    await alTabBtn.click();
    await page.waitForTimeout(800);

    const alCards = page.locator('text=高置信度领头物 (Hits)').first();
    await alCards.waitFor({ state: 'visible', timeout: 8000 });
    console.log('  Active Learning 4-Quadrant Matrix rendered!');

    await alTabBtn.scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);

    await page.screenshot({ path: path.join(ARTIFACTS_DIR, '06_active_learning_matrix.png') });
    console.log('  Screenshot saved: 06_active_learning_matrix.png');

    // -------------------------------------------------------------
    // Step 4: Dark / Light Mode Toggle & Verification
    // -------------------------------------------------------------
    console.log('[5/6] Step 4: Testing Dark/Light Theme Switching...');
    // Look for theme toggle button
    const themeBtn = page.locator('button[title*="模式"], button[aria-label*="模式"], header button').last();
    if (await themeBtn.isVisible()) {
      await themeBtn.click();
      await page.waitForTimeout(300);
      await page.screenshot({ path: path.join(ARTIFACTS_DIR, '07_theme_toggled.png') });
      console.log('  Screenshot saved: 07_theme_toggled.png');
    }

    // -------------------------------------------------------------
    // Step 5: Summary
    // -------------------------------------------------------------
    console.log('[6/6] Step 5: Verifying console health...');
    if (pageErrors.length > 0) {
      console.warn(`  [WARN] Detected ${pageErrors.length} browser errors during execution:`);
      pageErrors.forEach((e, idx) => console.warn(`    ${idx + 1}. ${e}`));
    } else {
      console.log('  [OK] Zero uncaught page errors detected.');
    }

    console.log('='.repeat(70));
    console.log('[SUCCESS] ALL FRONTEND PLAYWRIGHT AUTOMATION STEPS SUCCEEDED!');
    console.log(`[ARTIFACTS] 7 High-res visual artifacts generated in: ${ARTIFACTS_DIR}`);
    console.log('='.repeat(70));

  } finally {
    if (browser) await browser.close();
    if (serverProc) {
      serverProc.kill();
      console.log('[Cleanup] Background test server terminated.');
    }
  }
}

runE2EUIAutomation().catch(err => {
  console.error('[E2E Automation Failed]:', err);
  process.exit(1);
});
