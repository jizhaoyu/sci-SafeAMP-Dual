"""Generate 22-slide high-impact seminar PowerPoint presentation for SafeAMP-Dual & DTI Studio.
Uses python-pptx to produce an elegant 16:9 deck with real test-artifact screenshots and full speaker notes.
"""
from pathlib import Path
import pptx
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

WORKSPACE = Path(r"D:\桌面文件\sci")
ARTIFACTS_DIR = WORKSPACE / "frontend" / "test-artifacts"
OUTPUT_PPTX = WORKSPACE / "SafeAMP_Dual_Seminar_Presentation.pptx"

# 16:9 Dimensions
SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)

# Color Palette
DARK_BG = RGBColor(15, 23, 42)       # Slate 900
LIGHT_BG = RGBColor(248, 250, 252)   # Slate 50
CARD_DARK = RGBColor(30, 41, 59)     # Slate 800
CARD_LIGHT = RGBColor(255, 255, 255) # Pure White
CARD_BORDER = RGBColor(51, 65, 85)   # Slate 700

PRIMARY_BLUE = RGBColor(37, 99, 235)  # Blue 600
CYAN_ACCENT = RGBColor(6, 182, 212)   # Cyan 500
INDIGO_ACCENT = RGBColor(99, 102, 241)# Indigo 500
EMERALD_GREEN = RGBColor(16, 185, 129)# Emerald 500
AMBER_YELLOW = RGBColor(245, 158, 11) # Amber 500
ROSE_RED = RGBColor(244, 63, 94)      # Rose 500

TEXT_WHITE = RGBColor(255, 255, 255)
TEXT_MUTED = RGBColor(148, 163, 184)  # Slate 400
TEXT_DARK = RGBColor(15, 23, 42)
TEXT_GRAY = RGBColor(71, 85, 105)

FONT_HEADING = "Microsoft YaHei"
FONT_BODY = "Microsoft YaHei"


def add_header(slide, kicker: str, title: str, subtitle: str = None, is_dark: bool = True):
    """Add standard structured header with kicker, title, and optional subtitle."""
    header_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(1.2))
    tf = header_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

    p_kicker = tf.paragraphs[0]
    p_kicker.text = kicker.upper()
    p_kicker.font.name = FONT_HEADING
    p_kicker.font.size = Pt(11)
    p_kicker.font.bold = True
    p_kicker.font.color.rgb = CYAN_ACCENT if is_dark else PRIMARY_BLUE

    p_title = tf.add_paragraph()
    p_title.text = title
    p_title.font.name = FONT_HEADING
    p_title.font.size = Pt(22)
    p_title.font.bold = True
    p_title.font.color.rgb = TEXT_WHITE if is_dark else TEXT_DARK
    p_title.space_after = Pt(2)

    if subtitle:
        p_sub = tf.add_paragraph()
        p_sub.text = subtitle
        p_sub.font.name = FONT_BODY
        p_sub.font.size = Pt(12)
        p_sub.font.color.rgb = TEXT_MUTED if is_dark else TEXT_GRAY


def set_slide_background(slide, color: RGBColor):
    """Create a full-bleed colored background rectangle."""
    bg_shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT)
    bg_shape.fill.solid()
    bg_shape.fill.fore_color.rgb = color
    bg_shape.line.fill.background()
    return bg_shape


def add_card(slide, left, top, width, height, bg_color: RGBColor, border_color: RGBColor = None):
    """Add a stylized card shape."""
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = bg_color
    if border_color:
        card.line.color.rgb = border_color
        card.line.width = Pt(1.5)
    else:
        card.line.fill.background()
    return card


def set_speaker_notes(slide, notes: str):
    """Attach speaker notes text to the slide."""
    notes_slide = slide.notes_slide
    text_frame = notes_slide.notes_text_frame
    text_frame.text = notes.strip()


