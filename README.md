# Consumer Credit Risk — PD, LGD, EAD, Expected Loss & Stress Testing

An end-to-end IRB-style credit-risk model for a consumer-credit portfolio: probability of default
(**PD**) scorecard, loss given default (**LGD**), exposure at default (**EAD**) with a revolving
credit-conversion factor, Expected Loss (**EL = PD × LGD × EAD**), IFRS 9 / AASB 9 staging, and two
methods of stress testing.

Built on the public **Home Credit Default Risk** dataset: **307,511 borrowers** scored for the PD
model and a **credit-card book of 104,307 accounts (3.84m monthly rows)** for the revolving EAD work.
All models are interpretable (logistic regression, WOE/IV scorecard, credit-conversion factors) and
every result is reproduced by the pipeline into [outputs/tables/](outputs/tables/).

> **Scope, stated up front.** This is a portfolio demonstration on public competition data, not a
> production bank model. Two data facts shape it and are documented, not smoothed over: the dataset
> has **no recovery cash flows** (so LGD is an external benchmark, not modelled) and a **broken
> revolving-default flag** (the card `SK_DPD` counter accumulates and never resets, so the 90+DPD flag
> is not economic default) — so the **EAD/EL layer is a methodology demonstration**, not a credible
> loss estimate. A recovery-based LGD and a clean default definition are demonstrated in the companion
> **Freddie Mac mortgage** project, whose output-table contract this project mirrors.

## Methods used (summary)

| Component | Method |
|---|---|
| **PD** | Logistic regression on application + bureau/behavioural features → WOE/IV points scorecard → 8 retail pools (G1 riskiest → G8 safest) on a master scale. Count-weighted long-run calibration; margin of conservatism; revise-upward ratchet; 5 bps floor. |
| **LGD** | **External-benchmark assumption** — the dataset has no recovery cash flows, so LGD is not modelled. Base 0.75 / downturn 0.85 within a ~0.65–0.90 published unsecured-consumer band; EL shown across the range. |
| **EAD** | **Revolving credit-conversion factor (CCF)** on the credit-card segment — own-EAD is mandatory for revolving retail. Onset-of-delinquency anchor, 12-month horizon, receivables-inclusive, floored at drawn; ULF basis with an LF/BF switch in the high-utilisation region of instability; long-run count-weighted + downturn + MoC. |
| **EL** | EL = PD × LGD × EAD: account-level (PD per account via `SK_ID_CURR`), by rating grade + portfolio (reconciles to the master scale), and IFRS 9 / AASB 9 Stage 1/2/3. |
| **Stress — method A** | Observed multipliers (mild + severe recession) applied to PD, LGD and EAD. |
| **Stress — method B** | Macro-credit "satellite" model: a regression of the consumer-credit default rate on macro drivers → stressed PD per grade with migration, triangulated. |
| **Validation** | Discrimination (AUC/Gini/KS), calibration plot, binomial + Hosmer-Lemeshow test, confusion matrix, out-of-sample / cold holdout, PSI; the 8-element framework (APG 113 para 140). |

## Results (summary)

- **PD:** held-out AUC 0.71 / Gini 0.41 / KS 0.30; 8 pools rank-order from predicted 10.8% (G1) to
  6.6% (G8); every pool passes the binomial calibration test (the portfolio is conservative vs the
  benign test window). Rank-ordering holds on a never-seen cold holdout (AUC 0.71, PSI ≈ 0).
- **EAD:** onset-anchored EAD ~**$2,005/account**; long-run ULF CCF **−0.88** — a genuine finding that
  card balances pay *down* in the months before default, so the conversion factor is negative and EAD
  falls back to the drawn-balance floor.
- **LGD:** external benchmark **0.75 base / 0.85 downturn** (no recovery data), EL shown across a
  ~0.65–0.90 range.
- **EL:** portfolio 12-month EL ≈ **$14.1m** (763 bps of the card exposure base), rising to ≈ **$26.9m**
  once IFRS 9 lifetime staging applies to Stages 2 and 3.
- **Stress:** a severe recession lifts EL ~**2.4×** under observed multipliers (method A); the satellite
  (method B) puts the severe PD multiplier at **×2.36**, triangulated against the observed industry
  ceiling ×3.09 and the method-A multiplier ×2.50.

---

## 1. Data and inputs

