
import pandas as pd

def apply_bins(series, spec):
    if spec["type"] == "numeric":
        return pd.cut(series, bins=spec["edges"], include_lowest=True).astype(str).fillna("MISSING")
    return series.astype(str).fillna("MISSING")

def transform_to_woe(df, binning_store, default_woe=0.0):
    out = pd.DataFrame(index=df.index)
    for feature, meta in binning_store.items():
        bins = apply_bins(df[feature], meta["spec"])
        out[feature] = bins.map(meta["mapping"]).fillna(default_woe)
    return out
