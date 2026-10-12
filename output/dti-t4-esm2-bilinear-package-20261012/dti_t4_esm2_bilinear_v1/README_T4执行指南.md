# NVIDIA T4 云端实验执行指南 (ESM-2 + Bilinear Interaction DTI)

制定日期：2026-10-12  
模型：`BilinearInteractionDTI`（双线性特征交叉 + ESM-2 480维蛋白表征 + 4折严格实体隔离）

---

## 1. 为什么需要这次云端实验？

1. **打破加性排序退化**：CPU 线性模型（加性 Ridge）导致所有药物对同一靶点库的排序完全一致；本模型通过双线性特征交叉 $d^T W t + \dots$，使不同药物具备独立的靶点特异性排序。
2. **蛋白质表征升级**：从传统手选 28 维升级为预计算的 480 维 ESM-2 (`esm2_t12_35M_UR50D`) 深度特征。
3. **超轻量算力开销**：模型参数量约 35 万，单批次显存仅约 6.56 MB，在 NVIDIA T4（16GB 显存 / 8 核 CPU）上预计完整 4 折训练仅需 **10 ~ 15 分钟**。

---

## 2. 云端标准执行流程 (三步走)

### 第一步：上传并解压
将生成的 `dti_t4_esm2_bilinear_v1.zip` 上传至云服务器（如 `/workspace`），解压并进入目录：
```bash
cd /workspace
python -m zipfile -e dti_t4_esm2_bilinear_v1.zip .
cd dti_t4_esm2_bilinear_v1
```

### 第二步：环境自检与依赖准备
执行环境一键安装脚本（自动配置清华镜像加速并运行 `check_bundle.py` 数据自检）：
```bash
bash setup_env.sh
```
看到 `[PREFLIGHT CHECK PASS]` 即表示一切就绪。

### 第三步：启动后台脱离训练
执行后台守护启动脚本：
```bash
bash start_training.sh
```
* **终端可安全关闭**：程序采用 `nohup` 脱离交互终端，即使关闭网页或 SSH 断连，训练仍会在后台持续运行，不会被平台信号终止。
* **实时跟踪进度**：
  ```bash
  bash watch_progress.sh
  ```
  *(随时可按 Ctrl+C 退出日志查看，后台训练不受任何影响)*

---

## 3. 容灾与辅助控制命令

- **查看当前运行状态与日志**：
  ```bash
  bash watch_progress.sh
  ```
- **安全停止当前训练**：
  ```bash
  bash stop_training.sh
  ```
- **从断点继续训练 (跳过已完成折)**：
  ```bash
  bash continue_training.sh
  ```
  *注意：系统每跑完一折会自动将结果与模型权重写入 `checkpoints/`，若中途意外关机，再次启动将自动跳过已完成折，绝不浪费算力。*

---

## 4. 结果导出与回传

训练完整结束后，程序会自动将模型、预测指标、日志打包为：
```text
DTI_T4_results_YYYYMMDDTHHMMSSZ.zip
```
并在控制台输出下载提示。

**请将该 ZIP 结果包下载回本地工作区，交给智能体核验，随后及时停止云端计费实例。**

---

## 5. 验收门槛标准

- **突破成功门槛**：4 折平均 Dual-Cold P@10 显著提升（$P@10 \ge 0.1500$），且跨药物 Spearman 排序相关性 $< 0.85$（证明排序特异性成立）。
- **瓶颈确认门槛**：若 Dual-Cold P@10 仍停留在 $0.10 \sim 0.11$，则确凿证实 DAVIS 数据集在双冷场景下的固有特征瓶颈，正式封存 Exit A 并交付受限筛选工具。
