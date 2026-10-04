# SafeAMP-Dual 3.0 多功能生物计算科研工作站实施计划 (Implementation Plan)

> **For agentic workers:** Implement the plan with the available Codex tools and repository conventions. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建并上线 SafeAMP-Dual 3.0 多工作台生物计算科研平台，包含高通量协同筛选、AI 定向进化突变、生信级 SVG 螺旋轮构象投影与学术报告工坊，并完成云服务器生产部署与端到端验证。

**Architecture:** 前端采用基于响应式暗黑科研美学（Dark Science Theme）的单页多工作台（SPA Tabbed Studios）架构，结合浏览器全局状态管理（Peptide Cart 暂存箱）；后端基于 FastAPI 驱动，融合 Meta ESM-2 (8M) 蛋白质语言模型、PyTorch 跨模态自适应门控双任务网络与 Eisenberg 疏水力矩螺旋投影算法。

**Tech Stack:** Python 3.10+, FastAPI, PyTorch 2.x, HuggingFace Transformers (Meta ESM-2), NumPy, SVG Vector Graphics, Vanilla JS, Modern Responsive CSS, Systemd, Nginx.

## Global Constraints

* 平台必须在 Windows (本地开发) 与 Ubuntu 22.04 LTS (云端 4 核 4GB 服务器 `62.234.141.184:8090`) 上 100% 兼容稳定运行。
* 严禁在 Markdown 或前端渲染中使用任何导致公式乱码的多行 LaTeX 环境（如 `\begin{aligned}`）；推导统一采用清晰的列点列表。
* 前端零沉重外部框架依赖（纯原生 HTML5/CSS3/Vanilla JS 与动态 SVG），保证极速冷启动与高并发毫秒级响应。
* 保护云服务器上正在运行的外部服务：端口 8000 (`reranker_server.py`) 与 8081 (`sub2api`) 绝不可干扰或中断。

---

### Task 1: 螺旋轮数学投影与物理化学算法模块 (Helical Wheel Engine)

**Files:**
- Create: `D:\桌面文件\sci\02_code\helical_wheel.py`
- Test: `D:\桌面文件\sci\02_code\test_helical_wheel.py`

**Interfaces:**
- Consumes: `feature_extractor.py:clean_sequence`, `KYTE_DOOLITTLE`, `CHARGE_ESTIMATE`
- Produces: `compute_helical_wheel_data(seq: str) -> Dict` containing:
  - `residues`: `List[Dict]` with `pos`, `aa`, `angle_deg`, `x`, `y`, `color_category`, `hydrophobicity`, `charge`
  - `hydrophobic_moment`: `float` (Eisenberg $\mu_H$)
  - `hydrophobic_angle_span`: `float`
  - `mean_hydrophobicity`: `float`
  - `net_charge`: `float`

- [x] **Step 1: 编写螺旋轮算法单元测试**

```python
# D:\桌面文件\sci\02_code\test_helical_wheel.py
import pytest
from helical_wheel import compute_helical_wheel_data

def test_helical_wheel_melittin():
    seq = "GIGAVLKVLTTGLPALISWIKRKRQQ"
    data = compute_helical_wheel_data(seq)
    assert len(data["residues"]) == 26
    # 验证第一个残基角度 (0 度)
    assert data["residues"][0]["angle_deg"] == 0.0
    # 验证第二个残基角度 (100 度)
    assert data["residues"][1]["angle_deg"] == 100.0
    # 验证疏水力矩大于 0
    assert data["hydrophobic_moment"] > 0.1
    # 验证电荷与疏水性存在
    assert "net_charge" in data
    assert "mean_hydrophobicity" in data

def test_helical_wheel_short():
    seq = "ADAD"
    data = compute_helical_wheel_data(seq)
    assert len(data["residues"]) == 4
    assert data["hydrophobic_moment"] >= 0.0
```

- [x] **Step 2: 运行测试验证失败**

```powershell
python -m pytest "D:\桌面文件\sci\02_code\test_helical_wheel.py" -v
```
预期输出：`ModuleNotFoundError: No module named 'helical_wheel'`

- [x] **Step 3: 编写 helical_wheel.py 实现**

