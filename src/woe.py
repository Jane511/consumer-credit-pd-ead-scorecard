
import pandas as pd
import numpy as np

def safe_qcut(series, max_bins=5):
    clean = series.dropna()
    if clean.nunique() <= 1:
        return None
    if clean.nunique() <= max_bins:
        try:
            return pd.cut(clean, bins=clean.nunique(), duplicates="drop")
        except:
            return None
    for q in range(max_bins, 1, -1):
        try:
            cats = pd.qcut(clean, q=q, duplicates="drop")
            if len(cats.cat.categories) >= 2:
                return cats
        except:
            continue
    return None

def fit_woe(train_series, target, feature_name, max_bins=5, smoothing=0.5):
    df = pd.DataFrame({"x": train_series, "target": target})

    if pd.api.types.is_numeric_dtype(df["x"]):
        binned = safe_qcut(df["x"], max_bins)
        if binned is None:
            df["bin"] = df["x"].astype(str).fillna("MISSING")
            spec = {"type": "categorical"}
        else:
            df.loc[binned.index, "bin"] = binned.astype(str)
            df["bin"] = df["bin"].fillna("MISSING")
            intervals = pd.IntervalIndex(binned.cat.categories)
            edges = [intervals[0].left] + [iv.right for iv in intervals]
            spec = {"type": "numeric", "edges": edges}
    else:
        df["bin"] = df["x"].astype(str).fillna("MISSING")
        spec = {"type": "categorical"}

    grp = df.groupby("bin")["target"].agg(total="count", bad="sum").reset_index()
    grp["good"] = grp["total"] - grp["bad"]

    total_good = grp["good"].sum()
    total_bad = grp["bad"].sum()

    grp["dist_good"] = (grp["good"] + smoothing) / (total_good + smoothing * len(grp))
    grp["dist_bad"] = (grp["bad"] + smoothing) / (total_bad + smoothing * len(grp))

    grp["woe"] = np.log(grp["dist_good"] / grp["dist_bad"])
    grp["iv_component"] = (grp["dist_good"] - grp["dist_bad"]) * grp["woe"]
    grp["iv"] = grp["iv_component"].sum()
    grp["feature"] = feature_name

    mapping = dict(zip(grp["bin"], grp["woe"]))

    return grp, spec, mapping