**Coverage.** A **cross-sectional snapshot**, not a time series: one application record per borrower
plus linked behavioural histories in relative time. **No new data was downloaded for this build** —
the existing sample is used as-is and its coverage is documented rather than expanded.

| | |
|---|---|
| Modelling base (PD) | `application_train` — **307,511** borrowers; **~8.07%** default rate (`TARGET`); 80/20 train/test |
| Revolving segment (EAD) | `credit_card_balance` — **3.84m** monthly rows across **104,307** card accounts |
| Time dimension | **none usable** — `DAYS_*` are relative offsets and `MONTHS_BALANCE` is relative to each application, so a calendar out-of-time split is not feasible (see §2 validation) |

**Source.** Home Credit Default Risk (Kaggle, 2018) — public consumer-credit data spanning personal
loans, point-of-sale finance and credit cards. Raw data is **not** redistributed in this repo.
Source: <https://www.kaggle.com/competitions/home-credit-default-risk>

**Key raw variables.**

| Application / bureau (borrower level) | Behavioural files (account-month level) |
|---|---|
| `EXT_SOURCE_2`, `EXT_SOURCE_3` (external bureau scores) | `credit_card_balance`: `AMT_BALANCE`, `AMT_CREDIT_LIMIT_ACTUAL` |
| `DAYS_BIRTH` (age), `DAYS_EMPLOYED` (tenure) | `AMT_TOTAL_RECEIVABLE`, `SK_DPD` (days past due) |
| `AMT_CREDIT`, `AMT_ANNUITY` (affordability) | `MONTHS_BALANCE` (relative month) |
| `bureau` / `bureau_balance`: history depth, active lines | `POS_CASH_balance`, `installments_payments`, `previous_application` |

**Cleaning, transformation, feature engineering.**

- **Sentinel / missing handling** — Home Credit sentinels (e.g. `DAYS_EMPLOYED` = 365243) mapped to NA;
  external scores median-context handled inside the WOE transform; behavioural tables aggregated to
  borrower level (notebooks 00–02).
- **Target** — the Home Credit `TARGET` flag, treated as **broad-equivalence** with the APS 220
  reference default (unlikely-to-pay / 90+DPD), one-year horizon documented (APS 113 Att D para 5).
- **WOE/IV transform** — candidate features screened by Information Value, binned and transformed to
  weight of evidence, then refit as an interpretable scorecard → [01_iv_summary.csv](outputs/tables/scorecard_outputs/01_iv_summary.csv) · [02_woe_table.csv](outputs/tables/scorecard_outputs/02_woe_table.csv).
- **EAD base table** — for the card segment, the **onset-of-delinquency** month is reconstructed per
  account (the broken `SK_DPD` flag is kept only as a diagnostic), with the reference exposure taken
  12 months earlier (notebook 08).

---

## 2. PD model

Estimates the 12-month probability that a borrower defaults.

**Method.**

- **Model** — logistic regression built in stages: a baseline on application data, then enrichment
  from bureau and prior-behaviour tables aggregated to borrower level (notebooks 00–02).
- **Scorecard** — the logistic model is converted to a **WOE/IV points scorecard** (base score 600,
  base odds 0.08, PDO 20; 12 features retained) and borrowers are sorted into **8 retail pools, G1
  (riskiest) → G8 (safest)** — the master scale ([score_to_grade_mapping.csv](outputs/tables/scorecard_outputs/score_to_grade_mapping.csv)).
- **Calibration** — each pool is calibrated to its **count-weighted long-run** one-year default rate,
  then adjusted by a **+15% margin of conservatism**, a **revise-upward ratchet** (lifts any pool whose
  realised rate exceeds the prediction; APS 113 Validation para 6) and the **5 bps regulatory floor**.
  The final `pd_final` is the capital PD that feeds EL, so EL reconciles to the master scale.

**Coefficients** (logistic betas on the WOE-transformed features; `exp(coef)` = odds multiplier)
→ [03_scorecard_coefficients.csv](outputs/tables/scorecard_outputs/03_scorecard_coefficients.csv):

