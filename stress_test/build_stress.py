"""
stress_test/build_stress.py — statistical macro-credit "satellite" stress model (Approach B).

Closes the largest Freddie parity gap: a regression of the default rate on macro drivers, used
to translate macro scenarios into a stressed PD per rating grade with grade migration, then
triangulated against the simple observed-multiplier method (notebook 09). Mirrors the Freddie
`stress_test/` module, adapted to CONSUMER drivers (unemployment, wage growth, inflation, GDP).

Run:
    python stress_test/build_stress.py

Inputs:
  stress_test/macro/macro_consumer.csv                    — macro history + industry outcome
  outputs/tables/scorecard_outputs/18_grade_pd_moc_floor.csv — final capital PD per grade
  outputs/tables/scorecard_outputs/15_stress_test.csv        — notebook-09 observed multipliers

Outputs (stress_test/outputs/tables/):
  satellite_panel.csv             — yearly panel: macro + observed vs fitted default rate
  satellite_coefficients.csv      — standardized macro coefficients, expected sign, sign_ok
  scenario_stressed_pd_by_grade.csv — base vs stressed PD per grade, multiplier, migration
  triangulation.csv               — satellite vs observed-peak vs notebook-09 multiplier

DATA-HONESTY NOTE (carried into the README): the Home Credit book is a single cross-sectional
snapshot with NO calendar timeline, so a point-in-time default-rate panel cannot be built from the
loan data itself. The satellite is therefore estimated on REAL PUBLIC US consumer-credit history
(credit-card charge-off rate, FRED CORCCACBS, vs FRED macro series) — a published-benchmark
outcome, the same philosophy as the benchmarked LGD. The fitted macro SENSITIVITY is then applied
to the portfolio's own calibrated grade PDs (level anchored to the portfolio, slope from the
industry satellite). A fully loan-data-estimated satellite on dated vintages is demonstrated in the
companion Freddie Mac project. Coefficients are sign-restricted; only economically-correct drivers
enter the stress.

Framework: Basel CRE36.51 (>= mild recession; PD/LGD/EAD); APG 113 para 92 (no diversification);
APS 220 paras 72-76 (severe-but-plausible, contingency, independent validation); model-risk
triangulation of the tail (WP14; APG 113 para 140).
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

SC = ROOT / "outputs" / "tables" / "scorecard_outputs"
OUT = HERE / "outputs" / "tables"
OUT.mkdir(parents=True, exist_ok=True)

DRIVERS = ["unemployment", "wage_growth", "inflation", "gdp_growth"]
# Economic priors: higher unemployment / inflation raise consumer defaults; higher wage growth
# and GDP growth lower them. Drivers whose fitted sign disagrees are EXCLUDED from the stress.
EXPECTED_SIGN = {"unemployment": +1, "wage_growth": -1, "inflation": +1, "gdp_growth": -1}

# Macro scenarios (annual). Mild = Basel CRE36.51 "~two quarters of zero growth"; severe = a
# GFC-like consumer downturn. Inputs are clipped to the observed support before use.
SCENARIOS = {
    "baseline":         {"unemployment": 4.0, "wage_growth": 4.0, "inflation": 2.9, "gdp_growth": 2.8},
    "mild recession":   {"unemployment": 6.5, "wage_growth": 2.5, "inflation": 3.5, "gdp_growth": 0.0},
    "severe recession": {"unemployment": 9.6, "wage_growth": 1.9, "inflation": 1.0, "gdp_growth": -2.6},
}


def _logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def _inv_logit(x):
    return 1.0 / (1.0 + np.exp(-x))


def fit_satellite(macro):
    """Fit logit(default_rate) ~ standardized macro drivers (sign-restricted)."""
    y = _logit(macro["cc_default_rate"].to_numpy() / 100.0)
    mu = macro[DRIVERS].mean()
    sd = macro[DRIVERS].std(ddof=0)
    Z = (macro[DRIVERS] - mu) / sd
    lr = LinearRegression().fit(Z, y)
    coef = dict(zip(DRIVERS, lr.coef_))
    r2 = lr.score(Z, y)
    fitted = _inv_logit(lr.predict(Z)) * 100.0
    return {"intercept": float(lr.intercept_), "coef": coef, "mu": mu, "sd": sd,
            "r2": float(r2), "fitted": fitted}


def write_panel(macro, fit):
    panel = macro.copy()
    panel["fitted_default_rate"] = np.round(fit["fitted"], 3)
    panel["residual"] = np.round(panel["cc_default_rate"] - panel["fitted_default_rate"], 3)
    panel.to_csv(OUT / "satellite_panel.csv", index=False)
    print("Saved -> stress_test/outputs/tables/satellite_panel.csv (R2=%.3f, %d years)"
          % (fit["r2"], len(panel)))


def write_coefficients(fit):
    rows = []
    for d in DRIVERS:
        c = fit["coef"][d]
        ok = int(np.sign(c) == EXPECTED_SIGN[d])
        rows.append({"variable": d, "coefficient_std": round(c, 4),
                     "expected_sign": EXPECTED_SIGN[d], "sign_ok": ok,
                     "used_in_stress": ok})
    rows.append({"variable": "_R2", "coefficient_std": round(fit["r2"], 4),
                 "expected_sign": "", "sign_ok": "", "used_in_stress": ""})
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "satellite_coefficients.csv", index=False)
    print("Saved -> stress_test/outputs/tables/satellite_coefficients.csv")
    used = [r["variable"] for r in rows if r.get("used_in_stress") == 1]
    print("  sign-consistent drivers used in stress:", used)
    return out


def _scenario_shift(fit, scenario):
    """Macro log-odds shift of a scenario vs baseline, using sign-consistent drivers only.

    Each driver is clipped to the observed support, standardized with the panel mean/sd, and the
    shift is sum_k coef_k * (z_scenario_k - z_baseline_k). The intercept cancels in the difference.
    """
    shift = 0.0
    for d in DRIVERS:
        if np.sign(fit["coef"][d]) != EXPECTED_SIGN[d]:
            continue  # wrong economic sign -> excluded
        z_s = (np.clip(SCENARIOS[scenario][d], fit["support"][d][0], fit["support"][d][1])
               - fit["mu"][d]) / fit["sd"][d]
        z_b = (np.clip(SCENARIOS["baseline"][d], fit["support"][d][0], fit["support"][d][1])
               - fit["mu"][d]) / fit["sd"][d]
        shift += fit["coef"][d] * (z_s - z_b)
    return float(shift)


def _grade_mapper(grades):
    """Return f(pd) -> (nearest grade label, beyond_worst bool) on the master scale."""
    pdf = grades.set_index("grade")["pd_final"]
    worst_pd = pdf.max()

    def f(pd_val):
        nearest = (pdf - pd_val).abs().idxmin()
        return nearest, bool(pd_val > worst_pd)
    return f


def write_stressed_pd_by_grade(fit, grades):
    mapper = _grade_mapper(grades)
    rows = []
    shifts = {s: _scenario_shift(fit, s) for s in SCENARIOS}
    for scenario in SCENARIOS:
        shift = shifts[scenario]
        for _, g in grades.iterrows():
            base = float(g["pd_final"])
            stressed = float(_inv_logit(_logit(base) + shift))
            grade_to, beyond = mapper(stressed)
            rows.append({
                "scenario": scenario,
                "grade": g["grade"],
                "base_pd": round(base, 6),
                "macro_logit_shift": round(shift, 4),
                "stressed_pd": round(stressed, 6),
                "pd_multiplier": round(stressed / base, 2),
                "stressed_grade": grade_to,
                "migrated_beyond_worst": beyond,
            })
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "scenario_stressed_pd_by_grade.csv", index=False)
    print("Saved -> stress_test/outputs/tables/scenario_stressed_pd_by_grade.csv")
    for s in SCENARIOS:
        sub = out[out.scenario == s]
        print("  %-17s logit shift %+.3f  avg PD multiplier x%.2f"
              % (s, shifts[s], sub["pd_multiplier"].mean()))
    return out, shifts


def write_triangulation(macro, stressed, grades):
    # 1) satellite severe = average PD multiplier across grades under the severe scenario
    sat = stressed[stressed.scenario == "severe recession"]["pd_multiplier"].mean()
    # 2) observed industry ceiling = peak charge-off / calm-years average (2014-2019)
    calm = macro[macro.year.between(2014, 2019)]["cc_default_rate"].mean()
    peak_ratio = macro["cc_default_rate"].max() / calm
    # 3) notebook-09 observed-multiplier approach (Method A) severe PD multiplier
    nb09 = pd.read_csv(SC / "15_stress_test.csv")
    nb09_mult = float(nb09.loc[nb09["scenario"].str.contains("Severe", case=False), "pd_mult"].iloc[0])

    out = pd.DataFrame([
        {"method": "satellite severe (this module)", "severe_PD_mult_x": round(sat, 2),
         "note": "logit-linear macro model on public consumer-credit history; inputs clipped to support"},
        {"method": "observed industry peak (data)", "severe_PD_mult_x": round(peak_ratio, 2),
         "note": "FRED CC charge-off peak (2010) / calm-years avg (2014-19) — the realised ceiling"},
        {"method": "notebook-09 multiplier (Method A)", "severe_PD_mult_x": round(nb09_mult, 2),
         "note": "judgemental observed multiplier used in the simple stress test"},
    ])
    out.to_csv(OUT / "triangulation.csv", index=False)
    print("Saved -> stress_test/outputs/tables/triangulation.csv")
    print("  satellite x%.2f vs observed-peak x%.2f vs nb09 x%.2f"
          % (sat, peak_ratio, nb09_mult))


def main():
    macro = pd.read_csv(HERE / "macro" / "macro_consumer.csv")
    grades = pd.read_csv(SC / "18_grade_pd_moc_floor.csv")[["grade", "pd_final"]]

    fit = fit_satellite(macro)
    fit["support"] = {d: (float(macro[d].min()), float(macro[d].max())) for d in DRIVERS}

    write_panel(macro, fit)
    write_coefficients(fit)
    stressed, _ = write_stressed_pd_by_grade(fit, grades)
    write_triangulation(macro, stressed, grades)


if __name__ == "__main__":
    main()
