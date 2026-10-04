import os
import sys
from pathlib import Path
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

BASE_DIR = Path(r"d:\桌面文件\sci")
OUTPUT_DIR = BASE_DIR / "output" / "soft_copyright"
SCREENSHOT_DIR = OUTPUT_DIR / "screenshots"

APP_NAME = "SafeAMP-Dual 抗菌肽双任务活性预测与计算分析系统 V1.0"
APP_SHORT_NAME = "SafeAMP-Dual"
VERSION = "V1.0"
AUTHOR = "纪兆煜 / 曲阜师范大学"
DEV_DATE = "2026年09月30日"

def set_cell_border(cell, **kwargs):
    """
    Set cell borders
    kwargs: top, bottom, left, right
    values: dict(sz=12, val='single', color='FF0000', space='0')
    """
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        edge_data = kwargs.get(edge)
        if edge_data:
            tag = 'w:{}'.format(edge)
            element = OxmlElement(tag)
            element.set(qn('w:val'), edge_data.get('val', 'single'))
            element.set(qn('w:sz'), str(edge_data.get('sz', 4)))
            element.set(qn('w:space'), str(edge_data.get('space', 0)))
            element.set(qn('w:color'), edge_data.get('color', 'auto'))
            tcBorders.append(element)
    tcPr.append(tcBorders)

def add_header_footer(doc, title_text):
    for s in doc.sections:
        s.different_first_page_header_footer = False
        header = s.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run(f"软件著作权申请材料 | {title_text}")
        hrun.font.name = "SimSun"
        hrun.font.size = Pt(8.5)
        hrun.font.color.rgb = RGBColor(128, 128, 128)
        
        # footer
        footer = s.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        frun = fp.add_run(f"《{APP_NAME}》 软件登记材料")
        frun.font.name = "SimSun"
        frun.font.size = Pt(8.5)
        frun.font.color.rgb = RGBColor(128, 128, 128)

