# 每折断点更新
每折训练和验证预测完成后保存 checkpoints/fold_progress/<experiment_id>.npz。
保存成功打印 [FOLD SAVED]；恢复打印 [FOLD RESUME]。
数据、顺序、划分、模型参数、Python/NumPy/SciPy/sklearn 版本及线程环境必须一致。
不兼容或损坏的断点会报错，不自动覆盖；临时 .tmp 文件不用于恢复。
旧日志无法还原 OOF 预测，安装前未保存的折次需要重做。
最终全量重训练若中断仍需重做，但已保存的 OOF 折次会跳过。
原完整设置 checkpoint 优先，models 与 checkpoints 整个目录均需备份。
模型参数、指标函数及 NNLS 拟合调用未改变；保留详细日志。
fit_time_sec 包含从断点恢复的成功折次耗时，不包括此前失败尝试的耗时。
本次仅模拟验证，未启动本地训练或完成云端真实训练验证。
