# PD Scorecard Project

## Overview
This project builds a bank-style Probability of Default (PD) scorecard using WOE, IV, and logistic regression.

## Methodology
Data → Binning → WOE → IV → Logistic Regression → Scorecard → Validation → Monitoring → Governance

## Components
- Feature Engineering
- WOE / IV Transformation
- Logistic Regression Model
- Scorecard Scaling
- Validation (AUC, KS, Gini)
- Monitoring (PSI)
- Calibration
- Score-to-Grade Mapping
- Model Documentation
- Backtesting
- Policy Cut-offs

## Key Result
AUC ≈ 0.746 (robust, interpretable model)

## Business Use
- Credit approval decisions
- Risk segmentation
- Pricing input
- Portfolio monitoring

## Governance
Includes:
- Model limitations
- Monitoring thresholds
- Stability checks
- Policy usage framework

## Notes
This project prioritises interpretability, stability, and real-world banking alignment over marginal performance gains.