| Feature | Coefficient | Odds × | IV | Reading |
|---|---:|---:|---:|---|
| EXT_SOURCE_3 | −1.15 | 0.32 | 0.31 | external bureau score — strongest protective driver |
| BUREAU_IS_ACTIVE_SUM | −0.95 | 0.39 | 0.05 | more active bureau lines (managed) → lower default |
| BUREAU_DAYS_CREDIT_MEAN | −0.91 | 0.40 | 0.12 | longer credit history → lower default |
| EXT_SOURCE_2 | −0.80 | 0.45 | 0.28 | second external score — second strongest |
| PREV_CNT_PAYMENT_MAX | −0.64 | 0.53 | 0.02 | longer prior-loan terms successfully served |
| ANNUITY_TO_CREDIT | −0.58 | 0.56 | 0.04 | affordability of the instalment |
| AGE / EMPLOYMENT_YEARS | −0.52 / −0.51 | 0.60 | 0.08 / 0.11 | older / longer-employed → lower default |

All 12 retained features are economically consistent (every one protective — higher value lowers
default odds), led by the two external bureau scores, which also carry the highest Information Value.

**Rating pools — master scale** (predicted vs observed default rate per pool)
→ [18_grade_pd_moc_floor.csv](outputs/tables/scorecard_outputs/18_grade_pd_moc_floor.csv):

| Pool | Borrowers | Long-run PD | Observed | Final capital PD |
|---|---:|---:|---:|---:|
| G1 (riskiest) | 11,532 | 10.8% | 11.1% | 12.4% |
| G2 | 11,532 | 10.2% | 9.8% | 11.8% |
| G3 | 11,531 | 9.9% | 8.9% | 11.4% |
| G4 | 11,532 | 8.2% | 7.4% | 9.4% |
| G5 | 11,532 | 9.3% | 8.1% | 10.7% |
| G6 | 11,532 | 7.8% | 6.8% | 9.0% |
| G7 | 11,531 | 8.0% | 6.9% | 9.2% |
| G8 (safest) | 11,532 | 6.6% | 5.6% | 7.6% |

The pools rank risk broadly monotonically (G1 → G8), though separation is modest — discrimination is
AUC ≈ 0.71, so the PD band is compressed (7.6%–12.4%). The final capital PD sits above the observed
rate in every pool (the MoC overlay), so the book is conservative against this benign window.
→ [13_calibration_test.csv](outputs/tables/scorecard_outputs/13_calibration_test.csv) · [14_pd_moc_overlay.csv](outputs/tables/scorecard_outputs/14_pd_moc_overlay.csv)

**Validation.**

| Test | Result | Source |
|---|---|---|
| Discrimination (held-out) | AUC 0.706 · Gini 0.41 · KS 0.30 | [08_validation_summary.csv](outputs/tables/scorecard_outputs/08_validation_summary.csv) |
| Calibration | predicted vs observed on the diagonal | [chart](outputs/charts/pd_calibration.png) |
| Calibration test | per-pool binomial all green; portfolio Hosmer-Lemeshow conservative (8.85% predicted vs 8.07% observed) | [13_calibration_test.csv](outputs/tables/scorecard_outputs/13_calibration_test.csv) |
| Confusion matrix (cut-off = 8.85% prevalence) | recall 0.68 (5,058/7,448 defaults caught), precision 0.14 — low precision expected at an ~8% base rate | [16_confusion_matrix.csv](outputs/tables/scorecard_outputs/16_confusion_matrix.csv) |
| Out-of-sample + cold holdout | re-fit on the training slice, score a held-out slice: AUC ~0.71, PSI ≈ 0 — rank-ordering generalises | [17_oot_validation.csv](outputs/tables/scorecard_outputs/17_oot_validation.csv) |
| Calendar out-of-time | **not feasible** — cross-sectional snapshot with no origination date (a true time-based OOT + forward holdout is in the Freddie Mac project) | — |

---

## 3. LGD model

Estimates, given default, the fraction of EAD that is lost.

**Loss definition.** Economic loss ÷ EAD — discounted recovery cash flows net of direct and indirect
collection costs (CRE36.76 / APS 113 Att D LGD para 1). **The dataset has no recovery cash flows**, so
LGD cannot be modelled from settled losses. It is therefore set as an **external-benchmark
assumption**, explicitly labelled as such (not fabricated):

| View | LGD | Basis |
|---|---:|---|
| benchmark low | 0.65 | low end of the published unsecured-consumer / credit-card range |
| **base** | **0.75** | central benchmark for unsecured revolving |
| **downturn** | **0.85** | cyclical uplift used for capital / EL (APS 113 Att D LGD paras 4–5) |
| benchmark high | 0.90 | high end of the range |

