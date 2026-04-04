import numpy as np
import pandas as pd


def psi(expected, actual, eps=1e-6):
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)
    expected = np.where(expected <= 0, eps, expected)
    actual = np.where(actual <= 0, eps, actual)
    return np.sum((actual - expected) * np.log(actual / expected))


def psi_table(expected_counts, actual_counts, labels=None, eps=1e-6):
    expected_counts = np.asarray(expected_counts, dtype=float)
    actual_counts = np.asarray(actual_counts, dtype=float)

    expected_dist = expected_counts / expected_counts.sum()
    actual_dist = actual_counts / actual_counts.sum()

    expected_dist = np.where(expected_dist <= 0, eps, expected_dist)
    actual_dist = np.where(actual_dist <= 0, eps, actual_dist)

    psi_component = (actual_dist - expected_dist) * np.log(actual_dist / expected_dist)

    out = pd.DataFrame({
        "band": labels if labels is not None else np.arange(len(expected_counts)),
        "expected_count": expected_counts,
        "actual_count": actual_counts,
        "expected_dist": expected_dist,
        "actual_dist": actual_dist,
        "psi_component": psi_component
    })
    out["psi_total"] = out["psi_component"].sum()
    return out


def monotonic_bad_rate_table(df, feature_col, target_col="TARGET"):
    temp = df[[feature_col, target_col]].copy()
    out = (
        temp.groupby(feature_col)[target_col]
        .agg(obs="count", bads="sum", bad_rate="mean")
        .reset_index()
        .sort_values(feature_col)
    )
    out["bad_rate_diff"] = out["bad_rate"].diff()
    return out


def time_split(df, date_col, split_date):
    temp = df.copy()
    temp[date_col] = pd.to_datetime(temp[date_col])
    split_date = pd.to_datetime(split_date)
    train = temp[temp[date_col] < split_date].copy()
    test = temp[temp[date_col] >= split_date].copy()
    return train, test


def score_to_grade_mapping(df, score_col, target_col="TARGET", n_grades=8, grade_labels=None):
    temp = df[[score_col, target_col]].dropna().copy()
    temp["grade"] = pd.qcut(temp[score_col], q=n_grades, duplicates="drop")

    out = (
        temp.groupby("grade")[target_col]
        .agg(obs="count", bads="sum", default_rate="mean")
        .reset_index()
        .sort_values("grade")
    )

    if grade_labels is not None and len(grade_labels) == len(out):
        out["grade_name"] = grade_labels
    else:
        out["grade_name"] = [f"G{i+1}" for i in range(len(out))]

    return out
