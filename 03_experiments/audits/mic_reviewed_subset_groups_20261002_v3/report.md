# 加入 Ludwig 原论文候选后的全员与五折审计

现有 41 条分子、54 条测定，完整比较 820 对；达到 0.40 的 31 对和共享论文连接后，保留 8 个不可拆分组件。含阴性 5 组、含阳性 6 组。Api810 连到现有 Okimura 肽，并将同论文的 Api801/Api805 一起连接，未新增独立阴性组件。

固定 StratifiedGroupKFold、seed 42、5 折中 5/5 折具备训练和验证两类；跨折超阈值同源边 0，跨折论文标识 0。本次未调整阈值、seed 或折数。候选证据尚未全量释放，正式训练数仍为 0，状态为 `blocked`。

阻断项：
- The full selected cohort still needs complete primary-paper review and a new immutable training protocol.
