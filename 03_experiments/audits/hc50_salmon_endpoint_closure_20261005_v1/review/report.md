# 鲑鱼五候选：HC50检索与正式图身份核查

生成时间：2026-10-05T03:31:45.973158+00:00（UTC）。数据版本 `hc50_salmon_endpoint_closure_20261005_v1`；协议 `protocol-amd-02`。

## 本轮结论

复核既有五条，未新增候选；本轮未增加可准入的人红细胞数值HC50，正式外部新增0，原双任务仍blocked。既有MIC探索训练及协议不变，未训练新模型。这里的结论仅覆盖实际检查的来源，不能推断全网没有数据。

## 原始来源核查

- 出版方[正式Figure 1](https://ars.els-cdn.com/content/image/1-s2.0-S1050464816306994-gr1_lrg.jpg)与作者稿五条序列一致。地址由已核对的PII推导，下载后人工视读核实内容；不声称从文章网页观察到此附件链接。原图未改动，来源和转录分别绑定摘要。
- TT(1-24)仍显示20残基；原表MW为2510.8 Da。按项目现有质量常数、假设线性游离末端复算为2181.4312 Da，差329.3688 Da。仅为条件一致性诊断，不证明实际形式或错误原因，不补写4个残基，不据此换算测定单位或标签。
- rtCATH2(5-40)正式图为36残基，与前一批2006原文一致，仍与历史35残基清单冲突。前一批身份更正提案继续未准入。
- [Chang 2005](https://pmc.ncbi.nlm.nih.gov/articles/PMC1201231/)测定对象为虹鳟红细胞和rtCATH_1片段；[Bridle 2011](https://pmc.ncbi.nlm.nih.gov/articles/PMC3153500/)为大西洋鲑红细胞及asCATH1/asCATH2。不同RBC物种及分子不能转移为本批人HC50；引用既有研究也不构成新测量来源。原文定位见 `primary_endpoint_screen.csv`。
- [Scocchi 2009](https://pubmed.ncbi.nlm.nih.gov/19168146/)和[Zhang 2015](https://pubmed.ncbi.nlm.nih.gov/25876762/)本批仅获得可核对元数据；前者DOI返回跳转页，后者访问403。不能判断未取得的全文是否含目标端点。2020引用路由返回挑战页，不能作为原始证据。
- [Crossref记录](https://api.crossref.org/works/10.1016/j.fsi.2016.11.004)在获取时没有update-to或relation条目；这不能证明没有勘误。

## 检索覆盖与边界

保存8个Europe PMC查询及逐命中决定。带括号片段名的首个查询返回5条无关命中，全部拒作肽证据。增加生物学限定后0命中；全序列查询仅命中已检查2006论文；PMID索引对照找到了2016论文。这表明片段名和序列检索不能完整覆盖补充材料，0命中不是没有实验的证明。所有页内记录已保存，无分页截断。元数据、综述、预测及单点溶血均不生成标签。

累计78条候选中41条已端点初筛，37条缺原文，五条本轮跟进仍为来源不足。其他73条决定原样保留；22条来源不足、47条待原文、9条形式排除。47与37来自不同计数维度，不能互换。

## 交付及核查方式

`candidate_decisions.csv`保留逐条理由；`merged_candidate_decisions.csv`为78条累计表；`mass_and_sequence_diagnostics.csv`为条件质量/序列诊断；`search_coverage.csv`和`search_hit_review.csv`为检索追溯；`summary.json`为本批机器状态。原始抓取和时间位于上级acquisition及focused_search。manifest绑定输入、历史保护文件及输出。

执行 `python .../scripts/review.py --output <本批中新的目录>` 可重建表格。`verify.py --review <目录> --output <新的JSON文件>`独立核对摘要、五条/78条覆盖、质量算术与原文目标。视觉转录为代理复核，程序只能验证绑定及一致性，不是独立人工作者评审。未运行模型或pytest。

## 仍待解决

取得同一分子的人红细胞数值HC50或足以按现行规则明确类别的原始删失端点；澄清TT(1-24)实测身份与质量、rtCATH2短片段身份；完整形式复核后再按既有协议执行全员/来源隔离。不能通过借用鱼RBC或其他分子的数值解除blocked。未向作者发送邮件。
