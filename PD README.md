Yes — call it:

👉 **`PD_README.md`**
or use it as the main `README.md` inside your PD project folder.

Below is a **full PD README** aligned with your earlier work and matching the style of the LGD README.

---

# 📊 Probability of Default (PD) Modelling Project

### Home Credit Default Risk | Logistic Regression Credit Risk Portfolio Project

---

## 📌 Project Overview

This project develops a **Probability of Default (PD) model** using the **Home Credit Default Risk** dataset, with a focus on building a **bank-style, interpretable credit risk model**.

The objective is to estimate the likelihood that a borrower will default, using application-level borrower characteristics and a logistic regression framework. The project is designed to reflect how traditional banks and regulated lenders commonly approach PD modelling: prioritising **interpretability, stability, and economic intuition** over pure black-box performance.

This project forms part of a broader credit risk framework including:

* Probability of Default (PD)
* Loss Given Default (LGD)
* Expected Loss (EL)

---

## 🏦 Business Context

In credit risk modelling:

[
\text{Expected Loss (EL)} = PD \times LGD \times EAD
]

Where:

* **PD** = Probability of Default
* **LGD** = Loss Given Default
* **EAD** = Exposure at Default

PD is a core building block for:

* Credit approval and decline decisions
* Risk-based pricing
* Risk grading / scorecards
* Portfolio monitoring
* Capital and provisioning frameworks

---

## 📁 Dataset Description

This project uses the **Home Credit Default Risk** application data, specifically the **application_train** dataset.

The target variable is:

* `TARGET = 1` → borrower defaulted
* `TARGET = 0` → borrower did not default

The modelling dataset includes a set of selected borrower and loan features designed to capture repayment capacity, leverage, external bureau-style indicators, and borrower stability.

---

## 🎯 Selected Features

The final feature set used in the baseline logistic regression model includes:

* `AMT_INCOME_TOTAL`
* `AMT_CREDIT`
* `AMT_ANNUITY`
* `DTI`
* `INST_TO_INCOME`
* `LTV_PROXY`
* `AGE`
* `EMPLOYMENT_YEARS`
* `CNT_CHILDREN`
* `EXT_SOURCE_2`
* `EXT_SOURCE_3`

These variables were selected to balance:

* predictive relevance
* economic interpretability
* practical usability in a credit underwriting setting

---

## 🧠 Feature Meaning

### Borrower affordability / serviceability

* `AMT_INCOME_TOTAL` – borrower income
* `AMT_ANNUITY` – periodic repayment obligation
* `DTI` – debt-to-income ratio
* `INST_TO_INCOME` – instalment burden relative to income

### Loan size / leverage

* `AMT_CREDIT` – loan amount
* `LTV_PROXY` – proxy measure of leverage or loan-to-value style risk

### Borrower stability

* `AGE` – borrower age
* `EMPLOYMENT_YEARS` – time in employment
* `CNT_CHILDREN` – household burden / dependency proxy

### External risk signals

* `EXT_SOURCE_2`
* `EXT_SOURCE_3`

The `EXT_SOURCE` variables are particularly important in this dataset and act similarly to external bureau or third-party risk indicators.

---

# 💥 PD Methodology

## 📌 1. Conceptual Definition

Probability of Default is the estimated probability that a borrower defaults within the model horizon.

In this project:

[
PD = P(\text{TARGET}=1 \mid X)
]

Where:

* `TARGET = 1` represents default
* `X` represents borrower and loan characteristics

---

## 📊 2. Model Choice

The baseline PD model is built using **Logistic Regression**.

### Why Logistic Regression?

Logistic regression remains the standard benchmark model for many bank PD applications because it offers:

* strong interpretability
* stable probability outputs
* clear coefficient direction
* regulatory familiarity
* easy validation and calibration

This makes it well suited for a portfolio project aimed at **bank credit risk / risk modelling roles**.

---

## 🔹 3. Data Preparation

### Feature subset

A focused modelling dataset was created using the selected features and target variable.

### Missing value treatment

Numeric variables were imputed using **median imputation**, which is robust and commonly used for skewed financial variables.

### Scaling

A **StandardScaler** was fitted on the training data and then applied consistently to:

* test data
* any future unseen data

This is important because the fitted scaler captures the training-data mean and standard deviation, and must be reused for consistent model predictions.

---

## 🔹 4. Train / Test Split

The dataset was split into:

* training sample
* test sample

The model was fitted on the training data and evaluated on the test data to assess out-of-sample discriminatory power.

---

## 🔹 5. Feature Selection

Feature selection was supported using **RFECV (Recursive Feature Elimination with Cross Validation)** to identify a compact subset of relevant predictors.

