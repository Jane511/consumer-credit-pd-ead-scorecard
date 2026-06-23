# Methodology & framework alignment — consumer credit (Home Credit)

Technical companion to the README. It states the method used for each risk component (PD, EAD,
LGD, Expected Loss, IFRS 9 ECL, stress testing), the actual results, and the APS 113 / APG 113 /
Basel CRE36 / WP14 / IFRS 9 rules each step satisfies. The project is a portfolio demonstration on
the public Home Credit Default Risk dataset, not a production bank model; all cut-offs and overlays
are illustrative. It is built to the same output-table contract as the companion **Freddie Mac
mortgage** project, adapted for the three structural differences of consumer credit (revolving EAD →
CCF, unsecured → benchmark LGD, consumer macro drivers).

The most important scoping fact, stated up front: **this dataset has no recovery data and a broken
revolving-default flag** (the credit-card `SK_DPD` counter accumulates and never resets, so the
90+DPD flag is not economic default). LGD is therefore an external-benchmark assumption, and the
EAD/EL layer is a **methodology demonstration**, not a credible loss estimate. A recovery-based LGD
and a clean (non-reviving) default definition are demonstrated in the Freddie Mac project.

## Methods used

| Component | Method |
|---|---|
| **PD** | Logistic regression on application + bureau/behavioural features → **WOE/IV points scorecard** → 8 retail pools (G1–G8) on a **master scale**. Long-run calibration, +15% MoC, ratchet (revise-up), 5 bps floor; binomial + Hosmer-Lemeshow calibration test; **confusion matrix** + **out-of-sample / cold-holdout** validation. |
| **EAD** | **Revolving credit-conversion factor (CCF)** on the credit-card segment: ULF basis with an **LF/BF switch in the high-utilisation region of instability**; onset-of-delinquency anchor; receivables-inclusive, floored at drawn balance; long-run count-weighted + downturn + MoC. |
| **LGD** | **External-benchmark assumption** (no recovery data): base 0.75 / downturn 0.85, within a ~0.65–0.90 unsecured-consumer band; economic-loss / discounting / floor treatment documented. |
| **EL** | EL = PD × LGD × EAD: **account-level** on the card segment, plus an **EL-by-grade + portfolio** table that reconciles to the master scale, plus **IFRS 9 / AASB 9 three-stage ECL**. |
| **Stress** | **A —** scenario multipliers on PD/LGD/EAD (mild + severe); **B —** statistical **macro-credit satellite** model → stressed PD per grade + migration, triangulated. |
| **Validation** | AUC / Gini / KS, decile + score-band rank-ordering, calibration test, confusion matrix, out-of-sample / cold holdout, PSI stability; **8-element framework (APG 113 para 140)** referenced. |

---

## 1. PD model

**Target.** The Home Credit `TARGET` flag (competition proxy for default); the APS 220 reference is
unlikely-to-pay or 90+DPD, so this is treated as **broad-equivalence** (APS 113 Att D para 5) with a
**one-year horizon**, the basis for a long-run one-year PD (CRE36.63).

**Method.**

- **Logistic regression** built in stages: a baseline on application data (notebooks 00–02), then
  feature enrichment from bureau and prior-behaviour tables aggregated to borrower level.
- **WOE/IV scorecard** — variables screened by Information Value, transformed to weight of evidence,
  refit as an interpretable logistic scorecard, scaled to points (base score 600, base odds 0.08,
  PDO 20). A 12-feature scorecard is retained; coefficients + odds-ratios are exported
  (`03_scorecard_coefficients.csv`).
- **Master scale** — scores are banded into **8 retail pools G1 (riskiest) → G8 (safest)**
  (`score_to_grade_mapping.csv`); consumer credit is retail, so the bands are pools.
