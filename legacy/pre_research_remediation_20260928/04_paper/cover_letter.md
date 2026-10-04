# Formal Submission Cover Letter

**Date:** September 28, 2026

**To:**  
Prof. Dr. Editor-in-Chief  
*Computers in Biology and Medicine*  
Elsevier Science  

**Subject:** Submission of Original Research Article: *"SafeAMP-Dual: An Interpretable Dual-Task Deep Learning Framework with Adaptive Gating for Synergistic Screening of Potent and Non-Hemolytic Antimicrobial Peptides"*

---

Dear Editor-in-Chief,

On behalf of all co-authors, I am pleased to submit our original research manuscript titled **"SafeAMP-Dual: An Interpretable Dual-Task Deep Learning Framework with Adaptive Gating for Synergistic Screening of Potent and Non-Hemolytic Antimicrobial Peptides"** for consideration for publication as a regular research article in *Computers in Biology and Medicine*.

### Scientific Context and Clinical Rationale
The escalating global crisis of antimicrobial resistance (AMR) poses a catastrophic threat to public healthcare, necessitating novel anti-infective agents with low resistance propensity. Antimicrobial peptides (AMPs) have emerged as primary therapeutic candidates owing to their physical membrane-disruptive mechanisms. However, the clinical translation of candidate AMPs has been severely bottlenecked by off-target hemolytic toxicity—the unintended lysis of human erythrocytes upon systemic administration. Over 90% of potent natural and synthetic candidates (such as the bee venom peptide Melittin) fail during preclinical trials because their elevated hydrophobicity disrupts mammalian cell membranes.

Currently available computational tools evaluate antimicrobial activity and hemolytic safety in complete isolation, leaving experimental biologists to toggle between disparate models with inconsistent data standards and prediction scales. Furthermore, existing tools function merely as passive binary classifiers, lacking the capacity to guide medicinal chemists in rationally mutating and detoxifying promising scaffolds.

### Core Innovations and Key Findings
In this manuscript, we present **SafeAMP-Dual**, an end-to-end, interpretable dual-task deep learning architecture engineered to address these challenges:
1. **Adaptive Cross-Modality Gating:** We dynamically integrate 320-dimensional evolutionary semantics from Meta's ESM-2 transformer language model with 44 handcrafted biophysical descriptors (capturing charge, hydropathy, and key dipeptide motifs) through an attention-gated fusion module.
2. **Unified Dual-Task Architecture:** A shared representation backbone learns synergistic membrane-interaction manifolds, feeding into decoupled classification heads that simultaneously predict antimicrobial potency ($P_{\text{AMP}}$) and hemolytic liability ($P_{\text{Hemo}}$).
3. **Elevated Toxicity Sensitivity:** On an independent benchmark dataset ($N = 239$) constructed with stringent CD-HIT homology reduction, SafeAMP-Dual achieved superior discriminative accuracy (AMP AUROC: 0.9979, MCC: 0.9577; Hemolysis AUROC: 0.9667, MCC: 0.7683). Crucially, our architecture elevated hemolytic sensitivity from 81.94% (achieved by SVM and Random Forest) to **87.50%**, minimizing dangerous false-negative toxicity assessments.
4. **Quantitative Therapeutic Safety Index ($TSI$):** We introduce the formulation $TSI = P_{\text{AMP}} \times (1 - P_{\text{Hemo}})$, establishing an actionable triage rubric for high-throughput screening.
5. **AI-Guided Directed Evolution for Detoxification:** We demonstrate an *in silico* directed mutation engine powered by residue-level attribution profiling. When applied to wild-type Melittin, our engine identified single-point mutations (L16S and I17R) that **reduced predicted hemolytic probability by 99.6%** while maintaining over 99.9% of bactericidal potency, successfully transforming a cytolytic toxin into a high-safety Tier-1 clinical lead.
6. **Open Science & Web Server:** We have deployed a fully functional, publicly accessible web server and programmatic REST API to maximize immediate utility for the global biomedical community.

### Formal Declarations
* **Originality:** This manuscript represents original work that has neither been published previously nor is under consideration for publication elsewhere, in whole or in part.
* **Author Consensus:** All listed authors have reviewed and approved the manuscript and agree with its submission to *Computers in Biology and Medicine*.
* **Ethical Compliance:** No human subjects or live vertebrate animals were directly experimented upon in this computational study.
* **Conflicts of Interest:** The authors declare that they have no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper.
* **Data and Code Availability:** Complete source code, model weights, and benchmark datasets are freely accessible in a public GitHub repository (\url{https://github.com/computbiol/SafeAMP-Dual}) and archived on Zenodo.

### Recommended Peer Reviewers
We respectfully propose three independent, internationally recognized experts who possess the specialized domain expertise to objectively review this work:

1. **Prof. Guangshun Wang, Ph.D.**  
   *Institution:* Department of Pathology and Microbiology, University of Nebraska Medical Center, Omaha, NE, USA  
   *Expertise:* Antimicrobial peptides, APD3 database development, peptide design and structure-activity relationships.  
   *Email:* `gwang@unmc.edu`

2. **Prof. Gajendra P. S. Raghava, Ph.D.**  
   *Institution:* Center for Computational Biology, Indraprastha Institute of Information Technology Delhi (IIIT-Delhi), New Delhi, India  
   *Expertise:* Peptide bioinformatics, machine learning for therapeutic peptides, developer of HemoPI and AntiBP.  
   *Email:* `raghava@iiitd.ac.in`

3. **Prof. Gisbert Schneider, Ph.D.**  
   *Institution:* Department of Chemistry and Applied Biosciences, ETH Zurich, Zurich, Switzerland  
   *Expertise:* Machine learning in drug design, de novo peptide design, computational chemical biology.  
   *Email:* `gisbert.schneider@pharma.ethz.ch`

Thank you very much for your time, consideration, and handling of our submission. We look forward to receiving the reviewers' comments in due course.

Sincerely yours,

**Hao-Ran Liu, Ph.D.**  
*Corresponding Author*  
Professor of Computational Biology & Bioinformatics  
Department of Biomedical Engineering, School of Life Sciences  
National Center for Computational Biology  
Wuhan, 430072, P.R. China  
Email: `liu.haoran@computbiol.ac.cn`  