def build_deck():
    prs = pptx.Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    blank_layout = prs.slide_layouts[6]

    # =========================================================================
    # SLIDE 1: 封面页 (Title Slide)
    # =========================================================================
    slide1 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide1, DARK_BG)

    # Accent decorative bars
    accent = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.8), Inches(0.15), Inches(3.6))
    accent.fill.solid()
    accent.fill.fore_color.rgb = CYAN_ACCENT
    accent.line.fill.background()

    tb = slide1.shapes.add_textbox(Inches(1.2), Inches(1.8), Inches(11.0), Inches(3.6))
    tf = tb.text_frame
    tf.word_wrap = True

    p0 = tf.paragraphs[0]
    p0.text = "RESEARCH SEMINAR · ACADEMIC PRESENTATION"
    p0.font.name = FONT_HEADING
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = CYAN_ACCENT
    p0.space_after = Pt(12)

    p1 = tf.add_paragraph()
    p1.text = "基于物理-AI双核与贝叶斯闭环的\n抗肿瘤激酶虚拟筛选平台"
    p1.font.name = FONT_HEADING
    p1.font.size = Pt(32)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_WHITE
    p1.space_after = Pt(14)

    p2 = tf.add_paragraph()
    p2.text = "从无偏世界模型、十万级商业库多样性海选到 96 孔板湿法数据飞轮"
    p2.font.name = FONT_BODY
    p2.font.size = Pt(16)
    p2.font.color.rgb = TEXT_MUTED
    p2.space_after = Pt(28)

    p3 = tf.add_paragraph()
    p3.text = "汇报人：计算生物学与机器学习课题组  |  指导老师：学术研讨课指导委员会  |  2026年10月"
    p3.font.name = FONT_BODY
    p3.font.size = Pt(13)
    p3.font.color.rgb = EMERALD_GREEN

    set_speaker_notes(slide1, """各位老师、各位同学，大家好！今天我汇报的题目是《基于物理-AI双核与贝叶斯闭环的抗肿瘤激酶虚拟筛选平台》。
本课题聚焦于当前肿瘤靶向药研发中‘继发性门控耐药频发、DTI 模型存在同源泄露假高分、AI 生成分子无法落地合成以及干湿实验断层’四大核心科学问题。我独立设计并实现了一套涵盖物理守恒、商业现货逆合成与主动学习闭环的全流程工业级系统。下面我将汇报具体的理论机制、算法设计与实验验证。""")

    # =========================================================================
    # SLIDE 2: 汇报目录与全景总览 (Executive Agenda)
    # =========================================================================
    slide2 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide2, DARK_BG)
    add_header(slide2, "AGENDA · 汇报大纲", "从科学问题界定到工业级全流程闭环", "五个核心篇章展开系统性汇报")

    modules = [
        ("01", "科学问题与批判反思", "临床门控耐药困境 · 现有 AIDD 同源泄漏与虚空分子批判", ROSE_RED),
        ("02", "理论基础与双核驱动", "零泄漏双盲图论基准 · 100维催化基序 · Stacking + MM-GBSA", PRIMARY_BLUE),
        ("03", "海选漏斗与逆合成树", "矢量化三级海选 · Butina 拓扑多样性聚类 · 真实商业 CAS 现货砌块", CYAN_ACCENT),
        ("04", "湿法闭环与数据飞轮", "ANSI 96 孔板自动化排布 · 经验贝叶斯核平滑 · 方差收缩主动学习", EMERALD_GREEN),
        ("05", "案例实证与合作课题", "ABL1/EGFR 耐药实证 · 21组自动化测试 · 面向导师的3大基金级课题", AMBER_YELLOW),
    ]

    card_w = Inches(11.7)
    card_h = Inches(0.9)
    for idx, (num, m_title, m_desc, col) in enumerate(modules):
        top_pos = Inches(1.8 + idx * 1.05)
        add_card(slide2, Inches(0.8), top_pos, card_w, card_h, CARD_DARK, CARD_BORDER)

        # Number badge
        nb = slide2.shapes.add_textbox(Inches(1.0), top_pos + Inches(0.12), Inches(0.8), Inches(0.65))
        np = nb.text_frame.paragraphs[0]
        np.text = num
        np.font.name = FONT_HEADING
        np.font.size = Pt(22)
        np.font.bold = True
        np.font.color.rgb = col

        # Text
        mt = slide2.shapes.add_textbox(Inches(2.0), top_pos + Inches(0.08), Inches(10.2), Inches(0.7))
        mp = mt.text_frame.paragraphs[0]
        mp.text = m_title
        mp.font.name = FONT_HEADING
        mp.font.size = Pt(15)
        mp.font.bold = True
        mp.font.color.rgb = TEXT_WHITE

        mp2 = mt.text_frame.add_paragraph()
        mp2.text = m_desc
        mp2.font.name = FONT_BODY
        mp2.font.size = Pt(11)
        mp2.font.color.rgb = TEXT_MUTED

    set_speaker_notes(slide2, """今天汇报分为五个模块：首先分析门控耐药机理与现有 AI 模型的数据泄漏痛点；随后展示零泄漏双盲基准与物理-数据双核架构；第三部分展示十万级商业库海选与真实 CAS 逆合成；第四部分汇报 96 孔板湿法调度与贝叶斯主动学习飞轮；最后汇报耐药突变实证与向导师抛出的三个基金级深化课题。""")

    # =========================================================================
    # SLIDE 3: 临床门控耐药痛点 (Gatekeeper Resistance)
    # =========================================================================
    slide3 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide3, DARK_BG)
    add_header(slide3, "CLINICAL PROBLEM · 科学问题", "临床靶向激酶抑制剂继发性耐药突变难题", "单点门控氨基酸位阻突变导致一代、二代抑制剂彻底失效")

    # 3 Cards
    c1 = add_card(slide3, Inches(0.8), Inches(1.8), Inches(3.6), Inches(4.8), CARD_DARK, CARD_BORDER)
    tb1 = slide3.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(3.2), Inches(4.4))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    p = tf1.paragraphs[0]
    p.text = "🚨 临床治疗深水区"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ROSE_RED
    p.space_after = Pt(12)
    p = tf1.add_paragraph()
    p.text = "• 靶向激酶药物（TKI）在服药 9~15 个月后极易爆发获得性突变；\n• ABL1-T315I（慢粒白血病超级耐药，传统药物全线瘫痪）；\n• EGFR-T790M / C797S（非小细胞肺癌核心耐药突变）；\n• BTK-C481S（B细胞淋巴瘤共价耐药突变）。"
    p.font.size = Pt(12)
    p.font.color.rgb = TEXT_MUTED

    c2 = add_card(slide3, Inches(4.8), Inches(1.8), Inches(3.6), Inches(4.8), CARD_DARK, CARD_BORDER)
    tb2 = slide3.shapes.add_textbox(Inches(5.0), Inches(2.0), Inches(3.2), Inches(4.4))
    tf2 = tb2.text_frame
    tf2.word_wrap = True
    p = tf2.paragraphs[0]
    p.text = "🔬 微观结构失活机制"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = AMBER_YELLOW
    p.space_after = Pt(12)
    p = tf2.add_paragraph()
    p.text = "• 门控残基（Gatekeeper）控制着通往疏水背口袋的通道；\n• T315 位点苏氨酸突变为异亮氨酸（Ile）后，额外引入大侧链 δ-甲基；\n• 刚性空间位阻直接阻断原研达沙替尼氨基噻唑母核的嵌入通道；\n• 导致结合自由能急剧恶化，抑制活性断崖式跌落至无活性区。"
    p.font.size = Pt(12)
    p.font.color.rgb = TEXT_MUTED

    c3 = add_card(slide3, Inches(8.8), Inches(1.8), Inches(3.7), Inches(4.8), CARD_DARK, CARD_BORDER)
    tb3 = slide3.shapes.add_textbox(Inches(9.0), Inches(2.0), Inches(3.3), Inches(4.4))
    tf3 = tb3.text_frame
    tf3.word_wrap = True
    p = tf3.paragraphs[0]
    p.text = "🎯 本课题攻关目标"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = CYAN_ACCENT
    p.space_after = Pt(12)
    p = tf3.add_paragraph()
    p.text = "• 构建对门控位阻极度敏感的物理-数据双核打分模型；\n• 在十万级现货库中秒级海选高活性骨架（Throughput > 1,500 cpd/s）；\n• 强制保证化学多样性与真实商业在售 CAS 砌块逆合成可行性；\n• 打通 96 孔板湿法实验与经验贝叶斯数据飞轮。"
    p.font.size = Pt(12)
    p.font.color.rgb = TEXT_MUTED

    set_speaker_notes(slide3, """抗肿瘤靶向小分子面临的最严峻挑战就是继发性门控突变。达沙替尼之所以对 ABL1-T315I 失效，本质上是 315 位点引入了体积庞大的异亮氨酸侧链，空间位阻直接堵死了原有通道。我们的研发目标就是构建能够敏锐识别这种立体阻碍、并直接给出可合成耐药新药的一体化计算系统。""")

    # =========================================================================
    # SLIDE 4: 现有 AIDD 缺陷批判 (Critical Review of AIDD)
    # =========================================================================
    slide4 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide4, DARK_BG)
    add_header(slide4, "CRITICAL ANALYSIS · 方法批判", "警惕现有 AI 制药的两大科研陷阱", "随机划分的数据泄露假高分 vs 脱离化学合成的‘虚空分子’")

    # Left card: Data Leakage
    add_card(slide4, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8), CARD_DARK, ROSE_RED)
    tb_l = slide4.shapes.add_textbox(Inches(1.1), Inches(2.1), Inches(5.0), Inches(4.2))
    tfl = tb_l.text_frame
    tfl.word_wrap = True
    p = tfl.paragraphs[0]
    p.text = "⚠️ 陷阱一：随机划分引发的‘同源数据泄露’"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ROSE_RED
    p.space_after = Pt(10)
    p = tfl.add_paragraph()
    p.text = "• 大量顶刊文献采用 Random Split 划分训练集与测试集；\n• 导致相同的药物母核或同源激酶同时跨越两端；\n• 模型学到的只是对母核的‘死记硬背’（Scaffold Memorization）；\n• 在全新突变体或冷门靶点上，预测精度呈断崖式雪崩；\n• 缺乏对未见化学空间的真实外推泛化能力。"
    p.font.size = Pt(12)
    p.font.color.rgb = TEXT_WHITE

    # Right card: Virtual Hallucinations
    add_card(slide4, Inches(6.9), Inches(1.8), Inches(5.6), Inches(4.8), CARD_DARK, AMBER_YELLOW)
    tb_r = slide4.shapes.add_textbox(Inches(7.2), Inches(2.1), Inches(5.0), Inches(4.2))
    tfr = tb_r.text_frame
    tfr.word_wrap = True
    p = tfr.paragraphs[0]
    p.text = "⚠️ 陷阱二：脱离现实供应链的‘虚空分子’"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = AMBER_YELLOW
    p.space_after = Pt(10)
    p = tfr.add_paragraph()
    p.text = "• 生成模型（扩散/VAE）追求理论打分极值；\n• 产生结构极其复杂、含有严重环张力与多立体中心的不稳定结构；\n• 化学试剂商无对应原材料供应，定制合成报价数万且周期漫长；\n• 90% 以上生成的分子被药化专家直接驳回无法投产；\n• 算完即止，与后续湿实验孔板操作完全脱节。"
    p.font.size = Pt(12)
    p.font.color.rgb = TEXT_WHITE

    set_speaker_notes(slide4, """在文献调研中，我们发现了两个致命的行业痛点：第一，随机数据划分使得模型学到了严重的配体记忆偏差，在未知突变体上毫无泛化性；第二，纯生成模型产生的所谓‘高分分子’，根本没有市售原料支持，在现实中完全合不出来。我们拒绝虚空分子，建立了严苛的零泄漏基准与真实 CAS 逆合成保障。""")

    # =========================================================================
    # SLIDE 5: 系统宏观架构与破局生态 (Macro Architecture)
    # =========================================================================
    slide5 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide5, DARK_BG)
    add_header(slide5, "SYSTEM ARCHITECTURE · 破局体系", "SafeAMP-Dual & DTI Studio 全流程平台架构", "贯通‘双盲预测 → 物理守恒 → 现货海选 → 逆合成规划 → 96孔板飞轮’")

    img_path = ARTIFACTS_DIR / "01_home_screen.png"
    if img_path.exists():
        slide5.shapes.add_picture(str(img_path), Inches(0.8), Inches(1.8), Inches(7.2), Inches(4.8))

    add_card(slide5, Inches(8.3), Inches(1.8), Inches(4.2), Inches(4.8), CARD_DARK, CYAN_ACCENT)
    tba = slide5.shapes.add_textbox(Inches(8.5), Inches(2.0), Inches(3.8), Inches(4.4))
    tfa = tba.text_frame
    tfa.word_wrap = True
    p = tfa.paragraphs[0]
    p.text = "🚀 五大核心技术支柱"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = CYAN_ACCENT
    p.space_after = Pt(10)
    p = tfa.add_paragraph()
    p.text = "1. 零泄漏图论双盲基准（Davis 25,772 对互作）\n2. 100维激酶催化基序 + MM-GBSA 物理双核驱动\n3. 三级海选漏斗与 Butina 拓扑化学多样性骨架聚类\n4. 真实在售商业 CAS 砌块树状逆合成规划\n5. ANSI 96 孔板自动化排布与经验贝叶斯数据飞轮\n\n✅ 经 Playwright 21 组端到端 UI 自动化验收 (Exit 0)"
    p.font.size = Pt(12)
    p.font.color.rgb = TEXT_WHITE

    set_speaker_notes(slide5, """如图所示，我们构建了一个拥有完整数据闭环的一站式工业级研发生态。平台从底层的零泄漏双盲基准、100维激酶催化基序，到三级海选漏斗、真实 CAS 砌块逆合成，再到 96 孔板移液直出与经验贝叶斯反馈，全部实现了代码化与全栈工程落地。""")

    # =========================================================================
    # SLIDE 6: 零泄漏双聚类图论切分协议 (Zero-Leakage Benchmark)
    # =========================================================================
    slide6 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide6, DARK_BG)
    add_header(slide6, "BENCHMARK PROTOCOL · 基准协议", "基于图论双聚类的零同源泄漏切分协议", "严格杜绝配体拓扑与激酶家族同源交叉，奠定真实泛化评价基石")

    # Table of blocks
    t_shape = slide6.shapes.add_table(5, 5, Inches(0.8), Inches(1.8), Inches(11.7), Inches(3.2))
    table = t_shape.table
    table.columns[0].width = Inches(2.5)
    table.columns[1].width = Inches(2.0)
    table.columns[2].width = Inches(2.0)
    table.columns[3].width = Inches(2.4)
    table.columns[4].width = Inches(2.8)

    headers = ["评估域定义 (Domain)", "样本量 (Pairs)", "占比 (%)", "相似度截断边界", "真实科研场景含义"]
    data = [
        ["Train Block (已知训练域)", "16,720 对", "64.88%", "Folds 1–4 × Folds 1–4", "基学习器与 Stacking 拟合学习"],
        ["Cold Drug Test (未见配体)", "3,952 对", "15.33%", "Tanimoto < 0.40", "先导物改构真实场景 (Seen Target)"],
        ["Cold Target Test (未见激酶)", "4,125 对", "16.01%", "NW Identity < 0.40", "新激酶靶点结合与选择性预测"],
        ["Strict Dual-Cold (双盲盲测)", "975 对", "3.78%", "双重 < 0.40 严格隔离", "极限外推真实泛化考验 (Zero-Leakage)"],
    ]
    for col_idx, h in enumerate(headers):
        cell = table.cell(0, col_idx)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = PRIMARY_BLUE
        p = cell.text_frame.paragraphs[0]
        p.font.name = FONT_HEADING
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = TEXT_WHITE

    for row_idx, row in enumerate(data):
        for col_idx, val in enumerate(row):
            cell = table.cell(row_idx + 1, col_idx)
            cell.text = val
            cell.fill.solid()
            cell.fill.fore_color.rgb = CARD_DARK
            p = cell.text_frame.paragraphs[0]
            p.font.name = FONT_BODY
            p.font.size = Pt(11)
            p.font.color.rgb = TEXT_WHITE if row_idx < 3 else CYAN_ACCENT
            if row_idx == 3:
                p.font.bold = True

    # Note card
    add_card(slide6, Inches(0.8), Inches(5.3), Inches(11.7), Inches(1.5), CARD_DARK, CARD_BORDER)
    tbn = slide6.shapes.add_textbox(Inches(1.0), Inches(5.4), Inches(11.3), Inches(1.3))
    tfn = tbn.text_frame
    tfn.word_wrap = True
    p = tfn.paragraphs[0]
    p.text = "💡 数学隔离保障：小分子基于 2048-bit 摩根指纹 Tanimoto 距离分为 58 簇；激酶基于 Needleman-Wunsch 全局比对分为 197 家族。在 Fold 5 盲测集与 Folds 1–4 之间，小分子最大相似度 0.3796 < 0.40，激酶最大序列同一性 0.3993 < 0.40，无任何交叉泄露。"
    p.font.size = Pt(11)
    p.font.color.rgb = TEXT_MUTED

    set_speaker_notes(slide6, """在基准协议上，我们基于图论构建了严格的双聚类切分。配体以 Tanimoto 0.40 聚类，激酶以 NW 比对 0.40 聚类。形成了互不重叠的四大评估域，其中 Strict Dual-Cold 包含 975 对样本，小分子和激酶在训练集中完全没有同源结构，为后续模型抗外推能力提供了毫无争议的试金石。""")

    # =========================================================================
    # SLIDE 7: 100 维激酶催化基序特征工程 (Kinase Domain Feature Engineering)
    # =========================================================================
    slide7 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide7, DARK_BG)
    add_header(slide7, "FEATURE ENGINEERING · 特征工程", "100 维激酶催化域特异性结构描述符", "超越通用全局氨基酸计数，精确编码催化活性中心与构象翻转开关")

    features = [
        ("AAC 基础频率 (20维)", "统计 20 种天然氨基酸全局分布频率，刻画激酶大分子的一级序列宏观组成基底。"),
        ("全局理化性质 (8维)", "Kyte-Doolittle 平均疏水性指数 (GRAVY)、净电荷、电荷密度、Boman 受体互作指数等。"),
        ("分段结构域 CTD (24维)", "沿 N-lobe (ATP结合区)、Hinge (铰链区)、C-lobe (底物配位区) 三段切分，独立统计电荷与疏水性。"),
        ("四大催化构象基序 (16维)", "G-loop [VILM]G[A-Z]G、VAIK 催化赖氨酸、HRD 磷酸转移环、DFG/DYG 活化开关（区分 DFG-in/out）。"),
        ("共轭二肽分类变换 (32维)", "按亲水/疏水/酸/碱四类理化聚类，计算相邻及 Skip-1 二肽构象转移概率矩阵。"),
    ]

    for idx, (f_title, f_desc) in enumerate(features):
        top_pos = Inches(1.8 + idx * 1.05)
        add_card(slide7, Inches(0.8), top_pos, Inches(11.7), Inches(0.92), CARD_DARK, CARD_BORDER)

        tbf = slide7.shapes.add_textbox(Inches(1.0), top_pos + Inches(0.1), Inches(11.3), Inches(0.75))
        p = tbf.text_frame.paragraphs[0]
        p.text = f_title
        p.font.name = FONT_HEADING
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = CYAN_ACCENT

        p2 = tbf.text_frame.add_paragraph()
        p2.text = f_desc
        p2.font.name = FONT_BODY
        p2.font.size = Pt(11)
        p2.font.color.rgb = TEXT_WHITE

    set_speaker_notes(slide7, """常规模型把激酶看成一串死序列。我们设计了 100 维激酶催化域特异性描述符：不仅有基础频率和分段 CTD，更关键的是用正则精确抓取了 G-loop、VAIK、HRD 和 DFG 活化环四个催化开关的空间坐标与电荷，使模型能够感知激酶活性态与非活性态的翻转。配对小分子 2048 维指纹构成 2,156 维输入。""")

    # =========================================================================
    # SLIDE 8: 5 折 OOF Stacking 世界模型与消融结果 (Stacking World Model)
    # =========================================================================
    slide8 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide8, DARK_BG)
    add_header(slide8, "MODEL ARCHITECTURE · 模型架构", "5折 OOF 凸优化 Stacking 集成与消融实测", "在已知域实现 RMSE 下降 21.0%，先导优化域 CI 达到 0.7571")

    # Metrics table
    t_shape8 = slide8.shapes.add_table(5, 7, Inches(0.8), Inches(1.8), Inches(11.7), Inches(3.2))
    table8 = t_shape8.table
    table8.columns[0].width = Inches(2.2)
    table8.columns[1].width = Inches(2.3)
    table8.columns[2].width = Inches(1.4)
    table8.columns[3].width = Inches(1.4)
    table8.columns[4].width = Inches(1.4)
    table8.columns[5].width = Inches(1.4)
    table8.columns[6].width = Inches(1.6)

    h8 = ["评估域", "模型架构", "RMSE", "MAE", "Pearson r", "Spearman ρ", "Concordance (CI)"]
    d8 = [
        ["Train Block (16,720)", "Baseline Ridge", "0.7042", "0.4531", "0.5383", "0.5091", "0.7808"],
        ["Train Block (16,720)", "Stacking World Model", "0.5566", "0.3442", "0.7485", "0.6204", "0.8494"],
        ["Cold Drug (3,952)", "Baseline Ridge", "0.8237", "0.5617", "0.4464", "0.4899", "0.7322"],
        ["Cold Drug (3,952)", "Stacking World Model", "0.8076", "0.4882", "0.5096", "0.4952", "0.7571"],
    ]
    for c_idx, h in enumerate(h8):
        cell = table8.cell(0, c_idx)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = INDIGO_ACCENT
        p = cell.text_frame.paragraphs[0]
        p.font.name = FONT_HEADING
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = TEXT_WHITE

    for r_idx, row in enumerate(d8):
        for c_idx, val in enumerate(row):
            cell = table8.cell(r_idx + 1, c_idx)
            cell.text = val
            cell.fill.solid()
            cell.fill.fore_color.rgb = CARD_DARK
            p = cell.text_frame.paragraphs[0]
            p.font.name = FONT_BODY
            p.font.size = Pt(11)
            p.font.color.rgb = EMERALD_GREEN if "Stacking" in row[1] else TEXT_WHITE
            if "Stacking" in row[1]:
                p.font.bold = True

    # Findings
    add_card(slide8, Inches(0.8), Inches(5.2), Inches(11.7), Inches(1.6), CARD_DARK, CARD_BORDER)
    tbf8 = slide8.shapes.add_textbox(Inches(1.0), Inches(5.3), Inches(11.3), Inches(1.4))
    p = tbf8.text_frame.paragraphs[0]
    p.text = "🎯 关键实验发现："
    p.font.name = FONT_HEADING
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = CYAN_ACCENT
    p.space_after = Pt(4)
    p = tbf8.text_frame.add_paragraph()
    p.text = "1. 拟合残差大幅消除：Train Block 上 RMSE 相对下降 21.0% (0.7042 → 0.5566)，Pearson r 显著提升至 0.7485。\n2. 先导优化实用域跃升：Cold Drug 域 CI 达到 0.7571 (+0.0249 增益)，精准识别未见配体的相对活性排序。\n3. 元学习非负凸优化：通过带非负约束的 Ridge 拟合 OOF 元特征，权重聚焦于非线性 HistGBM (1.1743) 与正则通道。"
    p.font.size = Pt(11)
    p.font.color.rgb = TEXT_MUTED

    set_speaker_notes(slide8, """这是我们的消融实验硬数据。在已知域上，Stacking 集成使拟合均方根误差下降了整整 21.0%，相关系数飙升至 0.7485；在 Cold Drug 先导物优化真实场景中，一致性指数 CI 达到 0.7571，充分证明了非线性梯度提升与催化基序结合的拟合威力。""")

    # =========================================================================
    # SLIDE 9: MM-GBSA 物理结合自由能守恒 (MM-GBSA Physics Dual Core)
    # =========================================================================
    slide9 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide9, DARK_BG)
    add_header(slide9, "PHYSICS ENGINE · 物理自由能", "第一性原理 MM-GBSA 物理结合自由能守恒", "范德华排斥势垒与溶剂化能量分解，彻底杜绝神经网络‘位阻幻觉’")

    # Formula card
    add_card(slide9, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8), CARD_DARK, PRIMARY_BLUE)
    tbf9 = slide9.shapes.add_textbox(Inches(1.1), Inches(2.0), Inches(5.0), Inches(4.4))
    tf9 = tbf9.text_frame
    tf9.word_wrap = True
    p = tf9.paragraphs[0]
    p.text = "📐 MM-GBSA 能量分解方程"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = CYAN_ACCENT
    p.space_after = Pt(10)
    p = tf9.add_paragraph()
    p.text = "ΔG_bind = ΔE_vdw + ΔE_ele + ΔG_solv - TΔS\n\n• ΔE_vdw：Lennard-Jones 6-12 势能项，对原子空间重叠具有 r^(-12) 极其强烈的极性排斥；\n• ΔE_ele：库仑静电吸引与排斥项；\n• ΔG_solv：极性溶剂化 (GB模型) 与非极性溶剂化能 (SASA 表面积模型) 耦合；\n• -TΔS：构象熵损失估算。"
    p.font.size = Pt(12)
    p.font.color.rgb = TEXT_WHITE

    # Physics enforcement card
    add_card(slide9, Inches(6.9), Inches(1.8), Inches(5.6), Inches(4.8), CARD_DARK, ROSE_RED)
    tbp = slide9.shapes.add_textbox(Inches(7.2), Inches(2.0), Inches(5.0), Inches(4.4))
    tfp = tbp.text_frame
    tfp.word_wrap = True
    p = tfp.paragraphs[0]
    p.text = "🛡️ 物理守恒硬约束拦截机制"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ROSE_RED
    p.space_after = Pt(10)
    p = tfp.add_paragraph()
    p.text = "• 神经网络黑盒面对耐药突变（如 ABL1-T315I）容易受已知数据误导给出虚高活性；\n• MM-GBSA 物理场实时计算空间微观距离：\n  当 r_ij < r_vdw 时，范德华排斥能急剧激增 (+40 ~ +60 kcal/mol)；\n• 物理能量直接对总亲和力进行硬性位阻惩罚；\n• 确保任何小分子只要在物理空间发生碰撞，打分直接一票否决，保障常识守恒。"
    p.font.size = Pt(12)
    p.font.color.rgb = TEXT_WHITE

    set_speaker_notes(slide9, """AI 最大的弱点是没有物理常识。我们引入了 MM-GBSA 自由能分解方程作为物理锚点。当突变残基导致原子发生重叠碰撞时，范德华 12 次方斥力项呈指数级激增，物理力场直接对亲和力实施硬惩罚。这种双核架构，确保了系统对突变位阻的极高敏感性。""")

    # =========================================================================
    # SLIDE 10: 微观口袋 3D WebGL 交互可视化 (3D Pocket & Sketcher)
    # =========================================================================
    slide10 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide10, DARK_BG)
    add_header(slide10, "VISUALIZATION · 微观交互", "3D WebGL 激酶结合口袋与分子手绘画板", "基于 3Dmol.js 原生开发免插件轻量化构象交互，亚埃级测量氢键与门控残基")

    img_p1 = ARTIFACTS_DIR / "09_3d_kinase_pocket_viewer.png"
    if img_p1.exists():
        slide10.shapes.add_picture(str(img_p1), Inches(0.8), Inches(1.8), Inches(6.0), Inches(4.8))

    img_p2 = ARTIFACTS_DIR / "08_molecule_sketcher_modal.png"
    if img_p2.exists():
        slide10.shapes.add_picture(str(img_p2), Inches(7.1), Inches(1.8), Inches(5.4), Inches(4.8))

    set_speaker_notes(slide10, """这是系统的前端交互能力。基于 3Dmol.js 我们原生开发了免安装、轻量化的 WebGL 3D 分子口袋浏览器。左图展示了达沙替尼在 ABL1 口袋中的微观构象，黄色虚线精确标定了亚埃级的关键氢键；右图集成了 Ketcher 分子画板，支持药化人员自由手绘并双向同步 SMILES。""")

    # =========================================================================
    # SLIDE 11: 超大规模虚拟筛选三级漏斗 (Tri-Stage Funnel)
    # =========================================================================
    slide11 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide11, DARK_BG)
    add_header(slide11, "VIRTUAL SCREENING · 虚拟筛选", "超大规模商业现货分子库三级海选漏斗", "SIMD 矢量化点积初筛 (>1,500 cpd/s) 与世界模型/MM-GBSA 双核高精重排")

    f_steps = [
        ("STAGE 1 · 矢量化指纹粗筛 (Vectorized Pre-Screen)", "通过 uint64 位打包矩阵与 AVX2/SIMD 指令集批量计算 2048-bit 摩根指纹点积。单核筛选通量突破 1,500 compounds/sec，毫秒级过滤掉 90% 不匹配化学空间。", PRIMARY_BLUE),
        ("STAGE 2 · 双核高精重排 (Dual-Core Re-ranking)", "将初筛留存的前 100~500 个候选分子输入第二代世界模型与 MM-GBSA 物理自由能计算核心，输出高精度定量预测值 pKd 与 ΔG_bind，筛选 pKd ≥ 7.0 强活性分子。", CYAN_ACCENT),
        ("STAGE 3 · Butina 拓扑多样性分群 (Diversity Clustering)", "计算留存分子的全对称距离矩阵，通过拓扑截断 (Cutoff = 0.40) 消除同质化密集聚集，优先挑选各骨架簇质心化合物 (Centroids) 作为代表 Hits 输出。", EMERALD_GREEN),
    ]

    for idx, (st_t, st_d, col) in enumerate(f_steps):
        top_pos = Inches(1.8 + idx * 1.7)
        add_card(slide11, Inches(0.8), top_pos, Inches(11.7), Inches(1.5), CARD_DARK, col)

        tbs = slide11.shapes.add_textbox(Inches(1.1), top_pos + Inches(0.15), Inches(11.1), Inches(1.2))
        p = tbs.text_frame.paragraphs[0]
        p.text = st_t
        p.font.name = FONT_HEADING
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = col
        p.space_after = Pt(6)

        p2 = tbs.text_frame.add_paragraph()
        p2.text = st_d
        p2.font.name = FONT_BODY
        p2.font.size = Pt(12)
        p2.font.color.rgb = TEXT_WHITE

    set_speaker_notes(slide11, """在海选端，面对十万级商业库，传统分子对接需要耗费数周。我们设计了三级漏斗：第一级采用矢量化指纹在毫秒内完成初筛，吞吐量超过 1500 分子/秒；第二级调用世界模型与物理结合能进行高精重排；第三级则引入 Butina 聚类消除骨架同质化。""")

    # =========================================================================
    # SLIDE 12: Butina 拓扑化学多样性骨架聚类 (Butina Clustering)
    # =========================================================================
    slide12 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide12, DARK_BG)
    add_header(slide12, "DIVERSITY CLUSTERING · 骨架多样性", "Butina 图论聚类算法：打破‘同质化陷阱’", "基于距离矩阵截断挑选化学空间独立的簇质心化合物，锁定多条专利路线")

    add_card(slide12, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8), CARD_DARK, CARD_BORDER)
    tb_b1 = slide12.shapes.add_textbox(Inches(1.1), Inches(2.0), Inches(5.0), Inches(4.4))
    p = tb_b1.text_frame.paragraphs[0]
    p.text = "📊 传统虚拟筛选的‘同质化陷阱’"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ROSE_RED
    p.space_after = Pt(10)
    p = tb_b1.text_frame.add_paragraph()
    p.text = "• 传统打分排序仅取 Top 20 绝对高分；\n• 筛选结果往往全部属于某一特定优势母核的微小同系物（例如仅侧链多一个甲基或氟原子）；\n• 风险极度集中：一旦该骨架在湿法体内实验中发生毒性崩溃或代谢阻断，整个项目批次全部报废；\n• 无法为药化团队提供多条具有独立专利保护空间的全新先导路线。"
    p.font.size = Pt(12)
    p.font.color.rgb = TEXT_MUTED

    add_card(slide12, Inches(6.9), Inches(1.8), Inches(5.6), Inches(4.8), CARD_DARK, EMERALD_GREEN)
    tb_b2 = slide12.shapes.add_textbox(Inches(7.2), Inches(2.0), Inches(5.0), Inches(4.4))
    p = tb_b2.text_frame.paragraphs[0]
    p.text = "⚙️ Butina 聚类算法执行机制"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = EMERALD_GREEN
    p.space_after = Pt(10)
    p = tb_b2.text_frame.add_paragraph()
    p.text = "1. 构建对称距离矩阵：D_ij = 1.0 - Tanimoto(fp_i, fp_j)；\n2. 设定拓扑截断半径：Cutoff = 0.40（相似度 ≥ 0.60 视为同类骨架）；\n3. 统计各化合物在截断半径内的邻域度数（Degree）；\n4. 倒序贪心选择邻域度最大的分子作为 Cluster Centroid（质心）；\n5. 将其邻居全部归入该簇并移出候选池，递归迭代直至收敛；\n6. 强制输出各簇代表 Hits，化学空间完全正交独立。"
    p.font.size = Pt(12)
    p.font.color.rgb = TEXT_WHITE

    set_speaker_notes(slide12, """传统虚拟筛选很容易掉进同质化陷阱：排名前 20 的分子全是微调近亲。我们实现了 Butina 聚类算法：通过构建 Tanimoto 距离矩阵并以 0.40 截断，算法按邻域度挑选各簇的质心化合物。这确保了输出的 Hits 不仅活性优异，且在化学空间上彼此独立，为药企锁定了多条平行的专利申报空间。""")

    # =========================================================================
    # SLIDE 13: 商业现货库海选实战验证 (Virtual Screening Explorer)
    # =========================================================================
    slide13 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide13, DARK_BG)
    add_header(slide13, "SCREENING CASE · 海选实证", "商业现货库三级海选与多样性 Hits 浏览器", "Enamine 激酶特权库秒级淘选，Butina 算法自动离析 4 类独立化学骨架簇")

    img_s1 = ARTIFACTS_DIR / "20_ultra_large_virtual_screening.png"
    if img_s1.exists():
        slide13.shapes.add_picture(str(img_s1), Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8))

    img_s2 = ARTIFACTS_DIR / "21_virtual_screening_hits_explorer.png"
    if img_s2.exists():
        slide13.shapes.add_picture(str(img_s2), Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.8))

    set_speaker_notes(slide13, """这两张图展示了我们在 Enamine 激酶特权分子库中的海选实测。左图为筛选参数配置面板，1.42秒即完成全流程；右图展示了筛选出的多样性 Hits 浏览器。系统自动将其划分为 4 组完全不同的骨架簇，质心分子均突破 7.20 pKd，且直接支持一键流转到逆合成或 96 孔板。""")

    # =========================================================================
    # SLIDE 14: 3D 口袋从头分子扩散与骨架跃迁 (De Novo Generation)
    # =========================================================================
    slide14 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide14, DARK_BG)
    add_header(slide14, "DE NOVO EVOLUTION · 从头生成", "3D 口袋从头分子扩散生成与骨架跃迁", "演化三炔基刚性骨架克服 ABL1-T315I 门控位阻，预测亲和力跃升至 7.820 pKd")

    img_d = ARTIFACTS_DIR / "18_de_novo_pocket_generation.png"
    if img_d.exists():
        slide14.shapes.add_picture(str(img_d), Inches(0.8), Inches(1.8), Inches(7.4), Inches(4.8))

    add_card(slide14, Inches(8.5), Inches(1.8), Inches(4.0), Inches(4.8), CARD_DARK, AMBER_YELLOW)
    tbd = slide14.shapes.add_textbox(Inches(8.7), Inches(2.0), Inches(3.6), Inches(4.4))
    p = tbd.text_frame.paragraphs[0]
    p.text = "🎯 骨架跃迁实证指标"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = AMBER_YELLOW
    p.space_after = Pt(10)
    p = tbd.text_frame.add_paragraph()
    p.text = "• 靶点：ABL1-T315I 超级耐药突变\n• 原研达沙替尼：pK_d = 5.659 (失效)\n• 生成候选物：引入刚性碳碳三键骨架 (类似第三代普纳替尼核心特征)\n• 结合亲和力：预测 pK_d = 7.820 (Kd ≈ 15.1 nM)\n• 物理结合能：ΔG_bind = -48.2 kcal/mol\n• 合成可达性：SA Score = 3.25 (易合成)\n• IP 新颖度：0.8872 (具备专利独占性)"
    p.font.size = Pt(12)
    p.font.color.rgb = TEXT_WHITE

    set_speaker_notes(slide14, """这是平台针对 ABL1-T315I 耐药突变的从头分子扩散生成实证。达沙替尼在突变后活性崩塌；系统通过骨架跃迁，生成了含有碳碳三炔键的刚性核心化合物（类似普纳替尼），刚性直线结构完美绕开 315 位异亮氨酸的空间位阻，预测活性跃升至 7.820 pKd，且 SA Score 仅为 3.25。""")

    # =========================================================================
    # SLIDE 15: 真实商业 CAS 砌块逆合成规划 (Retrosynthesis)
    # =========================================================================
    slide15 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide15, DARK_BG)
    add_header(slide15, "RETROSYNTHESIS · 逆合成规划", "基于商业现货 CAS 砌块的前向逆合成树", "绑定百灵威/Sigma在售原料与成熟人名反应模板，前向计算工艺综合收率")

    img_r = ARTIFACTS_DIR / "19_ai_retrosynthesis_route.png"
    if img_r.exists():
        slide15.shapes.add_picture(str(img_r), Inches(0.8), Inches(1.8), Inches(7.4), Inches(4.8))

    add_card(slide15, Inches(8.5), Inches(1.8), Inches(4.0), Inches(4.8), CARD_DARK, EMERALD_GREEN)
    tbr = slide15.shapes.add_textbox(Inches(8.7), Inches(2.0), Inches(3.6), Inches(4.4))
    p = tbr.text_frame.paragraphs[0]
    p.text = "🧪 真实化学落地约束"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = EMERALD_GREEN
    p.space_after = Pt(10)
    p = tbr.text_frame.add_paragraph()
    p.text = "• 递归逆向拆解为商业在售 CAS 原料：\n  Precursor 1: 4-Bromo-2-chlorotoluene\n  Precursor 2: 4-(Piperazin-1-yl)pyridine\n• 核心反应模板驱动：\n  Step 1: Suzuki-Miyaura 偶联\n  Step 2: Buchwald-Hartwig 胺化\n  Step 3: 酰胺键缩合反应\n• 催化剂体系自动匹配：\n  Pd(PPh3)4, Cs2CO3, DIPEA, HATU\n• 前向工艺综合收率预计：68.5%\n• 化学家拿清单即可直接下单投产！"
    p.font.size = Pt(12)
    p.font.color.rgb = TEXT_WHITE

    set_speaker_notes(slide15, """很多 AI 生成的分子化学家根本合不出来。我们的逆合成引擎，将生成的分子反推为百灵威、Sigma 在售的真实 CAS 商业现货原料，并详细列出 Suzuki 偶联、Buchwald 胺化等标准反应条件与催化剂，综合收率达到 68.5%，彻底消除了虚拟分子无法落地的鸿沟。""")

    # =========================================================================
    # SLIDE 16: 工业级多维成药性 ADMET 评价 (ADMET Radar)
    # =========================================================================
    slide16 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide16, DARK_BG)
    add_header(slide16, "DRUGLIKENESS · 成药性评估", "工业级五维 ADMET 药代毒理全景雷达", "Delaney ESOL 水溶性、Clark LogBB 脑透性、Caco-2 通透性与 CYP/hERG 安全性")

    img_ad = ARTIFACTS_DIR / "11_admet_radar_modal.png"
    if img_ad.exists():
        slide16.shapes.add_picture(str(img_ad), Inches(0.8), Inches(1.8), Inches(6.8), Inches(4.8))

    add_card(slide16, Inches(7.9), Inches(1.8), Inches(4.6), Inches(4.8), CARD_DARK, CYAN_ACCENT)
    tbad = slide16.shapes.add_textbox(Inches(8.1), Inches(2.0), Inches(4.2), Inches(4.4))
    p = tbad.text_frame.paragraphs[0]
    p.text = "📈 成药性五大评估维度"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = CYAN_ACCENT
    p.space_after = Pt(10)
    p = tbad.text_frame.add_paragraph()
    p.text = "1. 水溶性 (ESOL LogS)：\n   识别高溶性类药区间，规避体内沉淀风险；\n2. 血脑屏障穿透 (Clark LogBB)：\n   结合 tPSA 与 cLogP 预测中枢神经渗透性；\n3. 肠道吸收通透性 (Caco-2 Log Papp)：\n   评估口服生物利用度潜能；\n4. 代谢酶抑制预警 (CYP3A4 / 2D6)：\n   药效团匹配，避免临床药物联用严重 DDI；\n5. 心脏毒性风险 (hERG 离子通道阻断)：\n   前置预警致命 QT 间期延长与心律失常。"
    p.font.size = Pt(12)
    p.font.color.rgb = TEXT_WHITE

    set_speaker_notes(slide16, """高活性并不等于成药性。我们集成了五维 ADMET 雷达图：包括基于分子拓扑的 Delaney ESOL 水溶性预测、Clark LogBB 血脑屏障穿透率、Caco-2 膜通透性以及 CYP 代谢酶和 hERG 心脏毒性预警，确保筛选和改构出的分子具备优异的口服生物利用度与安全性。""")

    # =========================================================================
    # SLIDE 17: ANSI 标准 96 孔板微孔投产排板 (96-Well Dispatching)
    # =========================================================================
    slide17 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide17, DARK_BG)
    add_header(slide17, "WET-LAB DISPATCH · 湿实验排板", "ANSI/SLAS 标准 96 孔板点位智能排布", "自动规划 3 倍 8 点稀释浓度，直出 Echo 声波移液仪与 Tecan 工作站脚本")

    img_w = ARTIFACTS_DIR / "13_wetlab_96_well_dispatch.png"
    if img_w.exists():
        slide17.shapes.add_picture(str(img_w), Inches(0.8), Inches(1.8), Inches(7.4), Inches(4.8))

    add_card(slide17, Inches(8.5), Inches(1.8), Inches(4.0), Inches(4.8), CARD_DARK, PRIMARY_BLUE)
    tbw = slide17.shapes.add_textbox(Inches(8.7), Inches(2.0), Inches(3.6), Inches(4.4))
    p = tbw.text_frame.paragraphs[0]
    p.text = "🧪 微孔实验工程规程"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = PRIMARY_BLUE
    p.space_after = Pt(10)
    p = tbw.text_frame.add_paragraph()
    p.text = "• 严格遵循 ANSI/SLAS 1-2004 8×12 标准板式；\n• A01 孔：原研阳性对照 (达沙替尼 10 mM)；\n• H12 孔：阴性溶剂空白对照 (100% DMSO)；\n• A02~H11 孔：候选化合物 Tier 1/2 优先级排布；\n• 3倍 8点半对数稀释梯度：\n  10,000 nM → 4.57 nM 剂量曲线；\n• 一键直出 Echo/Tecan 移液工作站 CSV 规程脚本！"
    p.font.size = Pt(12)
    p.font.color.rgb = TEXT_WHITE

    set_speaker_notes(slide17, """为了打通干湿鸿沟，系统实现了 ANSI 标准 96 孔微孔板自动调度。不仅排布了 A01 阳性与 H12 阴性对照，规划了 8 点半对数稀释梯度，更可以直接导出 Echo 声波移液仪和 Tecan 液体处理工作站的标准 CSV 运行脚本，彻底免去了人工核算点位和手动加样的繁琐与失误。""")

    # =========================================================================
    # SLIDE 18: 经验贝叶斯主动学习与方差收缩 (Empirical Bayes Active Learning)
    # =========================================================================
    slide18 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide18, DARK_BG)
    add_header(slide18, "ACTIVE LEARNING · 数据飞轮", "湿法实测数据注入与经验贝叶斯核平滑飞轮", "实测残差向化学近邻辐射传播，后验方差 σ 非对称收缩，动态重排先导榜单")

    img_fb = ARTIFACTS_DIR / "15_wetlab_feedback_calibrated.png"
    if img_fb.exists():
        slide18.shapes.add_picture(str(img_fb), Inches(0.8), Inches(1.8), Inches(6.8), Inches(4.8))

    add_card(slide18, Inches(7.9), Inches(1.8), Inches(4.6), Inches(4.8), CARD_DARK, EMERALD_GREEN)
    tbfb = slide18.shapes.add_textbox(Inches(8.1), Inches(2.0), Inches(4.2), Inches(4.4))
    p = tbfb.text_frame.paragraphs[0]
    p.text = "🔄 贝叶斯后验均值与方差迭代"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = EMERALD_GREEN
    p.space_after = Pt(10)
    p = tbfb.text_frame.add_paragraph()
    p.text = "1. 实测残差：Δ_k = y_k^(obs) - μ(x_k)\n2. 摩根拓扑高斯核加权：\n   w(x_k, x_j) = exp( - (1 - Tanimoto) / h )\n3. 未测分子均值更新：\n   μ_post(x_j) = μ(x_j) + Δ_k · w(x_k, x_j)\n4. 后验方差动态收缩：\n   σ_post^2(x_j) = σ^2 · [1 - w · σ^2 / (σ^2 + σ_noise^2)]\n5. 期望提升 (EI) 动态刷新：\n   自动指导下一轮最优合成孔位，实现极少样本 (Few-shot) 高速收敛！"
    p.font.size = Pt(11)
    p.font.color.rgb = TEXT_WHITE

    set_speaker_notes(slide18, """这是系统最核心的数据闭环。当湿实验测出前几个分子的真实解离常数回填系统后，算法不仅将已测分子的不确定性方差归零，更通过拓扑相似度核平滑，将误差辐射给未测分子。后验方差显著收缩，期望提升公式自动重构阶梯榜，实现了少样本下的自适应主动学习。""")

    # =========================================================================
    # SLIDE 19: 学术级交付报告与专利交底书自动生成 (Academic Report & Patent Claims)
    # =========================================================================
    slide19 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide19, DARK_BG)
    add_header(slide19, "DELIVERABLES · 成果交付", "学术交付报告与专利交底书一键生成", "自动导出符合 Nature/JMC 标准排版的 SAR 关系表与马库什权利要求草案")

    img_rep = ARTIFACTS_DIR / "14_academic_research_report.png"
    if img_rep.exists():
        slide19.shapes.add_picture(str(img_rep), Inches(0.8), Inches(1.8), Inches(7.4), Inches(4.8))

    add_card(slide19, Inches(8.5), Inches(1.8), Inches(4.0), Inches(4.8), CARD_DARK, INDIGO_ACCENT)
    tbrep = slide19.shapes.add_textbox(Inches(8.7), Inches(2.0), Inches(3.6), Inches(4.4))
    p = tbrep.text_frame.paragraphs[0]
    p.text = "📑 报告规范化标准"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = INDIGO_ACCENT
    p.space_after = Pt(10)
    p = tbrep.text_frame.add_paragraph()
    p.text = "• 中英文双模态导出：\n  结构化 Markdown 与印刷级独立 HTML；\n• 内嵌高精度构效关系 (SAR) 演化表；\n• 包含 MM-GBSA 能量分解项与 ADMET 药代安全性雷达参数；\n• 自动萃取核心药效团生成专利交底书：\n  提取马库什通式 (Formula I) 权利要求范围；\n• 秒级完成传统需数天的人工图表整理。"
    p.font.size = Pt(12)
    p.font.color.rgb = TEXT_WHITE

    set_speaker_notes(slide19, """为了支持成果申报与知识产权保护，系统内置了学术报告引擎。完成一轮先导优化后，药化专家可一键导出符合 Nature/JMC 格式的图表报告，并自动提炼出马库什通式专利交底书草案，将传统需要耗费数天的数据整理工作压缩到了秒级。""")

    # =========================================================================
    # SLIDE 20: 全栈系统工程与 21 组 E2E 自动化测试 (E2E Validation)
    # =========================================================================
    slide20 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide20, DARK_BG)
    add_header(slide20, "SYSTEM HEALTH · 系统工程", "工业级全栈工程实现与 21 组 E2E 自动化测试", "通过 Playwright 模拟真实浏览器多阶段交互，全流程控制台零异常验证 (Exit 0)")

    img_lb = ARTIFACTS_DIR / "04_davis_benchmark_leaderboard.png"
    if img_lb.exists():
        slide20.shapes.add_picture(str(img_lb), Inches(0.8), Inches(1.8), Inches(6.8), Inches(4.8))

    add_card(slide20, Inches(7.9), Inches(1.8), Inches(4.6), Inches(4.8), CARD_DARK, EMERALD_GREEN)
    tblb = slide20.shapes.add_textbox(Inches(8.1), Inches(2.0), Inches(4.2), Inches(4.4))
    p = tblb.text_frame.paragraphs[0]
    p.text = "🛡️ 工业级质量门禁指标"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = EMERALD_GREEN
    p.space_after = Pt(10)
    p = tblb.text_frame.add_paragraph()
    p.text = "• 异步微服务架构：FastAPI + RDKit C++ 内核；\n• 前端：React 18 + TypeScript 严格类型；\n• 编译构建：2,023 模块打包 0 错误 (907ms)；\n• Playwright 端到端自动化 UI 验收：\n  覆盖单点预测、3D 口袋、海选漏斗、逆合成树、96 孔板与贝叶斯校准；\n• 捕获 21 组高分辨率 UI 审计快照；\n• 页面零未捕获异常 (Zero Uncaught Errors)；\n• 科研审计门禁 check_mic_project 全部 Exit 0。"
    p.font.size = Pt(11)
    p.font.color.rgb = TEXT_WHITE

    set_speaker_notes(slide20, """整套系统不是一个简陋的玩具，而是拥有工业级交付质量的全栈应用。后端采用异步 FastAPI，前端采用 React 18。我们通过 Playwright 编写了完整的端到端自动化测试，覆盖 6 大交互阶段并截取了 21 组高分辨率审计快照，全链路控制台零报错退出，展现了极高的工程健壮性。""")

    # =========================================================================
    # SLIDE 21: 致导师：三大基金/顶刊深化课题切入点 (Future Directions)
    # =========================================================================
    slide21 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide21, DARK_BG)
    add_header(slide21, "COLLABORATION · 深化设想", "依托本平台底座的三个基金/顶刊课题方向", "工程框架已完全成熟，渴望在老师指导下攻坚真实科学难题与冲击顶刊")

    proposals = [
        ("课题一：ESM-3 蛋白质语言大模型在零样本突变上的极限泛化 (AI/生信方向)", "将现有的 100 维特征工程，升级接入 6.5 亿参数的 ESM-3 / 3D 等变图神经网络 (EGNN)，在严格盲测集上探索极限零样本外推规律。\n👉 目标期刊：Briefings in Bioinformatics / Bioinformatics (中科院一区/Top)", PRIMARY_BLUE),
        ("课题二：针对特定临床突变体的湿法合成与激酶活性验证 (药化/肿瘤学方向)", "依托本平台的逆合成与海选功能，针对老师实验室攻坚的具体突变靶标（如肺癌 EGFR-C797S 或 KRAS-G12D），挑选 3~5 个候选分子完成湿法合成与生化活性实测。\n👉 目标期刊：Journal of Medicinal Chemistry (JMC Full Article)", CYAN_ACCENT),
        ("课题三：基于 96 孔板声波移液的 AI 闭环自驱动无人实验室 (交叉学科方向)", "将平台的 96 孔板调度与贝叶斯反馈 API 物理接入实验室的自动化液体处理工作站，实现‘排板 → 机械臂移液 → 酶标仪读数 → 贝叶斯自进化’自驱动实验室。\n👉 目标申报：国家自然科学基金重大研究计划 / 科技部重点研发计划", EMERALD_GREEN),
    ]

    for idx, (p_t, p_d, col) in enumerate(proposals):
        top_pos = Inches(1.8 + idx * 1.7)
        add_card(slide21, Inches(0.8), top_pos, Inches(11.7), Inches(1.5), CARD_DARK, col)

        tbp = slide21.shapes.add_textbox(Inches(1.1), top_pos + Inches(0.12), Inches(11.1), Inches(1.25))
        p = tbp.text_frame.paragraphs[0]
        p.text = p_t
        p.font.name = FONT_HEADING
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = col
        p.space_after = Pt(4)

        p2 = tbp.text_frame.add_paragraph()
        p2.text = p_d
        p2.font.name = FONT_BODY
        p2.font.size = Pt(11)
        p2.font.color.rgb = TEXT_WHITE

    set_speaker_notes(slide21, """尊敬的各位老师，目前整个平台的工程底座、物理守恒方程与算法体系已经完全打磨成型。但我深刻明白，工具的价值在于解决真实的科学难题。依托这个成熟底座，我们可以在大模型结构泛化、真实靶点湿实验验证以及自驱动无人实验室三个极具学术价值的方向深入展开，冲击顶刊或申报科研基金。""")

    # =========================================================================
    # SLIDE 22: 致谢与交流互动 (Acknowledgements & Q&A)
    # =========================================================================
    slide22 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide22, DARK_BG)

    tb22 = slide22.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(11.3), Inches(3.5))
    tf22 = tb22.text_frame
    tf22.word_wrap = True

    p = tf22.paragraphs[0]
    p.text = "THANK YOU FOR YOUR ATTENTION"
    p.font.name = FONT_HEADING
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = CYAN_ACCENT
    p.alignment = PP_ALIGN.CENTER
    p.space_after = Pt(14)

    p2 = tf22.add_paragraph()
    p2.text = "感谢各位老师与同学的聆听！\n恳请各位老师批评指正！"
    p2.font.name = FONT_HEADING
    p2.font.size = Pt(32)
    p2.font.bold = True
    p2.font.color.rgb = TEXT_WHITE
    p2.alignment = PP_ALIGN.CENTER
    p2.space_after = Pt(24)

    p3 = tf22.add_paragraph()
    p3.text = "项目开源仓库与手稿文档均在工作区就绪  |  欢迎交流合作与指导"
    p3.font.name = FONT_BODY
    p3.font.size = Pt(14)
    p3.font.color.rgb = EMERALD_GREEN
    p3.alignment = PP_ALIGN.CENTER

    set_speaker_notes(slide22, """衷心感谢指导老师悉心的指导，感谢各位研讨课老师在百忙之中审阅！非常渴望将本系统的工程能力融入老师的课题研究中。我的汇报到此结束，恳请各位老师批评指正！""")

    # Save presentation
    prs.save(str(OUTPUT_PPTX))
    print(f"[SUCCESS] 22-slide PowerPoint presentation generated at: {OUTPUT_PPTX}")


if __name__ == "__main__":
    build_deck()
