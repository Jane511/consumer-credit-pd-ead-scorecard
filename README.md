# Probability of Default Modelling and Scorecard Project

A portfolio project that builds an interpretable **Probability of Default (PD)** workflow on the **Home Credit Default Risk** dataset, then extends that workflow into a more bank-style **scorecard**, **validation**, **monitoring**, and **governance** pack.

## What this repository shows

This repository is designed as a credit-risk portfolio project rather than a Kaggle-only modelling exercise.

It follows a staged workflow:

1. build a baseline logistic regression model on application data
2. engineer external bureau and behavioural aggregates
3. rerun logistic regression with richer features
4. convert the model into a WOE / IV scorecard
5. validate the scorecard with AUC, Gini, KS, deciles, and calibration
6. document monitoring, stability, governance, and policy use

The focus is on **interpretability, structure, and business use**, not just maximising one performance metric.

## Main entry point

Start here, then open the notebooks in the following order:

- `notebooks/HomeCredit_00_Logistic with Applicationdata.ipynb`
- `notebooks/HomeCredit_01_External_Data_Preparation.ipynb`
- `notebooks/HomeCredit_02_Logistic_With_External_Features.ipynb`
- `notebooks/HomeCredit_03_PD_Scorecard_Build.ipynb`
- `notebooks/HomeCredit_04_PD_Scorecard_Validation_and_Business_Use.ipynb`
- `notebooks/HomeCredit_05_PD_Scorecard_Advanced_Monitoring_and_Stability.ipynb`
- `notebooks/HomeCredit_06_PD_Scorecard_Model_Risk_and_Portfolio_Governance.ipynb`
- `notebooks/HomeCredit_07_PD_Scorecard_Model_Documentation_Backtesting_Policy.ipynb`

Supplementary notes:
- `PD_README.md`
- `Scorecard_README.md`

## Repository structure

```text
.
├── data/                 # raw Home Credit files
├── notebooks/            # ordered project workflow
├── output/               # notebook exports, tables, charts
├── outputs/              # recruiter-friendly snapshot tables and notes
├── src/                  # reusable helper modules
├── README.md             # main entry point
├── PD_README.md          # compact PD-specific notes
├── Scorecard_README.md   # compact scorecard-specific notes
└── requirements.txt
```

## Notebook map

### Notebook 00 — baseline logistic regression
Builds a simple application-data logistic regression model to create a benchmark using affordability, leverage, and stability variables.

### Notebook 01 — external data preparation
Aggregates bureau, previous applications, POS cash, instalments, and credit card history into a customer-level feature table.

### Notebook 02 — logistic regression with external features
Compares the baseline model against an enriched model that uses external aggregates.

### Notebook 03 — scorecard build
Applies WOE / IV, fits a logistic regression scorecard, creates points, and assigns score bands.

### Notebook 04 — validation and business use
Reviews discrimination, calibration, deciles, score bands, and a simple policy overlay.

### Notebook 05 — monitoring and stability
Documents PSI, monotonic review, calibration concepts, reject inference awareness, and score-to-grade mapping.

### Notebook 06 — governance
Adds a model-risk and portfolio-governance layer with monitoring thresholds, challenger discussion, override notes, and redevelopment triggers.

### Notebook 07 — documentation and policy
Summarises model documentation, backtesting framing, and policy cut-off design.

## Business interpretation

This project is aimed at explaining how an interpretable retail credit model can support credit decisions.

In business terms:

- **PD** estimates the likelihood that a borrower defaults
- the **scorecard** converts model logic into points and score bands
- safer score bands can support faster approvals
- weaker score bands can support manual review, tighter policy, or decline decisions
- validation and monitoring help check whether the model remains stable and useful over time

The project therefore connects model output to:
- credit approval
- risk segmentation
- policy cut-offs
- governance and monitoring

## Example portfolio message

A concise way to describe this project is:

> Built a bank-style Probability of Default modelling and scorecard portfolio project using the Home Credit dataset, covering baseline logistic regression, external feature aggregation, WOE / IV scorecard development, validation, calibration, monitoring, governance, and policy interpretation.

## Saved outputs for quick review

The repository includes recruiter-friendly snapshot files in `outputs/`, plus notebook export targets in `output/`.

Useful quick files:
- `outputs/portfolio_snapshot_metrics.csv`
- `outputs/portfolio_policy_cutoff_example.csv`
- `outputs/portfolio_notes.md`

## Requirements

Install packages with:

```bash
pip install -r requirements.txt
```

## Limitations

This is a **portfolio demonstration**, not a production or regulatory capital model.

Important limitations:

- it uses the public **Home Credit** dataset rather than a real bank portfolio
- it is designed to demonstrate methodology and workflow
- scorecard bins and policy cut-offs are illustrative
- reject inference is documented but not fully implemented
- calibration and monitoring are portfolio-level demonstrations, not formal bank production controls
- this is **not** an APRA IRB production model

## Documentation cleanup note

Older overlapping README-style files have been archived as redirect notes so that this `README.md` is now the single main entry point.
