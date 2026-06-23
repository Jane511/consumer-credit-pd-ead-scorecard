"""
tools/make_pd_validation.py — PD confusion matrix + out-of-sample / cold-holdout validation.

Closes two parity gaps against the Freddie Mac mortgage reference
(`03_confusion_matrix.csv`, `03c_oot_validation.csv`). Both artefacts are rebuilt from the
scored scorecard files (per-borrower predictions, gitignored but on disk) into committed
AGGREGATE tables, so they regenerate reproducibly with:

    python tools/make_pd_validation.py

Outputs (into outputs/tables/scorecard_outputs/):
  16_confusion_matrix.csv  — confusion matrix at a documented cut-off (the portfolio
                             prevalence threshold), with recall / precision / specificity
                             (PD framework Part 5; Freddie artefact 03_confusion_matrix.csv).
  17_oot_validation.csv    — discrimination + calibration + PSI on (a) the random
                             out-of-sample holdout and (b) a never-seen COLD holdout, each
                             with the scorecard's linear stage RE-FIT on the training slice
                             only (no leakage). Freddie artefact 03c_oot_validation.csv.

HONESTY NOTE (carried into the README + alignment doc): the Home Credit dataset is a single
cross-sectional snapshot with no reliable origination date, so a true *calendar* out-of-time
split is not feasible here. We therefore report a random out-of-sample holdout and a never-seen
cold holdout (genuine generalisation tests), and document the temporal-OOT limitation — a real
time-based OOT + forward holdout is demonstrated in the companion Freddie Mac project.

Framework: APS 113 Att D Validation paras 1-3 (realised vs estimated, independent), WP14
(discrimination + calibration), APG 113 para 73 (calibration basis).
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.calibration import apply_pd_floor
from src.psi import psi_table

SC = ROOT / "outputs" / "tables" / "scorecard_outputs"
RNG = 42  # fixed seed so the cold-holdout split is reproducible


def _calibration_factor():
    """Raw -> long-run calibration factor (same as make_pd_calibration.py)."""
    cs = pd.read_csv(SC / "calibration_summary.csv").iloc[0]
    return float(cs["calibrated_mean_pd"]) / float(cs["raw_mean_pd"])


def _points_cols(df):
    return [c for c in df.columns if c.endswith("__points")]


# ---------------------------------------------------------------------------------------
# 16_confusion_matrix.csv — at the portfolio prevalence cut-off
# ---------------------------------------------------------------------------------------
def build_confusion_matrix():
    """Confusion matrix on the test set at the prevalence (base-rate) cut-off.

    The cut-off is the portfolio's calibrated long-run PD, NOT an arbitrary 0.50: at a ~8%
    base rate a 0.50 threshold flags almost nothing, so prevalence-thresholding is the
    standard scorecard choice (high recall, low precision is expected and documented).
    """
    df = pd.read_csv(SC / "06_test_scored.csv", usecols=["pd_pred", "TARGET"]).dropna()
    pd_cal = apply_pd_floor(df["pd_pred"].to_numpy() * _calibration_factor())
    cutoff = float(pd_cal.mean())                         # prevalence threshold
    pred_default = pd_cal >= cutoff
    y = df["TARGET"].to_numpy().astype(int)

    tp = int(((pred_default == 1) & (y == 1)).sum())
    fp = int(((pred_default == 1) & (y == 0)).sum())
    tn = int(((pred_default == 0) & (y == 0)).sum())
    fn = int(((pred_default == 0) & (y == 1)).sum())
    recall = tp / (tp + fn) if (tp + fn) else np.nan          # sensitivity
    precision = tp / (tp + fp) if (tp + fp) else np.nan
    specificity = tn / (tn + fp) if (tn + fp) else np.nan
    accuracy = (tp + tn) / len(y)
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) else np.nan)

    out = pd.DataFrame({
        "metric": [
            "threshold (PD cut-off = portfolio prevalence)",
            "true_positives (caught defaults)",
            "false_positives (false alarms)",
            "true_negatives",
            "false_negatives (missed defaults)",
            "recall (sensitivity)",
            "precision",
            "specificity",
            "accuracy",
            "f1",
        ],
        "value": [
            round(cutoff, 4), tp, fp, tn, fn,
            round(recall, 4), round(precision, 4), round(specificity, 4),
            round(accuracy, 4), round(f1, 4),
        ],
    })
    out.to_csv(SC / "16_confusion_matrix.csv", index=False)
    print("Saved -> outputs/tables/scorecard_outputs/16_confusion_matrix.csv")
    print("  cut-off=%.4f  recall=%.3f  precision=%.3f  (low precision expected at ~8%% base rate)"
          % (cutoff, recall, precision))


# ---------------------------------------------------------------------------------------
# 17_oot_validation.csv — out-of-sample + cold holdout, model re-fit per split (no leakage)
# ---------------------------------------------------------------------------------------
def _fit_score(fit_df, eval_df, feats, factor):
    """Re-fit the scorecard's linear stage on `fit_df` only, score both sets."""
    lr = LogisticRegression(max_iter=1000)
    lr.fit(fit_df[feats], fit_df["TARGET"])
    p_fit = apply_pd_floor(lr.predict_proba(fit_df[feats])[:, 1] * factor)
    p_eval = apply_pd_floor(lr.predict_proba(eval_df[feats])[:, 1] * factor)
    return p_fit, p_eval


