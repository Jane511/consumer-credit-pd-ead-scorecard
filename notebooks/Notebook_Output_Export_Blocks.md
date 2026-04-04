# Notebook Output Export Blocks

Use these code cells at the **end of each notebook** to save key tables into `output/`.

Assumed project structure:

```python
from pathlib import Path
OUTPUT_DIR = Path("../output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
```

You can also use:
```python
from src.output import save_csv
```

---

## HomeCredit_01_External_Data_Preparation.ipynb

```python
from pathlib import Path
from src.output import save_csv

OUTPUT_DIR = Path("../output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Replace with your actual dataframe names
if "application_base" in locals():
    save_csv(application_base, OUTPUT_DIR / "application_base.csv")

if "external_feature_base" in locals():
    save_csv(external_feature_base, OUTPUT_DIR / "external_feature_base.csv")

if "bureau_agg" in locals():
    save_csv(bureau_agg, OUTPUT_DIR / "bureau_agg.csv")

if "previous_agg" in locals():
    save_csv(previous_agg, OUTPUT_DIR / "previous_agg.csv")

print("Notebook 01 outputs exported.")
```

---

## HomeCredit_02_Logistic_With_External_Features.ipynb

```python
from pathlib import Path
from src.output import save_csv
import pandas as pd

OUTPUT_DIR = Path("../output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Main modelling base
if "df_model" in locals():
    save_csv(df_model, OUTPUT_DIR / "model_dataset_with_external_features.csv")

# Selected feature list
if "selected_features" in locals():
    save_csv(pd.DataFrame({"feature": selected_features}), OUTPUT_DIR / "selected_features_logistic_external.csv")

# Coefficients
if "model" in locals() and "selected_features" in locals() and hasattr(model, "coef_"):
    coef_df = pd.DataFrame({
        "feature": selected_features,
        "coefficient": model.coef_[0]
    }).sort_values("coefficient", ascending=False)
    save_csv(coef_df, OUTPUT_DIR / "logistic_external_coefficients.csv")

# Predictions
if {"X_test", "y_test", "model"}.issubset(locals()):
    pred_test = pd.DataFrame({
        "actual_target": y_test,
        "pred_pd": model.predict_proba(X_test)[:, 1]
    })
    save_csv(pred_test, OUTPUT_DIR / "logistic_external_test_predictions.csv")

print("Notebook 02 outputs exported.")
```

---

## HomeCredit_03_PD_Scorecard_Build.ipynb

```python
from pathlib import Path
from src.output import save_csv
import pandas as pd

OUTPUT_DIR = Path("../output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 1. Full WOE table
if "woe_table_all" in locals():
    save_csv(woe_table_all, OUTPUT_DIR / "woe_table_all_features.csv")

# 2. IV summary
if "woe_table_all" in locals():
    iv_summary = (
        woe_table_all[["feature", "iv"]]
        .drop_duplicates()
        .sort_values("iv", ascending=False)
        .reset_index(drop=True)
    )
    save_csv(iv_summary, OUTPUT_DIR / "iv_summary.csv")

# 3. Selected features
if "selected_features" in locals():
    save_csv(pd.DataFrame({"feature": selected_features}), OUTPUT_DIR / "selected_features_scorecard.csv")

# 4. WOE-transformed train/test
if "X_train_woe" in locals():
    save_csv(X_train_woe, OUTPUT_DIR / "train_woe_transformed.csv")

if "X_test_woe" in locals():
    save_csv(X_test_woe, OUTPUT_DIR / "test_woe_transformed.csv")

# 5. Model coefficients on WOE features
if "scorecard_model" in locals() and "selected_features" in locals() and hasattr(scorecard_model, "coef_"):
    coef_df = pd.DataFrame({
        "feature": selected_features,
        "coefficient": scorecard_model.coef_[0]
    }).sort_values("coefficient", ascending=False)
    save_csv(coef_df, OUTPUT_DIR / "scorecard_model_coefficients.csv")

# 6. Scorecard points table
# Replace scorecard_points_table with your actual score table dataframe name
if "scorecard_points_table" in locals():
    save_csv(scorecard_points_table, OUTPUT_DIR / "scorecard_points_table.csv")

# 7. Train/test scored outputs
if {"X_train_woe", "y_train", "scorecard_model"}.issubset(locals()):
    train_scored = X_train_woe.copy()
    train_scored["TARGET"] = y_train
    train_scored["pred_pd"] = scorecard_model.predict_proba(X_train_woe)[:, 1]
    save_csv(train_scored, OUTPUT_DIR / "train_scored.csv")

if {"X_test_woe", "y_test", "scorecard_model"}.issubset(locals()):
    test_scored = X_test_woe.copy()
    test_scored["TARGET"] = y_test
    test_scored["pred_pd"] = scorecard_model.predict_proba(X_test_woe)[:, 1]
    save_csv(test_scored, OUTPUT_DIR / "test_scored.csv")

# 8. Optional score band summary
# Requires a score_total or score_band column if you created one
if "test_scored" in locals() and "score_band" in test_scored.columns:
    score_band_summary = (
        test_scored.groupby("score_band")["TARGET"]
        .agg(obs="count", bads="sum", default_rate="mean")
        .reset_index()
        .sort_values("score_band")
    )
    save_csv(score_band_summary, OUTPUT_DIR / "score_band_summary.csv")

print("Notebook 03 outputs exported.")
```