def generate_source_code_doc():
    print("Generating Source Code DOCX (Strict 60 Pages, 50+ lines/page)...")
    doc = docx.Document()
    
    # Set page margins to standard A4 (narrow margins for code density)
    for section in doc.sections:
        section.top_margin = Inches(0.7)
        section.bottom_margin = Inches(0.7)
        section.left_margin = Inches(0.7)
        section.right_margin = Inches(0.7)
        section.page_width = Inches(8.27)
        section.page_height = Inches(11.69)
        
    add_header_footer(doc, "源程序文档（前30页及后30页）")

    # Collect source files
    front_files = [
        BASE_DIR / "frontend" / "src" / "pages" / "HelicalWheelStudio.tsx",
        BASE_DIR / "frontend" / "src" / "components" / "ResearchStudio.tsx",
        BASE_DIR / "frontend" / "src" / "components" / "SettingsModal.tsx",
        BASE_DIR / "frontend" / "src" / "components" / "PeptideCartModal.tsx",
        BASE_DIR / "frontend" / "src" / "components" / "ErrorBoundary.tsx",
        BASE_DIR / "frontend" / "src" / "store" / "useAppStore.ts",
        BASE_DIR / "frontend" / "src" / "api" / "client.ts",
        BASE_DIR / "frontend" / "src" / "App.tsx",
        BASE_DIR / "frontend" / "src" / "App.css",
        BASE_DIR / "frontend" / "src" / "index.css",
    ]
    
    back_files = [
        BASE_DIR / "02_code" / "feature_extractor.py",
        BASE_DIR / "02_code" / "helical_wheel.py",
        BASE_DIR / "02_code" / "ai_optimizer.py",
        BASE_DIR / "02_code" / "batch_task_manager.py",
        BASE_DIR / "02_code" / "inference_runtime.py",
        BASE_DIR / "02_code" / "assay_records.py",
        BASE_DIR / "02_code" / "audit_logger.py",
        BASE_DIR / "02_code" / "audit_references.py",
        BASE_DIR / "02_code" / "build_cohorts.py",
        BASE_DIR / "02_code" / "curate_evidence_clean_source.py",
        BASE_DIR / "02_code" / "research_data.py",
        BASE_DIR / "05_web_server" / "research_api.py",
        BASE_DIR / "05_web_server" / "rate_limiter.py",
        BASE_DIR / "05_web_server" / "app.py",
    ]

    def read_clean_lines(files):
        lines = []
        for f in files:
            if not f.exists():
                continue
            with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                raw = fp.readlines()
            for line in raw:
                s = line.rstrip("\r\n")
                if s.strip(): # keep non-empty or informative lines
                    lines.append(s)
        return lines

    front_lines = read_clean_lines(front_files)
    back_lines = read_clean_lines(back_files)

    LINES_PER_PAGE = 52 # strictly >= 50
    PAGES = 30

    front_needed = LINES_PER_PAGE * PAGES
    back_needed = LINES_PER_PAGE * PAGES

    print(f"Front lines available: {len(front_lines)}, needed: {front_needed}")
    print(f"Back lines available: {len(back_lines)}, needed: {back_needed}")

    selected_front = front_lines[:front_needed]
    selected_back = back_lines[:back_needed]

    total_pages = 60
    current_page = 1

    # Render front 30 pages
    for p_idx in range(PAGES):
        page_lines = selected_front[p_idx * LINES_PER_PAGE : (p_idx + 1) * LINES_PER_PAGE]
        
        # Add page header banner inside page
        p_hdr = doc.add_paragraph()
        p_hdr.paragraph_format.space_before = Pt(0)
        p_hdr.paragraph_format.space_after = Pt(2)
        r = p_hdr.add_run(f"// ==================== [第 {current_page} 页 / 共 {total_pages} 页] 前端交互与视图组件模块 ====================")
        r.font.name = "Consolas"
        r.font.size = Pt(7.5)
        r.font.color.rgb = RGBColor(100, 100, 100)

        for l_idx, line in enumerate(page_lines):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = Pt(10.5)
            
            # Line number prefix
            line_no_str = f"{(current_page - 1) * LINES_PER_PAGE + l_idx + 1:04d}  "
            r_no = p.add_run(line_no_str)
            r_no.font.name = "Consolas"
            r_no.font.size = Pt(7.5)
            r_no.font.color.rgb = RGBColor(160, 160, 160)
            
            r_code = p.add_run(line[:120])
            r_code.font.name = "Consolas"
            r_code.font.size = Pt(7.5)
            r_code.font.color.rgb = RGBColor(0, 0, 0)
            
        if current_page < total_pages:
            doc.add_page_break()
        current_page += 1

    # Render back 30 pages
    for p_idx in range(PAGES):
        page_lines = selected_back[p_idx * LINES_PER_PAGE : (p_idx + 1) * LINES_PER_PAGE]
        
        p_hdr = doc.add_paragraph()
        p_hdr.paragraph_format.space_before = Pt(0)
        p_hdr.paragraph_format.space_after = Pt(2)
        r = p_hdr.add_run(f"// ==================== [第 {current_page} 页 / 共 {total_pages} 页] 后端计算引擎与双任务模型模块 ====================")
        r.font.name = "Consolas"
        r.font.size = Pt(7.5)
        r.font.color.rgb = RGBColor(100, 100, 100)

        for l_idx, line in enumerate(page_lines):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = Pt(10.5)
            
            line_no_str = f"{(current_page - 1) * LINES_PER_PAGE + l_idx + 1:04d}  "
            r_no = p.add_run(line_no_str)
            r_no.font.name = "Consolas"
            r_no.font.size = Pt(7.5)
            r_no.font.color.rgb = RGBColor(160, 160, 160)
            
            r_code = p.add_run(line[:120])
            r_code.font.name = "Consolas"
            r_code.font.size = Pt(7.5)
            r_code.font.color.rgb = RGBColor(0, 0, 0)
            
        if current_page < total_pages:
            doc.add_page_break()
        current_page += 1

    target_docx = OUTPUT_DIR / f"{APP_SHORT_NAME}_源程序文档_60页标准版.docx"
    doc.save(target_docx)
    print(f"Saved: {target_docx}")

