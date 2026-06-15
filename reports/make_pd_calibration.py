"""
reports/make_pd_calibration.py — PD calibration test + margin-of-conservatism overlay.

Builds two committed artefacts from the existing scorecard outputs (aggregated grade
results only — never raw borrower records), so they regenerate reproducibly with:

    python reports/make_pd_calibration.py

Outputs (into output/scorecard_outputs/):
  13_calibration_test.csv  — per-grade binomial + Hosmer-Lemeshow calibration test
                             with a green/amber/red traffic-light flag (PD-2).
  14_pd_moc_overlay.csv    — per-grade master scale with the additive margin-of-
                             conservatism overlay applied, pre- vs post-MoC (PD-3).

Framework: PD framework Part 5.3 (calibration must be TESTED, not just charted);
APS 113 Att B para 1 (5 bps PD floor); CRE36.67 / Step 10 (margin of conservatism).
All three use the helpers in src/ (apply_pd_floor, binomial_pd_test, hosmer_lemeshow).
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.calibration import apply_pd_floor, PD_FLOOR
from src.validation import binomial_pd_test, hosmer_lemeshow

SC = ROOT / "output" / "scorecard_outputs"
N_GRADES = 8  # G1..G8, matching score_to_grade_mapping.csv (equal-frequency octiles)

# --- Margin-of-conservatism sizing (PD-3) ------------------------------------------
# Additive overlay, expressed as a relative uplift on each grade's calibrated PD.
# Justification (documented, not invented): this is a single-snapshot Kaggle book with
#   (a) a competition PROXY default flag (not an APS 220 economic default),  -> +10%
#   (b) NO through-the-cycle / downturn history (one cohort only),            -> +5%
#   (c) an ACCEPTS-ONLY sample with no reject inference.                      -> (in a)
# Total ~15% relative uplift. Mirrors the additive MoC style used for LGD.
MOC_RELATIVE = 0.15


def _grade_table():
    """Re-derive the per-grade PD table from the scored test set.

    Grades G1..G8 are equal-frequency octiles of `score` (G1 = lowest score = worst),
    reproducing output/scorecard_outputs/score_to_grade_mapping.csv. Predicted PD is the
    mean model PD in the grade (with the 5 bps floor applied, PD-1); observed is the
    realised default rate.
    """
    df = pd.read_csv(SC / "06_test_scored.csv", usecols=["score", "pd_pred", "TARGET"])
    df = df.dropna(subset=["score", "pd_pred", "TARGET"]).copy()
    # Test the CALIBRATED PD (the one used for grades/EL), not the raw model output.
    # calibration_summary.csv stores the long-run calibration; the factor scales the
    # raw mean PD up to the target long-run default rate (APG 113 para 73).
    cs = pd.read_csv(SC / "calibration_summary.csv").iloc[0]
    factor = float(cs["calibrated_mean_pd"]) / float(cs["raw_mean_pd"])
    df["pd_pred"] = apply_pd_floor(df["pd_pred"] * factor)  # PD-1: calibrate then 5 bps floor
    df["grade_idx"] = pd.qcut(df["score"], q=N_GRADES, labels=False, duplicates="drop")
    df["grade"] = ["G%d" % (i + 1) for i in df["grade_idx"]]  # ascending score -> G1 worst

    g = (df.groupby("grade")
            .agg(n=("TARGET", "size"),
                 observed_defaults=("TARGET", "sum"),
                 observed_rate=("TARGET", "mean"),
                 predicted_pd=("pd_pred", "mean"),
                 avg_score=("score", "mean"))
            .reset_index()
            .sort_values("avg_score"))         # worst (G1) first
    return df, g


def build_calibration_test(df, g):
    """PD-2: per-grade binomial test + an overall Hosmer-Lemeshow line."""
    rows = []
    for _, r in g.iterrows():
        res = binomial_pd_test(r["predicted_pd"], r["observed_defaults"], r["n"])
        rows.append({
            "grade": r["grade"],
            "n": res["n"],
            "predicted_pd": round(res["predicted_pd"], 6),
            "observed_rate": round(res["observed_rate"], 6),
            "observed_defaults": res["observed_defaults"],
            "expected_defaults": round(res["expected_defaults"], 1),
            "binomial_p_underest": round(res["p_value_underest"], 6),
            "flag": res["flag"],
        })
    out = pd.DataFrame(rows)

    # Overall Hosmer-Lemeshow across deciles of predicted PD.
    hl = hosmer_lemeshow(df["TARGET"], df["pd_pred"], n_bins=10)
    out = pd.concat([out, pd.DataFrame([{
        "grade": "OVERALL_HL",
        "n": int(df.shape[0]),
        "predicted_pd": round(float(df["pd_pred"].mean()), 6),
        "observed_rate": round(float(df["TARGET"].mean()), 6),
        "observed_defaults": int(df["TARGET"].sum()),
        "expected_defaults": round(float(df["pd_pred"].sum()), 1),
        "binomial_p_underest": round(hl["p_value"], 6),  # HL chi-square p-value
        "flag": "green" if hl["p_value"] >= 0.05 else ("amber" if hl["p_value"] >= 0.01 else "red"),
    }])], ignore_index=True)
    out.attrs["hl"] = hl
    return out


def build_moc_overlay(g):
    """PD-3: additive margin-of-conservatism overlay on the calibrated grade PDs."""
    out = g[["grade", "n", "avg_score", "predicted_pd", "observed_rate"]].copy()
    out["moc_add"] = MOC_RELATIVE * out["predicted_pd"]           # additive overlay
    out["pd_post_moc"] = apply_pd_floor(out["predicted_pd"] + out["moc_add"])  # +floor
    # Sensitivity only (APG 113 para 114): exposure-weighted view would go here; this
    # book has no exposure per borrower, so we report count-weighted PD as the basis.
    for c in ["predicted_pd", "observed_rate", "moc_add", "pd_post_moc"]:
        out[c] = out[c].round(6)
    out["avg_score"] = out["avg_score"].round(1)
    return out.rename(columns={"predicted_pd": "pd_pre_moc"})


def main():
    df, g = _grade_table()

    cal = build_calibration_test(df, g)
    cal.to_csv(SC / "13_calibration_test.csv", index=False)
    hl = cal.attrs["hl"]
    print("Saved -> output/scorecard_outputs/13_calibration_test.csv")
    print("  per-grade binomial flags:", dict(cal[cal.grade.str.startswith("G")]
                                               .set_index("grade")["flag"]))
    print("  Hosmer-Lemeshow chi2=%.2f dof=%d p=%.4f (independence caveat applies)"
          % (hl["chi2"], hl["dof"], hl["p_value"]))

    moc = build_moc_overlay(g)
    moc.to_csv(SC / "14_pd_moc_overlay.csv", index=False)
    print("Saved -> output/scorecard_outputs/14_pd_moc_overlay.csv")
    print("  PD floor = %.4f (5 bps); MoC = +%.0f%% relative, additive."
          % (PD_FLOOR, MOC_RELATIVE * 100))


if __name__ == "__main__":
    main()
