# DAVIS 基准数据集官方获取与校验报告

* **数据来源：** Harvard Dataverse (Therapeutics Data Commons: [doi:10.7910/DVN/21LKWG](https://doi.org/10.7910/DVN/21LKWG))
* **下载链接：** `https://dataverse.harvard.edu/api/access/datafile/5219748?format=original` (Datafile ID: 5219748, format=original)
* **文件名：** `davis.csv`
* **文件大小：** 21,222,080 字节
* **官方 MD5 校验：** `6c7949b81aea69e9d816db88602d771e` (**校验通过：与官方 Dataverse 元数据 6c7949b81aea69e9d816db88602d771e 完全匹配**)
* **本地 SHA-256：** `d54e81d2b6172f5ea71dacc4d7615adaee1cfbabcefccc7f2b46c7c48c19a373`
* **准入说明：** 
  * 首版获取（v1）请求默认端点时取得 Dataverse 自动转换的 TSV 格式（21,376,712 字节，MD5 843c1bde8b468500fc8356de6cb6adb9），因与官方元数据记录的原始文件 MD5 不一致而拒绝准入；失败现场已完整保留在 `dti_davis_acquisition_20261006_v1`。
  * 本版（v2）显式请求原始格式 `?format=original`，取得官方发布的完整原始 CSV 文件，MD5 完全一致。
  * 当前仅完成文件获取与哈希闭环，未进入模型训练，未释放标签。
