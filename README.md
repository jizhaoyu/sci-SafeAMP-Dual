# AI药物靶点亲和力预测平台 (DTA / DTI)

> **计算生物学与药物–靶点相互作用研究工作台**  
> 聚焦小分子药物与蛋白质激酶靶点亲和力（$pK_d$）预测与先导分子结构优化。依托标准基准数据集（DAVIS Kinome 379 个激酶靶点、68 种化合物、25,772 个配对），提供端到端的机器学习与化学信息学研究套件。

---

## 核心功能与架构

1. **3D 激酶结合口袋与微观互作 (`KinasePocketViewer3D`)**：
   - 基于 3Dmol.js WebGL，清晰呈现 ABL1 (2GQG)、EGFR (1M17)、BRAF (4MNE) 等关键靶点催化结构域、DFG-in/out 构象与铰链区主链氢键网络。
2. **分子结构交互画板 (`MoleculeSketcherModal`)**：
   - 支持常见芳香/杂环骨架模板一键植入、修饰基团笔刷追加、实时 2D 拓扑渲染与 SMILES 双向实时同步。
3. **合成可达性与 ADMET 属性评估 (`SA Score` & `ADMETRadarModal`)**：
   - 基于 Ertl & Schuffenhauer 原理标定合成难度（1.0~10.0），结合 Lipinski 五规则与理化雷达图评估类药性。
4. **先导物改构优化与主动学习 (`LeadOptimizerStudio`)**：
   - 支持骨架跃迁、侧链官能团替换，基于亲和力预测分数进行先导物排序优化。
5. **严谨的基准模型与双冷域泛化评测**：
   - 涵盖 Ridge 基线、Bilinear 交互模型、ESM-2 蛋白特征与 Tobit 截断回归模型，并在严格隔离的冷靶点（Cold Target）与双冷（Dual Cold）域上独立评测。

---

## 项目快速上手

### 1. 环境准备
```powershell
# Python 依赖安装
pip install -r requirements.txt

# 前端依赖安装与构建
cd frontend
npm install
npm run build
cd ..
```

### 2. 启动本地研发工作台
```powershell
# 启动 API 与前端服务 (默认端口 8000)
python 05_web_server/app.py
```
启动后在浏览器打开 `http://127.0.0.1:8000` 即可使用研究工作台。

### 3. 运行自动化测试
```powershell
pytest
```

---

## 核心文档导航

* 论文全稿（中文）：[论文全稿_中文.md](file:///d:/桌面文件/sci/output/dta-paper-full-draft-v1-20261010/论文全稿_中文.md)
* 学术英文手稿：[MANUSCRIPT_DTI_DAVIS_STACKED_FRAMEWORK.md](file:///d:/桌面文件/sci/04_paper/MANUSCRIPT_DTI_DAVIS_STACKED_FRAMEWORK.md)
* 汇报讲稿与演示文档：[药物靶点项目_20页_纠正研究范围_20261013](file:///d:/桌面文件/sci/output/药物靶点项目_20页_纠正研究范围_20261013/交付)
* 文档索引：[文档导航.md](file:///d:/桌面文件/sci/文档导航.md)
