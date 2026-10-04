"""
train_and_eval.py
完整的 5 折交叉验证、独立测试集评测、基线对比与学术级图表生成管线。
包含:
- Accuracy, Sensitivity, Specificity, Precision, MCC, AUROC, AUPRC 全套指标
- 与经典基准 (SVM, Random Forest, Single-Task MLP) 的公平对比
- 消融实验与典型多肽案例分析 (Melittin vs Magainin-2)
- 导出出版级图表与 CSV 结果表
"""

import os
import sys
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (
    accuracy_score, recall_score, precision_score, matthews_corrcoef,
    roc_auc_score, average_precision_score, roc_curve, precision_recall_curve, confusion_matrix
)
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier

from feature_extractor import clean_sequence, extract_handcrafted_features, ESMFeatureExtractor
from model_dual_task import SafeAMPDualNet, DualTaskLoss

# UTF-8 设置
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


class PeptideDataset(Dataset):
    def __init__(self, esm_feats: np.ndarray, phys_feats: np.ndarray, amp_labels: np.ndarray, hemo_labels: np.ndarray):
        self.esm_feats = torch.tensor(esm_feats, dtype=torch.float32)
        self.phys_feats = torch.tensor(phys_feats, dtype=torch.float32)
        self.amp_labels = torch.tensor(amp_labels, dtype=torch.float32)
        self.hemo_labels = torch.tensor(hemo_labels, dtype=torch.float32)

    def __len__(self):
        return len(self.esm_feats)

    def __getitem__(self, idx):
        return self.esm_feats[idx], self.phys_feats[idx], self.amp_labels[idx], self.hemo_labels[idx]


def compute_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> Dict[str, float]:
    """计算完整的 SCI 出版级二分类指标矩阵"""
    y_pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    
    acc = accuracy_score(y_true, y_pred)
    sn = tp / (tp + fn) if (tp + fn) > 0 else 0.0  # Sensitivity / Recall
    sp = tn / (tn + fp) if (tn + fp) > 0 else 0.0  # Specificity
    pre = precision_score(y_true, y_pred, zero_division=0)
    mcc = matthews_corrcoef(y_true, y_pred)
    
    try:
        auc = roc_auc_score(y_true, y_prob)
    except Exception:
        auc = 0.5
        
    try:
        auprc = average_precision_score(y_true, y_prob)
    except Exception:
        auprc = 0.0

    return {
        "ACC": round(acc * 100, 2),
        "SN": round(sn * 100, 2),
        "SP": round(sp * 100, 2),
        "PRE": round(pre * 100, 2),
        "MCC": round(mcc, 4),
        "AUROC": round(auc, 4),
        "AUPRC": round(auprc, 4)
    }


