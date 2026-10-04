# 作者数据核实请求草稿

状态：仅本地草稿，尚未发送。发送前由用户填写自己的姓名、机构和联系方式。

**Subject:** Clarification of experimental peptide identities and hemolysis source data — s41564-025-02061-0

Dear authors,

We are reviewing the public experimental evidence accompanying your article, “Deep learning reveals antibiotics in the archaeal proteome” (doi: 10.1038/s41564-025-02061-0), for a reproducible computational biology analysis.

We obtained the 80 peptide certificates of analysis from Mendeley Data (10.17632/d8yzgtdrcp.3 / .5), as well as the MIC and HC50 source workbooks. To ensure that we associate measurements with the actual tested molecules, could you please provide or point us to the following information?

1. A table explicitly mapping each assay identifier (Archaeasin-1 through Archaeasin-80) to its certificate peptide name, amino-acid sequence, and synthesis batch. We will not infer this mapping from file or row order.
2. The N-terminal and C-terminal forms of the synthesized molecules, including any acetylation, amidation, other covalent modifications, or stereochemical substitutions. The certificates provide sequences and masses but do not explicitly state the terminal forms. A synthesis specification or batch record would be helpful.
3. The original source workbook for Extended Data Fig. 7 (`41564_2025_2061_MOESM17_ESM.xlsx`), ideally with concentrations, replicate absorbance or hemolysis values, controls, and assay identifiers. Our publisher download returned HTML rather than a workbook.
4. Clarification of the concentration range: the Methods describe 0.78–100 µM peptide solution mixed with an equal volume of RBC suspension, whereas the Extended Data Fig. 7 caption describes 4–64 µM. Which concentrations are the final concentrations in the measured wells?
5. How HC50 values were calculated. The figure caption describes nonlinear interpolation, while the Methods and reported outputs require clarification about fitting and values outside the tested range. Were any reported values extrapolated? Can values without an observed 50% crossing be represented as a lower bound at the highest validated concentration?
6. The meaning of blank MIC entries in the Fig. 2 source workbook: not tested, no inhibition at the highest tested concentration, or another status. We will retain these as missing until confirmed.

We only need molecule and assay data; no donor-identifying information is requested. Please also confirm the applicable reuse license for any additional files.

Thank you for your help.

[Name]
[Institution]
[Contact]
