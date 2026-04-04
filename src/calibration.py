
import numpy as np
import pandas as pd

def calibration_table(df, score_col, target_col="TARGET", bins=10):
    df = df.copy()
    df["bucket"] = pd.qcut(df[score_col], q=bins, duplicates="drop")
    return df.groupby("bucket")[target_col].mean().reset_index()

def calibrate_pd(raw_pd, observed_dr, target_dr):
    factor = target_dr / observed_dr
    return np.clip(raw_pd * factor, 1e-6, 1.0), factor