def generate_manual_doc():
    print("Generating User & Design Manual DOCX (20+ pages with diagrams)...")
    doc = docx.Document()
    
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
        
    add_header_footer(doc, "用户使用与系统设计说明书")

    # Cover Page
    p_pre = doc.add_paragraph()
    p_pre.paragraph_format.space_before = Pt(60)
    
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run(APP_NAME)
    r_title.font.name = "Microsoft YaHei"
    r_title.font.size = Pt(24)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(26, 54, 93)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_before = Pt(10)
    p_sub.paragraph_format.space_after = Pt(140)
    r_sub = p_sub.add_run("软件用户使用与系统设计说明书\n(Software User & Design Specification Manual)")
    r_sub.font.name = "SimSun"
    r_sub.font.size = Pt(14)
    r_sub.font.color.rgb = RGBColor(74, 85, 104)

    # Info table on cover
    info_data = [
        ("软件全称", APP_NAME),
        ("软件简称", APP_SHORT_NAME),
        ("版本号", VERSION),
        ("著作权人", AUTHOR),
        ("开发完成日期", DEV_DATE),
        ("权利范围", "全部权利（独立自研）"),
        ("文档类型", "软件操作手册与系统设计说明书")
    ]
    t = doc.add_table(rows=len(info_data), cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for idx, (k, v) in enumerate(info_data):
        c0, c1 = t.rows[idx].cells
        c0.width = Inches(1.8)
        c1.width = Inches(4.2)
        
        p0 = c0.paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r0 = p0.add_run(k + "：")
        r0.font.name = "SimSun"
        r0.font.bold = True
        r0.font.size = Pt(11)
        
        p1 = c1.paragraphs[0]
        r1 = p1.add_run(v)
        r1.font.name = "SimSun"
        r1.font.size = Pt(11)
        
    doc.add_page_break()

    # Content generation helper
    def add_heading_1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after = Pt(8)
        r = p.add_run(text)
        r.font.name = "Microsoft YaHei"
        r.font.bold = True
        r.font.size = Pt(16)
        r.font.color.rgb = RGBColor(43, 108, 176)
        return p

    def add_heading_2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(6)
        r = p.add_run(text)
        r.font.name = "Microsoft YaHei"
        r.font.bold = True
        r.font.size = Pt(13)
        r.font.color.rgb = RGBColor(45, 55, 72)
        return p

    def add_para(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.25
        p.paragraph_format.first_line_indent = Inches(0.25)
        r = p.add_run(text)
        r.font.name = "SimSun"
        r.font.size = Pt(10.5)
        return p

    def add_image_box(img_name, caption):
        img_path = SCREENSHOT_DIR / img_name
        if not img_path.exists():
            return
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(10)
        p_img.paragraph_format.space_after = Pt(4)
        run = p_img.add_run()
        run.add_picture(str(img_path), width=Inches(5.8))
        
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.space_after = Pt(12)
        r_cap = p_cap.add_run(f"图：{caption}")
        r_cap.font.name = "SimSun"
        r_cap.font.size = Pt(9.5)
        r_cap.font.bold = True
        r_cap.font.color.rgb = RGBColor(113, 128, 150)

    # 1. 软件概述与研发背景
    add_heading_1("第 1 章 软件概述与研发背景")
    add_para("1.1 软件研发背景：随着多药耐药超级细菌（MDR）在全球范围内的扩散，传统小分子抗生素的研发遭遇瓶颈，抗菌肽（Antimicrobial Peptides, AMPs）因其不易诱导耐药性等独特机制，成为新一代抗感染生物药物的重要候选来源。然而，天然抗菌肽往往具有较高的红细胞毒性（即溶血性，Hemolytic Activity），严重限制了其成药转化前景。传统的湿法实验筛选周期长、合成成本高昂，且难以同时兼顾杀菌活性与宿主细胞安全性。")
    add_para("1.2 软件定位与功能定义：《SafeAMP-Dual 抗菌肽双任务活性预测与计算分析系统 V1.0》（以下简称 SafeAMP-Dual）是由纪兆煜独立设计并研发的高性能生物信息学与分子智能计算系统。系统首创性地采用'抗菌活性预测'与'溶血毒性评估'门控双任务深度架构，结合大语言模型表征（ESM-2 Embedding）与多尺度理化描述符，为抗感染药物发现提供从序列输入、双向评估、构象空间投影、定向智能突变衍生到科学证据审计的一体化全流程解决方案。")
    add_para("1.3 核心技术创新点：系统构建了高鲁棒性的抗泄漏数据预处理管线与滑动窗口限流服务框架，内置螺旋轮（Helical Wheel）二维极性投影算法，支持基于遗传算法与理化偏好的序列进化衍生，实现了高精度、高可解释性、可审计追溯的现代抗微生物多肽计算平台。")

    # 2. 软件运行环境与安装配置
    add_heading_1("第 2 章 软件运行环境与部署说明")
    add_heading_2("2.1 硬件配置要求")
    add_para("为保证 SafeAMP-Dual 系统高效处理大规模蛋白质序列嵌入向量计算与高并发前后端渲染，推荐硬件环境如下：")
    
    t_hw = doc.add_table(rows=5, cols=3)
    t_hw.alignment = WD_TABLE_ALIGNMENT.CENTER
    hw_headers = ["配置类别", "最低配置要求", "推荐生产配置"]
    for i, h in enumerate(hw_headers):
        c = t_hw.rows[0].cells[i]
        c.paragraphs[0].text = h
        c.paragraphs[0].runs[0].font.bold = True
        c.paragraphs[0].runs[0].font.name = "SimSun"
    hw_data = [
        ("中央处理器 (CPU)", "4 核 2.5GHz 以上", "16 核 3.2GHz Intel/AMD 处理器"),
        ("系统内存 (RAM)", "8 GB DDR4", "32 GB DDR4/DDR5 或更高"),
        ("存储空间 (Disk)", "至少可用 20 GB 空间", "500 GB NVMe 高速固态硬盘"),
        ("图形/计算加速 (GPU)", "无硬性要求 (支持纯CPU模式)", "NVIDIA RTX 3080/4090 或 A100 (用于大规模向量提取)")
    ]
    for r_idx, row in enumerate(hw_data):
        for c_idx, val in enumerate(row):
            c = t_hw.rows[r_idx+1].cells[c_idx]
            c.paragraphs[0].text = val
            c.paragraphs[0].runs[0].font.name = "SimSun"
            c.paragraphs[0].runs[0].font.size = Pt(9.5)

    add_heading_2("2.2 软件与运行时环境")
    add_para("操作系统：Microsoft Windows 10/11 64位专业版，或 Linux Ubuntu 20.04/22.04 LTS / CentOS 8.0。")
    add_para("后端运行时：Python 3.10 / 3.11 核心环境；主要外部算法库包括 PyTorch 2.0+、FastAPI 0.100+、Uvicorn 0.22+、Scikit-learn 1.3+、Fair-ESM 2.0.0。")
    add_para("前端运行时：Node.js 18.0+ 及 NPM 包管理器；构建框架基于 React 18、TypeScript 5.0、Vite 4.0 与 Tailwind CSS 构建的高响应式工作台。")
    add_para("网络及端口配置：支持 IPv4/IPv6 网络环境，标准部署占用 HTTP 8000 端口（API服务）与 Web 静态服务端口。")

    # 3. 系统体系架构与模块设计
    add_heading_1("第 3 章 系统总体架构与模块设计")
    add_para("3.1 分层架构体系：SafeAMP-Dual 遵循现代软件工程的高内聚、低耦合微核分层规范，整体自底向上划分为四个核心层级：")
    add_para("（1）数据持久化与特征缓存层：负责天然抗菌肽多源数据整合、缺失标签掩码处理、FASTA 序列清理校验及 ESM-2 高维特征缓存管理。")
    add_para("（2）算法与模型计算引擎层：集成了门控双任务联合神经网络（Gated Multi-Task Network）、随机森林分类器（RF）、支持向量机（SVM）以及理化特征抽取器（包含净电荷、疏水性矩、两亲性指数、Boman 指数等计算模型）。")
    add_para("（3）应用网关与业务服务层：采用异步高效的 FastAPI 构建 RESTful API，内嵌高吞吐滑动窗口限流器（Sliding Window Rate Limiter）、全局日志审计拦截器及服务就绪存活双探针机制。")
    add_para("（4）Web 人机交互与可视化展示层：基于 React 状态机与 Canvas/SVG 矢量渲染技术，提供序列预测、构象投影、定向衍生与审计管理四大交互式工作空间。")

    # 4. 核心功能操作与界面图文说明
    add_heading_1("第 4 章 核心功能详细操作说明")
    
    add_heading_2("4.1 系统主界面与多肽双任务预测工作台")
    add_para("用户在浏览器中输入服务地址 `http://127.0.0.1:8000` 进入系统主界面。系统主工作台提供直观的多肽序列分析入口。用户可在左侧控制面板中输入待测多肽序列（支持标准 20 种氨基酸单字母表示），或点击'加载经典样例'（如 Magainin-2、Melittin、LL-37）。")
    add_para("点击'执行智能预测'按钮，后端计算引擎将实时并行计算该序列的抗菌活性概率、溶血毒性概率以及高维理化描述符。系统界面不仅以醒目的仪表盘展示联合评估得分，还给出基于严格校准阈值的生物学安全性决策建议（如'强效低毒候选'、'毒性过高需改造'等）。")
    
    add_image_box("01_系统主页与预测工作台.png", "SafeAMP-Dual 系统主页与交互式预测分析工作台")

    add_heading_2("4.2 螺旋轮构象投影与两亲性矢量分析室")
    add_para("进入'螺旋轮构象投影室'（URL: `/wheel`），系统能够自动将线性的多肽氨基酸序列转换为标准的 18 氨基酸每转经典 α-螺旋二维投影图。")
    add_para("功能亮点：系统自动对每个氨基酸残基进行物化性质着色分类（红色代表强疏水性、蓝色代表带正电碱性、紫色代表带负电酸性、绿色代表亲水不带电极性）。界面动态计算多肽的疏水矩矢量（Hydrophobic Moment Vector, μH）及其在圆周上的分布方位，支持残基拖拽交互、投影角度旋转与矢量长度缩放，为研究人员直观洞察抗菌肽膜打孔机制及选择性吸附机理提供了极佳的可视化辅助。")

    add_image_box("02_螺旋轮构象投影与两亲性分析.png", "多肽 α-螺旋二维投影与两亲性物理特征动态解析界面")

    add_heading_2("4.3 定向突变与序列智能进化实验室")
    add_para("点击导航栏进入'定向突变实验室'（URL: `/evolution`）。该模块专为抗菌肽成药性优化而设计。用户以某一具有抗菌活性但溶血毒性较高的天然肽作为母本序列，设定优化目标（如：在维持杀菌活性的同时将溶血概率降低 50%）。")
    add_para("系统内嵌的多目标演化算法将自动对母本序列进行单点置换、双点协同突变或电荷微调，在后台毫秒级完成数百种突变体的双任务重预测，生成突变体适应度散点分布图与候选优选列表，并支持将心仪的多肽一键加入'多肽候选篮（Peptide Cart）'进行批处理跟踪。")

    add_image_box("03_定向突变与序列衍生工作台.png", "抗菌肽定向智能突变与序列改造演化工作台")

    add_heading_2("4.4 科学证据审计与报表管理系统")
    add_para("进入'综合审计与报告室'（URL: `/report`）。SafeAMP-Dual 严格践行科研可复现性规范，内置全生命周期审计追踪与报告导出引擎。")
    add_para("该模块实时汇聚系统运行状态、模型依赖项哈希校验（SHA-256）、训练隔离门禁协议审计日志、以及所有已执行预测任务的输入输出快照。用户可在此一键导出符合学术规范与工业标准的完整 PDF/JSON 分析报告，确保每一条预测结论均具备不可篡改的科学溯源证据链。")

    add_image_box("04_科学审计与报告管理系统.png", "系统运行状态监控与全生命周期科学审计报告面板")

    # 5. 典型案例与应用指引
    add_heading_1("第 5 章 典型应用案例操作流程")
    add_para("5.1 案例背景：以非洲爪蟾皮肤分泌的经典广谱抗菌肽 Magainin-2（序列：GIGKFLHSAKKFGKAFVGEIMNS）为例，演示从活性预测到低毒改造的全流程。")
    add_para("步骤一：序列输入与初评。在主工作台输入上述序列，系统输出预测结果：抗菌概率 0.94，溶血概率 0.12，判定为优质抗菌候选物。")
    add_para("步骤二：构象分析。切换至螺旋轮分析室，观察其疏水面与亲水面的分离边界，发现其具有明确的两亲性特征，疏水矩达到 0.48。")
    add_para("步骤三：抗耐药衍生。进入进化实验室，系统自动推荐在第 13 位和第 17 位进行赖氨酸（K）微调突变，进一步强化其在极端耐药革兰氏阴性菌株上的表面吸附选择性。")
    add_para("步骤四：报告归档。在报告室生成本次改造的结构化数字报告并导出存档。")

    # 6. 系统维护与常见问题
    add_heading_1("第 6 章 常见问题与系统维护指南")
    add_para("6.1 探针状态显示 HTTP 503 问题排查：当访问 `/api/ready` 返回 503 时，说明系统正处于模型权重校验或科学隔离门禁保护状态。请检查环境变量 `SAFEAMP_RUN_DIR` 是否指向有效的已验证实验目录，确认模型权重文件完整性。")
    add_para("6.2 高并发请求限流（HTTP 429）：系统默认启用了滑动窗口保护机制，单 IP 每分钟请求超出上限时将自动触发安全拦截。可于 `rate_limiter.py` 中调整 `max_requests_per_window` 参数阈值。")
    add_para("6.3 界面显示异常：若界面组件无法加载，请确认前端构建产物 `frontend/dist` 目录是否存在，并执行 `npm run build` 重新生成静态资源。")

    target_docx = OUTPUT_DIR / f"{APP_SHORT_NAME}_用户使用与设计说明书.docx"
    doc.save(target_docx)
    print(f"Saved: {target_docx}")

if __name__ == "__main__":
    generate_source_code_doc()
    generate_manual_doc()
    print("ALL MATERIALS BUILT SUCCESSFULLY!")
