# Home Credit PD Scorecard Portfolio Notebooks

Open the notebooks in this order:

1. `01_Home_Credit_PD_Scorecard_Build.ipynb`
   - Builds a compact WOE/logistic scorecard
   - Creates score points and score bands
   - Saves outputs to `../processed/scorecard_outputs/`

2. `02_Home_Credit_PD_Scorecard_Validation_and_Business_Use.ipynb`
   - Loads the saved scorecard outputs
   - Produces AUC, Gini, KS, decile, calibration, and policy tables
   - Adds business interpretation for portfolio presentation

## Expected data structure

The notebooks assume the same folder structure used in your earlier Home Credit project:

- `../data/application_train.csv`
- `../processed/home_credit_external_features.csv`

If you already saved a merged file at `../processed/home_credit_model_base_after_merge.csv`, the first notebook will use that directly.

## Portfolio note

The notebooks are designed to move from:
- exploratory logistic regression
to
- a more bank-style scorecard workflow with validation and business interpretation.