def _psi_pd(p_train, p_eval, bins=10):
    """PSI of the predicted-PD distribution, train (expected) vs eval (actual)."""
    edges = np.quantile(p_train, np.linspace(0, 1, bins + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    exp = np.histogram(p_train, bins=edges)[0].astype(float)
    act = np.histogram(p_eval, bins=edges)[0].astype(float)
    return float(psi_table(exp, act))


def build_oot_validation():
    train = pd.read_csv(SC / "05_train_scored.csv")
    test = pd.read_csv(SC / "06_test_scored.csv")
    feats = _points_cols(test)
    factor = _calibration_factor()
    rows = []

    # (A) Random out-of-sample holdout — the existing train/test split. Fit on train,
    #     score test: this is the realised-vs-estimated comparison (Validation para 3).
    p_tr, p_te = _fit_score(train, test, feats, factor)
    rows.append({
        "split": "A) random out-of-sample: fit on train -> score held-out test",
        "train_auc": round(roc_auc_score(train["TARGET"], p_tr), 4),
        "test_auc": round(roc_auc_score(test["TARGET"], p_te), 4),
        "train_avg_predicted_pd": round(float(p_tr.mean()), 4),
        "test_avg_predicted_pd": round(float(p_te.mean()), 4),
        "test_observed_default_rate": round(float(test["TARGET"].mean()), 4),
        "psi_train_vs_test": round(_psi_pd(p_tr, p_te), 4),
    })

    # (B) Cold holdout — pool train+test, hold out a never-seen 30% slice, fit on the
    #     other 70%, score the cold slice. A genuine generalisation test. NOTE: this is a
    #     RANDOM cold slice, not a calendar split: Home Credit is a cross-sectional snapshot
    #     with no usable origination date, so a true time-based OOT is not feasible here
    #     (it IS demonstrated in the Freddie Mac project). Documented, not smoothed over.
    pool = pd.concat([train, test], ignore_index=True)
    cold = pool.sample(frac=0.30, random_state=RNG)
    warm = pool.drop(cold.index)
    p_warm, p_cold = _fit_score(warm, cold, feats, factor)
    rows.append({
        "split": "B) cold holdout (random never-seen 30%; temporal OOT not feasible on snapshot)",
        "train_auc": round(roc_auc_score(warm["TARGET"], p_warm), 4),
        "test_auc": round(roc_auc_score(cold["TARGET"], p_cold), 4),
        "train_avg_predicted_pd": round(float(p_warm.mean()), 4),
        "test_avg_predicted_pd": round(float(p_cold.mean()), 4),
        "test_observed_default_rate": round(float(cold["TARGET"].mean()), 4),
        "psi_train_vs_test": round(_psi_pd(p_warm, p_cold), 4),
    })

    out = pd.DataFrame(rows)
    out.to_csv(SC / "17_oot_validation.csv", index=False)
    print("Saved -> outputs/tables/scorecard_outputs/17_oot_validation.csv")
    for _, r in out.iterrows():
        print("  %-72s test AUC %.3f  PSI %.4f"
              % (r["split"][:72], r["test_auc"], r["psi_train_vs_test"]))


def main():
    build_confusion_matrix()
    build_oot_validation()


if __name__ == "__main__":
    main()