Expected Loss is shown **across the 0.65–0.90 range** as a sensitivity rather than a single point.
The economic-loss / discounting treatment and the (collateral-specific) regulatory floors are
documented in [consumer_credit_alignment.md](consumer_credit_alignment.md) §3; none can be computed
without recovery data. A real recovery-based, discounted, downturn LGD is built in the Freddie Mac
project.

---

## 4. EAD model

Estimates the amount owed at the moment of default — the **key structural difference** from a term
mortgage.

**Method.**

- **Revolving → credit-conversion factor.** A credit card is **revolving**, so EAD must convert the
  **undrawn limit** into expected additional drawings: `EAD = drawn balance + CCF × undrawn limit`.
  Own-EAD estimates are **mandatory for revolving retail** (unlike a term loan, which has no CCF).
- **Anchor & horizon** — the broken 90+DPD flag is a diagnostic only; the **onset-of-delinquency**
  month is the primary anchor, with the reference exposure taken **12 months before** it (Att D EAD
  para 7). Exposure = drawn balance **plus receivables / limit excesses**, not capped at balance/limit
  (Att D EAD para 10), **floored at the current drawn balance** (CRE36.89); post-default drawings go to
  LGD, not EAD.
- **Region of instability** — observed CCFs are **not** clipped to [0, 1] and over-limit accounts are
  **not** dropped (both named ineffective mitigations, CRE36.95(2)). In the high-utilisation region the
  basis switches from the undrawn-limit factor (ULF) to a **limit / balance factor (LF/BF)** so a
  near-zero undrawn amount is not in the denominator (CRE36.95(1)).
- **Long-run / downturn / MoC** — long-run **count-weighted** CCF, a **downturn** CCF, a **MoC** add-on
  (positive default/EAD correlation), and the allowed homogeneity exclusion of accounts already
  problematic at the reference date (APG 113 para 129(b)).

**Results** → [ead_summary.csv](outputs/tables/ead_summary.csv):

| Metric | Value |
|---|---:|
| Defaulted accounts → with reference → after homogeneity exclusion | 1,806 → 1,539 → **1,376** |
| EAD (onset anchor, primary) | **~$2,005 / account** |
| EAD (90+DPD anchor, secondary) | ~$2,964 / account |
| Long-run ULF CCF (count-weighted) | **−0.88** |
| Downturn CCF / MoC add-on | −0.28 / +0.09 |

The **negative CCF is a genuine data finding**: on this book card balances typically *pay down* in the
months before default, so the undrawn-limit conversion is negative and EAD falls back to the
drawn-balance floor (100% of accounts). It is reported, not smoothed over.

---

## 5. Expected Loss

`EL = PD × LGD × EAD`. The PD used is the **calibrated capital pool PD** (long-run + MoC + ratchet +
floor), so EL reconciles to the master scale. Delivered three ways: account-level, by rating grade,
and by IFRS 9 / AASB 9 stage.

**Account-level** (notebook 08) — each card account linked to **its own borrower PD** via `SK_ID_CURR`:
mean EL **$310 (base) / $351 (downturn)** per account. The PD link covers ~25% of the card book (the
scorecard test split), so the example is account-level but illustrative.

**By rating grade and portfolio total** → [19_el_summary_by_grade.csv](outputs/tables/scorecard_outputs/19_el_summary_by_grade.csv):

| Pool | Borrowers | Total EAD | Avg PD | Avg LGD | 12-mo Expected Loss | EL rate (bps) |
|---|---:|---:|---:|---:|---:|---:|
| G1 | 11,532 | $23.1m | 12.4% | 0.75 | $2.15m | 930 |
| G2 | 11,532 | $23.1m | 11.8% | 0.75 | $2.04m | 883 |
| G3 | 11,531 | $23.1m | 11.4% | 0.75 | $1.97m | 852 |
| G4 | 11,532 | $23.1m | 9.4% | 0.75 | $1.64m | 708 |
| G5 | 11,532 | $23.1m | 10.7% | 0.75 | $1.85m | 801 |
| G6 | 11,532 | $23.1m | 9.0% | 0.75 | $1.56m | 675 |
| G7 | 11,531 | $23.1m | 9.2% | 0.75 | $1.59m | 688 |
| G8 | 11,532 | $23.1m | 7.6% | 0.75 | $1.32m | 569 |
| **PORTFOLIO** | **92,254** | **$185.0m** | **10.2%** | **0.75** | **$14.12m** | **763** |

