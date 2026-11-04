# 补充方法与复现接口（方案阶段）

本文件描述已实现的程序。当前没有正式实验结果或已执行的超参数搜索。

## 数据
来源表必须包含 record_id、seq、amp、hemo、source_dataset、source_accession、source_url、evidence_reference、label_basis、assay_conditions、modifications、evidence_type、is_synthetic、source_role、raw_path、raw_sha256。

未知标签以空值保存；验证器派生 amp_observed、hemo_observed 并检查已有标记的一致性。is_synthetic 指计算模拟记录，不是化学合成后实际测定的肽。当前仅接受未修饰标准序列。DBAASP 标签会从原始文件重新导出并对照，不能只靠哈希掩盖被改动的标签。

同序列标签冲突保留为缺失，精确跨来源重叠有排除记录。来源名称不同还需全序列检查，不能据此假定独立性。外部来源由另行获取的真实证据提供，不得给同一数据库随机留出部分换名称。

## 实验
七模型 × 三种子 × 五个开发折，开发集全量重训。SVM 内部随机概率 CV 关闭；所有方法统一使用开发 OOF 分数上的 logistic 校准。C=1，logit 输入裁剪为 [1e-6,1−1e-6]。没有嵌套调参或最佳折选择。预处理器、校准参数及每个种子的分类器均保留。

阈值以开发数据特异度至少 0.95 为约束选择最大敏感度；测试达到的特异度如实报告。三种子均值有单独开发阈值；不能把三个种子当成独立样本。OOF 校准和阈值使用同一开发集合，相关指标只是选择记录。

## 产物
predictions.csv 含 sample_id、cluster_id、split、fold、model、seed、task、y_true、probability、raw_probability、threshold。ensemble_predictions.csv 为三种子均值，seed=-1 明确表示集成。metrics.json、ensemble_metrics.json、confidence_intervals.json、comparisons.json 与所有权重及配置均受运行清单校验。

区间是固定模型条件下按序列连通簇重采样的 95% 百分位区间，记录无效单类别抽样次数。主端点使用 average precision。比较使用成对簇交换检验，Holm 覆盖预定的内部与外部主端点比较；不使用硬编码折数组或独立折 t 检验。

publication_artifacts.py 从通过验证的预测文件重新计算表格和图。生成文件仍标注 publication_ready=false，需进一步完成声明和引用的作者审查。所有图的来源、转换、区间定义和输出哈希写入清单；目标期刊格式尚未选择。
