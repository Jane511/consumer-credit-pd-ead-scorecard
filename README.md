# Consumer Credit — PD Scorecard + EAD + Expected Loss + Stress Testing

An interpretable consumer-credit risk model on the public **Home Credit Default Risk** dataset:
a probability-of-default (**PD**) scorecard, a revolving exposure-at-default (**EAD / CCF**) layer,
an Expected Loss (**EL = PD × LGD × EAD**) view, and a recession stress test. Methods are
transparent (logistic regression, WOE/IV scorecard, credit-conversion factors) and every result is
reproduced into [outputs/tables/](outputs/tables/). Portfolio demonstration, not a production model.

Full methodology and the APS 113 / APG 113 / Basel / WP14 mapping is in
[consumer_credit_alignment.md](consumer_credit_alignment.md); WOE/IV and score-scaling theory is in
[Scorecard_README.md](Scorecard_README.md).

## Methods used

| Component | Method |
|---|---|
| **PD** | Logistic regression on application + bureau/behavioural features → **WOE/IV points scorecard** → 8 retail pools (G1–G8); long-run calibration, +15% margin of conservatism, 5 bps floor; binomial + Hosmer-Lemeshow calibration test. |
| **EAD** | **Revolving credit-conversion factor (CCF)** on the credit-card segment: ULF basis with an LF/BF switch in the high-utilisation region of instability; onset-of-delinquency anchor; receivables-inclusive, floored at drawn; long-run count-weighted + downturn + MoC. |
| **LGD** | External-benchmark assumption (no recovery data): base 0.75 / downturn 0.85, within a ~0.65–0.90 unsecured band. |
| **EL** | EL = PD × LGD × EAD: account-level (PD per account via `SK_ID_CURR`), **EL-by-grade + portfolio** (reconciles to the master scale), and **IFRS 9 / AASB 9 three-stage ECL**. |
| **Stress** | **A —** scenario multipliers on PD/LGD/EAD (mild + severe); **B —** statistical **macro-credit satellite** → stressed PD per grade + migration, triangulated. |
| **Validation** | AUC / Gini / KS, decile + score-band rank-ordering, calibration test, **confusion matrix**, **out-of-sample / cold holdout**, PSI stability; **8-element framework (APG 113 para 140)**. |

## Results (summary)

| Metric | Result |
|---|---|
| Scorecard discrimination | AUC **0.706** (train and test) · Gini **0.41** · KS **0.30** |
| Rating pools | 8 pools, predicted PD **10.8% (G1) → 6.6% (G8)** (observed 11.1% → 5.6%) |
| Calibration | binomial under-estimation test green per pool; overall Hosmer-Lemeshow conservative (8.85% predicted vs 8.07% observed) |
| EAD (card segment) | onset-anchored ~**$2,005/account**; long-run ULF CCF **−0.88** (cards pay down before default) |
| Expected Loss | ~**$310 (base) / $351 (downturn)** per account; portfolio baseline EL **$14.1m** (reconciles to the EL-by-grade total) |
| IFRS 9 ECL | 3-stage: S1 77.5k / S2 7.3k / S3 7.4k accounts; reported ECL ≈ **$26.9m** |
| Stress A (multipliers) | severe recession lifts portfolio EL to **$48.5m (+2.4×)**; mild to $24.5m (+0.7×) |
| Stress B (satellite) | severe PD **×2.36** — triangulated vs observed industry peak ×3.09 and the nb09 multiplier ×2.50 |

---

## 1. PD model

**Target.** The Home Credit `TARGET` flag (a competition proxy); the APS 220 reference is
unlikely-to-pay or 90+DPD, treated here as broad-equivalence with the horizon documented.

**Method.**

- **Logistic regression** built in stages — baseline on application data (notebooks 00–02), then
  enrichment from bureau and prior-behaviour tables aggregated to borrower level.
