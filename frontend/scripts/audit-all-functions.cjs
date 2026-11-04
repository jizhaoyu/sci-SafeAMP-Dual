const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const dir = path.resolve(__dirname, '../../output/function-audit-20261008');
fs.mkdirSync(dir, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, permissions: ['clipboard-read', 'clipboard-write'] });
  const page = await context.newPage();
  page.setDefaultTimeout(20000);
  const results = [], errors = [], responses = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('response', response => { if (response.url().includes('/api/')) responses.push({ path: new URL(response.url()).pathname, status: response.status() }); });
  async function check(name, run) {
    const start = Date.now(), offset = errors.length;
    try { await run(); assert.equal(errors.length, offset, errors.slice(offset).join('; ')); results.push({ name, status: 'passed', ms: Date.now()-start }); }
    catch(error) { results.push({ name, status: 'failed', message: error.message.slice(0,1800), ms: Date.now()-start }); }
    await page.screenshot({ path: path.join(dir, `${String(results.length).padStart(2,'0')}.png`) }).catch(()=>{});
    console.log(JSON.stringify(results.at(-1)));
    fs.writeFileSync(path.join(dir,'browser-results.json'), JSON.stringify({ results, errors, responses },null,2));
  }
  async function home() { await page.goto('http://127.0.0.1:5173/'); await page.getByRole('textbox',{name:'分子 SMILES',exact:true}).waitFor(); await page.waitForFunction(()=>document.querySelector('textarea').value.length>0); }
  async function advanced() { await home(); await page.locator('summary').filter({ hasText: '更多研究工具' }).click(); }
  try {
    await check('首页目录加载与步骤跳转', async()=> { await home(); assert(await page.locator('select').first().locator('option').count()>=68); await page.getByRole('link',{name:'选择靶点',exact:true}).click(); assert.equal(await page.getByRole('textbox',{name:'靶点氨基酸序列'}).inputValue() !== '', true); });
    await check('分子画板：骨架选择并回填', async()=> { await home(); await page.getByRole('button',{name:'分子手绘画板',exact:true}).click(); await page.getByRole('button',{name:/吡啶环/}).click(); await page.getByRole('button',{name:'应用并填入分析面板',exact:true}).click(); assert.equal(await page.getByRole('textbox',{name:'分子 SMILES'}).inputValue(),'c1ccncc1'); });
    await check('单点预测与物理分析', async()=> { await home(); await page.getByRole('button',{name:'仅载入',exact:true}).first().click(); await page.getByRole('button',{name:'开始预测',exact:true}).first().click(); await page.getByText('预测推断与结合评分 (Affinity Output)',{exact:true}).waitFor(); await page.getByText(/3D 诱导契合与 MM-GBSA/).first().waitFor(); });
    await check('3D口袋请求与可视化画布', async()=> { await page.getByText(/催化结合口袋 3D 微观构象/).first().waitFor(); await page.locator('canvas').first().waitFor(); });
    await check('ADMET雷达', async()=> { await home(); await page.getByRole('button',{name:'ADMET 雷达',exact:true}).click(); await page.getByText('ADMET 成药性与药代毒理全景雷达',{exact:true}).waitFor(); await page.getByRole('button',{name:'完成查看',exact:true}).waitFor(); });
    await check('临床靶点库：搜索与回填', async()=> { await advanced(); await page.getByRole('button',{name:/60\+ 临床靶点库/}).first().click(); await page.locator('input[placeholder*="搜索基因符号"]').fill('ABL1'); await page.getByRole('button',{name:/载入靶点/}).first().click(); });
    await check('从头分子生成', async()=> { await advanced(); await page.getByRole('button',{name:/3D 从头生成/}).first().click(); await page.getByRole('button',{name:/启动 3D 口袋从头生成/}).click(); await page.getByText(/IP 新颖度/).first().waitFor(); });
    await check('逆合成规划', async()=> { await advanced(); await page.getByRole('button',{name:/AI 逆合成规划/}).first().click(); await page.getByText(/商业现货起始原料清单/).waitFor(); });
    await check('虚拟筛选：提交与候选列表', async()=> { await advanced(); await page.getByRole('button',{name:/超大虚拟海选/}).click(); await page.getByRole('button',{name:/启动高通量虚拟筛选/}).click(); await page.getByText('淘选 Hits / 骨架簇',{exact:true}).waitFor(); });
    await check('激酶选择性分析与CSV导出', async()=> { await home(); await page.getByRole('button',{name:'激酶谱选择性分析',exact:true}).click(); await page.waitForTimeout(1500); const button=page.getByRole('button',{name:/导出.*CSV/}).first(); await button.waitFor(); const download=page.waitForEvent('download'); await button.click(); assert((await download).suggestedFilename().endsWith('.csv')); });
    await check('基准对比页', async()=> { await home(); await page.getByRole('button',{name:'模型基准对比',exact:true}).click(); await page.locator('table').first().waitFor(); });
    await check('模型配置弹窗与关闭', async()=> { await home(); await page.getByRole('button',{name:'模型配置',exact:true}).click(); await page.getByRole('dialog',{name:'配置中心'}).waitFor(); await page.getByRole('button',{name:'关闭配置中心',exact:true}).click(); });
    await check('分子库空态', async()=> { await page.getByRole('button',{name:/分子库/}).first().click(); await page.getByText(/候选.*暂存|分子.*暂存|暂无/).first().waitFor(); });
    await check('先导优化：候选与主动学习结果', async()=> { await page.goto('http://127.0.0.1:5173/evolution'); await page.getByRole('button',{name:/达沙替尼 \(Dasatinib\) → ABL1/}).click(); await page.getByRole('button',{name:/开始智能改构与贝叶斯主动学习评估/}).click(); await page.getByText('先导母体基准 (Baseline Lead)',{exact:true}).waitFor(); });
    await check('96孔板规划与CSV下载', async()=> { await page.getByRole('button',{name:'96 孔板投产清单',exact:true}).click(); const download=page.waitForEvent('download'); await page.getByRole('button',{name:'下载孔板 CSV',exact:true}).click(); assert((await download).suggestedFilename().endsWith('.csv')); });
    await check('学术报告弹窗与生成', async()=> { await page.goto('http://127.0.0.1:5173/evolution'); await page.getByRole('button',{name:/达沙替尼 \(Dasatinib\) → ABL1/}).click(); await page.getByRole('button',{name:/开始智能改构与贝叶斯主动学习评估/}).click(); await page.getByRole('button',{name:'生成学术交付报告',exact:true}).click(); const download=page.waitForEvent('download'); await page.getByRole('button',{name:'下载 .md',exact:true}).click(); assert((await download).suggestedFilename().endsWith('.md')); });
    for (const route of ['/amp-screening','/wheel','/report']) await check(`辅助页面 ${route}`,async()=> { await page.goto(`http://127.0.0.1:5173${route}`); await page.waitForTimeout(800); assert.equal(await page.getByText('科研工作台页面组件运行异常',{exact:true}).count(),0); assert((await page.locator('main').innerText()).length>150); });
  } finally { await browser.close(); }
  const passed = results.filter(r => r.status === 'passed').length;
  const failed = results.filter(r => r.status === 'failed');
  console.log('SUMMARY', passed, '/', results.length);
  if (failed.length > 0) {
    console.error('AUDIT FAILED:', failed);
    process.exitCode = 1;
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
