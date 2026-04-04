# PD Scorecard Development

## Overview

This project develops a **Probability of Default (PD) scorecard** using a traditional credit risk modelling framework widely applied in retail banking.

The modelling approach follows:

Data → Binning → WOE → IV → Logistic Regression → Scorecard → PD Mapping

This ensures:
- interpretability
- stability
- regulatory explainability
- business usability

---

## Alignment with Banking Practice

Australian banks operate under APRA (Australian Prudential Regulation Authority).

Under APS 113:
- banks must estimate PD, LGD, EAD
- maintain internal rating systems
- ensure validation and governance

APRA does NOT prescribe specific methods (e.g. WOE/logistic), but banks commonly use scorecards.

Retail banking commonly uses scorecards for PD estimation.

---

## Methodology

### 1. Variable Binning

Variables are grouped into bins to:
- capture non-linearity
- improve stability
- enforce monotonic risk

---

### 2. Weight of Evidence (WOE)

WOE is defined as:

WOE_i = ln( (G_i / G) / (B_i / B) )

Where:
- G_i = goods in bin
- B_i = bads in bin

Interpretation:
- Positive → lower risk
- Negative → higher risk

---

### 3. Information Value (IV)

IV is defined as:

IV = Σ (P_good - P_bad) × WOE

Used for:
- feature selection
- removing weak predictors

---

### 4. Logistic Regression

Model:

logit(PD) = β0 + β1 × WOE1 + ...

Benefits:
- linear relationship
- stable coefficients
- explainability

---

### 5. Scorecard Scaling

- Convert model into points
- Total score = sum of variable points
- Map score → PD bands

---

## Model Validation

- AUC / ROC
- Gini
- KS
- Decile analysis
- Calibration

Model achieved:
AUC ≈ 0.746

---

## Business Use

- credit approval
- risk ranking
- pricing input
- portfolio monitoring

---

## Key Principles

- interpretability over complexity
- stability over marginal AUC gain
- regulatory alignment
- business usability

---

## Summary

This project demonstrates a traditional bank-style PD scorecard aligned with:
- IRB framework
- retail banking practices
- WOE/IV methodology