- **Calibration → MoC → ratchet → floor** — grade PDs calibrated to the long-run rate; a **+15%
  additive margin of conservatism**; the **revise-upward ratchet** (lift the PD to the realised rate
  where it exceeds the estimate, Validation para 6); and the **5 bps PD floor** (Att B para 1). The
  full chain is one table, `18_grade_pd_moc_floor.csv`, whose `pd_final` is the capital PD that feeds
  EL — so EL and the master scale reconcile (PDR2-1).

**Results.**

- Discrimination: **AUC 0.706** (train and test), **Gini 0.41**, **KS 0.30**.
- Pools rank-order: predicted PD **10.8% (G1) → 6.6% (G8)** (observed **11.1% → 5.6%**); bad rate by
  score band rises from best to worst band.
- **Calibration test** (`13_calibration_test.csv`): every pool **passes** the one-sided binomial
  under-estimation test (all green); the overall **Hosmer-Lemeshow** flags red, reflecting that the
  calibrated level is *conservative* against the benign test window (predicted 8.85% vs observed
  8.07%). The binomial/H-L **independence caveat** (WP14) is stated — flags are review prompts.
- **MoC + floor chain** (`18_grade_pd_moc_floor.csv`): e.g. G1 long-run 10.8% → +MoC 12.4% → ratchet
  (does not bind, post-MoC already > observed) → floor (does not bind) → `pd_final` 12.4%.
- **Confusion matrix** (`16_confusion_matrix.csv`): at the **portfolio prevalence cut-off** (8.85%,
  not an arbitrary 0.5), **recall 0.68 / precision 0.14 / specificity 0.62** — low precision is
  expected at an ~8% base rate and is the right trade-off for a triage scorecard.
- **Out-of-sample + cold holdout** (`17_oot_validation.csv`): the scorecard's linear stage is re-fit
  on the training slice and scored on a held-out slice (no leakage). (A) random out-of-sample test
  **AUC 0.71, PSI ≈ 0**; (B) a never-seen **cold holdout** test **AUC 0.71, PSI ≈ 0** — rank-ordering
  generalises. **Honest limitation:** Home Credit is a single cross-sectional snapshot with no usable
  origination date, so a true *calendar* out-of-time split is **not feasible** here; a real
  time-based OOT + forward holdout is demonstrated in the Freddie Mac project.

**Compliance.** Count-weighted long-run calibration (Att D PD para 3); MoC (CRE36.67 / Step 10);
ratchet (Validation para 6); 5 bps floor (Att B para 1); formal calibration test (Part 5.3);
discrimination + calibration validation (WP14); retail-pool framing and PIT-leaning rating philosophy
with the APG 113 para 73 caveat (calibrating PIT to a long-run average does not by itself make it
through-the-cycle) — documented in the governance notebook.

---

## 2. EAD model (revolving — CCF)

Unlike a term mortgage (no CCF), a credit card is **revolving**: EAD must convert the undrawn limit
via a **credit-conversion factor**. Own-EAD estimates are mandatory for revolving retail.

**Method.**

- **Default anchor / 12-month horizon** — the broken 90+DPD flag is kept only as a diagnostic; the
  **onset-of-delinquency** month is the **primary** EAD anchor, with the reference exposure taken
  **12 months before** the anchor (Att D EAD para 7) — the closest this data gets to the required
  fixed-horizon, true-default basis.
- **EAD definition** — drawn balance **plus receivables / limit excesses** where the card file
  exposes them (not capped at balance/limit; Att D EAD para 10), **floored at the current drawn
  balance** (CRE36.89). Post-default drawings are assigned to LGD, not EAD.
- **CCF basis and the region of instability** — observed CCFs are **not** clipped to [0, 1] and
  over-limit accounts are **not** dropped (both named ineffective mitigations, CRE36.95(2)). In the
  **high-utilisation** region the basis switches from ULF to a **limit factor (LF) / balance factor
  (BF)** so a near-zero undrawn amount is not in the denominator (CRE36.95(1)); CCF is reported by
  utilisation band.
