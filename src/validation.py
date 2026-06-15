import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score, roc_curve


def binomial_pd_test(predicted_pd, observed_defaults, n, alpha=0.05):
    """One-sided binomial calibration test per grade/pool (PD framework Part 5.3).

    Tests whether the predicted PD materially UNDER-estimates the realised default
    rate. Under H0 the number of defaults ~ Binomial(n, predicted_pd); the one-sided
    p-value is P(X >= observed_defaults). A small p-value means more defaults occurred
    than the PD predicted -> the grade looks under-calibrated (optimistic).

    IMPORTANT caveat (WP14): the binomial test assumes defaults are INDEPENDENT. When
    defaults are correlated (the realistic case) it understates the true Type-I error,
    so amber/red flags are prompts for review, not hard pass/fail.

    Returns a dict: predicted_pd, observed_defaults, n, observed_rate, expected_defaults,
    p_value (one-sided, under-estimation), and a green/amber/red traffic-light flag.
    """
    n = int(n)
    observed_defaults = int(observed_defaults)
    p = float(predicted_pd)
    # P(X >= observed) = sf(observed - 1) on a Binomial(n, p).
    p_value = float(stats.binom.sf(observed_defaults - 1, n, p)) if n > 0 else np.nan
    if np.isnan(p_value):
        flag = "n/a"
    elif p_value >= alpha:
        flag = "green"                       # not significantly under-predicted
    elif p_value >= alpha / 5.0:             # 0.01 .. 0.05
        flag = "amber"
    else:
        flag = "red"                         # strongly under-predicted
    return {
        "predicted_pd": p,
        "n": n,
        "observed_defaults": observed_defaults,
        "observed_rate": observed_defaults / n if n else np.nan,
        "expected_defaults": p * n,
        "p_value_underest": p_value,
        "flag": flag,
    }


def hosmer_lemeshow(y_true, y_score, n_bins=10):
    """Hosmer-Lemeshow chi-square goodness-of-fit / calibration test.

    Buckets observations by predicted PD into n_bins (deciles by default) and compares
    observed vs expected defaults per bucket. The statistic is
        H = sum_g (O_g - E_g)^2 / (E_g * (1 - E_g / n_g))
    distributed approximately chi-square with (n_bins - 2) degrees of freedom. A small
    p-value indicates poor calibration. Like the binomial test it assumes independent
    observations (WP14 caveat) and so understates error under default correlation.

    Returns dict: chi2, dof, p_value, n_bins_used, plus the per-bucket table.
    """
    df = pd.DataFrame({"y": np.asarray(y_true, dtype=float),
                       "p": np.asarray(y_score, dtype=float)}).dropna()
    df["bucket"] = pd.qcut(df["p"], q=n_bins, duplicates="drop")
    g = df.groupby("bucket", observed=True).agg(
        n=("y", "size"), observed=("y", "sum"), expected=("p", "sum")
    ).reset_index()
    denom = g["expected"] * (1.0 - g["expected"] / g["n"])
    denom = denom.replace(0, np.nan)
    g["contrib"] = (g["observed"] - g["expected"]) ** 2 / denom
    chi2 = float(g["contrib"].sum())
    dof = max(len(g) - 2, 1)
    p_value = float(stats.chi2.sf(chi2, dof))
    return {"chi2": chi2, "dof": dof, "p_value": p_value,
            "n_bins_used": int(len(g)), "table": g}


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
