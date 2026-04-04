# PD Scorecard Theory, Mathematics, and Implementation Guide

This document is the detailed technical guide for the **PD scorecard** part of the repository. It brings together the theory, mathematical framework, business purpose, and Python implementation logic used across the scorecard notebooks.

## 1. What a PD scorecard is

A **Probability of Default (PD) scorecard** is a structured model that estimates the likelihood that a borrower will default within a defined time horizon.

In retail credit practice, a scorecard is often preferred because it is:
- interpretable
- stable
- explainable to business users
- suitable for monitoring and governance

The workflow used in this repository follows:

Data → Feature Engineering → Binning → WOE → IV → Logistic Regression → Score Scaling → Validation → Monitoring → Governance

## 2. Business purpose

A scorecard is not only a predictive model. It is also a practical credit decision framework.

Typical uses include:
- approval and decline support
- manual review prioritisation
- score band segmentation
- portfolio monitoring
- policy cut-off design
- pricing support

In a broader credit risk framework:

Expected Loss = PD × LGD × EAD

Where:
- **PD** = probability of default
- **LGD** = loss given default
- **EAD** = exposure at default

This repository focuses on the **PD** component.

## 3. Why use a scorecard instead of only raw machine learning

The repository deliberately prioritises a bank-style scorecard rather than a pure black-box model.

Reasons:
- coefficient direction can be reviewed
- variable risk ordering can be checked
- score points can be explained to non-technical users
- monitoring is easier over time
- model governance is easier to document

For portfolio purposes, this also shows understanding of how modelling is used in a real lending environment, not only how to maximise benchmark performance.

## 4. Core theory

### 4.1 Binning

Raw variables are first grouped into bins.

Purpose of binning:
- capture non-linear relationships
- reduce noise
- make risk trends easier to inspect
- support more stable modelling
- allow missing values to be handled explicitly

Examples:
- income may be grouped into ranges
- utilisation may be grouped into bands
- delinquency may be grouped into risk buckets

### 4.2 Weight of Evidence (WOE)

For each bin, Weight of Evidence is calculated as:

WOE_i = ln((G_i / G) / (B_i / B))

Where:
- G_i = number of goods in bin i
- B_i = number of bads in bin i
- G = total goods in the sample
- B = total bads in the sample

Interpretation:
- positive WOE usually indicates lower risk than average
- negative WOE usually indicates higher risk than average
- WOE near zero indicates neutral risk

Why WOE is useful:
- converts bins into a numeric form suitable for logistic regression
- makes direction of risk easier to understand
- can improve stability and interpretability

### 4.3 Information Value (IV)

Information Value is used to summarise predictive strength of a variable.

IV = Σ (Dist_Good_i - Dist_Bad_i) × WOE_i

Where:
- Dist_Good_i = proportion of total goods in bin i
- Dist_Bad_i = proportion of total bads in bin i

Common interpretation guide:
- IV < 0.02 → very weak
- 0.02 to 0.10 → weak
- 0.10 to 0.30 → medium
- 0.30 to 0.50 → strong
- > 0.50 → may require review for leakage or instability

IV is used here to help shortlist scorecard variables.

### 4.4 Logistic regression

After WOE transformation, the scorecard model is estimated with logistic regression.

The model is:

logit(PD) = ln(PD / (1 - PD)) = β0 + β1X1 + β2X2 + ... + βnXn

Where:
- β0 is the intercept
- βi are coefficients
- Xi are WOE-transformed variables

The predicted PD is then:

PD = 1 / (1 + exp(-(β0 + β1X1 + ... + βnXn)))

Why logistic regression is used:
- outputs probabilities
- coefficients are interpretable
- widely accepted in scorecard practice
- works naturally with WOE-transformed inputs

## 5. Score scaling mathematics

A logistic model gives log-odds or predicted PD, but business users often want a **score**.

The repository converts model output into a points-based scale using:

Score = Offset - Factor × log(Odds)

Where Odds usually means:

Odds = PD / (1 - PD)

Two common calibration settings are used:
- **Base Score**: score assigned to a chosen base odds level
- **PDO**: points to double the odds

The scaling constants are:

Factor = PDO / ln(2)

Offset = Base Score - Factor × ln(Base Odds)

This lets the score behave in a controlled, explainable way.

Higher score usually means lower risk.

### Bin-level points

Once the scorecard model is fitted on WOE variables, the repository allocates points to each bin using the coefficient and WOE value.

Conceptually:

Points for a bin = base allocation - Factor × β × WOE

This creates a full points table that can be used to:
- score borrowers
- create score bands
- link score bands to policy actions

## 6. Validation framework