- **Long-run / downturn / MoC / exclusions** — long-run **count-weighted** CCF (Att D EAD para 2);
  the *allowed* homogeneity exclusion of accounts already problematic at the reference date (APG 113
  para 129(b)); a **downturn CCF** and a **MoC** add-on with a note on positive default/EAD
  correlation.

**Results** (`ead_summary.csv`).

- 1,806 90+DPD accounts → 1,539 with a reference month → **1,376 after the homogeneity exclusion**.
- **EAD (onset anchor, primary) ~$2,005/account**; 90+DPD anchor (secondary) ~$2,964.
- **Long-run ULF CCF −0.88** (count-weighted) — a genuine finding: card balances typically **pay
  down** in the months before default, so the conversion factor is **negative**; downturn CCF −0.28,
  MoC add-on +0.09. EAD therefore falls back to the drawn-balance floor (100% of accounts).

**Compliance.** CRE36.95 region-of-instability handling; Att D EAD paras 1/2/7/10; CRE36.89 floor;
APG 113 para 129(b) exclusion. The negative observed CCF and the broken default flag are documented
as data-quality findings, not smoothed over.

---

## 3. LGD

**Method.** The dataset has **no recovery cash flows**, so LGD cannot be modelled from economic
loss. It is set as an **external-benchmark assumption**: **base 0.75 / downturn 0.85** within a
~**0.65–0.90** published unsecured-consumer / credit-card range, and Expected Loss is shown **across
that range** as a sensitivity rather than a single point.

**Economic-loss / discounting / floor treatment (documented).** The framework wants **economic
loss** — discounted recovery cash flows net of direct and indirect collection costs (CRE36.76 /
Att D LGD para 1), discounted at the facility rate or a documented proxy (APG 113 para 122). With no
recovery cash flows in the data, none of these can be computed; the benchmark range is the documented
substitute. The unsecured-LGD treatment also has no 20% residential-mortgage floor (that floor is
collateral-specific, Att B); the benchmark itself sits well above any practical floor. A real
recovery-based, discounted, downturn LGD is built in the Freddie Mac project.

**Compliance.** Economic-loss LGD from recoveries (CRE36.76) is not available; the benchmark range +
downturn pair is the documented, defensible substitute, explicitly labelled as an assumption.

---

## 4. Expected Loss

**Method.** `EL = PD × LGD × EAD`, delivered three ways:

1. **Account-level** on the credit-card segment — each card account linked to **its own borrower PD**
   via `SK_ID_CURR` (rather than a portfolio-average PD); EL shown across the LGD base/downturn range.
2. **By rating grade + portfolio total** (`19_el_summary_by_grade.csv`) — loans, total EAD, avg PD,
   avg LGD, total EL and **EL-rate (bps)** per grade, using the **`pd_final` capital PD** from the
   master scale. The portfolio total **reconciles exactly to the stress-test baseline** (PDR2-1 / Att
   B EL para 1).
3. **IFRS 9 / AASB 9 three-stage ECL** (`20_ifrs9_staging.csv`).

**Results.**

- Account-level: mean EL **$310 (base) / $351 (downturn)** per account; the PD link covers **~25%** of
  the card book (the scorecard test split), so the example is account-level but **illustrative**.
- By grade: **portfolio EL ≈ $14.1m**, avg PD 10.2%, LGD 0.75, **EL-rate ~763 bps**; per grade the
  EL-rate runs **569 bps (G8) → 930 bps (G1)** — high, as expected for unsecured cards at 75% LGD.
- IFRS 9 stages: **S1 performing 77,475 / S2 SICR 7,331 / S3 impaired 7,448**; reported ECL **S1
  $8.4m** (12-month), **S2 $7.3m** (lifetime proxy ×3), **S3 $11.2m** (best-estimate-of-EL = LGD×EAD,
  default having occurred) — total ≈ **$26.9m**.

