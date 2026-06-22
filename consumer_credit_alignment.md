# Methodology & framework alignment — consumer credit (Home Credit)

Technical companion to the README. It states the method used for each risk component (PD, EAD,
LGD, Expected Loss, stress testing), the actual results, and the APS 113 / APG 113 / Basel CRE36 /
WP14 rules each step satisfies. The project is a portfolio demonstration on the public Home Credit
Default Risk dataset, not a production bank model; all cut-offs and overlays are illustrative.

The most important scoping fact, stated up front: **this dataset has no recovery data and a broken
revolving-default flag** (the credit-card `SK_DPD` counter accumulates and never resets, so the
90+DPD flag is not economic default). LGD is therefore an external-benchmark assumption, and the
EAD/EL layer is a **methodology demonstration**, not a credible loss estimate. A
recovery-based LGD and a clean (non-reviving) default definition are demonstrated in the companion
Freddie Mac mortgage project.

## Methods used

| Component | Method |
|---|---|
| **PD** | Logistic regression on application + bureau/behavioural features → **WOE/IV points scorecard** → 8 retail pools (G1–G8). Long-run calibration, +15% margin of conservatism, 5 bps floor; binomial + Hosmer-Lemeshow calibration test. |
| **EAD** | **Revolving credit-conversion factor (CCF)** on the credit-card segment: ULF basis with an **LF/BF switch in the high-utilisation region of instability**; onset-of-delinquency anchor; receivables-inclusive, floored at drawn balance; long-run count-weighted + downturn + MoC. |
| **LGD** | **External-benchmark assumption** (no recovery data in the dataset): base 0.75 / downturn 0.85, within a ~0.65–0.90 unsecured-consumer band. |
| **EL** | EL = PD × LGD × EAD, account-level on the card segment (each account's own borrower PD linked via `SK_ID_CURR`). |
| **Stress** | Scenario **multipliers** on PD / LGD / EAD (mild + severe recession), stacked with no diversification offset. |
| **Validation** | AUC / Gini / KS, decile + score-band rank-ordering, calibration test, PSI stability, governance / backtesting notes. |

---

## 1. PD model

**Target.** The Home Credit `TARGET` flag (competition proxy for default); the APS 220 reference is
unlikely-to-pay or 90+DPD, so this is treated as **broad-equivalence** with the horizon documented.

**Method.**

- **Logistic regression** built in stages: a baseline on application data (notebooks 00–02), then
  feature enrichment from bureau and prior-behaviour tables aggregated to borrower level.
- **WOE/IV scorecard** — selected variables screened by Information Value, transformed to weight of
  evidence, refit as an interpretable logistic scorecard, and scaled to points (base score 600,
  base odds 0.08, PDO 20). A 12-feature scorecard is retained.
- **Rating pools** — scores are banded into **8 retail pools G1 (riskiest) → G8 (safest)**;
  consumer credit is retail, so the bands are pools (a production system would also reflect LGD/EAD
  and separate delinquent vs current).
- **Calibration** — grade PDs calibrated to the long-run rate, a **+15% additive margin of
  conservatism** applied, and the **5 bps PD floor** (`apply_pd_floor`, APS 113 Att B para 1; does
  not bind here as PDs are ~5%+).

**Results.**

- Discrimination: **AUC 0.706** (train and test), **Gini 0.41**, **KS 0.30**.
- Pools rank-order cleanly: predicted PD **10.8% (G1) → 5.6% (G8)**; bad rate by score band rises
  from the best to the worst band.
- **Calibration test** (`13_calibration_test.csv`): every pool **passes** the one-sided binomial
  under-estimation test (all green); the overall **Hosmer-Lemeshow** flags red, reflecting that the
  calibrated level is *conservative* against the benign test window (predicted 8.85% vs observed
  8.07%). The binomial/H-L **independence caveat** (WP14) is stated — both understate Type-I error
  under correlated defaults, so flags are review prompts.
- **MoC overlay** (`14_pd_moc_overlay.csv`): pre/post-MoC pool PDs, e.g. G1 10.8% → 12.4%.

**Compliance.** Count-weighted long-run calibration; MoC (Step 10 / CRE36.67); 5 bps floor (Att B
para 1); formal calibration test (Part 5.3); retail-pool framing and PIT-leaning rating philosophy
with the APG 113 para 73 caveat (calibrating PIT to a long-run average does not by itself make it
through-the-cycle) — documented in the governance notebook.

---

## 2. EAD model (revolving — CCF)

Unlike a term mortgage (no CCF), a credit card is **revolving**: EAD must convert the undrawn limit
via a **credit-conversion factor**. Own-EAD estimates are mandatory for revolving retail.

**Method.**

- **Default anchor** — the broken 90+DPD flag is kept only as a diagnostic; the **onset-of-
  delinquency** month is the **primary** EAD anchor (the closest this data gets to a true default
  point).
- **EAD definition** — drawn balance **plus receivables / limit excesses** where the card file
  exposes them (not capped at balance/limit; APS 113 Att D EAD para 10), **floored at the current
  drawn balance** (Basel CRE36.89). Post-default drawings are assigned to LGD, not EAD.
- **CCF basis and the region of instability** — observed CCFs are **not** clipped to [0, 1] and
  over-limit accounts are **not** dropped (both are named ineffective mitigations, Basel CRE36.95(2)).
  In the **high-utilisation** region the basis switches from ULF to a **limit factor (LF) / balance
  factor (BF)** so a near-zero undrawn amount is not in the denominator (CRE36.95(1)); CCF is
  reported by utilisation band.
- **Long-run / downturn / MoC / exclusions** — long-run **count-weighted** CCF (Att D EAD para 2);
  the *allowed* homogeneity exclusion of accounts already problematic at the reference date (APG 113
  para 129(b), distinct from the forbidden exclusion above); a **downturn CCF** and a **MoC** add-on
  with a note on positive default/EAD correlation.

**Results** (`ead_summary.csv`).

- 1,806 90+DPD accounts → 1,539 with a reference month → **1,376 after the homogeneity exclusion**.
- **EAD (onset anchor, primary) ~$2,005/account**; 90+DPD anchor (secondary) ~$2,964.
- **Long-run ULF CCF −0.88** (count-weighted) — a genuine finding: on this data card balances
  typically **pay down** in the months before default, so the conversion factor is **negative**;
  downturn CCF −0.28, MoC add-on +0.09.

**Compliance.** CRE36.95 region-of-instability handling; Att D EAD paras 1/2/10; CRE36.89 floor;
APG 113 para 129(b) exclusion. The negative observed CCF and the broken default flag are documented
as data-quality findings, not smoothed over.

---

## 3. LGD

**Method.** The dataset has **no recovery cash flows**, so LGD cannot be modelled from economic
loss. It is set as an **external-benchmark assumption**: a **base 0.75 / downturn 0.85** pair within
a ~**0.65–0.90** published unsecured-consumer / credit-card range, and the Expected Loss is shown
**across that range** as a sensitivity rather than a single point.

**Compliance.** The framework wants economic-loss LGD from recoveries (CRE36.76); with none
available, the benchmark range + downturn pair is the documented, defensible substitute, explicitly
labelled as an assumption. A real recovery-based, downturn LGD is built in the Freddie Mac project.

---

## 4. Expected Loss

**Method.** `EL = PD × LGD × EAD`, computed **account-level** on the credit-card segment — each card
account is linked to **its own borrower PD** via `SK_ID_CURR` (rather than a portfolio-average PD).
EL is shown across the LGD base/downturn range.

**Results** (`ead_summary.csv`). Mean EL per account **$310 (base) / $351 (downturn)**; the PD link
covers **~25%** of the card book (the scorecard test split), so the example is account-level but
**illustrative**. A best-estimate-of-EL-for-defaulted note and an EL-vs-provisions framing are
documented (notebook 08).

**Compliance.** Same PD/LGD/EAD as the risk parameters; best-estimate-of-EL for defaulted accounts
(Att D EL para 1, no mechanical long-run/downturn LGD) documented; EL-vs-provisions framed as
documentation for a demo.

---

## 5. Stress testing

**Method.** A scenario **multiplier** stress test (notebook 09): a **mild** and a **severe**
recession apply multipliers to PD, LGD and EAD, and the portfolio EL = PD × LGD × EAD is recomputed.
Shocks **stack with no diversification offset** (APG 113 para 92). Management-action / contingency
and reverse-stress notes are included.

**Results** (`15_stress_test.csv`).

| Scenario | PD × | LGD × | EAD × | Portfolio EL | Uplift vs baseline |
|---|---:|---:|---:|---:|---:|
| baseline | 1.0 | 1.0 | 1.0 | $14.1m | — |
| mild recession | 1.5 | 1.1 | 1.05 | $24.5m | +0.73× |
| severe recession | 2.5 | 1.25 | 1.1 | $48.5m | +2.44× |

**Compliance.** Covers at least a mild recession (Basel CRE36.51); no-diversification (APG 113 para
92); contingency note (APS 220 para 74); independent validation of the stress framework noted as
required (APS 220 para 76). This is the simple multiplier method; the **statistical macro-credit
satellite model** (a regression of the default rate on macro variables) is demonstrated in the
Freddie Mac project's `stress_test/` module.

---

## Regulatory alignment — implemented vs documented-only

**Implemented in code + regenerated outputs:**

- PD: 5 bps floor; binomial + Hosmer-Lemeshow calibration test (`13_calibration_test.csv`); +15% MoC
  overlay (`14_pd_moc_overlay.csv`).
- EAD: onset anchor; receivables-inclusive, floored EAD; no CCF clipping / no over-limit dropping;
  ULF→LF/BF basis switch; long-run count-weighted, downturn, MoC, homogeneity exclusion.
- LGD: benchmarked base/downturn range with EL sensitivity.
- EL: account-level on the card segment via `SK_ID_CURR`.
- Stress: mild + severe scenarios (`15_stress_test.csv`).

**Documented-only (treatment stated, not operationalised on demo data):**

- Rating philosophy (PIT-leaning, long-run-calibrated; APG 113 para 73 caveat), retail-pool framing,
  use test, development/validation independence, override policy, reject inference (notebook 06).
- Best-estimate-of-EL for defaulted accounts and EL-vs-provisions (notebook 08).
- Management actions / contingency, reverse-stress, independent stress validation (notebook 09).
- Binomial / Hosmer-Lemeshow independence caveat under correlated defaults (WP14).

## Limitations

- Public Home Credit data, not a real lender's portfolio; cut-offs and overlays illustrative.
- **No LGD model** — LGD is an external-benchmark assumption (no recovery data).
- **EAD/EL is a methodology demonstration** — the `SK_DPD` counter accumulates and never resets, so
  the 90+DPD flag is not economic default (it fires late on a small residual; the pre-default peak
  balance sits ~10 months earlier; some accounts revive after their flagged "default"). Exposure and
  EL figures show the mechanics only.
- The EL example links ~25% of the card book to a borrower PD, so it is account-level but illustrative.
- Properly-anchored EAD and a recovery-based downturn LGD are demonstrated in the companion Freddie
  Mac mortgage project.