This helped reduce noise and improve model simplicity while preserving predictive performance.

---

## 🔹 6. Model Estimation

The final model was estimated using:

* **Logistic Regression**
* `solver='liblinear'`
* `max_iter=1000`

The final PD for each borrower is calculated using:

[
PD = \frac{1}{1 + e^{-(\beta_0 + \beta_1X_1 + \cdots + \beta_nX_n)}}
]

Where:

* (\beta_0) = intercept
* (\beta_i) = feature coefficients
* (X_i) = transformed feature values

---

## 🔹 7. Model Output

The fitted logistic regression model produces:

* predicted probability of default for each borrower
* coefficient estimates for each feature
* model performance metrics such as AUC

PD is obtained using:

* probability of class `1`
* i.e. `predict_proba(... )[:,1]`

---

## 📈 Model Performance

The baseline model achieved an **AUC of approximately 0.7243**.

This indicates:

* reasonable discriminatory power
* a solid baseline for a simple, interpretable PD model
* room for enhancement through additional feature engineering and data aggregation

For a baseline application-only model, this is a credible result.

---

## 📌 Interpretation of Coefficients

The logistic regression coefficients provide directional insight into borrower risk.

For example:

* positive coefficients indicate that an increase in the variable is associated with higher PD
* negative coefficients indicate that an increase in the variable is associated with lower PD

This is one of the key strengths of logistic regression in bank-style modelling, as it allows the modeller to explain risk drivers in economic terms.

Examples of business interpretation include:

* higher leverage or repayment burden may increase default risk
* stronger external risk scores may reduce default risk
* more stable employment may reduce default risk

---

## ⚠️ Methodological Notes

* This is a **baseline PD model** built from application data only
* It does not yet incorporate full behavioural or bureau aggregates
* It is intended for **portfolio and learning purposes**, not regulatory production use
* The model output is a raw statistical PD and has not yet been formally calibrated to long-run default rates

---

## 🧠 Planned Enhancements

The next planned improvements include adding richer feature sets from:

* **bureau data**
* **previous applications**
* **behavioural aggregates**

These are expected to materially improve model performance because default risk is influenced not only by static application characteristics, but also by repayment history, prior credit usage, and behavioural trends.

The longer-term roadmap includes:

* improved aggregation features
* scorecard-style binning / WOE transformation
* calibration of raw PDs
* integration with LGD and EAD

---

## 🏦 Alignment with Bank Practices

This project reflects several core principles of bank PD modelling:

| Component                       | Implemented |
| ------------------------------- | ----------- |
| Interpretable model structure   | ✅           |
| Logistic regression baseline    | ✅           |
| Missing value treatment         | ✅           |
| Train/test validation           | ✅           |
| Probability output              | ✅           |
| Coefficient interpretation      | ✅           |
| Calibration                     | Planned     |
| Behavioural / bureau enrichment | Planned     |

This makes the project more aligned with a traditional bank modelling workflow than a purely black-box machine learning approach.

---

## 📈 Outputs

The model produces:

* borrower-level PD estimates
* model coefficients
* AUC / ROC-based performance evaluation
* a foundation for downstream expected-loss modelling

---

## 🚀 Next Steps

* add bureau and previous application aggregates
* enrich the feature engineering layer
* improve discriminatory power
* calibrate PD outputs
* integrate PD with LGD and EAD
* build a full expected loss framework

---

## 📌 Disclaimer

This project uses publicly available data and simplified modelling choices for educational and portfolio purposes. It is intended to demonstrate PD modelling methodology and model-building workflow, not to serve as a production or regulatory capital model.

---

## ✅ Portfolio Positioning

A suitable way to describe this project is:

> Built an interpretable Probability of Default (PD) model using Home Credit application data and logistic regression, incorporating feature selection, scaling, coefficient interpretation, and out-of-sample validation, as part of a broader bank-style credit risk modelling framework.

---

## 📂 Suggested Repository Structure

```text
pd-model-project/
│
├── data/
│   └── application_train.csv
│
├── notebooks/
│   └── pd_model_development.ipynb
│
├── src/
│   └── pd_model.py
│
├── outputs/
│   ├── auc_curve.png
│   ├── coefficients.csv
│   └── pd_predictions.csv
│
└── README.md
```

---

## 🔥 Suggested File Name

Use either:

* **`README.md`** if this is the main file in the PD project folder
  or
* **`PD_README.md`** if you want to keep separate documentation files for PD and LGD

---

If you want, I can next write a **master repo README** that links your **PD + LGD + future EAD** projects into one full **bank risk modelling portfolio**.
