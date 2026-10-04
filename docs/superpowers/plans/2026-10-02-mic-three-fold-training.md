# MIC 三折探索训练与状态同步 Implementation Plan

> **For agentic workers:** Implement the plan with the available Codex tools and repository conventions. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 执行已冻结的 protocol-mic-07，复核真实训练产物，并发布与五份当前文档一致的新探索状态。

**Architecture:** 使用现有 train_mic_three_fold_v2.py 完成训练，不修改已冻结输入或算法。增加独立的产物复核入口，仅加载模型重算预测及指标；验证通过才生成后续状态。运行目录、状态和验证结果均拒绝覆盖已有文件。

**Tech Stack:** Python 3.11.9、NumPy 2.4.4、pandas 3.0.2、scikit-learn 1.8.0、joblib 1.5.3，均使用现有环境。

## Global Constraints

- 15 条分子、22 条 MIC、44 维固定特征、三折、seed 42、全员同源阈值 0.40 和原始研究分组保持冻结。
- 仅执行逻辑回归、随机森林和 prior 对照；不调参、不择优、不做全队列部署训练。
- 原双任务 research_status.json 保持 SHA-256 846c1fc2452646f3df9c2055b0a4a1b5140132acc2433bb2c304b133b6e8012c。
- 验证不拟合模型；逐折 1–2 条阳性，仅报告描述性探索结果，不作正式或临床结论。
- 保存 v11、旧协议及审计快照；新状态记录实际运行路径、时间、协议、数据版本及产物摘要。
- 工作区没有 Git 仓库；本轮不推送或部署。

---

### Task 1: 执行已授权的固定训练

**Files:**
- Read: `02_code/train_mic_three_fold_v2.py`
- Read: `03_experiments/protocols/protocol-mic-07.json`
- Create: `03_experiments/runs/mic_three_fold_20261002_v1/`

- [x] 运行以下命令，读取实际退出码与 manifest；状态为 local_exploratory_three_fold_training_completed，训练完成时间 2026-10-02 18:45:30（Asia/Shanghai），退出码 0。

```powershell
python 02_code/train_mic_three_fold_v2.py --output 03_experiments/runs/mic_three_fold_20261002_v1
```

- [x] 核对九个折模型、45 条 OOF 预测、九行逐折指标、三行汇总指标和 15×44 特征；保存全部预先声明模型的结果。

### Task 2: 复核训练产物并发布新机器状态

**Files:**
- Create: `02_code/validate_mic_three_fold_run.py`
- Create: `03_experiments/audits/mic_three_fold_run_validation_20261002_v1.json` 和同名 Markdown
- Create: `03_experiments/audits/mic_training_readiness_20261002_v12.json`

**Interfaces:** `validate(run_dir: Path, output: Path, publish_state: Path | None, state: Path | None, check_documents: bool) -> dict`；消费冻结协议、v11 就绪快照和运行 manifest，输出独立复核结果及可选的新状态。

- [x] 复用 load_validated() 核查源文件摘要、证据、105 对全员比较和 45 条角色；用禁止 fit 的补丁锁定复核期间无训练。
- [x] 运行目录限定于本地 runs；拒绝清单中逃出运行目录的路径及不完整清单，不允许将复核输出写进冻结运行目录；逐文件核对摘要，核对冻结协议、实现、环境、九个模型参数及 fitted 状态。
- [x] 每折重新计算预测；核对 LR 标准化器仅使用训练样本、RF 树数和 prior 类别比例；独立重算五项指标、OOF 覆盖和特征矩阵。
- [x] 使用以下命令发布新状态；仅在全部检查通过后写入，保留正式状态 blocked。v12 生成时间 2026-10-02 18:51:38（Asia/Shanghai），退出码 0。

```powershell
python 02_code/validate_mic_three_fold_run.py --run 03_experiments/runs/mic_three_fold_20261002_v1 --output 03_experiments/audits/mic_three_fold_run_validation_20261002_v1.json --publish-state 03_experiments/audits/mic_training_readiness_20261002_v12.json
```

### Task 3: 同步文档并完成产物交付

**Files:**
- Modify: `README.md`
- Modify: `docs/REMEDIATION_STATUS.md`
- Modify: `docs/DOCUMENTATION_INDEX.md`
- Modify: `docs/handoff/TASK_STATE.md`
- Modify: `03_experiments/audits/multi_database_ecoli_mic_screen_20261001.md`
- Create: `03_experiments/audits/mic_three_fold_run_validation_20261002_v2.json` 和同名 Markdown

- [x] 五份文档采用新状态的实际生成时间、数据版本、协议和运行路径；清除当前“尚未训练”，将 v11 及以前验证标为历史时点。
- [x] 将复算的全部模型指标、混淆计数和样本限制写入新验证报告；冻结运行报告及 manifest 不覆盖。
- [x] 运行新脚本的语法检查及以下文档复核；五份文档一致、模型重算通过、正式状态摘要不变，退出码均 0。最终验证生成于 2026-10-02 18:58:08（Asia/Shanghai）。

```powershell
python -m py_compile 02_code/validate_mic_three_fold_run.py
python 02_code/validate_mic_three_fold_run.py --run 03_experiments/runs/mic_three_fold_20261002_v1 --output 03_experiments/audits/mic_three_fold_run_validation_20261002_v2.json --state 03_experiments/audits/mic_training_readiness_20261002_v12.json --check-documents
```

- [x] 最终报告已交付并请求在 Codex 面板打开；完成范围是小样本 MIC-only 探索训练，原双任务仍阻断，真实负面结果与局限已说明。

## 执行记录与限制

- 初次产物复核失败发生在新复核器的 StandardScaler 均值比较；冻结特征为 float32，StandardScaler 使用 float64 累加，复核器默认 float32 均值产生约 1.9–4.0e-8 的舍入差异。
- 根因诊断对全部三折重算：float64 均值和方差与模型保存值最大差异均为 0。仅修正新复核器的累加精度，未改容差、模型、训练算法、标签或分区。初次失败没有写出状态或验证产物。
- LR / RF / prior 合并 OOF 的 AUROC 为 0.454545 / 0.318182 / 0.420455，AUPRC 为 0.300595 / 0.242262 / 0.238889。0.5 阈值下三者 TP 均为 0，全部四条阳性漏判；没有证明可靠分类能力。
- prior 各折 AUROC 为 0.5，合并不同训练先验后可偏离 0.5；11/15 的准确率来自全判阴性。无模型择优、参数搜索、校准、额外随机种子、全样本重训或部署。
- 原正式双任务状态与 protocol-mic-06、protocol-mic-07、既有来源/队列、训练入口及 v11 历史状态均通过摘要核查；本轮没有运行全量 pytest，旧 182 passed 仅是历史结果。
