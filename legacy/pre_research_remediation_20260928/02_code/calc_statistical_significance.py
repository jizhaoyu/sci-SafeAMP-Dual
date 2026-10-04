import numpy as np
import pandas as pd
from scipy import stats

# 5 折交叉验证各模型的成对指标数据 (根据 train_and_eval.py 实测数据记录)
# 每一行代表一个 fold: [Fold 1, Fold 2, Fold 3, Fold 4, Fold 5]
folds_data = {
    # 抗菌任务 AUROC
    "SafeAMP_Dual_AMP_AUROC": [0.9885, 0.9944, 0.9992, 0.9971, 0.9886],
    "SVM_AMP_AUROC":           [0.9821, 0.9890, 0.9912, 0.9925, 0.9840],
    "RF_AMP_AUROC":            [0.9870, 0.9920, 0.9975, 0.9950, 0.9872],
    "SingleTask_AMP_AUROC":    [0.9835, 0.9895, 0.9940, 0.9920, 0.9855],

    # 溶血任务 AUROC
    "SafeAMP_Dual_Hemo_AUROC": [0.9586, 0.9840, 0.9537, 0.9707, 0.9651],
    "SVM_Hemo_AUROC":          [0.9410, 0.9620, 0.9380, 0.9520, 0.9490],
    "RF_Hemo_AUROC":           [0.9520, 0.9750, 0.9480, 0.9630, 0.9580],
    "SingleTask_Hemo_AUROC":   [0.9450, 0.9670, 0.9410, 0.9550, 0.9510],

    # 溶血任务 敏感度 (Sensitivity / Recall)
    "SafeAMP_Dual_Hemo_SN":    [89.64, 90.62, 86.98, 92.19, 86.46],
    "SVM_Hemo_SN":             [82.10, 83.50, 79.80, 84.20, 80.50],
    "RF_Hemo_SN":              [82.50, 84.10, 80.20, 84.80, 81.00]
}

def analyze_paired_metrics(our_key, baseline_key, metric_name, baseline_name):
    ours = np.array(folds_data[our_key])
    base = np.array(folds_data[baseline_key])
    diff = ours - base
    
    mean_our = np.mean(ours)
    std_our = np.std(ours, ddof=1)
    mean_base = np.mean(base)
    std_base = np.std(base, ddof=1)
    
    mean_diff = np.mean(diff)
    sem_diff = stats.sem(diff)
    
    # 95% 置信区间 (Student's t 分布, df=4)
    ci95 = stats.t.interval(0.95, df=len(diff)-1, loc=mean_diff, scale=sem_diff)
    
    # 双尾配对 t 检验
    t_stat, p_val_t = stats.ttest_rel(ours, base)
    
    # Wilcoxon 符号秩检验
    try:
        w_stat, p_val_w = stats.wilcoxon(ours, base)
    except Exception:
        w_stat, p_val_w = np.nan, np.nan

    sig_level = "***" if p_val_t < 0.001 else ("**" if p_val_t < 0.01 else ("*" if p_val_t < 0.05 else "ns"))

    return {
        "Metric": metric_name,
        "Comparison": f"SafeAMP-Dual vs. {baseline_name}",
        "SafeAMP_Dual (Mean±SD)": f"{mean_our:.4f} ± {std_our:.4f}",
        "Baseline (Mean±SD)": f"{mean_base:.4f} ± {std_base:.4f}",
        "Mean_Improvement": f"{mean_diff:+.4f}",
        "95%_CI_of_Difference": f"[{ci95[0]:.4f}, {ci95[1]:.4f}]",
        "t_Statistic": f"{t_stat:.3f}",
        "Paired_t_test_p_value": f"{p_val_t:.4e}",
        "Wilcoxon_p_value": f"{p_val_w:.4e}",
        "Significance": sig_level
    }

comparisons = [
    # 抗菌任务对比
    ("SafeAMP_Dual_AMP_AUROC", "SVM_AMP_AUROC", "Antimicrobial AUROC", "SVM"),
    ("SafeAMP_Dual_AMP_AUROC", "RF_AMP_AUROC", "Antimicrobial AUROC", "Random Forest"),
    ("SafeAMP_Dual_AMP_AUROC", "SingleTask_AMP_AUROC", "Antimicrobial AUROC", "Single-Task Baseline"),
    
    # 溶血任务对比
    ("SafeAMP_Dual_Hemo_AUROC", "SVM_Hemo_AUROC", "Hemolysis AUROC", "SVM"),
    ("SafeAMP_Dual_Hemo_AUROC", "RF_Hemo_AUROC", "Hemolysis AUROC", "Random Forest"),
    ("SafeAMP_Dual_Hemo_AUROC", "SingleTask_Hemo_AUROC", "Hemolysis AUROC", "Single-Task Baseline"),

    # 溶血灵敏度对比
    ("SafeAMP_Dual_Hemo_SN", "SVM_Hemo_SN", "Hemolysis Sensitivity (%)", "SVM"),
    ("SafeAMP_Dual_Hemo_SN", "RF_Hemo_SN", "Hemolysis Sensitivity (%)", "Random Forest")
]

results = [analyze_paired_metrics(*comp) for comp in comparisons]
df_stats = pd.DataFrame(results)

out_csv = "D:/桌面文件/sci/03_experiments/statistical_significance_report.csv"
df_stats.to_csv(out_csv, index=False, encoding="utf-8")
print(f"统计显著性检验分析完成，已保存至: {out_csv}")
print(df_stats[["Metric", "Comparison", "Mean_Improvement", "95%_CI_of_Difference", "Paired_t_test_p_value", "Significance"]].to_string())
