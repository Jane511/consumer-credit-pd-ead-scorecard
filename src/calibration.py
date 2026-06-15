
import numpy as np
import pandas as pd

# Regulatory PD floor: APS 113 Attachment B para 1 / PD framework Step 11 require
# PD = max(estimate, 0.0005) for non-sovereign exposures (5 basis points).
PD_FLOOR = 0.0005


def apply_pd_floor(pd_estimate, floor=PD_FLOOR):
    """Apply the regulatory 5 bps PD floor: PD = max(estimate, floor).

    APS 113 Att B para 1 / PD framework Step 11. Accepts a scalar, numpy array or
    pandas Series and preserves the input type. On this book the minimum grade PD is
    ~5%, so the floor does not bind here -- it is applied for completeness and so the
    pipeline stays correct on any future, lower-risk segment.
    """
    if isinstance(pd_estimate, pd.Series):
        return pd_estimate.clip(lower=floor)
    return np.maximum(pd_estimate, floor)


def calibration_table(df, score_col, target_col="TARGET", bins=10):
    df = df.copy()
    df["bucket"] = pd.qcut(df[score_col], q=bins, duplicates="drop")
    return df.groupby("bucket")[target_col].mean().reset_index()

def calibrate_pd(raw_pd, observed_dr, target_dr):
    factor = target_dr / observed_dr
    # Lower bound is the regulatory 5 bps floor (was 1e-6) per APS 113 Att B para 1.
    return np.clip(raw_pd * factor, PD_FLOOR, 1.0), factor
