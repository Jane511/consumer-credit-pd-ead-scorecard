import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, roc_curve


def auc_gini(y_true, y_score):
    auc = roc_auc_score(y_true, y_score)
    gini = 2 * auc - 1
    return {"auc": float(auc), "gini": float(gini)}


def roc_curve_table(y_true, y_score):
    fpr, tpr, thresholds = roc_curve(y_true, y_score)
    return pd.DataFrame({
        "threshold": thresholds,
        "fpr": fpr,
        "tpr": tpr
    })


def ks_table(df, score_col, target_col="TARGET", n_bins=10):
    temp = df[[score_col, target_col]].dropna().copy()
    temp["bucket"] = pd.qcut(temp[score_col], q=n_bins, duplicates="drop")

    out = (
        temp.groupby("bucket")[target_col]
        .agg(total="count", bad="sum")
        .reset_index()
    )
    out["good"] = out["total"] - out["bad"]

    out = out.sort_values("bucket").reset_index(drop=True)

    total_good = out["good"].sum()
    total_bad = out["bad"].sum()

    out["cum_good_pct"] = out["good"].cumsum() / total_good
    out["cum_bad_pct"] = out["bad"].cumsum() / total_bad
    out["ks"] = np.abs(out["cum_bad_pct"] - out["cum_good_pct"])
    return out


def decile_table(df, score_col, target_col="TARGET", ascending=False, n_bins=10):
    temp = df[[score_col, target_col]].dropna().copy()

    if ascending:
        ranks = temp[score_col].rank(method="first", ascending=True)
    else:
        ranks = temp[score_col].rank(method="first", ascending=False)

    temp["decile"] = pd.qcut(ranks, q=n_bins, labels=False, duplicates="drop") + 1

    out = (
        temp.groupby("decile")[target_col]
        .agg(obs="count", bads="sum", bad_rate="mean")
        .reset_index()
        .sort_values("decile")
    )
    return out


def score_band_default_rates(df, band_col, target_col="TARGET"):
    return (
        df.groupby(band_col)[target_col]
        .agg(obs="count", bads="sum", default_rate="mean")
        .reset_index()
        .sort_values(band_col)
    )


def validation_metrics_table(y_true, y_score):
    metrics = auc_gini(y_true, y_score)
    return pd.DataFrame([metrics])
