# 缺原文37条：停止检索并退出本轮审查

用户决定：“这37条如果找不到就不找了,或者直接去掉”。本批已将37条移出当前审查范围，保留历史信息；未删除来源记录或修改实验标签。

- [报告](review/report.md)
- [当前41条已筛查范围](review/current_scope_records.csv)
- [37条退出清单及理由](review/scope_exclusions.csv)
- [78条历史追溯表](review/merged_candidate_decisions.csv)
- [本批机器状态](review/summary.json)与[摘要清单](review/manifest.json)
- [覆盖及保护核查](review/verification.json)与[复跑比较](reproduction_check.json)

生成时间2026-10-05T03:49:39.079556+00:00；版本`hc50_unavailable_scope_closure_20261005_v1`，协议`protocol-amd-02`。37条对应25个DOI/PMID标识对，不再继续网络检索；历史缺原文记录仍可追溯。

41条保留范围包括22条来源不足、10条待复核及9条已知形式排除。因此仅32条仍有证据复核问题，正式外部准入仍为0，双任务仍blocked；MIC探索状态v26不变。范围关闭不等于科学门禁通过。

## 复跑

在`D:/桌面文件/sci`执行，输出路径必须不存在：

```powershell
python 03_experiments/audits/hc50_unavailable_scope_closure_20261005_v1/scripts/close_scope.py close --output 03_experiments/audits/hc50_unavailable_scope_closure_20261005_v1/review_my_run
python 03_experiments/audits/hc50_unavailable_scope_closure_20261005_v1/scripts/close_scope.py verify --review 03_experiments/audits/hc50_unavailable_scope_closure_20261005_v1/review_my_run --output 03_experiments/audits/hc50_unavailable_scope_closure_20261005_v1/review_my_run/verification.json
```

核查37+41=78及ID覆盖、25个来源标识对、41条逐字段不变、37条仅范围决定变化、344份历史保护文件及五份当前状态块不变。本批未新增测定审查、模型拟合、pytest或网络请求。
