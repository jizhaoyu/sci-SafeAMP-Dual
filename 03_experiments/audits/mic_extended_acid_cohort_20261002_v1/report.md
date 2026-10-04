# 新原始来源合并后的全员分组审计

在原 11 条局部确认分子、16 条测定基础上，加入 4 条分子、6 条 MIC。Zhang 2021 两条游离酸阴性对照共用一个原始研究；Sharma 2013 的 Tritrpticin 与 12PhD1 共用一个研究，两株细菌的测定不计成独立来源。全部逐来源决定见 ../mic_independent_sources_review_20261002_v1/report.md。

当前 15 条分子（阳性 4、阴性 11），22 条测定、105 对全员比较、11 条同源边。同源与研究整体连接为 6 个组件：含阳性 3 个、含阴性 6 个。

五折每折两类至少需要 5 个含阳性与 5 个含阴性组件；含阳性仍至少缺 2 个。这是必要条件下界，补足后仍须检查固定 seed 42 的实际分折。当前分折未生成，跨折审计为 null。所有候选仅局部证据确认，完整释放待完成；训练释放为 0，训练未启动，状态 blocked。

- positive-bearing components: 3 < 5; five validation folds containing both classes are impossible.
- Full evidence release and a new immutable training protocol remain incomplete.

## 复跑

`python 02_code/audit_mic_extended_acid_cohort.py --output 03_experiments/audits/mic_extended_my_run`
须使用不存在的新目录。0.40、5 折、seed 42、32/128 标签边界与分子域保持冻结。