- **WOE/IV scorecard** — variables screened by Information Value, transformed to weight of evidence,
  refit as an interpretable logistic scorecard, scaled to points (base 600, base odds 0.08, PDO 20).
  12 features retained.
- **Master scale** — scores banded into 8 pools **G1 (riskiest) → G8 (safest)**
  ([score_to_grade_mapping.csv](outputs/tables/scorecard_outputs/score_to_grade_mapping.csv)).
- **Calibration → MoC → ratchet → floor** — long-run grade PDs, a **+15% additive margin of
  conservatism**, a **revise-upward ratchet**, and the **5 bps PD floor**, combined in one table
  ([18_grade_pd_moc_floor.csv](outputs/tables/scorecard_outputs/18_grade_pd_moc_floor.csv)); its
  `pd_final` is the capital PD that feeds EL, so EL and the master scale reconcile.

**Results.** AUC 0.706 / Gini 0.41 / KS 0.30; pools rank-order from predicted 10.8% (G1) to 6.6% (G8).
The calibration test ([13_calibration_test.csv](outputs/tables/scorecard_outputs/13_calibration_test.csv))
passes the binomial test in every pool and is conservative on the overall Hosmer-Lemeshow; the MoC
overlay ([14_pd_moc_overlay.csv](outputs/tables/scorecard_outputs/14_pd_moc_overlay.csv)) shows
pre/post-MoC pool PDs (e.g. G1 10.8% → 12.4%). A **confusion matrix** at the prevalence cut-off
([16_confusion_matrix.csv](outputs/tables/scorecard_outputs/16_confusion_matrix.csv); recall 0.68 /
precision 0.14) and **out-of-sample + cold-holdout** validation
([17_oot_validation.csv](outputs/tables/scorecard_outputs/17_oot_validation.csv); AUC ~0.71, PSI ≈ 0)
are exported — a true *calendar* OOT is not feasible on this cross-sectional snapshot (see
Limitations). Validation, deciles, score bands and PSI are in notebooks 04–07.

## 2. EAD model (revolving — CCF)

A credit card is **revolving**, so EAD converts the undrawn limit via a **credit-conversion factor**
(unlike a term loan, which has no CCF).

**Method.** Onset-of-delinquency as the primary default anchor (the 90+DPD flag is kept only as a
diagnostic — see Limitations); EAD = drawn balance + receivables/excesses, floored at the drawn
balance (Basel CRE36.89); observed CCFs **not** clipped to [0,1] and over-limit accounts **not**
dropped (both ineffective under CRE36.95(2)); a **ULF→LF/BF basis switch in the high-utilisation
region of instability** (CRE36.95(1)); long-run count-weighted CCF, downturn CCF, MoC, and the
allowed homogeneity exclusion (APG 113 para 129(b)).

**Results** ([ead_summary.csv](outputs/tables/ead_summary.csv)). 1,806 → 1,376 accounts after the
homogeneity exclusion; EAD ~$2,005/account (onset) vs $2,964 (90+DPD); **long-run ULF CCF −0.88** —
a real finding that card balances pay down before default, so the conversion factor is negative.

## 3. LGD

No recovery cash flows exist in the dataset, so LGD is an **external-benchmark assumption**: base
**0.75** / downturn **0.85** within a ~0.65–0.90 published unsecured range, with EL shown across the
range as a sensitivity. A recovery-based, modelled downturn LGD is built in the companion Freddie Mac
mortgage project.

## 4. Expected Loss

`EL = PD × LGD × EAD`, delivered three ways:

- **Account-level** on the card segment — each account linked to its own borrower PD via
  `SK_ID_CURR`. Mean EL ~$310 (base) / $351 (downturn) per account; the PD link covers ~25% of the
  card book, so the example is account-level but illustrative.
- **By rating grade + portfolio total**
  ([19_el_summary_by_grade.csv](outputs/tables/scorecard_outputs/19_el_summary_by_grade.csv)) — loans,
  EAD, avg PD/LGD, total EL and EL-rate (bps) per grade, using the `pd_final` capital PD; the
  portfolio total (**$14.1m**, ~763 bps) **reconciles exactly** to the stress-test baseline.