```python
# D:\桌面文件\sci\02_code\helical_wheel.py
import math
from typing import Dict, List, Tuple
import numpy as np

from feature_extractor import clean_sequence, KYTE_DOOLITTLE, CHARGE_ESTIMATE

# 氨基酸生信色彩分类标度
def get_residue_category(aa: str) -> Tuple[str, str]:
    """返回 (分类名, 十六进制主色)"""
    hydro = KYTE_DOOLITTLE.get(aa, 0.0)
    charge = CHARGE_ESTIMATE.get(aa, 0.0)
    
    if charge > 0:
        return "basic", "#38bdf8"      # 碱性阳离子 (天蓝)
    elif charge < 0:
        return "acidic", "#f43f5e"     # 酸性阴离子 (玫红)
    elif hydro >= 1.8:
        return "hydrophobic", "#f59e0b" # 强疏水 (橙黄)
    elif hydro > 0:
        return "moderate", "#fbbf24"    # 中度疏水 (淡黄)
    else:
        return "polar", "#10b981"       # 极性中性 (草绿)

def compute_helical_wheel_data(seq: str, radius: float = 120.0) -> Dict:
    """
    计算基于 Schiffer-Edmundson 100 度模型的螺旋轮投影数据
    包含 Eisenberg 疏水力矩 (Hydrophobic Moment μH)
    """
    cleaned = clean_sequence(seq)
    L = len(cleaned)
    residues = []
    
    sum_x = 0.0
    sum_y = 0.0
    
    for idx, aa in enumerate(cleaned):
        # 每一个残基在圆周上步进 100 度
        angle_deg = (idx * 100.0) % 360.0
        angle_rad = math.radians(angle_deg)
        
        # 极坐标转换为笛卡尔坐标 (以 (160, 160) 为圆心)
        cx = 160.0 + radius * math.sin(angle_rad)
        cy = 160.0 - radius * math.cos(angle_rad)
        
        category, color = get_residue_category(aa)
        hydro = KYTE_DOOLITTLE.get(aa, 0.0)
        charge = CHARGE_ESTIMATE.get(aa, 0.0)
        
        # 归一化疏水性贡献向量
        h_norm = (hydro + 4.5) / 9.0  # 映射到 0~1
        sum_x += h_norm * math.sin(angle_rad)
        sum_y += -h_norm * math.cos(angle_rad)
        
        residues.append({
            "pos": idx + 1,
            "aa": aa,
            "angle_deg": round(angle_deg, 1),
            "x": round(cx, 1),
            "y": round(cy, 1),
            "category": category,
            "color": color,
            "hydrophobicity": hydro,
            "charge": charge
        })
        
    # Eisenberg 疏水力矩模长
    moment_mag = math.sqrt(sum_x ** 2 + sum_y ** 2) / (L + 1e-6)
    moment_angle_deg = (math.degrees(math.atan2(sum_x, -sum_y)) + 360.0) % 360.0
    
    net_charge = sum(CHARGE_ESTIMATE.get(aa, 0.0) for aa in cleaned)
    mean_hydro = float(np.mean([KYTE_DOOLITTLE.get(aa, 0.0) for aa in cleaned]))
    
    return {
        "sequence": cleaned,
        "length": L,
        "residues": residues,
        "hydrophobic_moment": round(moment_mag, 4),
        "moment_angle_deg": round(moment_angle_deg, 1),
        "net_charge": round(net_charge, 2),
        "mean_hydrophobicity": round(mean_hydro, 2)
    }
```

- [x] **Step 4: 重新运行测试验证通过**

```powershell
python -m pytest "D:\桌面文件\sci\02_code\test_helical_wheel.py" -v
```
预期输出：`2 passed in 0.05s`

---

### Task 2: 后端 FastAPI 路由集成与接口增强

**Files:**
- Modify: `D:\桌面文件\sci\05_web_server\app.py`
- Test: `python -c "import app..."`

**Interfaces:**
- Produces: `POST /api/helical_wheel` (接收 `{sequence: str}`, 返回螺旋轮计算数据)

- [x] **Step 1: 在 app.py 中引入并暴露 /api/helical_wheel 路由**

