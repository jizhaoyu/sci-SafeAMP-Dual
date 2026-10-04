# 原始游离酸证据筛选后的重新分组

从原 41 条候选中仅保留 7 条末端形式已局部确认的分子；其余 34 条暂缓纳入，未补写无修饰状态。新增 4 条原始游离酸对照、7 条 MIC：Aurein 2.3-COOH，以及 MSI-103-COOH、PGLa-COOH、MAP-COOH。后 3 条来自实验作者 Deniz Tiltak 的 2009 学位论文，表 4.1/4.2 和方法 3.2.2；第 4 章明确与 2007 论文为同一研究，因此合并研究标识，未计为两套独立实验。

[Tiltak 原始学位论文](https://publikationen.bibliothek.kit.edu/1000012217)；[Cheng 原始论文](https://doi.org/10.1016/j.bbamem.2010.11.025)。原 PDF、表格渲染及哈希保存在来源目录；用于核查数值事实，未取得原文件再次发布的许可。latarcin 来源的 COOH 与 Rink amide 合成方法互相矛盾，4 条分子暂缓，未入选。

筛选后 11 条分子、16 条测定；完整比较 55 对，形成 4 个同源/研究不可拆分组件，含阳性 2 组、含阴性 4 组。旧 41 条结构通过的结论仅属于未释放候选，不能迁移到本筛选集。不足五组的类别无法分到五个同时具备两类的验证折；未运行不可能通过的分折，也未调整阈值、seed、折数。

当前训练释放 0，总状态 `blocked`。跨折审计在未生成有效分折时记为 null，不将未执行伪报为零泄漏。

- total components: 4 < 5; five validation folds with both classes are impossible.
- positive-bearing components: 2 < 5; five validation folds with both classes are impossible.
- negative-bearing components: 4 < 5; five validation folds with both classes are impossible.
- Local molecular evidence is not a training release; full release review and a new immutable training protocol are required.