**IFRS 9 stage logic (documented proxies — a single snapshot has no origination PD or DPD field).**
Stage 3 = the `TARGET` default proxy (credit-impaired); Stage 2 (SICR) = non-defaulted accounts whose
12-month PD ≥ 2× the portfolio PD; Stage 1 = performing. Per the accounting standard, IFRS 9 LGD is
the **unbiased best estimate** (no downturn add-on, no MoC), 12-month ECL for S1 and lifetime for
S2/S3; a 30-DPD SICR backstop and a full behavioural-lifetime PD term structure are noted as
documented, not operationalised on this snapshot.

**Compliance.** Same PD/LGD/EAD as the risk parameters; best-estimate-of-EL for defaulted accounts
(CRE36.86 / Att D EL para 1, no mechanical long-run/downturn LGD) applied in Stage 3; IFRS 9 / AASB 9
three-stage ECL framed per BCBS Dec 2015 / APG 220 paras 106–108; EL-vs-provisions framed as
documentation for a demo.

---

## 5. Stress testing

**Approach A — observed multipliers** (notebook 09, `15_stress_test.csv`). A **mild** and a **severe**
recession apply multipliers to PD, LGD and EAD; portfolio EL = PD × LGD × EAD is recomputed. Shocks
**stack with no diversification offset** (APG 113 para 92).

| Scenario | PD × | LGD × | EAD × | Portfolio EL | Uplift vs baseline |
|---|---:|---:|---:|---:|---:|
| baseline | 1.0 | 1.0 | 1.0 | $14.1m | — |
| mild recession | 1.5 | 1.1 | 1.05 | $24.5m | +0.73× |
| severe recession | 2.5 | 1.25 | 1.1 | $48.5m | +2.44× |

**Approach B — statistical macro-credit satellite model** (`stress_test/`, see its README). A
logit-linear regression of the consumer-credit default rate on macro drivers (unemployment, wage
growth, inflation, GDP), used to translate macro scenarios into a **stressed PD per grade** with
**grade migration**, then **triangulated**.

- **Fit** (`satellite_coefficients.csv`): R² ≈ 0.45 on 19 years; all four drivers come out
  **economically sign-consistent** (unemployment +, wage −, inflation +, GDP −) and are retained;
  wrong-sign drivers would be excluded.
- **Scenarios → grades** (`scenario_stressed_pd_by_grade.csv`): mild **+0.59 logit → avg PD ×1.67**,
  severe **+1.02 logit → ×2.36**, applied to each grade's `pd_final`. Because the grades are weakly
  separated, even a mild shock migrates the whole book **to/beyond the worst grade (G1)** — reported
  honestly.
- **Triangulation** (`triangulation.csv`): satellite severe **×2.36** sits **below** the observed
  industry ceiling **×3.09** (FRED credit-card charge-off peak ÷ calm-years average) and beside the
  judgemental notebook-09 multiplier **×2.50** — a tight, mutually-supporting 2.4–3.1× band.

**Data-honesty note.** The Home Credit snapshot has no calendar timeline, so the satellite is
estimated on **real public US consumer-credit history** (industry charge-off vs FRED macro) and its
macro *sensitivity* is applied to the portfolio's own grade PDs (level anchored to the portfolio).
A fully loan-data-estimated satellite on dated vintages is in the Freddie Mac project.

**Compliance.** Mild recession (CRE36.51); severe-but-plausible (APS 220 para 72); no-diversification
(APG 113 para 92); contingency / reverse-stress notes (APS 220 para 74); independent validation +
tail triangulation (APS 220 para 76; APG 113 para 140; WP14).

---

## 6. Validation — the 8-element framework (APG 113 para 140)

Independent validation is structured against the **eight elements** of APG 113 para 140; on this
public-data demo each element is evidenced as below (operationalised where the data allows, otherwise
documented):

