# Macro-credit satellite stress model (Approach B)

The bank-grade complement to the simple multiplier stress test in `notebooks/09_Stress_Testing.ipynb`
(Approach A). Instead of judgemental multipliers, this module fits a **statistical satellite model** —
a regression of the consumer-credit default rate on macro drivers — and uses it to translate macro
**scenarios** into a **stressed PD per rating grade**, with **grade migration** and a **triangulation**
control on the tail. Mirrors the Freddie Mac project's `stress_test/` module, adapted to consumer
drivers (unemployment, wage growth, inflation, GDP).

```
python stress_test/build_stress.py
```

## Data-honesty note (read first)

The Home Credit book is a single **cross-sectional snapshot with no calendar timeline**, so a
point-in-time default-rate panel *cannot* be built from the loan data itself. The satellite is
therefore estimated on **real public US consumer-credit history** — the credit-card charge-off rate
(FRED `CORCCACBS`) against FRED macro series — a published-benchmark outcome, the same philosophy as
the benchmarked LGD elsewhere in this project. The fitted macro **sensitivity** is then applied to the
portfolio's own calibrated grade PDs (**level** anchored to the portfolio, **slope** from the industry
satellite). A fully loan-data-estimated satellite on dated vintages is demonstrated in the companion
Freddie Mac mortgage project. Macro values in `macro/macro_consumer.csv` are approximate annual
figures entered offline (no download), consistent with the project's no-new-data constraint.

## 1. Panel & satellite fit — `satellite_panel.csv`, `satellite_coefficients.csv`

`logit(default_rate_t) = α + β · z(unemployment, wage_growth, inflation, gdp_growth)_t`

- 19 annual observations (2006–2024) spanning two genuine downturns (GFC 2008–10, COVID 2020).
- Each driver is **standardised** (z-score); the outcome is the logit of the charge-off rate.
- **In-sample R² ≈ 0.45.** Economic **signs are enforced**: unemployment **+**, wage growth **−**,
  inflation **+**, GDP growth **−** — all four come out sign-consistent and are retained. Any
  wrong-sign driver would be **excluded** from the stress (as Freddie dropped the mortgage rate).

## 2. Scenarios → stressed PD by grade — `scenario_stressed_pd_by_grade.csv`

Three scenarios (inputs clipped to the observed support):

| Scenario | Unemployment | Wage growth | Inflation | GDP growth | Basis |
|---|---:|---:|---:|---:|---|
| baseline | 4.0% | 4.0% | 2.9% | +2.8% | current-like |
| mild recession | 6.5% | 2.5% | 3.5% | 0.0% | Basel CRE36.51 (~2 quarters zero growth) |
| severe recession | 9.6% | 1.9% | 1.0% | −2.6% | GFC-like consumer downturn |

The scenario **macro log-odds shift** (vs baseline) is added to each grade's calibrated PD:

`logit(stressed_pd_grade) = logit(base_pd_grade) + macro_logit_shift`

- Mild shift **+0.59 logit → avg PD ×1.67**; severe shift **+1.02 logit → avg PD ×2.36**.
- `base_pd` is the **final capital PD** per grade from `18_grade_pd_moc_floor.csv`, so the stress
  starts from the same master scale that drives EL and capital.
- **Grade migration:** because this book's grades are weakly separated (AUC ≈ 0.71, PD band only
  ~7.6%–12.4%), even a mild macro shock pushes every grade **to/beyond the worst current grade (G1)** —
  reported honestly via `migrated_beyond_worst`. A more discriminating model would show staged
  migration; here the whole book shifts together.

## 3. Triangulation (model-risk control) — `triangulation.csv`

The satellite tail is cross-checked against two independent reference points (WP14; APG 113 para 140):

| Method | Severe PD ×| Reading |
|---|---:|---|
| satellite severe (this module) | **2.36** | logit-linear macro model, inputs clipped to support |
| observed industry peak (data) | **3.09** | FRED CC charge-off peak (2010) ÷ calm-years avg (2014–19) — the realised ceiling |
| notebook-09 multiplier (Method A) | **2.50** | judgemental observed multiplier in the simple stress test |

The three sit in a tight **2.4–3.1×** band: the satellite is **below the observed ceiling** and beside
the judgemental multiplier — a credible, mutually-supporting result (unlike a satellite that
over-states the tail, which would be the flag to investigate).

## 4. Compliance mapping

| Requirement | Source | Where satisfied |
|---|---|---|
| Stress ≥ a mild recession; shock PD/LGD/EAD | Basel CRE36.51 | §2 scenarios (mild = 2-quarters-zero-growth) |
| Severe-but-plausible scenario | APS 220 para 72 | §2 severe recession |
| No diversification benefit assumed | APG 113 para 92 | shocks stacked, no offset (carried from nb09) |
| Independent validation of the stress framework | APS 220 para 76; APG 113 para 140 | §1 fit + §3 triangulation (8-element framework, esp. elements 3 & 4) |
| Model-risk controls / tail triangulation | WP14 | §3 triangulation.csv |

## Outputs

```
stress_test/
├── macro/macro_consumer.csv                 # macro history + industry charge-off outcome
├── build_stress.py                          # the pipeline
└── outputs/
    ├── tables/
    │   ├── satellite_panel.csv              # macro + observed vs fitted default rate
    │   ├── satellite_coefficients.csv       # standardised coefficients + sign checks + R²
    │   ├── scenario_stressed_pd_by_grade.csv# base vs stressed PD per grade + migration
    │   └── triangulation.csv                # satellite vs observed-peak vs nb09 multiplier
    └── charts/stressed_pd_by_grade.png      # regenerated by tools/make_figures.py
```