---

## HomeCredit_04_PD_Scorecard_Validation_and_Business_Use.ipynb

```python
from pathlib import Path
from src.output import save_csv
from src.validation import validation_metrics_table, roc_curve_table, ks_table, decile_table, score_band_default_rates

OUTPUT_DIR = Path("../output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Assumes test_scored has pred_pd and TARGET
if "test_scored" in locals() and {"pred_pd", "TARGET"}.issubset(test_scored.columns):
    validation_metrics = validation_metrics_table(test_scored["TARGET"], test_scored["pred_pd"])
    save_csv(validation_metrics, OUTPUT_DIR / "validation_metrics.csv")

    roc_tbl = roc_curve_table(test_scored["TARGET"], test_scored["pred_pd"])
    save_csv(roc_tbl, OUTPUT_DIR / "roc_curve_points.csv")

    ks_tbl = ks_table(test_scored, score_col="pred_pd", target_col="TARGET", n_bins=10)
    save_csv(ks_tbl, OUTPUT_DIR / "ks_table.csv")

    dec_tbl = decile_table(test_scored, score_col="pred_pd", target_col="TARGET", ascending=False, n_bins=10)
    save_csv(dec_tbl, OUTPUT_DIR / "decile_table.csv")

    save_csv(test_scored, OUTPUT_DIR / "predictions_test.csv")

# Score band default rates
if "test_scored" in locals() and "score_band" in test_scored.columns:
    band_tbl = score_band_default_rates(test_scored, band_col="score_band", target_col="TARGET")
    save_csv(band_tbl, OUTPUT_DIR / "score_band_default_rates.csv")

# Calibration table
# Replace score_total with pred_pd if your calibration is by predicted PD
from src.calibration import calibration_table
if "test_scored" in locals() and {"pred_pd", "TARGET"}.issubset(test_scored.columns):
    calib_tbl = calibration_table(test_scored, score_col="pred_pd", target_col="TARGET", bins=10)
    save_csv(calib_tbl, OUTPUT_DIR / "calibration_table.csv")

print("Notebook 04 outputs exported.")
```

---

## HomeCredit_05_PD_Scorecard_Advanced_Monitoring_and_Stability.ipynb

