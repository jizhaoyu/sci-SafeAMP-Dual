# 加入 EtCec3-OH 后的候选结构复核

原论文候选现为 50 条测定、38 条唯一分子；完整全员比对为 703 对，其中 25 对达到 0.40。以原始论文和同源连通后为 8 个组件，含阴性 5 个，含阳性 5 个。EtCec3-OH 是当前核查子集中的新增独立阴性组件；若恢复旧未核实的 324 条队列，它会与其中一条旧序列合并。

原有固定 StratifiedGroupKFold、seed 42、五折仅 4/5 折具备训练和验证两类。未改变阈值、折数或 seed 追求放行。候选证据与新冻结训练协议也尚未完成；训练释放数为 0，状态仍为 `blocked`。

阻断项：
- Fixed seed 42 fold 1 lacks both classes.
- The full selected cohort lacks independent primary-paper review and an immutable training protocol.
