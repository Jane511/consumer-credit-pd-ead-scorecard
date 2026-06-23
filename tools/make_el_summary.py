"""
tools/make_el_summary.py — Expected Loss by rating grade, and IFRS 9 / AASB 9 staging.

Closes two Freddie parity gaps: `06_el_summary_by_grade.csv` (regulatory EL by grade) and
`06_expected_loss.csv` (IFRS 9 three-stage ECL). Both rebuild from committed aggregates +
the scored test file (gitignored, on disk) into committed tables:

    python tools/make_el_summary.py

Outputs (into outputs/tables/scorecard_outputs/):
  19_el_summary_by_grade.csv — per-grade loans, EAD, avg PD, avg LGD, total EL, EL-rate bps,
                               plus a PORTFOLIO total. Uses the FINAL capital PD per grade
                               (18_grade_pd_moc_floor.csv) so EL reconciles to the master
                               scale and to the stress-test baseline (PDR2-1 / APS 113 Att B EL).
  20_ifrs9_staging.csv       — Stage 1/2/3 counts + 12-month vs reported (lifetime) ECL.

EAD/LGD inputs come from outputs/tables/ead_summary.csv (the revolving-CCF segment work in
notebook 08). Because this Kaggle book has no per-grade card exposure, a single portfolio-average
onset EAD is applied to every grade — a documented simplification consistent with the EAD/EL layer
being a methodology demonstration (see Limitations); the grade-level RANKING is driven entirely by
PD, which is the point of the table.

Framework: EL = PD x LGD x EAD (CRE35.3); same PD as capital (APS 113 Att B EL para 1);
IFRS 9 / AASB 9 three-stage ECL with SICR (BCBS Dec 2015; APG 220 paras 106-108) — IFRS 9 LGD is
the UNBIASED best estimate (no downturn add-on, no MoC), per the consolidated reference Section 5.
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.calibration import apply_pd_floor

SC = ROOT / "outputs" / "tables" / "scorecard_outputs"
TAB = ROOT / "outputs" / "tables"

# IFRS 9 staging proxies (documented — a single snapshot has no origination PD or DPD field):
SICR_PD_MULT = 2.0    # Stage 2 = non-defaulted accounts whose 12m PD >= 2x the portfolio PD
LIFETIME_MULT = 3.0   # Stage 2 reported ECL = 12m EL x behavioural-life proxy (unsecured
                      # revolving life is shorter than a mortgage; Freddie used 4 for mortgages).
                      # Stage 3 uses best-estimate-of-EL (LGD x EAD), default having occurred.


def _ead_lgd():
    s = pd.read_csv(TAB / "ead_summary.csv").set_index("metric")["value"]
    return float(s["EAD_onset_primary_avg"]), float(s["LGD_base"])


# ---------------------------------------------------------------------------------------
# 19_el_summary_by_grade.csv
# ---------------------------------------------------------------------------------------
def build_el_by_grade():
    pdf = pd.read_csv(SC / "18_grade_pd_moc_floor.csv")        # final capital PD per grade
    ead_avg, lgd = _ead_lgd()

    g = pdf[["grade"]].copy()
    n = pd.read_csv(SC / "14_pd_moc_overlay.csv").set_index("grade")["n"]
    g["loans"] = g["grade"].map(n).astype(int)
    g["total_ead"] = (g["loans"] * ead_avg).round(2)
    g["avg_pd"] = pdf["pd_final"].round(6)
    g["avg_lgd"] = round(lgd, 4)
    g["total_expected_loss"] = (g["avg_pd"] * g["avg_lgd"] * g["total_ead"]).round(2)
    g["el_rate_bps"] = (g["total_expected_loss"] / g["total_ead"] * 1e4).round(1)

    port = {
        "grade": "PORTFOLIO",
        "loans": int(g["loans"].sum()),
        "total_ead": round(float(g["total_ead"].sum()), 2),
        "avg_pd": round(float((g["avg_pd"] * g["loans"]).sum() / g["loans"].sum()), 6),
        "avg_lgd": round(lgd, 4),
        "total_expected_loss": round(float(g["total_expected_loss"].sum()), 2),
        "el_rate_bps": round(float(g["total_expected_loss"].sum()
                                   / g["total_ead"].sum() * 1e4), 1),
    }
    out = pd.concat([g, pd.DataFrame([port])], ignore_index=True)
    out.to_csv(SC / "19_el_summary_by_grade.csv", index=False)
    print("Saved -> outputs/tables/scorecard_outputs/19_el_summary_by_grade.csv")
    print("  portfolio EL = $%.1fm  (avg PD %.4f x LGD %.2f x EAD $%.0f x %d loans)"
          % (port["total_expected_loss"] / 1e6, port["avg_pd"], lgd, ead_avg, port["loans"]))
    return port["total_expected_loss"]


# ---------------------------------------------------------------------------------------
# 20_ifrs9_staging.csv
# ---------------------------------------------------------------------------------------
def build_ifrs9_staging():
    df = pd.read_csv(SC / "06_test_scored.csv", usecols=["pd_pred", "TARGET"]).dropna()
    cs = pd.read_csv(SC / "calibration_summary.csv").iloc[0]
    factor = float(cs["calibrated_mean_pd"]) / float(cs["raw_mean_pd"])
    df["pd_cal"] = apply_pd_floor(df["pd_pred"] * factor)
    ead_avg, lgd = _ead_lgd()
    port_pd = float(df["pd_cal"].mean())

    # Stage assignment (proxies documented above):
    #   3 = credit-impaired      -> TARGET == 1 (the default proxy flag)
    #   2 = SICR (not defaulted) -> 12m PD >= SICR_PD_MULT x portfolio PD
    #   1 = performing           -> everything else
    stage = np.where(df["TARGET"] == 1, 3,
                     np.where(df["pd_cal"] >= SICR_PD_MULT * port_pd, 2, 1))
    df["stage"] = stage

    rows = []
    for s, label in [(1, "1 (performing)"), (2, "2 (SICR)"), (3, "3 (credit-impaired)")]:
        sub = df[df["stage"] == s]
        loans = int(len(sub))
        total_ead = loans * ead_avg
        avg_pd = float(sub["pd_cal"].mean()) if loans else 0.0
        el_12m = avg_pd * lgd * total_ead
        if s == 1:
            reported = el_12m                       # 12-month ECL (performing)
        elif s == 2:
            reported = el_12m * LIFETIME_MULT        # lifetime ECL proxy (SICR)
        else:
            reported = lgd * total_ead               # S3: default occurred -> best-estimate
                                                     # of EL (PD=1), not mechanical 12m PD x LGD
                                                     # x EAD (CRE36.86 / Att D EL para 1)
        rows.append({
            "ifrs9_stage": label,
            "loans": loans,
            "avg_pd": round(avg_pd, 6),
            "avg_lgd": round(lgd, 4),                 # unbiased best estimate (no downturn)
            "total_ead": round(total_ead, 2),
            "expected_loss_12m": round(el_12m, 2),
            "reported_ecl": round(reported, 2),
        })
    out = pd.DataFrame(rows)
    out.to_csv(SC / "20_ifrs9_staging.csv", index=False)
    print("Saved -> outputs/tables/scorecard_outputs/20_ifrs9_staging.csv")
    print("  stage mix: S1 %d / S2 %d / S3 %d ; reported ECL = $%.2fm "
          "(S2 lifetime x%.0f; S3 best-estimate LGDxEAD)"
          % (rows[0]["loans"], rows[1]["loans"], rows[2]["loans"],
             out["reported_ecl"].sum() / 1e6, LIFETIME_MULT))


def main():
    build_el_by_grade()
    build_ifrs9_staging()


if __name__ == "__main__":
    main()
