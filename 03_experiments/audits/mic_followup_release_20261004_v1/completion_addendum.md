# 最终交付核验补充

当前机器状态为 `mic_training_readiness_20261004_v22.json`：16 分子、23 观察获准，固定三折训练和独立复核通过；原双任务仍 blocked。详情见本目录 `final_report.md` 和独立运行验证。

训练后追加摘要破坏和缩放器篡改回归，最终输出 **55 passed, 1 deselected**。被排除的是旧受保护测试 `test_protocol_11_and_freeze_slots_remain_unused_until_gate_passes`：它断言门禁通过前 protocol-mic-11 文件不存在，已不适用当前阶段。原测试没有修改；本轮用 `test_new_protocol_is_bound_to_admitted_pretraining_state` 验证新协议绑定了训练前通过门禁的真实状态。

测试首次追加时还暴露历史共享读取器依赖项目根工作目录；本轮复核与训练均从项目根目录执行并成功。CLI 复跑需在 `D:/桌面文件/sci` 执行；没有声称任意工作目录都受支持。篡改回归显式使用项目根目录，未绕过输入或模型检查。

最终回归记录为 `mic_followup_regression_20261004_v5/verification.json`。文档旧章节中固定引用 v20 的“当前准入”文字已改成引用页首机器状态，避免历史章节与新状态冲突。

本轮完整测试套件未运行；已完成相关证据、协议、隔离、原始观察和产物验证回归。模型结果仍为小样本描述性探索，没有外部验证、调参或投稿审批。