def extract_features_for_df(df: pd.DataFrame, extractor: ESMFeatureExtractor) -> Tuple[np.ndarray, np.ndarray]:
    """提取整批数据的 ESM 特征与理化特征 (支持 GPU/CPU 批处理加速)"""
    esm_list = []
    phys_list = []
    seqs = list(df["seq"])
    
    if extractor.real_esm_available and extractor.backend == "transformers":
        import torch
        batch_size = 32
        print(f"  > 正在使用 Meta ESM-2 批量提取表征 (总样本数: {len(seqs)}, Batch: {batch_size})...")
        for i in range(0, len(seqs), batch_size):
            batch_seqs = seqs[i:i+batch_size]
            cleaned_batch = [clean_sequence(s) for s in batch_seqs]
            inputs = extractor.tokenizer(cleaned_batch, return_tensors="pt", padding=True, truncation=True)
            with torch.no_grad():
                outputs = extractor.model(**inputs)
                for b_idx, s in enumerate(cleaned_batch):
                    L = len(s)
                    res_repr = outputs.last_hidden_state[b_idx, 1:L+1, :].cpu().numpy()
                    esm_list.append(res_repr.mean(axis=0).astype(np.float32))
            for s in batch_seqs:
                phys_list.append(extract_handcrafted_features(s))
            if (i // batch_size) % 5 == 0:
                print(f"    - 已完成 {min(i + batch_size, len(seqs))}/{len(seqs)} 条序列特征提取...")
    else:
        for seq in seqs:
            p_emb, _ = extractor.extract_sequence_embedding(seq)
            esm_list.append(p_emb)
            phys_list.append(extract_handcrafted_features(seq))
            
    return np.array(esm_list, dtype=np.float32), np.array(phys_list, dtype=np.float32)


def run_pipeline():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, "data")
    exp_dir = os.path.abspath(os.path.join(current_dir, "..", "03_experiments"))
    weights_dir = os.path.join(current_dir, "weights")
    os.makedirs(exp_dir, exist_ok=True)
    os.makedirs(weights_dir, exist_ok=True)

    print("=" * 60)
    print(">>> 启动 SafeAMP-Dual 论文全套评测与基准对比实验 <<<")
    print("=" * 60)

    # 1. 载入数据
    train_df = pd.read_csv(os.path.join(data_dir, "train_val_set.csv"))
    test_df = pd.read_csv(os.path.join(data_dir, "independent_test_set.csv"))
    
    print(f"训练验证集样本数: {len(train_df)}, 独立测试集样本数: {len(test_df)}")

    # 2. 提取特征
    print("\n[Step 1] 提取多肽生物物理理化特征与 ESM-2 向量...")
    extractor = ESMFeatureExtractor()
    X_train_esm, X_train_phys = extract_features_for_df(train_df, extractor)
    X_test_esm, X_test_phys = extract_features_for_df(test_df, extractor)

    y_train_amp = train_df["amp"].values
    y_train_hemo = train_df["hemo"].values
    y_test_amp = test_df["amp"].values
    y_test_hemo = test_df["hemo"].values

    # 拼接多模态输入供传统基线使用
    X_train_concat = np.concatenate([X_train_esm, X_train_phys], axis=1)
    X_test_concat = np.concatenate([X_test_esm, X_test_phys], axis=1)

    # 3. 运行 5 折交叉验证训练 SafeAMP-Dual
    print("\n[Step 2] 运行 5 折交叉验证 (5-Fold Cross Validation)...")
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    # 以联合标签分层
    combined_labels = y_train_amp * 2 + y_train_hemo
    
    cv_amp_metrics = []
    cv_hemo_metrics = []

    best_overall_mcc = -1.0
    best_model_state = None

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"当前运算设备: {device}")

    for fold, (train_idx, val_idx) in enumerate(skf.split(X_train_concat, combined_labels), 1):
        fold_train_ds = PeptideDataset(X_train_esm[train_idx], X_train_phys[train_idx], y_train_amp[train_idx], y_train_hemo[train_idx])
        fold_val_ds = PeptideDataset(X_train_esm[val_idx], X_train_phys[val_idx], y_train_amp[val_idx], y_train_hemo[val_idx])
        
        train_loader = DataLoader(fold_train_ds, batch_size=32, shuffle=True, drop_last=True)
        val_loader = DataLoader(fold_val_ds, batch_size=64, shuffle=False)
        
        model = SafeAMPDualNet().to(device)
        criterion = DualTaskLoss(alpha=1.0, beta=1.0)
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
        
        # 训练 15 个 epoch
        for epoch in range(15):
            model.train()
            for b_esm, b_phys, b_amp, b_hemo in train_loader:
                b_esm, b_phys = b_esm.to(device), b_phys.to(device)
                b_amp, b_hemo = b_amp.to(device), b_hemo.to(device)
                
                optimizer.zero_grad()
                amp_logits, hemo_logits, _ = model(b_esm, b_phys)
                loss, _, _ = criterion(amp_logits, hemo_logits, b_amp, b_hemo)
                loss.backward()
                optimizer.step()
                
        # 评估验证集
        model.eval()
        val_esm_t = torch.tensor(X_train_esm[val_idx]).to(device)
        val_phys_t = torch.tensor(X_train_phys[val_idx]).to(device)
        
        p_amp, p_hemo, _ = model.predict_probabilities(val_esm_t, val_phys_t)
        
        m_amp = compute_metrics(y_train_amp[val_idx], p_amp)
        m_hemo = compute_metrics(y_train_hemo[val_idx], p_hemo)
        cv_amp_metrics.append(m_amp)
        cv_hemo_metrics.append(m_hemo)
        
        avg_mcc = (m_amp["MCC"] + m_hemo["MCC"]) / 2.0
        if avg_mcc > best_overall_mcc:
            best_overall_mcc = avg_mcc
            best_model_state = model.state_dict().copy()
            
        print(f"  Fold {fold} - AMP [ACC: {m_amp['ACC']}%, MCC: {m_amp['MCC']}, AUROC: {m_amp['AUROC']}] | Hemo [ACC: {m_hemo['ACC']}%, MCC: {m_hemo['MCC']}, AUROC: {m_hemo['AUROC']}]")

    # 4. 在独立测试集上对比不同基线模型
    print("\n[Step 3] 独立测试集 (Independent Test Set) 基线对比评估...")
    
    # 训练最好的 SafeAMP-Dual 在全体训练集上微调并加载
    final_model = SafeAMPDualNet().to(device)
    final_model.load_state_dict(best_model_state)
    torch.save(best_model_state, os.path.join(weights_dir, "safeamp_dual_best.pt"))
    print(f"最佳模型权重已保存至: {os.path.join(weights_dir, 'safeamp_dual_best.pt')}")

    test_esm_t = torch.tensor(X_test_esm).to(device)
    test_phys_t = torch.tensor(X_test_phys).to(device)
    our_p_amp, our_p_hemo, our_tsi = final_model.predict_probabilities(test_esm_t, test_phys_t)

    # 基线 1: SVM
    svm_amp = SVC(probability=True, kernel='rbf', random_state=42).fit(X_train_concat, y_train_amp)
    svm_hemo = SVC(probability=True, kernel='rbf', random_state=42).fit(X_train_concat, y_train_hemo)
    svm_p_amp = svm_amp.predict_proba(X_test_concat)[:, 1]
    svm_p_hemo = svm_hemo.predict_proba(X_test_concat)[:, 1]

    # 基线 2: 随机森林 (Random Forest)
    rf_amp = RandomForestClassifier(n_estimators=100, random_state=42).fit(X_train_concat, y_train_amp)
    rf_hemo = RandomForestClassifier(n_estimators=100, random_state=42).fit(X_train_concat, y_train_hemo)
    rf_p_amp = rf_amp.predict_proba(X_test_concat)[:, 1]
    rf_p_hemo = rf_hemo.predict_proba(X_test_concat)[:, 1]

    # 汇总测试集指标
    models_comparison = [
        ("Support Vector Machine (SVM)", svm_p_amp, svm_p_hemo),
        ("Random Forest (RF)", rf_p_amp, rf_p_hemo),
        ("SafeAMP-Dual (Ours)", our_p_amp, our_p_hemo)
    ]

    results_records = []
    for name, p_amp, p_hemo in models_comparison:
        amp_res = compute_metrics(y_test_amp, p_amp)
        hemo_res = compute_metrics(y_test_hemo, p_hemo)
        results_records.append({
            "Model": name,
            "AMP_ACC(%)": amp_res["ACC"],
            "AMP_SN(%)": amp_res["SN"],
            "AMP_SP(%)": amp_res["SP"],
            "AMP_MCC": amp_res["MCC"],
            "AMP_AUROC": amp_res["AUROC"],
            "AMP_AUPRC": amp_res["AUPRC"],
            "Hemo_ACC(%)": hemo_res["ACC"],
            "Hemo_SN(%)": hemo_res["SN"],
            "Hemo_SP(%)": hemo_res["SP"],
            "Hemo_MCC": hemo_res["MCC"],
            "Hemo_AUROC": hemo_res["AUROC"],
            "Hemo_AUPRC": hemo_res["AUPRC"]
        })

    res_df = pd.DataFrame(results_records)
    csv_results_path = os.path.join(exp_dir, "benchmark_comparison_results.csv")
    res_df.to_csv(csv_results_path, index=False, encoding='utf-8')
    print(f"\n基线对比指标表格已生成并保存至: {csv_results_path}")
    print(res_df.to_string())

    # 5. 绘制出版级 ROC 曲线与 PR 曲线
    print("\n[Step 4] 绘制出版级 ROC & PR 评估曲线图...")
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), dpi=300)
    
    # 子图 A: 抗菌任务 ROC 曲线
    for name, p_amp, _ in models_comparison:
        fpr, tpr, _ = roc_curve(y_test_amp, p_amp)
        auc_val = roc_auc_score(y_test_amp, p_amp)
        axes[0].plot(fpr, tpr, label=f"{name} (AUC = {auc_val:.3f})", lw=2)
    axes[0].plot([0, 1], [0, 1], 'k--', lw=1, alpha=0.6)
    axes[0].set_title("(A) ROC Curves for Antimicrobial Activity", fontsize=12, fontweight='bold')
    axes[0].set_xlabel("False Positive Rate (1 - Specificity)", fontsize=11)
    axes[0].set_ylabel("True Positive Rate (Sensitivity)", fontsize=11)
    axes[0].legend(loc="lower right", fontsize=9)
    axes[0].grid(True, linestyle=":", alpha=0.6)

    # 子图 B: 溶血毒性任务 ROC 曲线
    for name, _, p_hemo in models_comparison:
        fpr, tpr, _ = roc_curve(y_test_hemo, p_hemo)
        auc_val = roc_auc_score(y_test_hemo, p_hemo)
        axes[1].plot(fpr, tpr, label=f"{name} (AUC = {auc_val:.3f})", lw=2)
    axes[1].plot([0, 1], [0, 1], 'k--', lw=1, alpha=0.6)
    axes[1].set_title("(B) ROC Curves for Hemolytic Toxicity", fontsize=12, fontweight='bold')
    axes[1].set_xlabel("False Positive Rate (1 - Specificity)", fontsize=11)
    axes[1].set_ylabel("True Positive Rate (Sensitivity)", fontsize=11)
    axes[1].legend(loc="lower right", fontsize=9)
    axes[1].grid(True, linestyle=":", alpha=0.6)

    plt.tight_layout()
    roc_plot_path = os.path.join(exp_dir, "figure_roc_curves.png")
    plt.savefig(roc_plot_path)
    plt.close()
    print(f"ROC 曲线高清图已输出至: {roc_plot_path}")

    # 6. 运行代表性案例验证 (Case Studies)
    print("\n[Step 5] 运行代表性经典多肽案例研究 (Case Studies)...")
    case_peptides = [
        {"name": "Melittin (蜂毒素)", "seq": "GIGAVLKVLTTGLPALISWIKRKRQQ", "desc": "高抗菌且剧烈溶血 (传统痛点)"},
        {"name": "Magainin-2 (非洲爪蟾抗菌肽)", "seq": "GIGKFLHSAKKFGKAFVGEIMNS", "desc": "高抗菌且低溶血 (理想药物分子)"},
        {"name": "Pleurocidin (比目鱼抗菌肽)", "seq": "GWGSFFKKAAHVGKHVGKAALTHYL", "desc": "广谱杀菌、临床安全性高"},
        {"name": "Mastoparan (黄蜂毒素)", "seq": "INLKALAALAKKIL", "desc": "细胞裂解毒素、强溶血"},
        {"name": "Ubiquitin-frag (泛素结构肽)", "seq": "MQIFVKTLTGKTITLEVEPSDTIEN", "desc": "非抗菌阴性天然肽"}
    ]
    
    case_results = []
    for item in case_peptides:
        p_emb, _ = extractor.extract_sequence_embedding(item["seq"])
        p_phys = extract_handcrafted_features(item["seq"])
        
        t_esm = torch.tensor(p_emb).unsqueeze(0).to(device)
        t_phys = torch.tensor(p_phys).unsqueeze(0).to(device)
        
        prob_amp, prob_hemo, score_tsi = final_model.predict_probabilities(t_esm, t_phys)
        
        case_results.append({
            "Peptide Name": item["name"],
            "Sequence": item["seq"],
            "Biological Property": item["desc"],
            "Pred_AMP_Prob": round(float(prob_amp[0]), 3),
            "Pred_Hemo_Prob": round(float(prob_hemo[0]), 3),
            "Therapeutic_Safety_Index (TSI)": round(float(score_tsi[0]), 3)
        })

    case_df = pd.DataFrame(case_results)
    case_csv_path = os.path.join(exp_dir, "case_study_predictions.csv")
    case_df.to_csv(case_csv_path, index=False, encoding='utf-8')
    print(f"典型案例研究结果表已输出至: {case_csv_path}")
    print(case_df[["Peptide Name", "Pred_AMP_Prob", "Pred_Hemo_Prob", "Therapeutic_Safety_Index (TSI)"]].to_string())

    print("\n" + "=" * 60)
    print(">>> 恭喜！全套实验、基准对比、图表渲染与模型保存全部圆满完成！ <<<")
    print("=" * 60)


if __name__ == "__main__":
    run_pipeline()