- **IFRS 9 / AASB 9 three-stage ECL**
  ([20_ifrs9_staging.csv](outputs/tables/scorecard_outputs/20_ifrs9_staging.csv)) — Stage 1 (12-month)
  / Stage 2 (lifetime, SICR) / Stage 3 (best-estimate, impaired), reported ECL ≈ $26.9m. IFRS 9 LGD is
  the unbiased best estimate (no downturn / MoC). Best-estimate-of-EL for defaulted accounts and an
  EL-vs-provisions framing are documented in notebook 08.

## 5. Stress testing

**Approach A — observed multipliers** (notebook 09), recomputing portfolio EL with shocks stacked and
**no diversification offset** (APG 113 para 92)
→ [15_stress_test.csv](outputs/tables/scorecard_outputs/15_stress_test.csv):

| Scenario | PD × | LGD × | EAD × | Portfolio EL | Uplift |
|---|---:|---:|---:|---:|---:|
| baseline | 1.0 | 1.0 | 1.0 | $14.1m | — |
| mild recession | 1.5 | 1.1 | 1.05 | $24.5m | +0.73× |
| severe recession | 2.5 | 1.25 | 1.1 | $48.5m | +2.44× |

**Approach B — statistical macro-credit satellite** ([stress_test/](stress_test/), see its
[README](stress_test/README.md)). A logit-linear regression of the consumer-credit default rate on
macro drivers (unemployment, wage growth, inflation, GDP) translates scenarios into a **stressed PD
per grade** with **grade migration**, then **triangulates** the tail: satellite severe **×2.36** sits
below the observed industry ceiling **×3.09** and beside the nb09 multiplier **×2.50**. All four macro
coefficients are economically sign-consistent. Because the Home Credit snapshot has no calendar
timeline, the satellite is fitted on real public industry history and its sensitivity applied to the
portfolio's grades (documented). Management-action / contingency and reverse-stress notes are included
(APS 220 para 74).

---

## Charts

Regenerated from committed scorecard outputs by [tools/make_figures.py](tools/make_figures.py)
(aggregated results only, no raw borrower records).

| Chart | Content |
|---|---|
| [bad_rate_by_score_decile.png](outputs/charts/bad_rate_by_score_decile.png) | Observed default rate by score decile |
| [pd_calibration.png](outputs/charts/pd_calibration.png) | Predicted PD vs observed default rate |
| [top_predictors_by_iv.png](outputs/charts/top_predictors_by_iv.png) | Strongest predictors by Information Value |
| [score_band_policy.png](outputs/charts/score_band_policy.png) | Default rate by score band A–E with approve / review / decline cut-offs |
| [el_by_grade.png](outputs/charts/el_by_grade.png) | Expected Loss ($m) and EL-rate (bps) by rating grade |
| [stressed_pd_by_grade.png](stress_test/outputs/charts/stressed_pd_by_grade.png) | Satellite stress: baseline vs mild vs severe PD by grade |

## Data source & coverage

**Home Credit Default Risk** (Kaggle, 2018) — public consumer-credit data (personal loans,
point-of-sale finance, credit cards). **No new data was downloaded for this build** — the existing
sample is used as-is; the project documents the coverage it has rather than expanding it.

| | |
|---|---|
| Modelling base (PD) | `application_train` — **307,511** borrowers; **~8.07%** default rate (`TARGET`); 80/20 train/test |
| Revolving segment (EAD) | `credit_card_balance` — **3.84m** monthly rows across **104,307** card accounts |
| Key raw inputs | external scores (`EXT_SOURCE_2/3`), bureau history (`bureau`, `bureau_balance`), prior apps (`previous_application`), POS/installments (`POS_CASH_balance`, `installments_payments`) |
| Time dimension | **cross-sectional snapshot** — `DAYS_*` are relative offsets, not calendar dates, so a true calendar OOT split is not feasible (documented in Limitations) |