A single portfolio-average EAD ($2,005) is applied to every pool (no per-grade card exposure exists),
so the grade ranking is PD-driven, which is the point. The EL rate runs 569 → 930 bps — high, as
expected for an unsecured book at 75% LGD. The portfolio total **reconciles exactly to the stress-test
baseline** (§6).

**By IFRS 9 stage** → [20_ifrs9_staging.csv](outputs/tables/scorecard_outputs/20_ifrs9_staging.csv):

| Stage | Borrowers | Avg PD | Avg LGD | Total EAD | 12-month EL | Reported ECL (staged) |
|---|---:|---:|---:|---:|---:|---:|
| 1 — performing | 77,475 | 7.2% | 0.75 | $155.3m | $8.35m | $8.35m (12-month) |
| 2 — significant ↑ in risk (SICR) | 7,331 | 22.1% | 0.75 | $14.7m | $2.44m | $7.31m (lifetime) |
| 3 — credit-impaired | 7,448 | 13.3% | 0.75 | $14.9m | $1.49m | $11.20m (best-estimate) |

Stages are assigned by documented proxies (a snapshot has no origination PD or DPD field): Stage 3 =
the `TARGET` default proxy; Stage 2 (SICR) = non-defaulted accounts with 12-month PD ≥ 2× the portfolio
PD; Stage 1 = performing. IFRS 9 LGD is the **unbiased best estimate** (no downturn / MoC); Stage 3 is
on a **best-estimate-of-EL** basis (default has occurred), per CRE36.86. Portfolio 12-month EL ≈ $14.1m
rises to a reported ECL ≈ **$26.9m** once lifetime staging applies.

---

## 6. Stress testing

A stress test asks: **if the economy deteriorates, how much does Expected Loss rise?** Each method
turns a recession scenario into a **stressed PD** (and, in method A, stressed LGD/EAD), then recomputes
**EL = PD × LGD × EAD**. Both stack the shocks with no diversification offset (APG 113 para 92) and
cover at least a mild recession (Basel CRE36.51). Two methods are implemented.

### 6.1 Method A — observed multipliers

The simple approach (notebook 09): multiply the baseline PD, LGD and EAD by judgemental recession
multipliers and recompute portfolio EL → [15_stress_test.csv](outputs/tables/scorecard_outputs/15_stress_test.csv):

| Scenario | PD × | LGD × | EAD × | Portfolio EL | Uplift |
|---|---:|---:|---:|---:|---:|
| baseline | 1.0 | 1.0 | 1.0 | $14.1m | — |
| mild recession | 1.5 | 1.1 | 1.05 | $24.5m | +0.73× |
| severe recession | 2.5 | 1.25 | 1.1 | $48.5m | +2.44× |

### 6.2 Method B — macro-credit satellite model (stressed PD)

The statistical approach ([stress_test/](stress_test/)): a **regression that takes macro variables as
inputs and predicts the default rate**, so a scenario produces the stressed PD through fitted
coefficients, not an assumed factor.

```text
logit(default rate) = α + β₁·unemployment + β₂·wage growth + β₃·inflation + β₄·GDP growth
```

**Where the macro data comes from — and an honest caveat.** The macro drivers are an external overlay
of public US consumer series, in [stress_test/macro/macro_consumer.csv](stress_test/macro/macro_consumer.csv)
(unemployment, wage growth, inflation, GDP, plus the industry credit-card charge-off rate as the
outcome). Because the Home Credit snapshot has **no calendar timeline**, a point-in-time default-rate
panel cannot be built from the loan data; the satellite is therefore fitted on **real public US
consumer-credit history** (industry charge-off vs FRED-style macro) and its macro *sensitivity* is
applied to the portfolio's own grade PDs — level anchored to the portfolio, slope from the industry
satellite. A fully loan-data-estimated satellite on dated vintages is in the Freddie Mac project.

**Coefficients** (standardised; all four economically sign-consistent, R² 0.45)
→ [satellite_coefficients.csv](stress_test/outputs/tables/satellite_coefficients.csv):

