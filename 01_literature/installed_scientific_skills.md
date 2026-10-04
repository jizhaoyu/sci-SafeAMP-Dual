# 项目已装载的科学研究专用 Agent 技能库 (Scientific Agent Skills)

来源开源仓库：[K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills)  
安装位置：`C:\Users\888\.gemini\config\skills\`（全局自动发现，随需加载）

针对本项目 **“计算生物学 + 多肽 AI 预测与逆向分子工程 + SCI 论文成稿”**，已精选并成功装载以下 **9 大核心科研技能**：

---

## 1. 生物信息计算与大模型核心 (Biology & LLM Foundation)

* **`esm`**：
  * **作用**：支持 Meta 的 Evolutionary Scale Modeling 全系列模型（ESM-2, ESM3, ESMC, ESMFold）。
  * **场景**：蛋白质/多肽序列嵌入提取、变异效应预测（Variant Effect Prediction）、从头序列生成。
  * **路径**：`[esm](file:///C:/Users/888/.gemini/config/skills/esm/SKILL.md)`
* **`biopython`**：
  * **作用**：生物信息学数据处理黄金标准库。
  * **场景**：FASTA 解析、ProtParam 理化特征提取、多序列比对（MSA）、PDB 三维结构解析。
  * **路径**：`[biopython](file:///C:/Users/888/.gemini/config/skills/biopython/SKILL.md)`

---

## 2. SCI 论文撰写与顶刊同行评审 (Writing & Peer Review)

* **`scientific-writing`**：
  * **作用**：学术级论文写作与规范化编排。
  * **场景**：严谨的 IMRaD 结构起草、避免证据捏造、清晰的论点-证据映射、符合国际出版伦理与声明规范。
  * **路径**：`[scientific-writing](file:///C:/Users/888/.gemini/config/skills/scientific-writing/SKILL.md)`
* **`peer-review`**：
  * **作用**：模拟顶刊审稿人进行全真预审与漏洞排查。
  * **场景**：在投稿前对方法学漏洞、统计严密性、图表表述、数据泄露风险进行“红蓝对抗”式挑刺，并协助制定谦逊周密的返修（Response to Reviewers）策略。
  * **路径**：`[peer-review](file:///C:/Users/888/.gemini/config/skills/peer-review/SKILL.md)`
* **`literature-review`**：
  * **作用**：系统性学术文献综述与前沿追踪。
  * **场景**：检索高引综述、梳理领域技术谱系、定位未解决的开放问题（Open Issues）。
  * **路径**：`[literature-review](file:///C:/Users/888/.gemini/config/skills/literature-review/SKILL.md)`
* **`citation-management`**：
  * **作用**：文献引用与 BibTeX 规范管理。
  * **场景**：验证引用真实性、消除格式错误、管理 Zotero/Mendeley 导出库，杜绝无效或幻觉引用。
  * **路径**：`[citation-management](file:///C:/Users/888/.gemini/config/skills/citation-management/SKILL.md)`

---

## 3. 实验统计与可解释性 AI (Statistics & Explainable AI)

* **`statistical-analysis`**：
  * **作用**：学术级假设检验与显著性分析。
  * **场景**：机器学习基准模型对比中的置信区间（95% CI）、配对 t 检验、Wilcoxon 符号秩检验与 p 值计算，增强数据公信力。
  * **路径**：`[statistical-analysis](file:///C:/Users/888/.gemini/config/skills/statistical-analysis/SKILL.md)`
* **`shap`**：
  * **作用**：可解释性 AI（XAI）与特征重要度量化。
  * **场景**：Shapley 值计算、多肽理化特征全局重要度排序、残基局部贡献度瀑布图绘制。
  * **路径**：`[shap](file:///C:/Users/888/.gemini/config/skills/shap/SKILL.md)`
* **`scientific-visualization`**：
  * **作用**：出版级高清学术图表配色与排版指南。
  * **场景**：ROC/PR 曲线美化、色盲友好型调色板选择（Colorblind-safe）、多子图拼版规范（300+ DPI 矢量图）。
  * **路径**：`[scientific-visualization](file:///C:/Users/888/.gemini/config/skills/scientific-visualization/SKILL.md)`
