# 原文核查候选集的全员隔离可行性

从 48 条逐测定候选、37 条唯一序列开始，读取冻结的全部 666 个候选序列配对；以固定 0.40 阈值和共同原始论文连接后为 7 个不可拆分组件，其中含阴性 4 组、含阳性 5 组。固定 seed 42 的 5 折中，满足两类条件的折数为 3/5。

此计算仅是结构可行性：候选有单人图片转录、来源化学形式与测定对象尚待全队列复核；Guan 原始绘图文件的 `80` 编码测定已排除。训练释放数为 0。

阻断项：
- Only 4 negative-bearing and 5 positive-bearing disjoint components for 5 folds.
- Fold 0 lacks both classes in training or validation.
- Fold 1 lacks both classes in training or validation.