| Driver | Coefficient | Expected sign | Reading |
|---|---:|:---:|---|
| unemployment | +0.109 | + | higher unemployment → higher default |
| inflation | +0.044 | + | higher inflation → higher default |
| wage_growth | −0.123 | − | stronger wage growth → lower default |
| gdp_growth | −0.175 | − | stronger GDP growth → lower default |

**Stressed PD per pool + migration.** A scenario's macro effect is a single **log-odds shift** (mild
+0.59, severe +1.02) added to each pool's base PD — `logit(stressed PD) = logit(base PD) + shift` — and
mapped back to the master scale → [scenario_stressed_pd_by_grade.csv](stress_test/outputs/tables/scenario_stressed_pd_by_grade.csv):

| Pool | Base PD | Mild → PD (×) | Severe → PD (×) |
|---|---:|---:|---:|
| G1 | 12.4% | 20.4% (×1.65) | 28.2% (×2.28) |
| G4 | 9.4% | 15.9% (×1.68) | 22.5% (×2.38) |
| G8 | 7.6% | 13.0% (×1.71) | 18.6% (×2.45) |

Because the pools are weakly separated, even a mild shock migrates the **whole book to/beyond the worst
current pool (G1)** — reported honestly via `migrated_beyond_worst`. A more discriminating model would
show staged migration.

**Triangulation** (model-risk control) → [triangulation.csv](stress_test/outputs/tables/triangulation.csv):

| Method | Severe PD × | Reading |
|---|---:|---|
| satellite severe (this module) | **2.36** | logit-linear macro model, inputs clipped to support |
| observed industry peak (data) | 3.09 | FRED charge-off peak (2010) ÷ calm-years avg (2014–19) — the realised ceiling |
| method-A multiplier | 2.50 | judgemental observed multiplier (§6.1) |

The three sit in a tight **2.4–3.1×** band: the satellite is **below** the observed ceiling and beside
the judgemental multiplier — a credible, mutually-supporting result. See
[stress_test/README.md](stress_test/README.md) for the full method and compliance mapping.

---

## Charts

Regenerated from committed result tables by [tools/make_figures.py](tools/make_figures.py)
(aggregated results only, no raw borrower records).

| Chart | Content |
|---|---|
| [bad_rate_by_score_decile.png](outputs/charts/bad_rate_by_score_decile.png) | Observed default rate by score decile (rank-ordering) |
| [pd_calibration.png](outputs/charts/pd_calibration.png) | Predicted PD vs observed default rate |
| [top_predictors_by_iv.png](outputs/charts/top_predictors_by_iv.png) | Strongest predictors by Information Value |
| [score_band_policy.png](outputs/charts/score_band_policy.png) | Default rate by score band A–E with approve / review / decline cut-offs |
| [el_by_grade.png](outputs/charts/el_by_grade.png) | Expected Loss ($m) and EL-rate (bps) by rating pool |
| [stress_test/.../stressed_pd_by_grade.png](stress_test/outputs/charts/stressed_pd_by_grade.png) | Baseline vs mild vs severe PD by pool (satellite model) |

---

## Notebooks

| # | Notebook | Output |
|---|---|---|
| 00 | [Baseline logistic — application data](notebooks/HomeCredit_00_Logistic_with_Applicationdata.ipynb) | baseline metrics + coefficients |
| 01 | [External data preparation](notebooks/HomeCredit_01_External_Data_Preparation.ipynb) — aggregate bureau / prior tables to borrower level | borrower-level features |
| 02 | [Logistic with external features](notebooks/HomeCredit_02_Logistic_With_External_Features.ipynb) | enriched model |
| 03 | [PD scorecard build](notebooks/HomeCredit_03_PD_Scorecard_Build.ipynb) — WOE/IV, points, pools, master scale | [03_scorecard_coefficients.csv](outputs/tables/scorecard_outputs/03_scorecard_coefficients.csv) |
| 04 | [Validation & business use](notebooks/HomeCredit_04_PD_Scorecard_Validation_and_Business_Use.ipynb) — deciles, score bands, policy | [08–12_*.csv](outputs/tables/scorecard_outputs/) |
| 05 | [Monitoring & stability](notebooks/HomeCredit_05_PD_Scorecard_Advanced_Monitoring_and_Stability.ipynb) — PSI | [psi_by_score_band.csv](outputs/tables/scorecard_outputs/psi_by_score_band.csv) |
| 06 | [Model risk & governance](notebooks/HomeCredit_06_PD_Scorecard_Model_Risk_and_Portfolio_Governance.ipynb) — rating philosophy | (documented) |
| 07 | [Documentation, backtesting, policy](notebooks/HomeCredit_07_PD_Scorecard_Model_Documentation_Backtesting_Policy.ipynb) | (documented) |
| 08 | [EAD / CCF / LGD / EL](notebooks/08_EAD_CCF.ipynb) — revolving CCF, benchmarked LGD, account-level EL | [ead_summary.csv](outputs/tables/ead_summary.csv) |
| 09 | [Stress testing](notebooks/09_Stress_Testing.ipynb) — observed multipliers (method A) | [15_stress_test.csv](outputs/tables/scorecard_outputs/15_stress_test.csv) |
| — | [stress_test/](stress_test/) — statistical macro-credit satellite model (method B) | [stress_test/outputs/tables/](stress_test/outputs/tables/) |