```python
from pathlib import Path
from src.output import save_csv
from src.monitoring import psi_table, score_to_grade_mapping

OUTPUT_DIR = Path("../output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 1. PSI by score band
if "train_scored" in locals() and "test_scored" in locals():
    if "score_band" in train_scored.columns and "score_band" in test_scored.columns:
        expected_counts = train_scored["score_band"].value_counts().sort_index()
        actual_counts = test_scored["score_band"].value_counts().sort_index()

        all_bands = sorted(set(expected_counts.index).union(set(actual_counts.index)))
        expected_counts = expected_counts.reindex(all_bands, fill_value=0)
        actual_counts = actual_counts.reindex(all_bands, fill_value=0)

        psi_tbl = psi_table(expected_counts.values, actual_counts.values, labels=all_bands)
        save_csv(psi_tbl, OUTPUT_DIR / "psi_by_score_band.csv")

# 2. Population shift summary (simple)
if "psi_tbl" in locals():
    population_shift_summary = psi_tbl[["band", "expected_dist", "actual_dist", "psi_component", "psi_total"]].copy()
    save_csv(population_shift_summary, OUTPUT_DIR / "population_shift_summary.csv")

# 3. Calibration summary
from src.calibration import calibrate_pd
import pandas as pd

if "test_scored" in locals() and {"pred_pd", "TARGET"}.issubset(test_scored.columns):
    observed_dr = test_scored["TARGET"].mean()
    target_long_run_dr = observed_dr * 1.10  # replace if you have a benchmark
    calibrated_pd, factor = calibrate_pd(test_scored["pred_pd"].values, observed_dr, target_long_run_dr)
    calibration_summary = pd.DataFrame({
        "observed_default_rate": [observed_dr],
        "target_long_run_default_rate": [target_long_run_dr],
        "calibration_factor": [factor],
        "mean_raw_pd": [test_scored["pred_pd"].mean()],
        "mean_calibrated_pd": [calibrated_pd.mean()]
    })
    save_csv(calibration_summary, OUTPUT_DIR / "calibration_summary.csv")

# 4. Score-to-grade mapping
if "test_scored" in locals() and "score_total" in test_scored.columns:
    grade_tbl = score_to_grade_mapping(test_scored, score_col="score_total", target_col="TARGET", n_grades=8)
    save_csv(grade_tbl, OUTPUT_DIR / "score_to_grade_mapping.csv")

# 5. OOT summary if created
if "oot_test" in locals() and {"pred_pd", "TARGET"}.issubset(oot_test.columns):
    oot_validation_summary = pd.DataFrame({
        "obs": [len(oot_test)],
        "observed_default_rate": [oot_test["TARGET"].mean()],
        "mean_pred_pd": [oot_test["pred_pd"].mean()]
    })
    save_csv(oot_validation_summary, OUTPUT_DIR / "oot_validation_summary.csv")

print("Notebook 05 outputs exported.")
```

---

## HomeCredit_06_PD_Scorecard_Model_Risk_and_Portfolio_Governance.ipynb

```python
from pathlib import Path
from src.output import save_csv
import pandas as pd

OUTPUT_DIR = Path("../output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Save these only if you created them in the notebook
if "monitoring_thresholds" in locals():
    save_csv(monitoring_thresholds, OUTPUT_DIR / "monitoring_thresholds.csv")

if "challenger_framework" in locals():
    save_csv(challenger_framework, OUTPUT_DIR / "challenger_framework.csv")

if "policy_example" in locals():
    save_csv(policy_example, OUTPUT_DIR / "policy_usage_example.csv")

if "redevelopment_triggers" in locals():
    save_csv(redevelopment_triggers, OUTPUT_DIR / "redevelopment_triggers.csv")

# Optional narrative summary table
governance_summary = pd.DataFrame({
    "section": [
        "model_limitations",
        "monitoring_thresholds",
        "challenger_models",
        "policy_usage",
        "redevelopment_triggers"
    ],
    "status": [
        "documented",
        "defined",
        "documented",
        "documented",
        "documented"
    ]
})
save_csv(governance_summary, OUTPUT_DIR / "governance_summary.csv")

print("Notebook 06 outputs exported.")
```

---

## HomeCredit_07_PD_Scorecard_Model_Documentation_Backtesting_Policy.ipynb

```python
from pathlib import Path
from src.output import save_csv
from src.backtesting import monthly_default_rate, monthly_predicted_vs_observed, policy_cutoff_table
import pandas as pd

OUTPUT_DIR = Path("../output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 1. Model documentation summary
if "model_documentation" in locals():
    model_doc_df = pd.DataFrame(model_documentation.items(), columns=["section", "details"])
    save_csv(model_doc_df, OUTPUT_DIR / "model_documentation_summary.csv")

# 2. Monthly backtesting
DATE_COL = None  # replace with your date column

if "test_scored" in locals() and DATE_COL is not None and DATE_COL in test_scored.columns:
    bt_default = monthly_default_rate(test_scored, date_col=DATE_COL, target_col="TARGET")
    save_csv(bt_default, OUTPUT_DIR / "backtesting_default_rate_by_month.csv")

    if "pred_pd" in test_scored.columns:
        bt_compare = monthly_predicted_vs_observed(test_scored, date_col=DATE_COL, pred_col="pred_pd", target_col="TARGET")
        save_csv(bt_compare, OUTPUT_DIR / "backtesting_predicted_vs_observed.csv")

# 3. Policy cut-off table
policy_tbl = policy_cutoff_table()
save_csv(policy_tbl, OUTPUT_DIR / "policy_cutoff_table.csv")

print("Notebook 07 outputs exported.")
```

---

## Optional: one common helper cell for every notebook

```python
from pathlib import Path
from src.output import save_csv

OUTPUT_DIR = Path("../output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("Output folder ready:", OUTPUT_DIR.resolve())
```
