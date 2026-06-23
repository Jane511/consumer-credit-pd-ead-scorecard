"""
tools/make_grade_pd_moc_floor.py — combined grade PD + MoC + floor master-scale table.

Closes the Freddie parity gap `03e_grade_pd_moc_floor.csv`: a single per-grade table that
walks long-run PD -> margin of conservatism -> ratchet (revise-upward) -> regulatory floor,
producing the FINAL capital PD per grade that feeds Expected Loss. Pure aggregate transform of
two already-committed tables (no raw data):

    python tools/make_grade_pd_moc_floor.py

Reads   : 13_calibration_test.csv (long-run PD, observed rate, calibration flag)
          14_pd_moc_overlay.csv   (MoC add-on, post-MoC PD)
Writes  : 18_grade_pd_moc_floor.csv

Framework: APS 113 Att D PD para 2-3 (count-weighted long-run); CRE36.67 (MoC);
APS 113 Att D Validation para 6 (revise UP where realised > expected -> the ratchet rule);
APS 113 Att B para 1 (5 bps floor). `pd_final` is the regulatory PD used for EL/capital, so EL
and the master scale reconcile (PDR2-1).
"""
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.calibration import apply_pd_floor

SC = ROOT / "outputs" / "tables" / "scorecard_outputs"


def main():
    cal = pd.read_csv(SC / "13_calibration_test.csv")
    cal = cal[cal["grade"].str.startswith("G")].copy()       # drop the OVERALL_HL row
    moc = pd.read_csv(SC / "14_pd_moc_overlay.csv")

    m = cal.merge(moc[["grade", "moc_add", "pd_post_moc"]], on="grade", how="left")

    out = pd.DataFrame({
        "grade": m["grade"],
        "long_run_pd": m["predicted_pd"].round(6),          # count-weighted long-run PD
        "moc_add": m["moc_add"].round(6),                   # margin of conservatism
        "pd_after_moc": m["pd_post_moc"].round(6),
        "observed_rate": m["observed_rate"].round(6),
        "flag": m["flag"],                                  # binomial traffic-light
        # Ratchet (Validation para 6): if realised > post-MoC estimate, lift the PD to it.
        "pd_revised": m[["pd_post_moc", "observed_rate"]].max(axis=1).round(6),
    })
    # Final capital PD = ratcheted PD with the 5 bps floor applied (does not bind here).
    out["pd_final"] = apply_pd_floor(out["pd_revised"]).round(6)
    out = out.sort_values("grade").reset_index(drop=True)

    out.to_csv(SC / "18_grade_pd_moc_floor.csv", index=False)
    print("Saved -> outputs/tables/scorecard_outputs/18_grade_pd_moc_floor.csv")
    binds = (out["pd_revised"] > out["pd_after_moc"]).sum()
    print("  ratchet lifted %d/%d grades to the observed rate; 5 bps floor binds on %d."
          % (binds, len(out), int((out["pd_final"] > out["pd_revised"]).sum())))


if __name__ == "__main__":
    main()