```python
from helical_wheel import compute_helical_wheel_data

@app.post("/api/helical_wheel")
def api_helical_wheel(req: SequenceRequest):
    """计算多肽 Schiffer-Edmundson 螺旋轮投影与两亲力矩"""
    try:
        cleaned = clean_sequence(req.sequence)
        data = compute_helical_wheel_data(cleaned)
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [x] **Step 2: 验证端点可用性**

```powershell
python -c "from app import api_helical_wheel, SequenceRequest; res = api_helical_wheel(SequenceRequest(sequence='GIGAVLKVLTTGLPALISWIKRKRQQ')); print('Moment:', res['hydrophobic_moment'])"
```
预期输出：`Moment: 0.2014`

---

### Task 3: 前端 SPA 多工作台框架与全局候选库 (Peptide Cart)

**Files:**
- Modify: `D:\桌面文件\sci\05_web_server\app.py` (HTML/CSS/JS 全景重构)

**Interfaces:**
- Produces:
  - Global Nav Tabs: `switchTab(tabId)`
  - Peptide Cart State: `addToCart(item)`, `removeFromCart(idx)`, `getCartItems()`, `renderCartModal()`
  - Quick Load Integration: 跨工作台调用 `sendToEvolution(seq)`, `sendToWheel(seq)`

- [x] \*\*Step 1: 编写四大工作台骨架 HTML 与 CSS 样式系统\*\*
  - 暗黑科研风格：CSS 变量 `--bg`, `--card`, `--primary`, `--border`, `--safe`, `--danger`
  - 顶部导航条：Logo、AI 模型状态徽章、`🛒 候选分子库` 触发器、`⚙️ LLM配置` 触发器
  - 4 个容器 `div#studio_screening`, `div#studio_evolution`, `div#studio_wheel`, `div#studio_report`
  - 暂存箱浮动抽屉/模态框 `div#cartModal`

- [x] \*\*Step 2: 编写全局暂存箱 JS 状态管理与事件派发\*\*
  - 维护内存数组 `window.peptideCart = []`
  - 本地缓存 `localStorage.setItem('safeamp_cart', ...)`
  - 徽章实时显示数量：`document.getElementById('cartBadge').innerText = peptideCart.length`

- [x] \*\*Step 3: 测试 Tab 切换与暂存箱状态增删\*\*

---

### Task 4: 工作台 1 —— 高通量协同筛选台与 Pareto 散点图实现

**Files:**
- Modify: `D:\桌面文件\sci\05_web_server\app.py`

**Interfaces:**
- Consumes: `POST /api/predict_batch`
- Produces:
  - 批量预测结果卡片渲染
  - SVG 双效 Pareto 交互散点图（动态绘制杀菌 vs 溶血气泡分布）
  - 短肽智能科普提示 Badge

- [x] \*\*Step 1: 编写 SVG Pareto 散点图渲染器 `renderParetoPlot(items)`\*\*
  - 画布坐标映射：横轴 $0 \sim 100\%$ 溶血，纵轴 $0 \sim 100\%$ 杀菌
  - 绘制辅助虚线（四象限基准：$AMP=50\%, Hemo=50\%$）
  - 左上角标注浅绿阴影区：“黄金成药候选区”
  - 每个分子渲染为一个带透明渐变与悬停高亮的 SVG `<circle>`，气泡大小与绿色深度映射 TSI
- [x] \*\*Step 2: 绑定筛选卡片与一键动作\*\*
  - `[📥 存入候选库]` ➔ 触发 `addToCart()`
  - `[⚡ 送入突变降毒]` ➔ 自动切换至 Tab 2 并填入该序列
  - `[🌀 绘制螺旋轮]` ➔ 自动切换至 Tab 3 并触发绘图

---

### Task 5: 工作台 2 —— AI 定向进化突变实验室实现

**Files:**
- Modify: `D:\桌面文件\sci\05_web_server\app.py`

**Interfaces:**
- Consumes: `POST /api/ai_optimize`
- Produces:
  - 母体分子选择器（支持读取暂存箱或手动输入）
  - 选择压微调交互条
  - Top-3 点突变方案卡片与母体/突变体指标并排对比
  - 药理学生物机理解析卡片