| # | Element | Evidence here |
|---|---|---|
| 1 | Design & construction | WOE/IV logic, rating philosophy, drivers, limitations (notebooks 03/06; this doc) |
| 2 | Data inputs & outputs | sentinel/missing handling, WOE transform, IV screening (notebooks 00–03) |
| 3 | Performance | AUC/Gini/KS, calibration test, confusion matrix, out-of-sample / cold holdout (`08`,`13`,`16`,`17`) |
| 4 | Conservative adjustments | MoC overlay + ratchet + floor chain (`18`); stress triangulation |
| 5 | Implementation | committed `tools/` regenerate every table from aggregates; code in `src/` |
| 6 | Use | score-band policy / cut-offs, override & reject-inference policy (notebooks 04/06, documented) |
| 7 | Documentation | this alignment doc + README + Scorecard_README + stress_test README |
| 8 | Management reporting | monitoring / PSI / backtesting governance (notebooks 05/07) |

Validation is **independent of development** with **no cross-validation** (APG 113 para 134), and
**annual review** is stated (CRE36.65). The binomial / Hosmer-Lemeshow **independence caveat** under
correlated defaults (WP14) is carried throughout.

---

## Regulatory alignment — implemented vs documented-only

**Implemented in code + regenerated outputs:**

- PD: coefficients + odds-ratios (`03_scorecard_coefficients.csv`); 5 bps floor; binomial +
  Hosmer-Lemeshow calibration test (`13`); +15% MoC overlay (`14`); long-run→MoC→ratchet→floor chain
  (`18`); confusion matrix at prevalence (`16`); out-of-sample / cold-holdout validation (`17`).
- EAD: 12-month-horizon onset anchor; receivables-inclusive, floored EAD; no CCF clipping / no
  over-limit dropping; ULF→LF/BF basis switch; long-run count-weighted, downturn, MoC, homogeneity
  exclusion (`ead_summary.csv`).
- LGD: benchmarked base/downturn range with EL sensitivity.
- EL: account-level via `SK_ID_CURR`; EL-by-grade + portfolio reconciling to the master scale (`19`);
  IFRS 9 / AASB 9 three-stage ECL (`20`).
- Stress: Approach A mild + severe (`15`); Approach B satellite — panel/coefficients, stressed PD by
  grade + migration, triangulation (`stress_test/`).

**Documented-only (treatment stated, not operationalised on demo data):**

- Rating philosophy (PIT-leaning, long-run-calibrated; APG 113 para 73 caveat), use test, override
  policy, reject inference (notebook 06).
- LGD economic-loss / discounting (no recovery cash flows); IFRS 9 30-DPD SICR backstop and full
  behavioural-lifetime PD term structure.
- True calendar out-of-time / forward holdout (no usable origination date — see §1).
- Management actions / contingency, reverse-stress, independent stress validation (notebook 09).
- Binomial / Hosmer-Lemeshow independence caveat under correlated defaults (WP14).

## Limitations

- Public Home Credit data, not a real lender's portfolio; cut-offs and overlays illustrative.
- **No LGD model** — LGD is an external-benchmark assumption (no recovery data).
- **EAD/EL is a methodology demonstration** — the `SK_DPD` counter accumulates and never resets, so
  the 90+DPD flag is not economic default (it fires late on a small residual; the pre-default peak
  balance sits ~10 months earlier; some accounts revive after their flagged "default"). Exposure and
  EL figures show the mechanics only.
- The EL example links ~25% of the card book to a borrower PD; the EL-by-grade table applies a single
  portfolio-average EAD to every grade (no per-grade card exposure exists) — so grade ranking is
  PD-driven, which is the point.
- **No calendar timeline** — the satellite is fitted on public industry history, not the loan data,
  and a true time-based OOT is not feasible here.
- Properly-anchored EAD, a recovery-based downturn LGD and a loan-data satellite are demonstrated in
  the companion Freddie Mac mortgage project.
