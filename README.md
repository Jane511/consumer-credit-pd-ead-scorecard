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
| **EL** | EL = PD × LGD × EAD, account-level on the card segment (PD linked per account via `SK_ID_CURR`). |
| **Stress** | Scenario multipliers on PD / LGD / EAD (mild + severe), stacked with no diversification offset. |
| **Validation** | AUC / Gini / KS, decile + score-band rank-ordering, calibration test, PSI stability, governance / backtesting. |

## Results (summary)

| Metric | Result |
|---|---|
| Scorecard discrimination | AUC **0.706** (train and test) · Gini **0.41** · KS **0.30** |
| Rating pools | 8 pools, predicted PD **10.8% (G1) → 5.6% (G8)** |
| Calibration | binomial under-estimation test green per pool; overall Hosmer-Lemeshow conservative (8.85% predicted vs 8.07% observed) |
| EAD (card segment) | onset-anchored ~**$2,005/account**; long-run ULF CCF **−0.88** (cards pay down before default) |
| Expected Loss | ~**$310 (base) / $351 (downturn)** per account; portfolio baseline EL **$14.1m** |
| Stress | severe recession lifts portfolio EL to **$48.5m (+2.4×)**; mild to $24.5m (+0.7×) |

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
- **Retail pools** — scores banded into 8 pools **G1 (riskiest) → G8 (safest)**.
- **Calibration** — long-run grade PDs, a **+15% additive margin of conservatism**, and the **5 bps
  PD floor** (does not bind; PDs ~5%+).

**Results.** AUC 0.706 / Gini 0.41 / KS 0.30; pools rank-order from 10.8% (G1) to 5.6% (G8). The
calibration test ([13_calibration_test.csv](outputs/tables/scorecard_outputs/13_calibration_test.csv))
passes the binomial test in every pool and is conservative on the overall Hosmer-Lemeshow; the MoC
overlay ([14_pd_moc_overlay.csv](outputs/tables/scorecard_outputs/14_pd_moc_overlay.csv)) shows
pre/post-MoC pool PDs (e.g. G1 10.8% → 12.4%). Validation, deciles, score bands and PSI are in
notebooks 04–07.

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

`EL = PD × LGD × EAD`, **account-level** on the card segment — each account linked to its own
borrower PD via `SK_ID_CURR`. Mean EL ~$310 (base) / $351 (downturn) per account; the PD link covers
~25% of the card book, so the example is account-level but illustrative. Best-estimate-of-EL for
defaulted accounts and an EL-vs-provisions framing are documented in notebook 08.

## 5. Stress testing

Scenario **multipliers** on PD / LGD / EAD (notebook 09), recomputing portfolio EL, with shocks
stacked and **no diversification offset** (APG 113 para 92)
→ [15_stress_test.csv](outputs/tables/scorecard_outputs/15_stress_test.csv):

| Scenario | PD × | LGD × | EAD × | Portfolio EL | Uplift |
|---|---:|---:|---:|---:|---:|
| baseline | 1.0 | 1.0 | 1.0 | $14.1m | — |
| mild recession | 1.5 | 1.1 | 1.05 | $24.5m | +0.73× |
| severe recession | 2.5 | 1.25 | 1.1 | $48.5m | +2.44× |

Management-action / contingency and reverse-stress notes are included (APS 220 para 74). The simple
multiplier method here contrasts with the statistical macro-credit satellite model in the Freddie Mac
project's `stress_test/` module.

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

## Data source

**Home Credit Default Risk** (Kaggle, 2018) — public consumer-credit data (personal loans,
point-of-sale finance, credit cards). Files: `application_train`, `bureau`, `bureau_balance`,
`previous_application`, `POS_CASH_balance`, `credit_card_balance`, `installments_payments`. Used for
demonstration only. Source: <https://www.kaggle.com/competitions/home-credit-default-risk>

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
# regenerate the PD calibration test + MoC overlay from committed aggregates (no raw data):
python tools/make_pd_calibration.py
```

## Repository layout

```
.
├── data/                 # Home Credit source data (not redistributed)
├── notebooks/            # 00–07 PD scorecard · 08 EAD/CCF/EL · 09 stress
├── outputs/tables/       # committed scorecard + EAD/EL/stress results  ·  outputs/charts/ — PNGs
├── src/                  # woe, transform, calibration, validation, psi, monitoring, backtesting
├── tools/                # make_figures.py, make_pd_calibration.py
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
