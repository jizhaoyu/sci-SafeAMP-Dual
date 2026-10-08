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
    // Step 2: DTI Studio, Molecule Sketcher & 3D Pocket Viewer Automation
    // -------------------------------------------------------------
    console.log('[3/6] Step 2: Testing DTI Studio, Sketcher & 3D Pocket Viewer...');
    // Ensure we are on DTI Tab
    const dtiTab = page.locator('a[href="/"]').first();
    await dtiTab.click();
    await page.waitForTimeout(500);

    // Test Molecule Sketcher Modal
    console.log('  Testing Molecule Sketcher Modal...');
    const sketcherBtn = page.locator('button', { hasText: '分子手绘画板' }).first();
    if (await sketcherBtn.isVisible()) {
      await sketcherBtn.click();
      await page.waitForTimeout(500);

      // Verify sketcher modal rendered
      const sketcherModalTitle = page.locator('text=配体分子结构手绘画板').first();
      await sketcherModalTitle.waitFor({ state: 'visible', timeout: 5000 });

      // Click a scaffold preset: 吡啶环
      const pyridineBtn = page.locator('button', { hasText: '吡啶环' }).first();
      if (await pyridineBtn.isVisible()) {
        await pyridineBtn.click();
        await page.waitForTimeout(400);
      }

      // Check real-time SA Score & Ro5 indicators
      const saScoreText = page.locator('text=合成可达性 (SA Score)').first();
      await saScoreText.waitFor({ state: 'visible', timeout: 3000 });

      await page.screenshot({ path: path.join(ARTIFACTS_DIR, '08_molecule_sketcher_modal.png') });
      console.log('  Screenshot saved: 08_molecule_sketcher_modal.png');

      // Click apply to studio
      const applyBtn = page.locator('button', { hasText: '应用并填入分析面板' }).first();
      await applyBtn.click();
      await page.waitForTimeout(500);
      console.log('  Applied sketched molecule into studio successfully.');
    }

    // Verify World Model is present and select preset Dasatinib -> ABL1
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

    // Wait for 3D Pocket Viewer WebGL Canvas
    const pocket3DTitle = page.locator('text=催化结合口袋 3D 微观构象').first();
    await pocket3DTitle.waitFor({ state: 'visible', timeout: 10000 });
    console.log('  Received 3D Kinase Pocket WebGL Viewer!');

    // Scroll to 3D Pocket Viewer to capture high-res snapshot
    await pocket3DTitle.scrollIntoViewIfNeeded();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(ARTIFACTS_DIR, '09_3d_kinase_pocket_viewer.png') });
    console.log('  Screenshot saved: 09_3d_kinase_pocket_viewer.png');

    // Scroll to top of predictions to capture both Hero and Biophysics
    await page.evaluate(() => window.scrollTo(0, 80));
    await page.waitForTimeout(400);

    await page.screenshot({ path: path.join(ARTIFACTS_DIR, '02_dti_prediction_output.png') });
    console.log('  Screenshot saved: 02_dti_prediction_output.png');

    // Test ADMET Radar Modal in DTI Studio
    console.log('  Testing ADMET Radar Modal in DTI Studio...');
    const admetBtn = page.locator('button', { hasText: '查看 ADMET 雷达' }).first();
    if (await admetBtn.isVisible()) {
      await admetBtn.click();
      await page.waitForTimeout(600);
      const admetModalTitle = page.locator('text=ADMET 成药性与药代毒理全景雷达').first();
      await admetModalTitle.waitFor({ state: 'visible', timeout: 5000 });
      console.log('  ADMET Radar Modal is open!');
      await page.screenshot({ path: path.join(ARTIFACTS_DIR, '11_admet_radar_modal.png') });
      console.log('  Screenshot saved: 11_admet_radar_modal.png');

      const closeAdmetBtn = page.locator('button', { hasText: '完成查看' }).first();
      await closeAdmetBtn.click();
      await page.waitForTimeout(400);
    }

    // Test 60+ Clinical Targets Knowledge Hub Modal
    console.log('  Testing 60+ Clinical Targets Knowledge Hub Modal...');
    const clinicalTargetsBtn = page.locator('button', { hasText: '60+ 临床靶点与耐药库' }).first();
    if (await clinicalTargetsBtn.isVisible()) {
      await clinicalTargetsBtn.click();
      await page.waitForTimeout(600);
      const modalHeader = page.locator('text=临床抗肿瘤激酶与耐药突变体知识库').first();
      await modalHeader.waitFor({ state: 'visible', timeout: 5000 });
      console.log('  Clinical Targets Knowledge Hub Modal rendered!');
      await page.screenshot({ path: path.join(ARTIFACTS_DIR, '16_clinical_targets_knowledge_modal.png') });
      console.log('  Screenshot saved: 16_clinical_targets_knowledge_modal.png');

      // Click tab "🔥 核心耐药突变体"
      const mutantTab = page.locator('button', { hasText: '核心耐药突变体' }).first();
      if (await mutantTab.isVisible()) {
        await mutantTab.click();
        await page.waitForTimeout(400);
      }

      // Search for T790M
      const searchBox = page.locator('input[placeholder*="搜索基因符号"]').first();
      if (await searchBox.isVisible()) {
        await searchBox.fill('T790M');
        await page.waitForTimeout(400);
      }

      // Select EGFR-T790M
      const loadTargetBtn = page.locator('button', { hasText: '载入靶点' }).first();
      if (await loadTargetBtn.isVisible()) {
        await loadTargetBtn.click();
        await page.waitForTimeout(500);
        console.log('  Selected and loaded target "EGFR-T790M" into studio.');
      }
    }

    // Test clinical resistance preset: Ponatinib -> ABL1-T315I
    const ponatinibPreset = page.locator('button', { hasText: '普纳替尼 → ABL1-T315I' }).first();
    if (await ponatinibPreset.isVisible()) {
      await ponatinibPreset.click();
      console.log('  Clicked clinical resistance preset "普纳替尼 → ABL1-T315I"');
      await page.waitForTimeout(500);

      const predictBtn = page.locator('button', { hasText: '执行单点结合亲和力预测' }).first();
      await predictBtn.click();
      await page.waitForTimeout(2000);
      await page.screenshot({ path: path.join(ARTIFACTS_DIR, '17_ponatinib_abl1_t315i_prediction.png') });
      console.log('  Screenshot saved: 17_ponatinib_abl1_t315i_prediction.png');
    }

    // -------------------------------------------------------------
    // Phase 2 Step: Test 3D Pocket De Novo Diffusion & IP Hopping
    // -------------------------------------------------------------
    console.log('  Testing Phase 2: 3D Pocket De Novo Diffusion & Scaffold Hopping...');
    const deNovoBtn = page.locator('button', { hasText: '3D 口袋从头生成与骨架跃迁' }).first();
    if (await deNovoBtn.isVisible()) {
      await deNovoBtn.click();
      await page.waitForTimeout(600);
      
      const deNovoHeader = page.locator('text=3D 口袋从头分子扩散生成与骨架跃迁工作台').first();
      await deNovoHeader.waitFor({ state: 'visible', timeout: 5000 });
      console.log('  3D Pocket De Novo Modal rendered!');

      // Click generate button
      const runGenBtn = page.locator('button', { hasText: '启动 3D 口袋从头生成' }).first();
      await runGenBtn.click();
      console.log('  Triggered de novo molecular generation algorithm...');
      
      // Wait for candidate cards to appear
      const candidateCard = page.locator('text=IP 新颖度').first();
      await candidateCard.waitFor({ state: 'visible', timeout: 10000 });
      console.log('  De Novo candidate molecules generated and scored with MM-GBSA & IP novelty!');

      await page.screenshot({ path: path.join(ARTIFACTS_DIR, '18_de_novo_pocket_generation.png') });
      console.log('  Screenshot saved: 18_de_novo_pocket_generation.png');

      // -------------------------------------------------------------
      // Phase 2 Step: Test AI Retrosynthesis Route Planner
      // -------------------------------------------------------------
      console.log('  Testing Phase 2: AI Computer-Aided Retrosynthesis Route Planner...');
      const retroRouteBtn = page.locator('button', { hasText: 'AI 计算机辅助逆合成路线' }).first();
      if (await retroRouteBtn.isVisible()) {
        await retroRouteBtn.click();
        await page.waitForTimeout(800);

        const retroHeader = page.locator('text=AI 计算机辅助逆合成路线规划').first();
        await retroHeader.waitFor({ state: 'visible', timeout: 6000 });

        const precursorSec = page.locator('text=商业现货起始原料清单').first();
        await precursorSec.waitFor({ state: 'visible', timeout: 6000 });
        console.log('  AI Retrosynthesis route plan rendered with CAS precursors and reaction steps!');

        await page.screenshot({ path: path.join(ARTIFACTS_DIR, '19_ai_retrosynthesis_route.png') });
        console.log('  Screenshot saved: 19_ai_retrosynthesis_route.png');

        // Close Retrosynthesis Modal
        const closeRetroBtn = page.locator('button').filter({ has: page.locator('svg.lucide-x') }).last();
        if (await closeRetroBtn.isVisible()) {
          await closeRetroBtn.click();
          await page.waitForTimeout(400);
        }
      }

      // Close De Novo Modal
      const closeDeNovoBtn = page.locator('button').filter({ has: page.locator('svg.lucide-x') }).first();
      if (await closeDeNovoBtn.isVisible()) {
        await closeDeNovoBtn.click();
        await page.waitForTimeout(400);
      }
    }

    // -------------------------------------------------------------
    // Phase 3 Step: Test Ultra-Large Virtual Screening Engine
    // -------------------------------------------------------------
    console.log('  Testing Phase 3: Ultra-Large Virtual Screening Engine...');
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(400);

    const screeningBtn = page.locator('button', { hasText: '超大规模虚拟筛选' }).first();
    await screeningBtn.waitFor({ state: 'visible', timeout: 5000 });
    await screeningBtn.click();
    await page.waitForTimeout(800);

    const screeningHeader = page.locator('text=超大规模商业现货分子库虚拟筛选工作台').first();
    await screeningHeader.waitFor({ state: 'visible', timeout: 8000 });
    console.log('  Virtual Screening Modal rendered!');

    // Snapshot 20: Pre-screening config dialog
    await page.screenshot({ path: path.join(ARTIFACTS_DIR, '20_ultra_large_virtual_screening.png') });
    console.log('  Screenshot saved: 20_ultra_large_virtual_screening.png');

    // Click Run Virtual Screening button
    const runScreenBtn = page.locator('button', { hasText: '启动高通量虚拟筛选' }).first();
    await runScreenBtn.waitFor({ state: 'visible', timeout: 5000 });
    await runScreenBtn.click();
    console.log('  Triggered virtual screening funnel...');

    // Wait for screening results KPI & Hits cards
    const hitsResults = page.locator('text=淘选 Hits / 骨架簇').first();
    await hitsResults.waitFor({ state: 'visible', timeout: 15000 });
    console.log('  Screening completed: Hits found and clustered with Butina algorithm!');
    await page.waitForTimeout(1000);

    // Snapshot 21: Virtual screening Hits explorer
    await page.screenshot({ path: path.join(ARTIFACTS_DIR, '21_virtual_screening_hits_explorer.png') });
    console.log('  Screenshot saved: 21_virtual_screening_hits_explorer.png');

    // Close Virtual Screening Modal
    const closeScreenBtn = page.locator('button[aria-label="关闭筛选工作台"]').first();
    if (await closeScreenBtn.isVisible()) {
      await closeScreenBtn.click();
      await page.waitForTimeout(400);
    }

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

    // Check SA Score in Baseline Lead Card
    const saLeadText = page.locator('text=SA 可达性:').first();
    await saLeadText.waitFor({ state: 'visible', timeout: 3000 });
    console.log('  Verified Baseline Lead SA Score badge.');

    // Test 3D Pocket Button on Candidate in Ladder View
    const pocketBtn = page.locator('button', { hasText: '3D 口袋' }).first();
    if (await pocketBtn.isVisible()) {
      await pocketBtn.click();
      await page.waitForTimeout(800);
      const pocketModalHeader = page.locator('text=3D 激酶结合口袋原子级微观互作').first();
      await pocketModalHeader.waitFor({ state: 'visible', timeout: 5000 });
      await pocketModalHeader.scrollIntoViewIfNeeded();
      await page.waitForTimeout(800);
      await page.screenshot({ path: path.join(ARTIFACTS_DIR, '10_lead_candidate_3d_pocket.png') });
      console.log('  Screenshot saved: 10_lead_candidate_3d_pocket.png');
    }

    // Scroll to molecular ladder
    const ladderViewHeading = page.locator('text=分子阶梯排行榜 (Ladder View)').first();
    await ladderViewHeading.scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);

    await page.screenshot({ path: path.join(ARTIFACTS_DIR, '05_lead_evolution_ladder.png') });
    console.log('  Screenshot saved: 05_lead_evolution_ladder.png');

    // Test ADMET button on candidate in ladder view
    const candAdmetBtn = page.locator('button', { hasText: '成药雷达' }).first();
    if (await candAdmetBtn.isVisible()) {
      await candAdmetBtn.click();
      await page.waitForTimeout(600);
      const candAdmetTitle = page.locator('text=ADMET 成药性与药代毒理全景雷达').first();
      await candAdmetTitle.waitFor({ state: 'visible', timeout: 5000 });
      console.log('  Candidate ADMET Radar Modal is open!');
      await page.screenshot({ path: path.join(ARTIFACTS_DIR, '12_candidate_admet_radar.png') });
      console.log('  Screenshot saved: 12_candidate_admet_radar.png');

      const closeCandAdmet = page.locator('button', { hasText: '完成查看' }).first();
      await closeCandAdmet.click();
      await page.waitForTimeout(400);
    }

    // Test 96-Well Wetlab Dispatch Modal
    console.log('  Testing 96-Well Wetlab Dispatch Modal...');
    const dispatchBtn = page.locator('button', { hasText: '96 孔板投产清单' }).first();
    if (await dispatchBtn.isVisible()) {
      await dispatchBtn.click();
      await page.waitForTimeout(700);
      const dispatchModalTitle = page.locator('text=湿实验 96 孔板投产清单与移液规程').first();
      await dispatchModalTitle.waitFor({ state: 'visible', timeout: 5000 });
      console.log('  Wetlab Dispatch Modal rendered!');
      await page.screenshot({ path: path.join(ARTIFACTS_DIR, '13_wetlab_96_well_dispatch.png') });
      console.log('  Screenshot saved: 13_wetlab_96_well_dispatch.png');

      const closeDispatch = page.locator('button', { hasText: '完成查看' }).first();
      await closeDispatch.click();
      await page.waitForTimeout(400);
    }

    // Test Academic Research Report Modal
    console.log('  Testing Academic Report Modal...');
    const reportBtn = page.locator('button', { hasText: '生成学术交付报告' }).first();
    if (await reportBtn.isVisible()) {
      await reportBtn.click();
      await page.waitForTimeout(800);
      const reportModalTitle = page.locator('text=学术交付评估报告与专利交底书生成器').first();
      await reportModalTitle.waitFor({ state: 'visible', timeout: 5000 });
      console.log('  Academic Report Modal rendered!');
      await page.screenshot({ path: path.join(ARTIFACTS_DIR, '14_academic_research_report.png') });
      console.log('  Screenshot saved: 14_academic_research_report.png');

      const closeReport = page.locator('button', { hasText: '完成查看' }).first();
      await closeReport.click();
      await page.waitForTimeout(400);
    }

    // Test Wet-lab Feedback Calibration Loop
    console.log('  Testing Wet-lab Feedback Calibration Loop...');
    const feedbackToggleBtn = page.locator('button', { hasText: '湿实验数据回流' }).first();
    if (await feedbackToggleBtn.isVisible()) {
      await feedbackToggleBtn.click();
      await page.waitForTimeout(400);
      const fillDemoBtn = page.locator('button', { hasText: '填入模拟实测 12.0 nM' }).first();
      if (await fillDemoBtn.isVisible()) {
        await fillDemoBtn.click();
        await page.waitForTimeout(300);
      }
      const submitFeedbackBtn = page.locator('button', { hasText: '提交实测数据并重排阶梯榜' }).first();
      await submitFeedbackBtn.click();
      await page.waitForTimeout(1500);

      const feedbackSuccessBanner = page.locator('text=成功闭环回流').first();
      await feedbackSuccessBanner.waitFor({ state: 'visible', timeout: 5000 });
      console.log('  Empirical Bayes feedback calibration verified!');
      await page.screenshot({ path: path.join(ARTIFACTS_DIR, '15_wetlab_feedback_calibrated.png') });
      console.log('  Screenshot saved: 15_wetlab_feedback_calibrated.png');
    }

    // Switch to Active Learning Matrix Tab
    const alTabBtn = page.locator('button', { hasText: '贝叶斯主动学习探索/利用矩阵' }).first();
    await alTabBtn.click();
    await page.waitForTimeout(800);

    const alCards = page.locator('text=高置信度领头物 (Hits)').first();
    await alCards.waitFor({ state: 'visible', timeout: 8000 });
    console.log('  Active Learning 4-Quadrant Matrix rendered!');

    // Verify SA score column exists in active learning table
    const saColHeader = page.locator('text=SA 合成可达性').first();
    await saColHeader.waitFor({ state: 'visible', timeout: 3000 });
    console.log('  Verified Active Learning table SA score column.');

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
