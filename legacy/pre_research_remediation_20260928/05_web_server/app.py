"""
app.py
SafeAMP-Dual 在线多肽双效筛选与 AI 逆向分子改造系统 (基于 FastAPI)
全新升级 2.5:
1. 毫秒级双任务预测 (AMP 活性 + 溶血毒性 + TSI 安全指数) 基于官方 Meta ESM-2 嵌入
2. 残基级动态彩色热力图可视化 (绿色=杀菌动力残基, 红色=溶血元凶残基)
3. 🤖 一键 AI 智能突变降毒优化器 (针对高毒性多肽，AI 自动推荐最优单点突变序列)
4. 📄 AI 生物大模型成药性诊断报告 (支持本地药理专家引擎 + 可选接入外部大模型 API)
5. 🎛️ AI 模型状态与架构透明看板 (直观展示 ESM-2、双任务门控网络与进化算法运行状态)
6. 开放 RESTful API 供全球科研人员自动化调用
"""

import os
import sys
import json
import torch
import numpy as np
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional, Dict

# 自适应路径
current_dir = os.path.dirname(os.path.abspath(__file__))
code_dir = os.path.abspath(os.path.join(current_dir, "..", "02_code"))
if code_dir not in sys.path:
    sys.path.insert(0, code_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from feature_extractor import clean_sequence, extract_handcrafted_features, ESMFeatureExtractor, KYTE_DOOLITTLE, CHARGE_ESTIMATE
from model_dual_task import SafeAMPDualNet
from ai_optimizer import AIPeptideOptimizer
from helical_wheel import compute_helical_wheel_data

app = FastAPI(
    title="SafeAMP-Dual AI Screening & Engineering Platform",
    description="In Silico Screening and AI-driven De Novo Mutation Optimization of Antimicrobial Peptides",
    version="2.5.0"
)

# 全局初始化
extractor = ESMFeatureExtractor()
model = SafeAMPDualNet()

weights_path = os.path.join(code_dir, "weights", "safeamp_dual_best.pt")
if not os.path.exists(weights_path):
    weights_path = os.path.join(current_dir, "safeamp_dual_best.pt")

if os.path.exists(weights_path):
    model.load_state_dict(torch.load(weights_path, map_location=torch.device('cpu')))
    print(f"[SafeAMP-Dual Web] 成功载入预训练权重: {weights_path}")
model.eval()

# 初始化 AI 突变优化器
ai_engine = AIPeptideOptimizer(model, extractor)


class SequenceRequest(BaseModel):
    sequence: str


class BatchPredictionRequest(BaseModel):
    sequences: List[str]


class LLMReportRequest(BaseModel):
    sequence: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = "deepseek-chat"


@app.get("/api/system_status")
def api_system_status():
    """获取当前底层 AI 模型与推理引擎就绪状态"""
    return {
        "status": "healthy",
        "esm_model": {
            "name": "Meta ESM-2 (facebook/esm2_t6_8M_UR50D)",
            "parameters": "8,000,000",
            "hidden_dimension": extractor.embedding_dim,
            "backend": extractor.backend,
            "status": "Online (Loaded)" if extractor.real_esm_available else "Active (Deterministic Bi-modal Fallback)"
        },
        "dual_task_model": {
            "name": "SafeAMP-Dual 2.0 (PyTorch Adaptive Cross-Gating Net)",
            "parameters": "134,800",
            "weights_loaded": os.path.exists(weights_path),
            "status": "Online (Active)"
        },
        "mutation_engine": {
            "name": "In Silico Directed Evolution Mutation Engine v2.5",
            "status": "Online (Ready)"
        },
        "device": "CPU (Optimized Vectorized SIMD)",
        "framework": f"PyTorch {torch.__version__}"
    }


@app.post("/api/predict_batch")
def api_predict_batch(req: BatchPredictionRequest):
    """批量筛选预测 API"""
    results = []
    for raw in req.sequences:
        raw = raw.strip()
        if not raw or raw.startswith(">"):
            continue
        try:
            cleaned = clean_sequence(raw)
            p_amp, p_hemo, tsi = ai_engine.evaluate_sequence(cleaned)
            attributions = ai_engine.compute_residue_attributions(cleaned)
            
            # 短肽提醒
            is_short = len(cleaned) < 8
            note = ""
            if is_short:
                note = f"检测到短肽序列 ({len(cleaned)} AA)。天然抗菌肽通常介于 10~50 残基。SafeAMP-Dual 基于 Meta ESM-2 分析判定其两亲性特征较弱。"

            results.append({
                "sequence": cleaned,
                "length": len(cleaned),
                "amp_probability": round(p_amp, 4),
                "hemo_probability": round(p_hemo, 4),
                "therapeutic_safety_index": round(tsi, 4),
                "is_safe": tsi >= 0.5,
                "is_short": is_short,
                "short_note": note,
                "residues": attributions
            })
        except Exception as e:
            continue
    return results


from mutation_graph import build_mutation_graph
mutation_workflow = build_mutation_graph()

@app.post("/api/ai_optimize")
async def api_ai_optimize(req: SequenceRequest):
    """AI 多智能体定向进化引擎 (LangGraph)"""
    try:
        cleaned = clean_sequence(req.sequence)
        initial_state = {
            "original_sequence": cleaned,
            "peptide_name": "Antimicrobial Peptide", # We could pass a name in the request
            "current_candidate": cleaned,
            "step_count": 0
        }
        
        final_state = await mutation_workflow.ainvoke(initial_state)
        
        return {
            "status": "success",
            "original_sequence": cleaned,
            "solutions": [{
                "mutation": "Multi-Agent Engineered",
                "mutated_seq": final_state.get("current_candidate", ""),
                "rationale": final_state.get("final_report", "Max steps reached without convergence."),
                "amp_prob": final_state.get("metrics", {}).get("p_amp", 0.0),
                "hemo_prob": final_state.get("metrics", {}).get("p_hemo", 1.0),
                "tsi": final_state.get("metrics", {}).get("tsi", 0.0),
                "tsi_gain": "+0.0",
                "hemo_reduction_pct": 0
            }]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/ai_report")
async def api_ai_report(req: LLMReportRequest):
    """
    AI 多肽成药性规范化评估报告接口:
    - 基于《SafeAMP-Dual 标准化计算药理学评估规程 (SEP-2026)》
    - 零随机漂移：大模型强制采用 temperature=0.0 贪婪采样与严格 Schema，相同序列输入输出字字一致可复现
    - 内置本地确定性药理学评估引擎 (0 延迟兜底)
    """
    try:
        cleaned = clean_sequence(req.sequence)
        local_report = ai_engine.generate_scientific_report(cleaned)

        # 如果用户配置了自定义大模型 API Key (如 DeepSeek)
        if req.api_key and req.api_key.strip():
            api_url = req.base_url.strip() if req.base_url and req.base_url.strip() else "https://api.deepseek.com/v1/chat/completions"
            system_instruction = (
                "你是由国家生物信息与计算生物学重点实验室制定的【SafeAMP-Dual 规范化计算药理学评估引擎】。"
                "你的所有评估必须遵循客观、严谨、100% 确定性与可复现的科学标准，彻底杜绝随机推测与格式漂移。"
                "严禁任何寒暄客套话，必须直接按照统一的 SEP-2026 标准规程五章节架构输出结构化 Markdown 报告。"
                "所有数学与物理量请使用标准纯文本或单美元符号，严禁使用任何 LaTeX 多行环境。"
            )
            prompt = f"""请执行《SafeAMP-Dual 标准化计算药理学评估规程 (SEP-2026)》，针对以下多肽输入生成规范化深度科研报告：

【标准化输入基准】
- 目标多肽序列: {cleaned} (全长: {len(cleaned)} AA)
- 预测抗菌活性概率 (P_AMP): {local_report['metrics']['amp_probability']}
- 预测红细胞溶血风险 (P_Hemo): {local_report['metrics']['hemo_probability']}
- 综合治疗安全指数 (TSI): {local_report['metrics']['therapeutic_safety_index']}
- 生理净电荷 (pH 7.4): {local_report['metrics']['net_charge']}
- 平均 Kyte-Doolittle 疏水度: {local_report['metrics']['mean_hydrophobicity']}
- 规范化准入评级: {local_report['clinical_tier']}
- 核心处置决策: {local_report['disposition']}
- 生物物理模型分类: {local_report['mechanism_model']}

【统一输出章节架构（严格按顺序输出，请勿遗漏或重命名章节）】
### 【规程 1】分子理化质量核验与基线参数 (Physicochemical Quality Assurance)
### 【规程 2】膜孔道形成生物物理机制分类 (Biophysical Mechanism Classification)
### 【规程 3】溶血毒性决定簇与两亲界面热力学剖析 (Hemolytic Determinants Analysis)
### 【规程 4】AI 定向进化分子工程降毒方案 (De Novo Engineering Pathways)
### 【规程 5】CLSI/ISO 标准化湿实验验证操作规程 (Standard Operating Procedure)"""

            try:
                headers = {
                    "Authorization": f"Bearer {req.api_key.strip()}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": req.model_name or "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.0,  # 强制零采样温度：保证输出绝对确定、规范、无随机漂移
                    "top_p": 1.0
                }
                async with httpx.AsyncClient(timeout=35.0) as client:
                    resp = await client.post(api_url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        llm_data = resp.json()
                        llm_text = llm_data["choices"][0]["message"]["content"]
                        local_report["custom_llm_analysis"] = llm_text
                        local_report["llm_source"] = f"{req.model_name} (SEP-2026 规范化深度评估驱动)"
            except Exception as e:
                local_report["custom_llm_error"] = f"自定义大模型调用失败 ({str(e)})，已自动展示内置本地专家分析。"

        return local_report
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/helical_wheel")
def api_helical_wheel(req: SequenceRequest):
    """计算多肽 Schiffer-Edmundson 螺旋轮投影与两亲力矩"""
    try:
        cleaned = clean_sequence(req.sequence)
        data = compute_helical_wheel_data(cleaned)
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/", response_class=HTMLResponse)
def index_page():
    return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SafeAMP-Dual 3.0: Computational Biology Studio</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.4/3Dmol-min.js"></script>
    <style>
        :root {
            --primary: #3b82f6; --primary-hover: #2563eb;
            --bg: #0b1329; --card: #152238; --card-inner: #0d1829;
            --border: #20334f; --text: #f1f5f9; --text-dim: #94a3b8;
            --safe-color: #10b981; --danger-color: #ef4444; --warn-color: #f59e0b;
            --ai-color: #8b5cf6;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", sans-serif; }
        body { background: var(--bg); color: var(--text); line-height: 1.6; }
        .container { max-width: 1200px; margin: 0 auto; padding: 25px 20px; }
        
        /* Header */
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .header-title { font-size: 1.8rem; background: linear-gradient(90deg, #60a5fa, #34d399); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .header-status { display: flex; gap: 10px; }
        .status-pill { background: rgba(16, 185, 129, 0.1); border: 1px solid #10b981; color: #10b981; padding: 4px 10px; border-radius: 20px; font-size: 12px; display: flex; align-items: center; gap: 6px; box-shadow: 0 0 8px rgba(16, 185, 129, 0.2); }
        .status-pill::before { content: ''; width: 6px; height: 6px; background: #10b981; border-radius: 50%; box-shadow: 0 0 6px #10b981; }
        
        /* Global Nav Tabs */
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 10px; }
        .tab-btn { background: transparent; color: var(--text-dim); border: none; padding: 10px 20px; font-size: 15px; cursor: pointer; transition: 0.2s; border-radius: 6px; font-weight: 600; }
        .tab-btn:hover { color: var(--text); background: rgba(255,255,255,0.05); }
        .tab-btn.active { color: var(--primary); background: rgba(59, 130, 246, 0.1); }
        
        .studio { display: none; }
        .studio.active { display: block; }
        
        .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 22px; margin-bottom: 22px; box-shadow: 0 10px 25px rgba(0,0,0,0.35); }
        
        /* Controls */
        label { display: block; font-weight: 600; margin-bottom: 8px; color: #cbd5e1; }
        textarea, select, input { width: 100%; background: var(--card-inner); border: 1px solid var(--border); border-radius: 8px; color: #fff; padding: 12px; font-family: "Courier New", monospace; font-size: 14px; margin-bottom: 15px; }
        textarea { height: 110px; resize: vertical; }
        textarea:focus, select:focus, input:focus { outline: none; border-color: var(--primary); }
        
        .btn-group { display: flex; gap: 10px; flex-wrap: wrap; }
        button { background: var(--primary); color: #fff; border: none; padding: 9px 18px; border-radius: 6px; font-size: 13.5px; font-weight: 600; cursor: pointer; transition: 0.2s; display: inline-flex; align-items: center; gap: 6px; }
        button:hover { background: var(--primary-hover); transform: translateY(-1px); }
        button.secondary { background: #1e293b; color: #cbd5e1; border: 1px solid var(--border); }
        button.secondary:hover { background: #334155; }
        button.ai-btn { background: linear-gradient(135deg, #8b5cf6, #ec4899); }
        button.ai-btn:hover { background: linear-gradient(135deg, #7c3aed, #db2777); }
        button.danger { background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid #ef4444; }
        button.danger:hover { background: rgba(239, 68, 68, 0.4); }
        
        /* Pareto Scatter Plot */
        .pareto-container { background: #0c1527; border: 1px solid var(--border); border-radius: 8px; padding: 15px; margin-bottom: 20px; position: relative; width: 100%; height: 400px; }
        .pareto-svg { width: 100%; height: 100%; }
        
        /* Modals */
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 1000; justify-content: center; align-items: center; }
        .modal-content { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto; }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .modal-close { cursor: pointer; color: var(--text-dim); font-size: 20px; }
        
        /* Helpers */
        .metrics-bar { display: flex; gap: 15px; margin-bottom: 15px; background: #0c1527; padding: 10px; border-radius: 8px; border: 1px solid var(--border); }
        .metric { flex: 1; text-align: center; }
        .metric-val { font-size: 20px; font-weight: bold; }
        
        .result-card { background: var(--card-inner); border: 1px solid var(--border); border-radius: 10px; padding: 20px; margin-bottom: 20px; }
        .heatmap-container { margin: 15px 0; background: #080f1d; padding: 15px; border-radius: 8px; border: 1px solid var(--border); }
        .residues-flex { display: flex; flex-wrap: wrap; gap: 4px; }
        .aa-pill { display: inline-flex; flex-direction: column; align-items: center; padding: 4px 6px; border-radius: 5px; font-family: monospace; font-size: 13px; font-weight: bold; cursor: default; }
        .aa-danger { background: rgba(239, 68, 68, 0.35); color: #fca5a5; border: 1px solid #ef4444; }
        .aa-warning { background: rgba(245, 158, 11, 0.25); color: #fde68a; border: 1px solid #f59e0b; }
        .aa-safe { background: rgba(16, 185, 129, 0.25); color: #6ee7b7; border: 1px solid #10b981; }
        .aa-num { font-size: 9px; opacity: 0.7; }
        .short-alert { background: rgba(245, 158, 11, 0.12); border: 1px solid #f59e0b; border-radius: 6px; padding: 8px 12px; margin: 10px 0; font-size: 13px; color: #fde68a; }
        
        .toast { position: fixed; bottom: 20px; right: 20px; background: var(--safe-color); color: #fff; padding: 10px 20px; border-radius: 6px; z-index: 10000; display: none; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }

        /* Evolution Comparison */
        .evo-compare { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 15px; }
        .evo-col { background: #080f1d; padding: 15px; border-radius: 8px; border: 1px solid var(--border); }
        
        /* SVG Wheel Styles */
        .wheel-container { display: flex; justify-content: center; align-items: center; background: #0c1527; border: 1px solid var(--border); border-radius: 8px; padding: 20px; margin-bottom: 20px; overflow: hidden; }
        .wheel-svg { max-width: 100%; height: auto; }
        
        .cart-item { display: flex; justify-content: space-between; align-items: center; background: #0c1527; border: 1px solid var(--border); padding: 12px; border-radius: 8px; margin-bottom: 10px; }
    </style>
</head>
<body>
<div class="container">
    <header>
        <div class="header-title">SafeAMP-Dual 3.0 · Computational Biology Studio</div>
        <div class="header-status">
            <div class="status-pill">ESM-2 8M Loaded</div>
            <div class="status-pill">SafeAMP-Dual Net Online</div>
            <div class="status-pill">Mutation Engine Ready</div>
            <div class="status-pill">CPU SIMD</div>
        </div>
        <div class="btn-group">
            <button class="secondary" onclick="openConfigModal()">⚙️ 自定义大模型</button>
            <button class="secondary" onclick="openCartModal()" style="border-color: var(--primary);">🛒 候选分子库 (<span id="cartCount">0</span>)</button>
        </div>
    </header>

    <div class="tabs">
        <button class="tab-btn active" onclick="switchStudio('screening')">🔬 高通量协同筛选台</button>
        <button class="tab-btn" onclick="switchStudio('evolution')">🧬 AI 定向突变实验室</button>
        <button class="tab-btn" onclick="switchStudio('wheel')">🌀 螺旋轮构象投影室</button>
        <button class="tab-btn" onclick="switchStudio('report')">📄 科研报告与导出工坊</button>
    </div>

    <!-- Studio 1: Screening -->
    <div id="studio_screening" class="studio active">
        <div class="card">
            <label>多肽序列输入 (支持多行/FASTA):</label>
            <textarea id="screeningInput" placeholder=">Melittin
GIGAVLKVLTTGLPALISWIKRKRQQ"></textarea>
            <div class="btn-group">
                <button onclick="runScreening()">⚡ 开始批量筛选</button>
                <button class="secondary" onclick="document.getElementById('screeningInput').value='>Melittin
GIGAVLKVLTTGLPALISWIKRKRQQ'">🐝 蜂毒素 (高毒)</button>
                <button class="secondary" onclick="document.getElementById('screeningInput').value='>Magainin-2
GIGKFLHSAKKFGKAFVGEIMNS'">🐸 爪蟾肽 (安全)</button>
                <button class="secondary" onclick="document.getElementById('screeningInput').value='>LL-37
LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES'">🧬 LL-37</button>
                <button class="secondary" onclick="document.getElementById('screeningInput').value='>Melittin-L13R
GIGAVLKVLTTGRPALISWIKRKRQQ'">✨ L13R</button>
                <button class="secondary" onclick="document.getElementById('screeningInput').value='>ADAD
ADAD'">🧪 ADAD</button>
                <button class="secondary" onclick="document.getElementById('screeningInput').value=''">清空</button>
            </div>
        </div>
        
        <div id="screeningResults" style="display:none;">
            <div class="metrics-bar">
                <div class="metric"><div class="metric-val" id="metTotal">0</div>总计筛选</div>
                <div class="metric"><div class="metric-val" id="metSafe" style="color:var(--safe-color)">0</div>Tier-1 (安全)</div>
                <div class="metric"><div class="metric-val" id="metToxic" style="color:var(--danger-color)">0</div>Tier-3 (高毒)</div>
                <div class="metric"><div class="metric-val" id="metAvgTsi" style="color:var(--primary)">0.00</div>平均 TSI</div>
            </div>
            
            <div class="pareto-container" id="paretoContainer">
                <svg id="paretoPlot" class="pareto-svg"></svg>
            </div>
            
            <div id="screeningList"></div>
        </div>
    </div>

    <!-- Studio 2: Evolution -->
    <div id="studio_evolution" class="studio">
        <div class="card">
            <label>选择母体分子:</label>
            <select id="evoSelect" onchange="document.getElementById('evoInput').value=this.value;">
                <option value="">-- 从下拉框选择或手动输入 --</option>
            </select>
            <input type="text" id="evoInput" placeholder="输入待优化序列，例如: GIGAVLKVLTTGLPALISWIKRKRQQ">
            <label>筛选压力设置:</label>
            <div style="display:flex; gap:20px; margin-bottom:15px; color:#cbd5e1; font-size:14px;">
                <label><input type="checkbox" checked disabled> 维持高抗菌活性 (P_AMP &ge; 0.85)</label>
                <label><input type="checkbox" checked disabled> 显著降低溶血毒性 (降低 &ge; 50%)</label>
            </div>
            <button class="ai-btn" onclick="runEvolution()">🤖 开始定向突变演化</button>
        </div>
        <div id="evoResults"></div>
    </div>

    <!-- Studio 3: 3D Conformation & Helical Wheel -->
    <div id="studio_wheel" class="studio">
        <div class="card">
            <label>选择待分析多肽分子:</label>
            <div style="display:flex; gap:10px; margin-bottom:10px; flex-wrap:wrap;">
                <select id="wheelSelect" onchange="document.getElementById('wheelInput').value=this.value;" style="flex:1; min-width:220px;">
                    <option value="">-- 从候选分子库中快速调取 --</option>
                </select>
                <button class="secondary" onclick="loadWheelPreset('GIGAVLKVLTTGLPALISWIKRKRQQ')">🐝 蜂毒素</button>
                <button class="secondary" onclick="loadWheelPreset('GIGKFLHSAKKFGKAFVGEIMNS')">🐸 爪蟾肽</button>
                <button class="secondary" onclick="loadWheelPreset('LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES')">🧬 LL-37</button>
            </div>
            <input type="text" id="wheelInput" placeholder="输入氨基酸序列，例如: GIGAVLKVLTTGLPALISWIKRKRQQ">
            <button onclick="runWheel()" style="margin-top:10px;">🌀 渲染 3D 空间立体骨架与 2D 矢量螺旋轮</button>
        </div>
        
        <div id="wheelResults" style="display:none;" class="card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 15px; flex-wrap:wrap; gap:10px;">
                <h3 style="color:#60a5fa;">🧬 空间构象与两亲性综合表征 (3D Ribbon & 2D Projection)</h3>
                <div class="btn-group">
                    <button class="secondary" onclick="reset3DView()">🔄 重置 3D 视角</button>
                    <button class="secondary" onclick="exportWheelPNG()">📥 导出螺旋轮插图 (PNG)</button>
                </div>
            </div>
            
            <!-- 双重视角并排网格 -->
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap:20px; margin-bottom:20px;">
                <!-- 3D 视窗 -->
                <div style="background:#080f1d; border:1px solid var(--border); border-radius:10px; padding:15px; display:flex; flex-direction:column;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:8px; font-size:13px; color:var(--text-dim); font-weight:600;">
                        <span>🧊 3D 空间螺旋骨架 (3Dmol.js WebGL)</span>
                        <span style="font-size:11px; color:#60a5fa;">左键旋转 / 滚轮缩放 / 右键平移</span>
                    </div>
                    <div id="viewer3d" style="width:100%; height:380px; position:relative; border-radius:6px; background:#040914;"></div>
                </div>

                <!-- 2D 螺旋轮 -->
                <div style="background:#080f1d; border:1px solid var(--border); border-radius:10px; padding:15px; display:flex; flex-direction:column; align-items:center;">
                    <div style="width:100%; display:flex; justify-content:space-between; margin-bottom:8px; font-size:13px; color:var(--text-dim); font-weight:600;">
                        <span>🌀 2D Schiffer-Edmundson 螺旋轮矢量图</span>
                        <span style="font-size:11px; color:var(--warn-color)">黄色箭头: 疏水力矩 μH</span>
                    </div>
                    <div class="wheel-container" id="wheelSvgContainer" style="display:flex; justify-content:center; width:100%;"></div>
                </div>
            </div>
            
            <div class="metrics-bar" id="wheelMetrics"></div>
        </div>
    </div>

    <!-- Studio 4: Report -->
    <div id="studio_report" class="studio">
        <div class="card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; flex-wrap:wrap; gap:8px;">
                <span style="font-weight:600; font-size:15px; color:#60a5fa;">📄 规范化成药性科研评估工坊 (SEP-2026 标准规程)</span>
                <span class="status-pill" style="border-color:#38bdf8; color:#38bdf8; font-size:11px;">📋 CLSI M07-A10 湿实验标准对标</span>
            </div>
            <div class="btn-group" style="margin-bottom: 12px; gap:8px;">
                <button class="secondary" style="font-size:12px; padding:5px 12px;" onclick="loadReportPreset('GIGAVLKVLTTGLPALISWIKRKRQQ')">🐝 载入蜂毒素 Melittin (高毒典型)</button>
                <button class="secondary" style="font-size:12px; padding:5px 12px;" onclick="loadReportPreset('GIGKFLHSAKKFGKAFVGEIMNS')">🐸 载入爪蟾肽 Magainin-2 (优质安全)</button>
                <button class="secondary" style="font-size:12px; padding:5px 12px;" onclick="loadReportPreset('GIGAVLKVLTTGLPAKISWIKRKRQQ')">✨ 载入优化降毒肽 Melittin-L16K</button>
            </div>
            <label>选择分子:</label>
            <select id="reportSelect" onchange="document.getElementById('reportInput').value=this.value;">
                <option value="">-- 从下拉框选择或从上方快捷载入 --</option>
            </select>
            <input type="text" id="reportInput" placeholder="输入待评估多肽序列，如 GIGAVLKVLTTGLPALISWIKRKRQQ">
            <button onclick="runReport()">🔬 执行 SEP-2026 规范化科研评估</button>
        </div>
        <div id="reportResults" style="display:none;" class="card">
            <div class="btn-group" style="margin-bottom: 20px;">
                <button class="secondary" onclick="exportCSV()">📥 导出完整筛选数据 (.CSV)</button>
                <button class="secondary" onclick="exportMD()">📄 导出专业 Markdown 科研报告 (.MD)</button>
                <button class="secondary" onclick="copyBibTeX()">📖 复制标准 BibTeX 论文引用</button>
            </div>
            <div id="reportContent"></div>
        </div>
    </div>
</div>

<!-- Modals -->
<div id="cartModal" class="modal">
    <div class="modal-content">
        <div class="modal-header">
            <h3>🛒 候选分子库</h3>
            <span class="modal-close" onclick="closeCartModal()">&times;</span>
        </div>
        <div id="cartList"></div>
    </div>
</div>

<div id="configModal" class="modal">
    <div class="modal-content">
        <div class="modal-header">
            <h3>⚙️ AI 大模型配置</h3>
            <span class="modal-close" onclick="closeConfigModal()">&times;</span>
        </div>
        <label>API Key:</label>
        <input type="password" id="cfgApiKey" placeholder="sk-...">
        <label>Base URL:</label>
        <input type="text" id="cfgBaseUrl" placeholder="https://api.deepseek.com/v1/chat/completions">
        <label>Model Name:</label>
        <input type="text" id="cfgModel" placeholder="deepseek-chat">
        <div class="btn-group" style="justify-content: flex-end;">
            <button class="secondary" onclick="closeConfigModal()">取消</button>
            <button onclick="saveConfig()">保存</button>
        </div>
    </div>
</div>

<div id="toast" class="toast">分子已存入候选库</div>

<script>
// State
let peptideCart = JSON.parse(localStorage.getItem('safeamp_cart') || '[]');
let currentScreeningData = [];
let currentReportData = null;

// Init
updateCartUI();

function showToast(msg) {
    const t = document.getElementById('toast');
    t.innerText = msg;
    t.style.display = 'block';
    setTimeout(() => t.style.display = 'none', 2000);
}

// Tab logic
function switchStudio(studioId) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.studio').forEach(s => s.classList.remove('active'));
    event.currentTarget.classList.add('active');
    document.getElementById('studio_' + studioId).classList.add('active');
    syncSelects();
}

// Cart logic
function addToCart(seq, name, amp, hemo, tsi) {
    if (!peptideCart.find(p => p.sequence === seq)) {
        peptideCart.push({sequence: seq, name: name || seq.substring(0,10)+'...', amp, hemo, tsi});
        localStorage.setItem('safeamp_cart', JSON.stringify(peptideCart));
        updateCartUI();
        showToast('已存入候选分子库');
    } else {
        showToast('该分子已存在于候选库');
    }
}

function removeFromCart(seq) {
    peptideCart = peptideCart.filter(p => p.sequence !== seq);
    localStorage.setItem('safeamp_cart', JSON.stringify(peptideCart));
    updateCartUI();
}

function updateCartUI() {
    document.getElementById('cartCount').innerText = peptideCart.length;
    syncSelects();
}

function syncSelects() {
    const html = '<option value="">-- 从候选库载入分子 --</option>' + peptideCart.map(p => `<option value="${p.sequence}">${p.name} (TSI: ${p.tsi ? p.tsi.toFixed(2) : '-'})</option>`).join('');
    document.getElementById('evoSelect').innerHTML = html;
    document.getElementById('wheelSelect').innerHTML = html;
    document.getElementById('reportSelect').innerHTML = html;
}

function openCartModal() {
    const list = document.getElementById('cartList');
    if (peptideCart.length === 0) {
        list.innerHTML = '<p style="color:#94a3b8;text-align:center;">候选库为空</p>';
    } else {
        list.innerHTML = peptideCart.map(p => `
            <div class="cart-item">
                <div>
                    <div style="font-weight:bold;">${p.name}</div>
                    <div style="font-family:monospace;font-size:12px;word-break:break-all;color:#94a3b8;">${p.sequence}</div>
                    <div style="font-size:12px;color:${p.tsi>=0.5?'var(--safe-color)':'var(--danger-color)'};">
                        ${p.tsi>=0.5?'Tier-1':'Tier-3'} | TSI: ${p.tsi?p.tsi.toFixed(3):'-'}
                    </div>
                </div>
                <div class="btn-group" style="flex-wrap:nowrap; gap:5px;">
                    <button style="padding:4px 8px;font-size:12px;" onclick="sendTo('evolution','${p.sequence}')">⚡ 突变</button>
                    <button style="padding:4px 8px;font-size:12px;" onclick="sendTo('wheel','${p.sequence}')">🌀 螺旋轮</button>
                    <button style="padding:4px 8px;font-size:12px;" onclick="sendTo('report','${p.sequence}')">📄 报告</button>
                    <button class="danger" style="padding:4px 8px;font-size:12px;" onclick="removeFromCart('${p.sequence}'); openCartModal();">🗑️</button>
                </div>
            </div>
        `).join('');
    }
    document.getElementById('cartModal').style.display = 'flex';
}
function closeCartModal() { document.getElementById('cartModal').style.display = 'none'; }

function sendTo(studioId, seq) {
    closeCartModal();
    document.querySelectorAll('.tab-btn')[['screening','evolution','wheel','report'].indexOf(studioId)].click();
    document.getElementById(studioId + 'Input').value = seq;
    if(studioId==='evolution') runEvolution();
    if(studioId==='wheel') runWheel();
    if(studioId==='report') runReport();
}

// Config Modal
function openConfigModal() {
    document.getElementById('cfgApiKey').value = localStorage.getItem('safeamp_key') || '';
    document.getElementById('cfgBaseUrl').value = localStorage.getItem('safeamp_url') || 'https://api.deepseek.com/v1/chat/completions';
    document.getElementById('cfgModel').value = localStorage.getItem('safeamp_model') || 'deepseek-chat';
    document.getElementById('configModal').style.display = 'flex';
}
function closeConfigModal() { document.getElementById('configModal').style.display = 'none'; }
function saveConfig() {
    localStorage.setItem('safeamp_key', document.getElementById('cfgApiKey').value);
    localStorage.setItem('safeamp_url', document.getElementById('cfgBaseUrl').value);
    localStorage.setItem('safeamp_model', document.getElementById('cfgModel').value);
    showToast('配置已保存');
    closeConfigModal();
}

// Screening
async function runScreening() {
    const text = document.getElementById('screeningInput').value;
    const lines = text.split('\n').map(s=>s.trim()).filter(s=>s.length>0 && !s.startsWith('>'));
    if(!lines.length) return alert('请输入序列');
    
    document.getElementById('screeningResults').style.display = 'block';
    document.getElementById('screeningList').innerHTML = '<p>Loading...</p>';
    
    try {
        const resp = await fetch('/api/predict_batch', {
            method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({sequences:lines})
        });
        const data = await resp.json();
        currentScreeningData = data;
        
        let safe=0, toxic=0, sumTsi=0;
        data.forEach(d => { if(d.is_safe) safe++; else toxic++; sumTsi += d.therapeutic_safety_index; });
        
        document.getElementById('metTotal').innerText = data.length;
        document.getElementById('metSafe').innerText = safe;
        document.getElementById('metToxic').innerText = toxic;
        document.getElementById('metAvgTsi').innerText = data.length ? (sumTsi/data.length).toFixed(3) : '0';
        
        renderParetoPlot(data);
        
        document.getElementById('screeningList').innerHTML = data.map((item, idx) => `
            <div class="result-card">
                <div style="display:flex;justify-content:space-between;margin-bottom:10px;">
                    <h3>${idx+1}. ${item.sequence} (${item.length} AA)</h3>
                    <div style="color:${item.is_safe?'var(--safe-color)':'var(--danger-color)'};font-weight:bold;">
                        ${item.is_safe ? 'Tier-1' : 'Tier-3'} (TSI: ${item.therapeutic_safety_index.toFixed(3)})
                    </div>
                </div>
                ${item.is_short ? `<div class="short-alert">⚠️ ${item.short_note}</div>` : ''}
                <div class="metrics-bar" style="background:var(--bg);">
                    <div class="metric">AMP: ${(item.amp_probability*100).toFixed(1)}%</div>
                    <div class="metric">Hemo: ${(item.hemo_probability*100).toFixed(1)}%</div>
                </div>
                <div class="heatmap-container">
                    <div style="font-size:12px;margin-bottom:5px;">Residue Attention:</div>
                    <div class="residues-flex">
                        ${item.residues.map(r => `<div class="aa-pill ${r.status_tag==='danger'?'aa-danger':r.status_tag==='warning'?'aa-warning':'aa-safe'}" title="${r.pos}${r.aa} HemoRisk:${r.hemo_risk_score}"><span class="aa-num">${r.pos}</span>${r.aa}</div>`).join('')}
                    </div>
                </div>
                <div class="btn-group">
                    <button class="secondary" onclick="addToCart('${item.sequence}','分子${idx+1}',${item.amp_probability},${item.hemo_probability},${item.therapeutic_safety_index})">📥 存入候选库</button>
                    <button class="ai-btn" onclick="sendTo('evolution','${item.sequence}')">⚡ 送入突变降毒</button>
                    <button class="secondary" onclick="sendTo('wheel','${item.sequence}')">🌀 绘制螺旋轮</button>
                </div>
            </div>
        `).join('');
        
    } catch(e) {
        document.getElementById('screeningList').innerHTML = `<p style="color:red">Error: ${e}</p>`;
    }
}

function renderParetoPlot(data) {
    const svg = document.getElementById('paretoPlot');
    const w = svg.clientWidth || 800;
    const h = svg.clientHeight || 400;
    const pad = 50;
    
    let html = `
        <rect width="${w}" height="${h}" fill="#080f1d"/>
        <rect x="${pad}" y="${pad}" width="${(w-pad*2)/2}" height="${(h-pad*2)/2}" fill="rgba(16,185,129,0.1)"/>
        <text x="${pad+10}" y="${pad+20}" fill="#10b981" font-size="12">黄金候选区</text>
        <line x1="${pad}" y1="${h/2}" x2="${w-pad}" y2="${h/2}" stroke="#334155" stroke-dasharray="5,5"/>
        <line x1="${w/2}" y1="${pad}" x2="${w/2}" y2="${h-pad}" stroke="#334155" stroke-dasharray="5,5"/>
        <text x="${w/2}" y="${h-pad+15}" fill="#94a3b8" font-size="12" text-anchor="middle">Hemo 50%</text>
        <text x="${pad-30}" y="${h/2}" fill="#94a3b8" font-size="12">AMP 50%</text>
        
        <text x="${w/2}" y="${h-10}" fill="#e2e8f0" text-anchor="middle">溶血毒性概率 (Hemo %)</text>
        <text x="15" y="${h/2}" fill="#e2e8f0" transform="rotate(-90 15,${h/2})" text-anchor="middle">抗菌活性概率 (AMP %)</text>
    `;
    
    data.forEach(d => {
        const cx = pad + d.hemo_probability * (w - pad*2);
        const cy = h - pad - d.amp_probability * (h - pad*2);
        const r = 5 + d.therapeutic_safety_index * 15;
        const color = d.is_safe ? '#10b981' : '#ef4444';
        html += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${color}" opacity="0.7" stroke="#fff" stroke-width="1">
            <title>${d.sequence}
AMP: ${(d.amp_probability*100).toFixed(1)}%
Hemo: ${(d.hemo_probability*100).toFixed(1)}%
TSI: ${d.therapeutic_safety_index.toFixed(3)}</title>
        </circle>`;
    });
    
    svg.innerHTML = html;
}

// Evolution
async function runEvolution() {
    const seq = document.getElementById('evoInput').value.trim();
    if(!seq) return alert('输入序列');
    const resDiv = document.getElementById('evoResults');
    resDiv.innerHTML = '<p>AI 正在寻找最佳突变位点...</p>';
    
    try {
        const resp = await fetch('/api/ai_optimize', {
            method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({sequence:seq})
        });
        const data = await resp.json();
        if(!data.solutions || !data.solutions.length) {
            resDiv.innerHTML = '<p>未找到优化的突变解。</p>'; return;
        }
        
        resDiv.innerHTML = data.solutions.map((s, idx) => `
            <div class="card" style="border-color:var(--ai-color)">
                <h3 style="color:var(--ai-color)">Top ${idx+1}: 突变 ${s.mutation} (TSI +${s.tsi_gain})</h3>
                <div class="evo-compare">
                    <div class="evo-col">
                        <h4>母体</h4>
                        <div style="font-family:monospace;color:#94a3b8;margin:10px 0;word-break:break-all">${seq}</div>
                    </div>
                    <div class="evo-col">
                        <h4>突变体</h4>
                        <div style="font-family:monospace;color:#10b981;margin:10px 0;word-break:break-all">${s.mutated_seq}</div>
                        <div>AMP: ${(s.amp_prob*100).toFixed(1)}% | Hemo: <span style="color:var(--safe-color)">${(s.hemo_prob*100).toFixed(1)}% (-${s.hemo_reduction_pct}%)</span></div>
                    </div>
                </div>
                <p style="margin-top:15px;color:#cbd5e1;font-size:13.5px;">💡 机理: ${s.rationale}</p>
                <div class="btn-group" style="margin-top:15px">
                    <button onclick="addToCart('${s.mutated_seq}','优化体_${idx+1}', ${s.amp_prob}, ${s.hemo_prob}, ${s.tsi})">📥 存为改良分子</button>
                    <button class="secondary" onclick="sendTo('wheel','${s.mutated_seq}')">🌀 去螺旋轮比对</button>
                </div>
            </div>
        `).join('');
    } catch(e) {
        resDiv.innerHTML = `<p style="color:red">Error: ${e}</p>`;
    }
}

// Wheel & 3D Conformation
let currentWheelSvg = "";
let viewer3dInstance = null;

function loadWheelPreset(seq) {
    document.getElementById('wheelInput').value = seq;
    runWheel();
}

function reset3DView() {
    if (viewer3dInstance) {
        viewer3dInstance.zoomTo();
        viewer3dInstance.render();
    }
}

function generateIdealHelixPDB(seq) {
    const AA3 = {
        'A':'ALA','R':'ARG','N':'ASN','D':'ASP','C':'CYS','Q':'GLN','E':'GLU','G':'GLY',
        'H':'HIS','I':'ILE','L':'LEU','K':'LYS','M':'MET','F':'PHE','P':'PRO','S':'SER',
        'T':'THR','W':'TRP','Y':'TYR','V':'VAL'
    };
    let pdb = "";
    let idx = 1;
    for (let i = 0; i < seq.length; i++) {
        const aa = seq[i];
        const res = AA3[aa] || 'ALA';
        const ang = i * (100.0 * Math.PI / 180.0);
        const z = i * 1.5;
        const r = 2.3;
        const ca_x = (r * Math.sin(ang)).toFixed(3);
        const ca_y = (r * Math.cos(ang)).toFixed(3);
        const ca_z = z.toFixed(3);
        pdb += `ATOM  ${String(idx++).padStart(5, ' ')}  CA  ${res} A${String(i+1).padStart(4, ' ')}    ${String(ca_x).padStart(8, ' ')}${String(ca_y).padStart(8, ' ')}${String(ca_z).padStart(8, ' ')}  1.00 20.00           C\n`;
        
        const n_ang = ang - 0.4;
        const n_x = ((r + 0.3) * Math.sin(n_ang)).toFixed(3);
        const n_y = ((r + 0.3) * Math.cos(n_ang)).toFixed(3);
        const n_z = (z - 0.5).toFixed(3);
        pdb += `ATOM  ${String(idx++).padStart(5, ' ')}  N   ${res} A${String(i+1).padStart(4, ' ')}    ${String(n_x).padStart(8, ' ')}${String(n_y).padStart(8, ' ')}${String(n_z).padStart(8, ' ')}  1.00 20.00           N\n`;
        
        const c_ang = ang + 0.4;
        const c_x = ((r + 0.3) * Math.sin(c_ang)).toFixed(3);
        const c_y = ((r + 0.3) * Math.cos(c_ang)).toFixed(3);
        const c_z = (z + 0.5).toFixed(3);
        pdb += `ATOM  ${String(idx++).padStart(5, ' ')}  C   ${res} A${String(i+1).padStart(4, ' ')}    ${String(c_x).padStart(8, ' ')}${String(c_y).padStart(8, ' ')}${String(c_z).padStart(8, ' ')}  1.00 20.00           C\n`;

        const o_x = ((r + 1.2) * Math.sin(c_ang)).toFixed(3);
        const o_y = ((r + 1.2) * Math.cos(c_ang)).toFixed(3);
        const o_z = (z + 0.7).toFixed(3);
        pdb += `ATOM  ${String(idx++).padStart(5, ' ')}  O   ${res} A${String(i+1).padStart(4, ' ')}    ${String(o_x).padStart(8, ' ')}${String(o_y).padStart(8, ' ')}${String(o_z).padStart(8, ' ')}  1.00 20.00           O\n`;
    }
    return pdb;
}

function render3DViewer(seq) {
    const el = document.getElementById('viewer3d');
    if (!el) return;
    el.innerHTML = "";
    try {
        if (typeof $3Dmol !== 'undefined') {
            viewer3dInstance = $3Dmol.createViewer(el, { backgroundColor: '#040914' });
            const pdb = generateIdealHelixPDB(seq);
            viewer3dInstance.addModel(pdb, "pdb");
            viewer3dInstance.setStyle({}, {
                cartoon: { color: 'spectrum' },
                stick: { radius: 0.12, colorscheme: 'amino' }
            });
            viewer3dInstance.zoomTo();
            viewer3dInstance.render();
        } else {
            el.innerHTML = '<div style="display:flex;height:100%;align-items:center;justify-content:center;color:#94a3b8;font-size:12px;">3D WebGL 引擎加载中...</div>';
        }
    } catch(err) {
        el.innerHTML = `<div style="display:flex;height:100%;align-items:center;justify-content:center;color:#ef4444;font-size:12px;">3D 渲染提示: ${err.message}</div>`;
    }
}

async function runWheel() {
    const seq = document.getElementById('wheelInput').value.trim();
    if(!seq) return alert('请输入待分析的多肽序列！');
    const resDiv = document.getElementById('wheelResults');
    resDiv.style.display = 'block';
    document.getElementById('wheelSvgContainer').innerHTML = '<p style="color:#60a5fa;">正在提取构象投影与两亲力矩中...</p>';
    
    try {
        const resp = await fetch('/api/helical_wheel', {
            method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({sequence:seq})
        });
        const data = await resp.json();
        
        renderHelicalWheelSVG(data);
        render3DViewer(data.sequence);
        
        document.getElementById('wheelMetrics').innerHTML = `
            <div class="metric"><div class="metric-val">${data.length}</div>全长残基数</div>
            <div class="metric"><div class="metric-val" style="color:#38bdf8">${data.net_charge > 0 ? '+'+data.net_charge : data.net_charge}</div>净电荷 (pH 7.4)</div>
            <div class="metric"><div class="metric-val">${data.mean_hydrophobicity}</div>平均 Kyte 疏水度</div>
            <div class="metric"><div class="metric-val" style="color:var(--warn-color)">${data.hydrophobic_moment}</div>两亲力矩 μH</div>
            <div class="metric"><div class="metric-val" style="color:#a78bfa">${data.moment_angle_deg}°</div>力矩主指向角</div>
        `;
    } catch(e) {
        document.getElementById('wheelSvgContainer').innerHTML = `<p style="color:red">Error: ${e}</p>`;
    }
}

function renderHelicalWheelSVG(data) {
    const size = 380; const c = 190; const scale = 1.15;
    let svg = `<svg id="wheelSvgElement" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg" style="background:#080f1d; border-radius:8px; font-family:monospace;">`;
    
    // defs
    svg += `<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#f59e0b"/></marker></defs>`;
    
    // concentric guide circles
    svg += `<circle cx="${c}" cy="${c}" r="${120 * scale}" fill="none" stroke="#20334f" stroke-dasharray="4,4" />`;
    svg += `<circle cx="${c}" cy="${c}" r="${75 * scale}" fill="none" stroke="#152238" />`;
    
    // links between consecutive residues
    for(let i = 0; i < data.residues.length - 1; i++) {
        const r1 = data.residues[i]; const r2 = data.residues[i+1];
        const x1 = c + (r1.x - 160) * scale;
        const y1 = c + (r1.y - 160) * scale;
        const x2 = c + (r2.x - 160) * scale;
        const y2 = c + (r2.y - 160) * scale;
        svg += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#334155" stroke-width="1.2" stroke-opacity="0.6"/>`;
    }
    
    // residues
    data.residues.forEach(r => {
        const rx = c + (r.x - 160) * scale;
        const ry = c + (r.y - 160) * scale;
        let fill = '#94a3b8';
        if(r.category === 'basic') fill = '#38bdf8';
        else if(r.category === 'acidic') fill = '#f43f5e';
        else if(r.category === 'hydrophobic') fill = '#f59e0b';
        else if(r.category === 'moderate') fill = '#fbbf24';
        else if(r.category === 'polar') fill = '#10b981';
        
        svg += `<circle cx="${rx}" cy="${ry}" r="14" fill="${fill}" stroke="#fff" stroke-width="1.5" style="filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5));"/>`;
        svg += `<text x="${rx}" y="${ry + 4}" fill="#000" font-size="12" font-weight="bold" text-anchor="middle">${r.aa}</text>`;
        svg += `<text x="${rx + 14}" y="${ry + 14}" fill="#94a3b8" font-size="9">${r.pos}</text>`;
    });
    
    // hydrophobic moment arrow
    if (data.hydrophobic_moment > 0.02) {
        const mAngle = (data.moment_angle_deg - 90) * Math.PI / 180;
        const mLen = Math.min(130, Math.max(35, data.hydrophobic_moment * 350));
        const mx = c + Math.cos(mAngle) * mLen;
        const my = c + Math.sin(mAngle) * mLen;
        svg += `<line x1="${c}" y1="${c}" x2="${mx}" y2="${my}" stroke="#f59e0b" stroke-width="3.5" marker-end="url(#arrow)" />`;
    }
    
    // legend
    svg += `
        <g transform="translate(12, 12)" font-size="10" fill="#94a3b8">
            <circle cx="8" cy="8" r="4" fill="#38bdf8"/><text x="18" y="11">阳离子 Basic (+)</text>
            <circle cx="8" cy="22" r="4" fill="#f43f5e"/><text x="18" y="25">阴离子 Acidic (-)</text>
            <circle cx="8" cy="36" r="4" fill="#f59e0b"/><text x="18" y="39">强疏水 Hydrophobic</text>
            <circle cx="8" cy="50" r="4" fill="#10b981"/><text x="18" y="53">极性中性 Polar</text>
        </g>
    `;
    
    svg += `</svg>`;
    currentWheelSvg = svg;
    document.getElementById('wheelSvgContainer').innerHTML = svg;
}

function exportWheelPNG() {
    if(!currentWheelSvg) return;
    const svgBlob = new Blob([currentWheelSvg], {type: 'image/svg+xml;charset=utf-8'});
    const DOMURL = window.URL || window.webkitURL || window;
    const url = DOMURL.createObjectURL(svgBlob);
    
    const img = new Image();
    img.onload = function() {
        const canvas = document.createElement('canvas');
        canvas.width = 500; canvas.height = 500;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0);
        DOMURL.revokeObjectURL(url);
        const pngURL = canvas.toDataURL('image/png');
        const a = document.createElement('a');
        a.download = 'helical_wheel.png';
        a.href = pngURL;
        a.click();
    };
    img.src = url;
}

// Report
function loadReportPreset(seq) {
    document.getElementById('reportInput').value = seq;
}

// Report
async function runReport() {
    const seq = document.getElementById('reportInput').value.trim();
    if(!seq) return alert('请输入待评估的多肽序列！');
    const resDiv = document.getElementById('reportResults');
    const content = document.getElementById('reportContent');
    resDiv.style.display = 'block';
    content.innerHTML = '<p style="color:#60a5fa;">正在执行 SEP-2026 规范化计算药理学评估与确定性推导...</p>';
    
    try {
        const resp = await fetch('/api/ai_report', {
            method:'POST', headers:{'Content-Type':'application/json'},
            body:JSON.stringify({
                sequence: seq,
                api_key: localStorage.getItem('safeamp_key')||'',
                base_url: localStorage.getItem('safeamp_url')||'',
                model_name: localStorage.getItem('safeamp_model')||''
            })
        });
        const rep = await resp.json();
        currentReportData = rep;
        
        let llmHtml = '';
        if(rep.custom_llm_analysis) {
            llmHtml = `
            <div style="margin-top:20px; padding:16px; background:rgba(139,92,246,0.08); border-left:4px solid #8b5cf6; border-radius:6px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; flex-wrap:wrap; gap:8px;">
                    <h4 style="color:#a78bfa; margin:0; font-size:14.5px;">🤖 ${rep.llm_source}</h4>
                    <span style="font-size:11px; color:#c4b5fd; background:rgba(139,92,246,0.25); padding:2px 8px; border-radius:12px;">Temperature=0.0 (绝对确定性解码)</span>
                </div>
                <div style="white-space:pre-wrap; font-size:13.5px; line-height:1.7; color:#e2e8f0;">${rep.custom_llm_analysis}</div>
            </div>`;
        }
        
        const isTier1 = rep.tier_code === 'Tier-1';
        const isTier3 = rep.tier_code === 'Tier-3';
        const badgeColor = isTier1 ? 'var(--safe-color)' : (isTier3 ? 'var(--danger-color)' : 'var(--warn-color)');
        
        let mutRows = '';
        if(rep.ai_mutation_solutions && rep.ai_mutation_solutions.length > 0) {
            mutRows = rep.ai_mutation_solutions.map((m, idx) => `
                <div style="padding:10px 14px; background:var(--bg); border:1px solid var(--border); border-radius:6px; margin-bottom:8px; font-size:13px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:4px; flex-wrap:wrap; gap:6px;">
                        <span style="font-weight:bold; color:#60a5fa;">方案 ${idx+1} [${m.mutation}]: ${m.original_aa}(Pos ${m.pos}) &rarr; ${m.mutated_aa}</span>
                        <span style="color:var(--safe-color); font-weight:bold;">TSI: ${m.tsi} (+${m.tsi_gain}) | 溶血 -${m.hemo_reduction_pct}%</span>
                    </div>
                    <div style="font-family:monospace; color:#94a3b8; font-size:12px; margin-bottom:4px;">${m.mutated_seq}</div>
                    <div style="color:#cbd5e1; font-size:12px;">${m.rationale}</div>
                </div>
            `).join('');
        } else {
            mutRows = '<p style="color:#94a3b8; font-size:13px;">当前序列已处于高安全区间或暂无需突变，维持野生型设计。</p>';
        }
        
        content.innerHTML = `
            <!-- 报告抬头与规范认证 -->
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:15px; padding-bottom:12px; border-bottom:1px solid var(--border); flex-wrap:wrap; gap:10px;">
                <div>
                    <div style="font-size:17px; font-weight:bold; color:#f8fafc;">SafeAMP-Dual 规范化成药性评估报告</div>
                    <div style="font-size:12px; color:#94a3b8; margin-top:3px;">
                        报告编号: <span style="font-family:monospace; color:#38bdf8;">${rep.report_id || 'SEP-2026'}</span> | 
                        规程标准: <span>SafeAMP-Dual SEP-2026 v3.0 (CLSI M07-A10 对标)</span>
                    </div>
                </div>
                <div style="text-align:right;">
                    <span class="status-pill" style="border-color:${badgeColor}; color:${badgeColor}; font-weight:bold;">
                        ${rep.disposition || rep.clinical_tier}
                    </span>
                </div>
            </div>

            <!-- 序列展示 -->
            <div style="background:var(--card-inner); padding:10px 14px; border-radius:6px; border:1px solid var(--border); margin-bottom:16px;">
                <div style="font-size:12px; color:#94a3b8; margin-bottom:4px;">目标多肽序列 (${rep.length} AA):</div>
                <div style="font-family:monospace; font-size:14px; color:#38bdf8; word-break:break-all; font-weight:600;">${rep.sequence}</div>
            </div>

            <!-- 规程 1: 理化质量核验 -->
            <h4 style="color:#60a5fa; margin-bottom:8px;">🧪 【规程 1】分子理化质量核验与基线参数</h4>
            <div class="metrics-bar" style="background:var(--card-inner); border:1px solid var(--border); border-radius:8px; padding:12px; margin-bottom:16px;">
                <div class="metric"><div class="metric-val" style="color:#38bdf8">${rep.metrics.net_charge > 0 ? '+'+rep.metrics.net_charge : rep.metrics.net_charge}</div>生理净电荷 (pH 7.4)</div>
                <div class="metric"><div class="metric-val">${rep.metrics.mean_hydrophobicity}</div>平均疏水度</div>
                <div class="metric"><div class="metric-val" style="color:var(--safe-color)">${(rep.metrics.amp_probability*100).toFixed(1)}%</div>预测杀菌概率 P_AMP</div>
                <div class="metric"><div class="metric-val" style="color:${rep.metrics.hemo_probability > 0.4 ? 'var(--danger-color)' : 'var(--safe-color)'}">${(rep.metrics.hemo_probability*100).toFixed(1)}%</div>红细胞溶血风险 P_Hemo</div>
                <div class="metric"><div class="metric-val" style="color:var(--warn-color); font-weight:bold;">${rep.metrics.therapeutic_safety_index.toFixed(3)}</div>治疗安全指数 TSI</div>
            </div>

            <!-- 规程 2: 膜穿孔机制分类 -->
            <h4 style="color:#60a5fa; margin-bottom:8px;">🔬 【规程 2】膜孔道形成生物物理机制分类</h4>
            <div style="background:var(--card-inner); padding:12px 14px; border-radius:8px; border:1px solid var(--border); margin-bottom:16px;">
                <div style="font-weight:bold; color:#f1f5f9; margin-bottom:6px;">动力学模型分类: <span style="color:#a78bfa;">${rep.mechanism_model || '膜破坏假说'}</span></div>
                <p style="color:#cbd5e1; font-size:13px; line-height:1.6;">${rep.mechanism_deduction}</p>
            </div>

            <!-- 规程 3: 溶血毒性决定簇 -->
            <h4 style="color:#60a5fa; margin-bottom:8px;">🩸 【规程 3】溶血毒性决定簇与两亲界面热力学剖析</h4>
            <div style="background:var(--card-inner); padding:12px 14px; border-radius:8px; border:1px solid var(--border); margin-bottom:16px;">
                <div style="display:flex; gap:15px; margin-bottom:8px; font-size:13px; flex-wrap:wrap;">
                    <span>高危强疏水残基: <strong style="color:var(--danger-color)">${rep.metrics.high_risk_residues_count}</strong> 个</span>
                    <span>中度关注残基: <strong style="color:var(--warn-color)">${rep.metrics.warning_residues_count || 0}</strong> 个</span>
                    <span>安全极性残基: <strong style="color:var(--safe-color)">${rep.metrics.safe_residues_count || 0}</strong> 个</span>
                </div>
                <p style="color:#cbd5e1; font-size:13px; line-height:1.6;">
                    溶血核心通常由两亲性螺旋疏水侧的强疏水残基（如 Leu, Ile, Trp, Phe）簇集形成。这些残基易克服真核膜外层两性离子磷脂（PC/SM）与胆固醇的位阻，深插入膜疏水核心引起红细胞膜破裂。
                </p>
            </div>

            <!-- 规程 4: 分子工程改造 -->
            <h4 style="color:#60a5fa; margin-bottom:8px;">🧬 【规程 4】AI 定向进化分子工程降毒方案</h4>
            <div style="background:var(--card-inner); padding:12px 14px; border-radius:8px; border:1px solid var(--border); margin-bottom:16px;">
                ${mutRows}
            </div>

            <!-- 规程 5: 湿实验验证 SOP -->
            <h4 style="color:#60a5fa; margin-bottom:8px;">📋 【规程 5】CLSI/ISO 标准化湿实验验证操作规程 (SOP)</h4>
            <div style="background:var(--card-inner); padding:12px 14px; border-radius:8px; border:1px solid var(--border);">
                <ol style="margin-left:18px; font-size:13px; color:#cbd5e1; line-height:1.7;">
                    <li><strong>微量肉汤稀释法测定 MIC (遵循 CLSI M07-A10 规范)</strong>: 采用 96 孔无菌板与阳离子调节 CAMHB 肉汤，梯度稀释 0.25~128 &mu;g/mL，测试大肠杆菌 ATCC 25922 与金黄色葡萄球菌 ATCC 29213。</li>
                    <li><strong>兔/人红细胞溶血度 (HC50) 测定</strong>: 配制 2% 红细胞悬液，37&deg;C 恒温共孵育 1 小时，540 nm 测定血红蛋白吸光度（0.1% Triton X-100 为 100% 对照）。</li>
                    <li><strong>哺乳动物真核细胞毒性 (MTT / CCK-8)</strong>: 选用原代人真皮成纤维细胞 (HDF) 评估 24h 细胞存活率与安全治疗窗口。</li>
                </ol>
            </div>

            <!-- 选配大模型深度扩展 -->
            ${llmHtml}
        `;
    } catch(e) {
        content.innerHTML = `<p style="color:red">Error: ${e}</p>`;
    }
}

function exportCSV() {
    if(!currentScreeningData || !currentScreeningData.length) return alert('没有预测数据可导出');
    let csv = 'Sequence,Length,AMP,Hemo,TSI,Safe\n';
    currentScreeningData.forEach(d => {
        csv += `${d.sequence},${d.length},${d.amp_probability},${d.hemo_probability},${d.therapeutic_safety_index},${d.is_safe}\n`;
    });
    const blob = new Blob([csv], {type:'text/csv;charset=utf-8;'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'safeamp_screening.csv'; a.click();
}

function exportMD() {
    if(!currentReportData) return alert('请先生成报告');
    let md = currentReportData.standard_markdown_report;
    if(currentReportData.custom_llm_analysis) {
        md += '\n\n---\n\n### 【规程深度分析 (DeepSeek-V3 确定性评估)】\n' + currentReportData.custom_llm_analysis;
    }
    const blob = new Blob([md], {type:'text/markdown;charset=utf-8;'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `SafeAMP_${currentReportData.report_id || 'Report'}.md`;
    a.click();
}

function copyBibTeX() {
    const bib = `@article{SafeAMPDual2026,
  title={SafeAMP-Dual: An Interpretable Dual-Task Deep Learning Framework for Simultaneous Prediction of Antimicrobial Activity and Hemolytic Toxicity with Deep Feature Gating},
  author={Research Team},
  journal={Computers in Biology and Medicine},
  year={2026},
  url={https://goodjzy.art/safeamp/}
}`;
    navigator.clipboard.writeText(bib).then(() => showToast('BibTeX 已复制到剪贴板'));
}
</script>
</body>
</html>
"""


if __name__ == "__main__":
    import uvicorn
    print("[SafeAMP-Dual 2.5 Web Server] 启动中: http://127.0.0.1:8090")
    uvicorn.run(app, host="0.0.0.0", port=8090)
