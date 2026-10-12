# NVIDIA T4 云端实验执行指南 (ESM-2 + Bilinear Interaction DTI)

制定日期：2026-10-12。模型：`BilinearInteractionDTI`。

## 1. 为什么需要这次云端实验？

1. **破除加性加和的排序退化**：CPU 上的线性模型使所有药物对同一靶点库的排序完全一致；本包采用双线性交叉网络 $d^T W t + \dots$，使不同药物具备特异性排序。
2. **蛋白表征升级**：靶点特征从 28 维升级为预计算的 480 维 ESM-2 (`esm2_t12_35M_UR50D`) 深度特征。
3. **超低算力开销**：模型参数量约 35 万，单批次峰值显存约 6.56 MB，在 NVIDIA T4（16GB 显存 / 8 核 CPU）上预计训练耗时仅需 **10 ~ 15 分钟**。

---

## 2. 云端三步操作流程

### 第一步：上传并解压
将生成的 `dti_t4_esm2_bilinear_v1.zip` 上传至云服务器的训练目录（如 `/workspace`），并执行解压：
```bash
cd /workspace
unzip dti_t4_esm2_bilinear_v1.zip
cd dti_t4_esm2_bilinear_v1
```

### 第二步：一键启动训练
执行启动脚本：
```bash
bash start_training.sh
```
* 脚本将自动检查 CUDA 环境、安装必要依赖、并在 4 个严格实体隔离折上展开 25 轮混合精度加速训练。
* 过程日志实时输出至 `t4_training.log`。

### 第三步：下载结果
训练完成后，将以下两个产物下载回本地工作区：
1. `t4_results.json`：包含 4 折平均 Dual-Cold P@10、AP、以及跨药物排序多样性分析；
2. `t4_training.log`：完整控制台训练日志。

---

## 3. 验收与结论判定标准

- **突破成功门槛**：4 折平均 Dual-Cold P@10 显著超越 CPU 极限（$P@10 \ge 0.1500$），且跨药物 Spearman 排序相关性 $< 0.85$（证明排序特异性成立）。
- **瓶颈确认门槛**：若 Dual-Cold P@10 仍徘徊在 $0.10 \sim 0.11$，则确凿证实 DAVIS 数据集在双冷场景下存在固有数据瓶颈，正式封存 Exit A 并交付受限筛选工具。