The committed aggregate tables (`13`–`20`) are regenerated from the scored outputs by the `tools/`
scripts (no raw-data download) — see **How to run**.

---

## Regulatory alignment (APS 113 / APG 113 / Basel / WP14 / IFRS 9)

The per-component sections state where each rule is applied; a full mapping is in
[consumer_credit_alignment.md](consumer_credit_alignment.md). In summary: a one-year PD calibrated to a
count-weighted long-run average with a margin of conservatism, a revise-upward ratchet and the 5 bps
floor; a documented external-benchmark LGD (no recovery data); **own-EAD for revolving retail with the
region-of-instability handling** that a term product does not need; EL on the same PD as capital, staged
under IFRS 9; and a stress test (observed multipliers plus a satellite model) covering at least a mild
recession with the no-diversification assumption. Independent validation is structured against the
**8-element framework (APG 113 para 140)**. WOE/IV and score-scaling theory is in
[Scorecard_README.md](Scorecard_README.md).

## Limitations

- Demonstration model on public Home Credit data, not a certified regulatory-capital calculation;
  cut-offs and overlays are illustrative.
- **No LGD model** — LGD is an external-benchmark assumption (no recovery data in the dataset).
- **EAD/EL is a methodology demonstration**, not a credible loss estimate: the card `SK_DPD` counter
  accumulates and never resets, so the 90+DPD flag is **not** economic default (it fires late on a small
  residual; the pre-default peak balance sits ~10 months earlier; some accounts revive after their
  flagged default). Exposure and EL figures show the mechanics only.
- **No calendar timeline** — a true time-based out-of-time split is not feasible, and the satellite is
  fitted on public industry history rather than the loan data (both documented).
- Properly-anchored EAD, a recovery-based downturn LGD and a loan-data satellite are demonstrated in the
  companion Freddie Mac mortgage project.

## How to run

```bash
pip install -r requirements.txt
# 1) run the notebooks in numeric order:
#    00–07 PD scorecard · 08 EAD/CCF/LGD/EL · 09 stress (method A)
# 2) regenerate every committed aggregate table from the scored outputs (no raw-data download):
python tools/make_pd_calibration.py      # 13 calibration test + 14 MoC overlay
python tools/make_pd_validation.py       # 16 confusion matrix + 17 OOT / cold holdout
python tools/make_grade_pd_moc_floor.py  # 18 long-run PD -> MoC -> ratchet -> floor
python tools/make_el_summary.py          # 19 EL-by-grade + 20 IFRS 9 staging
python stress_test/build_stress.py       # statistical satellite stress test (method B)
python tools/make_figures.py             # regenerate all charts from committed tables
```

## Repository layout

```
.
├── data/                 # Home Credit source data (gitignored, not redistributed)
├── notebooks/            # 00–07 PD scorecard · 08 EAD/CCF/EL · 09 stress (method A)
├── outputs/tables/       # committed scorecard + EAD/EL/IFRS9/stress CSVs · outputs/charts/ — PNGs
├── src/                  # woe, transform, calibration, validation, psi, monitoring, backtesting
├── tools/                # make_figures · make_pd_calibration · make_pd_validation · make_grade_pd_moc_floor · make_el_summary
├── stress_test/          # statistical macro-credit satellite stress test (method B, self-contained)
├── consumer_credit_alignment.md   # methodology + full regulatory alignment (technical companion)
└── Scorecard_README.md   # WOE/IV + score-scaling theory
```

## License

MIT License.