The repository validates the scorecard using multiple lenses rather than only one metric.

### 6.1 AUC / ROC

AUC measures discriminatory power.

Interpretation:
- 0.50 = random
- higher AUC = better separation of goods and bads

### 6.2 Gini

Gini is derived from AUC:

Gini = 2 × AUC - 1

It is a common credit risk summary metric.

### 6.3 KS

The Kolmogorov–Smirnov statistic measures maximum separation between cumulative bad and cumulative good distributions.

Higher KS usually indicates better rank separation.

### 6.4 Decile analysis

Predictions or scores are grouped into ranked buckets.

The goal is to check whether observed bad rate moves in the expected direction across the ranked groups.

### 6.5 Calibration

Discrimination checks ranking quality.
Calibration checks whether predicted PD is reasonably aligned with observed default rate.

This repository includes grouped calibration views and later calibration-to-benchmark discussion.

## 7. Monitoring and governance framework

A scorecard should not stop at model fit. This repository extends into the model lifecycle.

Included topics:
- monotonic bin review
- PSI by score band
- reject inference discussion
- time-based validation concept
- calibration to long-run or through-the-cycle PD
- score-to-grade mapping
- monitoring thresholds
- challenger framing
- policy usage and override discussion
- redevelopment triggers

### Population Stability Index (PSI)

PSI is used to compare the distribution of a population between two periods or samples.

Typical interpretation:
- PSI < 0.10 → minor shift
- 0.10 to 0.25 → moderate shift
- > 0.25 → material shift requiring review

This helps assess whether the scorecard is being applied to a population that looks different from the development sample.

## 8. Notebook implementation logic

The scorecard notebooks in this repository are organised as a staged workflow.

### Notebook 03 — PD scorecard build

Main implementation logic:
- load modelling base
- rebuild key application and external features
- choose scorecard candidate variables
- split train and test
- fit binning rules on training data
- calculate WOE tables and IV summary
- filter to final scorecard variables
- transform train and test data to WOE
- fit logistic regression on WOE inputs
- convert coefficients and WOE bins into score points
- score borrowers and assign score bands
- export scorecard artefacts

### Notebook 04 — validation and business use

Main implementation logic:
- load exported scorecard outputs
- compute AUC, Gini, KS
- create ROC and KS curves
- build decile tables
- build score-band summaries
- check grouped calibration
- overlay example policy actions by band
- export validation outputs

### Notebook 05 — advanced monitoring and stability

Main implementation logic:
- review monotonicity of bins
- calculate PSI by score band
- document reject inference limitations
- show out-of-time validation design concept
- demonstrate calibration to long-run benchmark idea
- convert score into grades for reporting use

### Notebook 06 — model risk and governance

Main implementation logic:
- document model limitations
- define monitoring thresholds
- explain champion / challenger framework
- explain scorecard use in policy and overrides
- define redevelopment triggers

### Notebook 07 — documentation, backtesting, policy

Main implementation logic:
- summarise model documentation
- document backtesting structure
- present example policy cut-off table

## 9. Python script logic behind the scorecard

Across the notebooks and `src/` modules, the implementation follows a reusable pattern.

### Input layer
- read raw or processed modelling data
- select the required columns
- handle missing values, type conversion, and simple feature engineering

### Transformation layer
- create bins on training data only
- calculate WOE per bin
- store binning specifications and WOE mappings
- apply the same stored rules to test or future data

### Modelling layer
- fit logistic regression on WOE variables
- calculate predicted PD
- inspect coefficient direction and odds ratios

### Scoring layer
- define base score, base odds, and PDO
- derive scaling constants
- assign bin-level points
- sum variable points into borrower score
- allocate score bands or grades

### Validation layer
- compute discrimination metrics
- compare score bands and deciles
- review calibration
- export result tables for further reporting

## 10. Key modelling principles shown in this repository

This repository is intentionally designed to demonstrate:
- interpretable modelling over black-box complexity
- stable workflow over marginal uplift chasing
- explicit linkage between theory and code
- practical business use after modelling
- awareness of monitoring and governance requirements

## 11. Limitations

This scorecard project is a **portfolio demonstration**, not a production bank model.

Important limitations:
- uses the public Home Credit dataset rather than a live internal portfolio
- uses simplified development choices suitable for demonstration
- does not implement a full reject inference solution
- does not claim APRA IRB production readiness
- uses illustrative score cut-offs and governance examples

## 12. Summary

This scorecard repository shows more than how to fit a logistic regression.
It demonstrates the full logic of a traditional PD scorecard:
- theory
- mathematics
- implementation
- validation
- monitoring
- governance
- business application

That is the main reason the project is useful as a credit risk portfolio piece.
