import pandas as pd


def monthly_default_rate(df, date_col, target_col="TARGET"):
    temp = df[[date_col, target_col]].dropna().copy()
    temp[date_col] = pd.to_datetime(temp[date_col])
    temp["month"] = temp[date_col].dt.to_period("M").astype(str)

    out = (
        temp.groupby("month")[target_col]
        .agg(obs="count", bads="sum", default_rate="mean")
        .reset_index()
        .sort_values("month")
    )
    return out


def monthly_predicted_vs_observed(df, date_col, pred_col="pred_pd", target_col="TARGET"):
    temp = df[[date_col, pred_col, target_col]].dropna().copy()
    temp[date_col] = pd.to_datetime(temp[date_col])
    temp["month"] = temp[date_col].dt.to_period("M").astype(str)

    out = (
        temp.groupby("month")
        .agg(
            obs=(target_col, "count"),
            observed_default_rate=(target_col, "mean"),
            mean_predicted_pd=(pred_col, "mean")
        )
        .reset_index()
        .sort_values("month")
    )
    out["calibration_gap"] = out["mean_predicted_pd"] - out["observed_default_rate"]
    return out


def policy_cutoff_table():
    return pd.DataFrame({
        "score_range": ["700+", "650-699", "600-649", "550-599", "<550"],
        "risk_level": ["Low", "Moderate", "Medium", "High", "Very High"],
        "decision": [
            "Approve",
            "Approve / Review",
            "Refer",
            "Decline / Senior Review",
            "Decline"
        ]
    })