Files: `application_train`, `bureau`, `bureau_balance`, `previous_application`, `POS_CASH_balance`,
`credit_card_balance`, `installments_payments`. Used for demonstration only.
Source: <https://www.kaggle.com/competitions/home-credit-default-risk>

## Notebooks

| Notebook | Content |
|---|---|
| `HomeCredit_00_Logistic_with_Applicationdata` | Baseline logistic regression on application data |
| `HomeCredit_01_External_Data_Preparation` | Aggregate linked external tables to borrower level |
| `HomeCredit_02_Logistic_With_External_Features` | Logistic model with external features |
| `HomeCredit_03_PD_Scorecard_Build` | WOE/IV scorecard build, points, PD |
| `HomeCredit_04_PD_Scorecard_Validation_and_Business_Use` | Validation, deciles, score bands, policy |
| `HomeCredit_05_PD_Scorecard_Advanced_Monitoring_and_Stability` | PSI monitoring and stability |
| `HomeCredit_06_PD_Scorecard_Model_Risk_and_Portfolio_Governance` | Model risk, governance, rating philosophy |
| `HomeCredit_07_PD_Scorecard_Model_Documentation_Backtesting_Policy` | Documentation, backtesting, policy |
| `08_EAD_CCF` | EAD, revolving CCF, benchmarked LGD range, account-level EL |
| `09_Stress_Testing` | Mild + severe recession stress test on portfolio EL |

## How to run

```bash
pip install -r requirements.txt
# run the notebooks in numeric order: 00–07 (PD scorecard), 08 (EAD/CCF/LGD/EL), 09 (stress)
# regenerate every committed aggregate table from the scored outputs (no raw data download):
python tools/make_pd_calibration.py      # 13 calibration test + 14 MoC overlay
python tools/make_pd_validation.py       # 16 confusion matrix + 17 OOT / cold holdout
python tools/make_grade_pd_moc_floor.py  # 18 long-run PD -> MoC -> ratchet -> floor
python tools/make_el_summary.py          # 19 EL-by-grade + 20 IFRS 9 staging
python stress_test/build_stress.py       # macro-credit satellite stress (Approach B)
python tools/make_figures.py             # regenerate all charts from committed tables
```

## Repository layout

```
.
├── data/                 # Home Credit source data (not redistributed)
├── notebooks/            # 00–07 PD scorecard · 08 EAD/CCF/EL · 09 stress
├── outputs/tables/       # committed scorecard + EAD/EL/IFRS9/stress results  ·  outputs/charts/ — PNGs
├── src/                  # woe, transform, calibration, validation, psi, monitoring, backtesting
├── tools/                # make_figures · make_pd_calibration · make_pd_validation · make_grade_pd_moc_floor · make_el_summary
├── stress_test/          # macro-credit satellite model (Approach B): macro CSV, build_stress.py, outputs
├── consumer_credit_alignment.md   # methodology + regulatory alignment (technical companion)
└── Scorecard_README.md   # WOE/IV + score-scaling theory
```

## Limitations

- Public Home Credit data, not a real lender's portfolio; cut-offs and overlays are illustrative.
- **No LGD model** — LGD is an external-benchmark assumption (no recovery data in the dataset).
- **EAD/EL is a methodology demonstration**, not a credible loss estimate: the credit-card `SK_DPD`
  counter accumulates and never resets, so the 90+DPD flag is **not** economic default (it fires late
  on a small residual; the pre-default peak balance sits ~10 months earlier; some accounts revive
  after their flagged default). Exposure and EL figures show the mechanics only. Properly-anchored
  EAD and a recovery-based LGD are demonstrated in the companion Freddie Mac mortgage project.
- The EL example links ~25% of the card book to a borrower PD — account-level but illustrative.

## License

MIT License.