- [x] \*\*Step 1: 实现母体序列输入与暂存箱快速载入\*\*
  - 页面加载时自动监听 `peptideCart` 更新，填充下拉列表
- [x] \*\*Step 2: 实现突变结果对比卡片\*\*
  - 展示：突变前 TSI vs 突变后 TSI、溶血降低百分比（大号绿色高亮）
  - 呈现 AI 生成的结构化学说（破坏插入红细胞的核心疏水残基）
- [x] \*\*Step 3: 动作按钮串联\*\*
  - `[📥 存入候选库为新分子]`
  - `[🌀 去螺旋轮对比变化]`

---

### Task 6: 工作台 3 —— SVG 螺旋轮构象投影室实现

**Files:**
- Modify: `D:\桌面文件\sci\05_web_server\app.py`

**Interfaces:**
- Consumes: `POST /api/helical_wheel`
- Produces:
  - 经典 Schiffer-Edmundson 100° 矢量 SVG 螺旋轮
  - 残基性质分类色彩图例（阳离子蓝、阴离子红、疏水黄、极性绿）
  - Eisenberg 两亲疏水力矩中心矢量箭头
  - 一键导出高清 PNG / SVG 矢量文件

- [x] \*\*Step 1: 编写纯原生 SVG 螺旋轮生成器 `renderHelicalWheelSVG(wheelData)`\*\*
  - 绘制内同心圆与圆周骨架虚线
  - 渲染外环带残基圆球 `<circle>` 与氨基酸文本 `<text>`
  - 渲染相连残基之间的连线或圆心引线
  - 绘制中心疏水力矩向量箭头 `<line marker-end="url(#arrow)">`
- [x] \*\*Step 2: 编写理化参数面板\*\*
  - 实时显示：全长、净电荷、平均疏水性、两亲力矩数值 $\mu_H$
- [x] \*\*Step 3: 编写一键导出论文插图功能\*\*
  - 通过 Canvas 转码实现 `exportWheelPNG()`

---

### Task 7: 工作台 4 —— 科研报告与导出工坊实现

**Files:**
- Modify: `D:\桌面文件\sci\05_web_server\app.py`

**Interfaces:**
- Consumes: `POST /api/ai_report`
- Produces:
  - 综合成药性评级与膜穿孔机理卡片
  - 大模型在线学术报告长文渲染（若配置了 API Key）
  - 完整筛选 CSV 导出、Markdown 报告下载与标准 BibTeX 论文引用卡片

- [x] \*\*Step 1: 实现多源报告聚合展示\*\*
  - 展示成药梯队（Tier-1 / Tier-3）、机理推导（Toroidal Pore vs Carpet）、理化参数对照
  - 若调用自定义大模型成功，以富文本 Markdown 形式展示深度论文级推导
- [x] \*\*Step 2: 导出功能整合\*\*
  - `exportResultsCSV()`、`downloadMarkdownReport()`、`copyBibTeX()`

---

### Task 8: 云端部署与全流程端到端集成验证 (Cloud Deployment & Live E2E)

**Files:**
- Remote: `/home/ubuntu/safeamp-server/app.py`
- Remote: `/home/ubuntu/safeamp-server/helical_wheel.py`

**Interfaces:**
- Nginx 反代: `https://goodjzy.art/safeamp/`
- Systemd: `safeamp.service`

- [x] **Step 1: 同步最新代码至云端服务器**
  - 上传 `helical_wheel.py` 与升级后的 `app.py` 至 `/home/ubuntu/safeamp-server/`
- [x] **Step 2: 重启云端 safeamp 服务并检查日志**
  - `sudo systemctl restart safeamp`
  - 检查 `systemctl status safeamp` 与 `journalctl -u safeamp -n 30`
- [x] **Step 3: 端到端功能回归测试**
  - 测试 4 个工作台 API 返回状态（`200 OK`）
  - 测试蜂毒素 Melittin 从【筛选】➔【加入暂存箱】➔【突变实验室】➔【螺旋轮绘图】➔【生成报告】全链路流转
  - 验证浏览器访问 `https://goodjzy.art/safeamp/` 渲染无报错
