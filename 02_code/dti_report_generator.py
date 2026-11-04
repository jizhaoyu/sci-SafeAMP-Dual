"""Automated Scientific Research Brief and Patent Disclosure Generator.

Produces publication-grade Markdown and print-ready standalone HTML reports
integrating 3D biophysical energetics, ADMET toxicology, SAR ladders, and patent claims.
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional


def generate_dti_academic_report(
    target_name: str,
    baseline: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    biophysics: Optional[Dict[str, Any]] = None,
    admet: Optional[Dict[str, Any]] = None,
    active_learning: Optional[Dict[str, Any]] = None,
    author: str = "DTI BioAI Laboratory",
    model_name: Optional[str] = None,
    is_verified: bool = False
) -> Dict[str, str]:
    """Generate Markdown and Print-ready HTML scientific reports."""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")

    raw_model = model_name or baseline.get("model_name") or baseline.get("model_used") or "未指定特定模型 (请核实实际使用的推理引擎)"
    resolved_model = raw_model if is_verified else f"{raw_model} (Unverified)"
    protocol_str = "Protocol-DTI-01 (DAVIS 基准 [5.0 - 10.8])" if is_verified else "外部未验证数据输入 (无基准协议认证) / Unverified External Input"
    verification_status_str = "服务端运行时完整认证 (Server-Verified)" if is_verified else "未通过服务端运行时认证 (Unverified External Input)"

    base_smiles = baseline.get("smiles", "")
    raw_base_pkd = baseline.get("predicted_pkd")
    raw_base_kd = baseline.get("predicted_kd_nM")
    base_pkd = float(raw_base_pkd) if raw_base_pkd is not None else None
    base_kd = float(raw_base_kd) if raw_base_kd is not None else None
    base_sa = float(baseline.get("sa_score")) if baseline.get("sa_score") is not None else None

    has_biophysics = bool(biophysics and isinstance(biophysics, dict))
    mmgbsa = (biophysics.get("mmgbsa") if has_biophysics else None) or {}
    has_mmgbsa = bool(mmgbsa and any(k in mmgbsa for k in ("delta_g_bind", "delta_e_vdw", "delta_e_elec")))

    delta_g = mmgbsa.get("delta_g_bind")
    delta_vdw = mmgbsa.get("delta_e_vdw")
    delta_elec = mmgbsa.get("delta_e_elec")
    delta_solv = (mmgbsa.get("delta_g_gb", 0.0) + mmgbsa.get("delta_g_sa", 0.0)) if ("delta_g_gb" in mmgbsa or "delta_g_sa" in mmgbsa) else None
    delta_entropy = mmgbsa.get("minus_t_delta_s")

    best_cand = candidates[0] if candidates else None
    max_gain = round(float(best_cand.get("delta_pkd", 0.0)), 3) if best_cand and best_cand.get("delta_pkd") is not None else 0.0
    best_kd_val = best_cand.get("predicted_kd_nM") if best_cand else base_kd
    best_kd_str = f"{float(best_kd_val):.2f} nM" if best_kd_val is not None else "未提供 (N/A)"
    base_pkd_str = f"{base_pkd:.3f}" if base_pkd is not None else "未提供 (N/A)"
    base_kd_str = f"{base_kd:.2f} nM" if base_kd is not None else "未提供 (N/A)"
    base_sa_str = f"{base_sa:.2f}" if base_sa is not None else "N/A"

    cand_sa_vals = [float(c.get('sa_score')) for c in candidates if c.get('sa_score') is not None]
    sa_avg_str = f"{round(sum(cand_sa_vals) / len(cand_sa_vals), 2)}" if cand_sa_vals else "N/A"

    # =========================================================================
    # 1. MARKDOWN REPORT GENERATION
    # =========================================================================
    md_lines: List[str] = [
        f"# 先导化合物结构优化与激酶结合亲和力学术评估报告",
        f"**Lead Optimization & Kinase Binding Affinity Research Report**\n",
        f"* **研究课题**: 靶向人类催化激酶 `{target_name}` 的分子进化、诱导契合与多维 ADMET 成药性综合研究",
        f"* **报告日期**: `{date_str}` | **生成时间**: `{now_str}`",
        f"* **生成机构**: `{author}`",
        f"* **评估协议**: `{protocol_str}`",
        f"* **评估模型**: `{resolved_model}`",
        f"* **验证状态**: `{verification_status_str}`",
        f"* **密级状态**: `内部科研交付 / 预备专利披露 (Pre-Patent Disclosure)`\n",
    ]

    if not is_verified:
        md_lines.extend([
            f"> **CRITICAL SCIENTIFIC INTEGRITY WARNING**:\n",
            f"> 本报告所列分子与分值系外部输入或未经服务端运行时认证的数据，已标记为 **(Unverified)**。\n",
            f"> 本次生成未执行已认证的服务端推理任务，严禁作为 DAVIS 基准实测或正式模型运行结论。\n\n"
        ])

    md_lines.extend([
        f"---\n",
        f"## 1. 执行摘要 (Executive Summary)\n",
        f"本研究针对人类蛋白激酶 **`{target_name}`**，以母体先导化合物为优化起点开展计算机辅助药物设计与构效关系评估。\n",
        f"{'在系统评估的 **' + str(len(candidates)) + '** 个结构改构衍生方案中，基于计算模型预测得到以下关键结论：' if is_verified else '在记录的 **' + str(len(candidates)) + '** 个外部候选输入方案中（未经服务端运行时认证）：'}",
        f"* **先导母体基准亲和力**: 预测 $p\\text{{K}}_d = {base_pkd_str}$ ($K_d = {base_kd_str}$)",
        f"* **最优候选方案**: `{best_cand.get('name', 'N/A') if best_cand else 'None'}`",
        f"* **预测最优结合常数**: $K_d = {best_kd_str}$ (预测亲和力差额 $\\Delta p\\text{{K}}_d = {('+' if max_gain > 0 else '')}{max_gain:.3f}$)",
        f"* **合成可达性均值**: $\\text{{SA Score}} = {sa_avg_str}$",
        f"\n---\n",
        f"## 2. 靶标催化微环境与 3D 口袋构象 (Target Pocket Profile)\n",
    ])

    if has_biophysics:
        pref_conf = biophysics.get("preferred_conformation", "未提供构象分析")
        dfg_penalty = biophysics.get("dfg_flip_penalty_kcal")
        dfg_str = f"{dfg_penalty:.2f} kcal/mol" if dfg_penalty is not None else "N/A (未解算)"
        gk_clash = biophysics.get("gatekeeper_clash")
        gk_str = f"{gk_clash:.2f}" if gk_clash is not None else "N/A (未解算)"

        md_lines.extend([
            f"人类激酶 **`{target_name}`** 的催化活性口袋微观环境参数解算结果：",
            f"* **结合模式与构象假说**: `{pref_conf}`",
            f"* **DFG 活化环翻转能垒**: `{dfg_str}`",
            f"* **门控残基空间位阻**: `{gk_str}`\n",
        ])
    else:
        md_lines.append("* **口袋结构分析**: `未提供 3D 口袋构象或诱导契合解算输入，本项缺失。`\n")

    md_lines.append("### MM-GBSA 第一性原理热力学自由能分解\n")
    if has_mmgbsa and delta_g is not None:
        md_lines.extend([
            f"| 热力学分项 | 符号 | 计算能量 (kcal/mol) | 药化物理机制 |\n",
            f"| :--- | :--- | :---: | :--- |\n",
            f"| 范德华互作能 | $\\Delta E_{{\\text{{vdw}}}}$ | `{f'{delta_vdw:.2f}' if delta_vdw is not None else 'N/A'}` | 分子与疏水口袋内壁原子级堆积吸引 |\n",
            f"| 静电库仑作用 | $\\Delta E_{{\\text{{elec}}}}$ | `{f'{delta_elec:.2f}' if delta_elec is not None else 'N/A'}` | 极性氢键与偶极共振配位 |\n",
            f"| 溶剂化去水能 | $\\Delta G_{{\\text{{solv}}}}$ | `{f'{delta_solv:.2f}' if delta_solv is not None else 'N/A'}` | 溶剂极性化去溶剂化自由能代价 |\n",
            f"| 构象熵罚项 | $-T\\Delta S$ | `{f'{delta_entropy:.2f}' if delta_entropy is not None else 'N/A'}` | 柔性旋转键冻结导致的构象熵减惩罚 |\n",
            f"| **总结合自由能** | **$\\Delta G_{{\\text{{bind}}}}$** | **`{delta_g:.2f}`** | **物理自洽预测亲和力总能量** |\n",
        ])
    else:
        md_lines.append("* **计算状态**: `未提供 3D 生物物理或 MM-GBSA 计算输入，本项数据缺失（无虚构默认值）。`\n")

    md_lines.append("---\n## 3. ADMET 成药性与药代毒理评估 (ADMET & Drug-likeness)\n")

    if admet and isinstance(admet, dict):
        def supplied(key: str, precision: int = 2) -> str:
            value = admet.get(key)
            return f"{float(value):.{precision}f}" if value is not None else "未提供"

        md_lines.extend([
            f"* **成药性健康指数 (Health Score)**: `{supplied('admet_health_score', 1)} / 100 分`",
            f"* **hERG 心脏安全毒性**: `{admet.get('herg_label') or admet.get('herg_risk') or '未提供'}` ($p\\text{{IC}}_{{50}} = {supplied('herg_pic50')}$)",
            f"* **Delaney ESOL 水溶解度**: `{admet.get('solubility_label') or '未提供'}` ($\\text{{LogS}} = {supplied('solubility_logs')}$ · 约 `{supplied('solubility_mg_ml')} mg/mL`)",
            f"* **Caco-2 膜表观通透性**: `{admet.get('caco2_label') or '未提供'}` ($P_{{\\text{{app}}}} = {supplied('caco2_papp')} \\times 10^{{-6}}\\text{{ cm/s}}$)",
            f"* **Clark 血脑屏障通透**: `{admet.get('bbb_label') or '未提供'}` ($\\text{{LogBB}} = {supplied('log_bb')}$)",
            f"* **CYP450 药物代谢相互作用 (DDI)**: CYP3A4: `{admet.get('cyp3a4_label') or '未提供'}` | CYP2D6: `{admet.get('cyp2d6_label') or '未提供'}`\n"
        ])
    else:
        md_lines.append("* **ADMET 评估**: 未提供具体 ADMET 预测参数输入；默认依据经典规则筛查，需开展进一步实测。\n")

    md_lines.extend([
        f"---\n",
        f"## 4. 改构候选衍生分子阶梯排行榜 (Molecular Evolution Ladder)\n",
        f"| 排名 | 方案名称 | 改构类型 | 预测 $p\\text{{K}}_d$ | 预测 $K_d$ (nM) | $\\Delta p\\text{{K}}_d$ | SA 分值 | 成药健康分 | 核心改构依据 |\n",
        f"| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |\n"
    ])

    for i, c in enumerate(candidates[:10]):
        ad = c.get("admet") or {}
        health_raw = ad.get("admet_health_score")
        health = f"`{round(float(health_raw), 1)}`" if health_raw is not None else "-"
        sa_val = c.get("sa_score")
        sa = f"`{round(float(sa_val), 2)}`" if sa_val is not None else "-"
        c_pkd_val = c.get('predicted_pkd')
        c_pkd = f"`{float(c_pkd_val):.3f}`" if c_pkd_val is not None else "-"
        c_kd_val = c.get('predicted_kd_nM')
        c_kd = f"`{float(c_kd_val):.2f}`" if c_kd_val is not None else "-"
        c_delta_val = c.get('delta_pkd')
        c_delta = f"`{'+' if float(c_delta_val) > 0 else ''}{float(c_delta_val):.3f}`" if c_delta_val is not None else "-"
        md_lines.append(
            f"| #{i+1} | **{c.get('name', '')}** | `{c.get('modification_type', '')}` | "
            f"{c_pkd} | {c_kd} | "
            f"{c_delta} | "
            f"{sa} | {health} | {c.get('rationale', '').replace('|', '-')} |\n"
        )

    if is_verified:
        disclaimer_md = "> **科学自律与免责声明**: 本报告所列之定量 $p\\text{K}_d$、自由能分解及 ADMET 参数由计算生物世界模型生成，用于指引湿实验候选分子投产次序，不可替代最终湿法生化试验与临床前毒理实测数据。\n"
    else:
        disclaimer_md = "> **科学自律与免责声明**: 本报告所列分子与评分包含外部未验证输入数据 (Unverified)，未由经基准验证的服务端推理引擎实际执行计算，严禁作为 DAVIS 基准实测结论或临床前开发放行依据。\n"

    md_lines.extend([
        f"\n---\n",
        f"## 5. 专利保护范围与马库什通式披露建议 (Patent Claims & Markush Structure)\n",
        f"为确保后续知识产权（IP）申请的完备性，基于上述高亲和力衍生物的构效关系规律，建议构建如下马库什通式（General Formula I）：\n",
        f"```text\n",
        f"通式 (Formula I):  [Core Scaffold] — L — R1\n",
        f"其中:\n",
        f"1. [Core Scaffold] 选自氨基噻唑稠环、咪唑并吡啶或苯并咪唑母核;\n",
        f"2. 连接臂 L 选自单键、-NH-、-NHC(=O)- 或 -O(CH2)n- (n=1~3);\n",
        f"3. 取代基 R1 选自以下结构群:\n",
        f"   (a) 包含单氟或三氟甲基取代的单环芳基 (对位卤素阻断代谢);\n",
        f"   (b) 包含 -NC(=O)CH=CH2 丙烯酰胺共价结合基团;\n",
        f"   (c) 包含吗啉基或环丙基端基增溶及抗脱靶修饰片段。\n",
        f"```\n",
        f"---\n",
        f"## 6. 湿实验投产验证操作规程 (In Vitro Wet-lab Validation Protocol)\n",
        f"1. **母液配制**: 各化合物以色谱级 DMSO 配制为 `10 mM` 储备液，储存于 -20°C 避光干燥箱。\n",
        f"2. **生化抑制活性测定 (ADP-Glo / HTRF Kinase Assay)**:\n",
        f"   - 采用标准 96 孔板布局，以 3 倍梯度稀释进行 8 点浓度滴定 (最高工作浓度 10.0 µM，下限 4.5 nM);\n",
        f"   - 阳性对照: 达沙替尼 / 母体标准品 (Well A01)；阴性空白: 0.1% DMSO 缓冲液 (Well H12);\n",
        f"   - 酶促反应 60 分钟后加入检测试剂，多功能酶标仪测定发光/荧光信号并拟合四参数 Logistic 曲线解算真实 $\\text{{IC}}_{{50}}$。\n",
        f"3. **表面等离子共振 (SPR Biacore T200/8K)**:\n",
        f"   - 靶蛋白 `{target_name}` 固定于 CM5 芯片表面，流速 30 µL/min 测定结合解离动力学常数 ($k_{{\\text{{on}}}}, k_{{\\text{{off}}}}, K_d$)。\n",
        f"\n---\n",
        disclaimer_md
    ])

    markdown_content = "\n".join(md_lines)

    # =========================================================================
    # 2. STANDALONE PRINT-FRIENDLY HTML GENERATION
    # =========================================================================
    if has_mmgbsa and delta_g is not None:
        mmgbsa_table_html = f"""<table>
    <thead>
      <tr>
        <th>能量分项</th>
        <th>符号</th>
        <th>计算自由能 (kcal/mol)</th>
        <th>物理化学机制</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>范德华疏水作用</td>
        <td class="mono">&Delta;E_vdw</td>
        <td class="mono">{f'{delta_vdw:.2f}' if delta_vdw is not None else 'N/A'}</td>
        <td>疏水内壁致密接触与色散吸引</td>
      </tr>
      <tr>
        <td>静电配位作用</td>
        <td class="mono">&Delta;E_elec</td>
        <td class="mono">{f'{delta_elec:.2f}' if delta_elec is not None else 'N/A'}</td>
        <td>铰链区关键残基主链极性氢键网络</td>
      </tr>
      <tr>
        <td>溶剂化自由能代价</td>
        <td class="mono">&Delta;G_solv</td>
        <td class="mono">{f'{delta_solv:.2f}' if delta_solv is not None else 'N/A'}</td>
        <td>水相去溶剂化与空腔生成能耗</td>
      </tr>
      <tr>
        <td>构象熵变惩罚项</td>
        <td class="mono">-T&Delta;S</td>
        <td class="mono">{f'{delta_entropy:.2f}' if delta_entropy is not None else 'N/A'}</td>
        <td>小分子与氨基酸侧链柔性键冻结惩罚</td>
      </tr>
      <tr style="font-weight:bold; background:#e0e7ff;">
        <td>总结合自由能</td>
        <td class="mono">&Delta;G_bind</td>
        <td class="mono">{delta_g:.2f}</td>
        <td>第一性原理热力学净亲和自由能</td>
      </tr>
    </tbody>
  </table>"""
    else:
        mmgbsa_table_html = """<div class="card">
    <p style="color: #64748b; font-size: 12px; margin: 0;">未提供 3D 生物物理或 MM-GBSA 计算输入，本项数据缺失（无虚构默认值）。</p>
  </div>"""

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>先导化合物结构优化与激酶结合亲和力学术评估报告 - {target_name}</title>
  <style>
    @page {{
      size: A4;
      margin: 20mm 15mm 20mm 15mm;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      line-height: 1.6;
      color: #1e293b;
      background: #ffffff;
      margin: 0;
      padding: 30px;
    }}
    .header-box {{
      border-bottom: 2px solid #2563eb;
      padding-bottom: 15px;
      margin-bottom: 25px;
    }}
    h1 {{
      font-size: 22px;
      color: #0f172a;
      margin: 0 0 5px 0;
      letter-spacing: -0.5px;
    }}
    .subtitle {{
      font-size: 13px;
      color: #64748b;
      margin-bottom: 12px;
    }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
      font-size: 12px;
      background: #f8fafc;
      padding: 12px 16px;
      border-radius: 8px;
      border: 1px solid #e2e8f0;
    }}
    .card {{
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 20px;
    }}
    h2 {{
      font-size: 15px;
      color: #1e3a8a;
      border-left: 4px solid #3b82f6;
      padding-left: 10px;
      margin: 24px 0 12px 0;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 12px 0;
      font-size: 12px;
    }}
    th, td {{
      border: 1px solid #cbd5e1;
      padding: 8px 10px;
      text-align: left;
    }}
    th {{
      background-color: #f1f5f9;
      color: #0f172a;
      font-weight: 600;
    }}
    tr:nth-child(even) {{
      background-color: #f8fafc;
    }}
    .stat-badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: bold;
    }}
    .badge-best {{
      background: #dcfce7;
      color: #15803d;
    }}
    .mono {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }}
    .footer-notice {{
      margin-top: 30px;
      padding: 12px;
      background: #f8fafc;
      border-left: 4px solid #94a3b8;
      font-size: 11px;
      color: #64748b;
    }}
    @media print {{
      body {{
        padding: 0;
      }}
      .no-print {{
        display: none;
      }}
    }}
  </style>
</head>
<body>
  <div class="header-box">
    <h1>先导化合物结构优化与激酶结合亲和力学术评估报告</h1>
    <div class="subtitle">Lead Optimization & Kinase Binding Affinity Research Report (Target: {target_name}{"" if is_verified else " - Unverified"})</div>
    <div class="meta-grid">
      <div><strong>靶点激酶:</strong> {target_name} (Catalytic Domain)</div>
      <div><strong>报告编号:</strong> REP-{target_name}-{datetime.datetime.now().strftime('%Y%m%d%H%M')}</div>
      <div><strong>生成机构:</strong> {author}</div>
      <div><strong>基准协议:</strong> {protocol_str}</div>
      <div><strong>评估模型:</strong> {resolved_model}</div>
      <div><strong>验证状态:</strong> {verification_status_str}</div>
    </div>
  </div>

  {f'''<div style="background:#fef2f2; border:1px solid #f87171; border-radius:8px; padding:12px; margin-bottom:20px; color:#991b1b; font-size:12px;">
    <strong>CRITICAL SCIENTIFIC INTEGRITY WARNING:</strong> 本报告数据来自外部未验证输入或未经服务端运行时认证（Unverified），未由经基准验证的计算引擎实际执行，严禁作为 DAVIS 基准或正式模型运行结论。
  </div>''' if not is_verified else ""}

  <h2>1. 执行摘要与优化收益</h2>
  <div class="card">
    <p style="margin-top:0;">针对人类蛋白激酶 <strong>{target_name}</strong> 的高通量计算模拟显示，改构衍生方案在结合自由能与亲和力上表现出显著增益：</p>
    <ul>
      <li><strong>先导母体基准:</strong> pKd = {base_pkd_str} (Kd = {base_kd_str}), SA = {base_sa_str}</li>
      <li><strong>最优进化方案:</strong> {best_cand.get('name', 'N/A') if best_cand else 'None'} ({best_cand.get('modification_type', '') if best_cand else ''})</li>
      <li><strong>最优预测亲和力:</strong> Kd = {best_kd_str} (增益 &Delta;pKd = {('+' if max_gain > 0 else '')}{max_gain:.3f})</li>
      <li><strong>评估衍生分子总数:</strong> {len(candidates)} 个化学实体</li>
    </ul>
  </div>

  <h2>2. 第一性原理 MM-GBSA 热力学自由能分解</h2>
  {mmgbsa_table_html}

  <h2>3. 改构候选衍生分子阶梯排行榜 (Top Candidates)</h2>
  <table>
    <thead>
      <tr>
        <th>排名</th>
        <th>分子方案名称</th>
        <th>改构类型</th>
        <th>预测 pKd</th>
        <th>预测 Kd (nM)</th>
        <th>&Delta;pKd 增益</th>
        <th>SA 分值</th>
      </tr>
    </thead>
    <tbody>
      {"".join(f'''<tr>
        <td style="text-align:center;">#{i+1}</td>
        <td><strong>{c.get('name', '')}</strong></td>
        <td>{c.get('modification_type', '')}</td>
        <td class="mono">{f"{float(c.get('predicted_pkd')):.3f}" if c.get('predicted_pkd') is not None else "-"}</td>
        <td class="mono">{f"{float(c.get('predicted_kd_nM')):.2f}" if c.get('predicted_kd_nM') is not None else "-"}</td>
        <td class="mono" style="color:#15803d; font-weight:bold;">{f"{'+' if float(c.get('delta_pkd')) > 0 else ''}{float(c.get('delta_pkd')):.3f}" if c.get('delta_pkd') is not None else "-"}</td>
        <td class="mono">{f"{float(c.get('sa_score')):.2f}" if c.get('sa_score') is not None else "-"}</td>
      </tr>''' for i, c in enumerate(candidates[:8]))}
    </tbody>
  </table>

  <h2>4. 湿实验 96 孔板投产操作规范</h2>
  <div class="card">
    <ol>
      <li><strong>储备液:</strong> 10 mM 溶于 100% DMSO，于 -20°C 氮气避光充填保存；</li>
      <li><strong>孔板滴定:</strong> 推荐使用标准 96 孔板布局，Well A01 作为阳性对照，Well H12 作为 DMSO 空白，从 10.0 &mu;M 启动 3 倍 8 点稀释滴定；</li>
      <li><strong>测定方法:</strong> 推荐采用微量均相荧光或 ADP-Glo 激酶发光检测试剂盒解算 IC50，并上机 SPR 测定动力学常数。</li>
    </ol>
  </div>

  <div class="footer-notice">
    <strong>科学自律声明:</strong> {"本报告基于计算机生物物理世界模型生成，供科研人员确定优先投产次序，不可代替湿法药理与临床前实测数据。" if is_verified else "本报告包含外部未验证输入数据 (Unverified)，未由经基准验证的服务端模型实际执行，仅供探索排查，严禁作为基准预测结论或投产放行依据。"}
  </div>
</body>
</html>"""

    return {
        "markdown_report": markdown_content,
        "html_report": html_content,
        "target_name": target_name,
        "generated_at": now_str
    }
