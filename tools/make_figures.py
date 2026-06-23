"""
tools/make_figures.py — regenerate the README charts for this repo.

Every figure is built from the committed scorecard outputs in outputs/tables/ (aggregated
results only — bad rates, IV, calibration buckets; never raw borrower records), so
the charts regenerate reproducibly with:

    python tools/make_figures.py

Outputs PNGs into outputs/charts/.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SC = ROOT / "outputs" / "tables" / "scorecard_outputs"
FIG = ROOT / "outputs" / "charts"
FIG.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130,
    "font.size": 13, "axes.titlesize": 15, "axes.titleweight": "bold",
    "axes.labelsize": 13, "axes.grid": True, "grid.alpha": 0.25,
    "axes.spines.top": False, "axes.spines.right": False,
})
GOOD, BAD, ACCENT = "#2166ac", "#b2182b", "#4d4d4d"


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / name)
    plt.close(fig)
    print("wrote", FIG / name)


# 1. Rank-ordering — bad rate by score decile (discrimination) ---------------
dec = pd.read_csv(SC / "09_decile_table.csv").sort_values("avg_score").reset_index(drop=True)
fig, ax = plt.subplots(figsize=(7.2, 4.6))
bars = ax.bar(range(len(dec)), dec.bad_rate * 100,
              color=plt.cm.RdYlGn([i / (len(dec) - 1) for i in range(len(dec))]),
              width=0.78, edgecolor="white")
ax.set_xticks(range(len(dec)))
ax.set_xticklabels([f"{s:.0f}" for s in dec.avg_score], rotation=0, fontsize=10)
ax.set_xlabel("score decile (avg score — low = riskier → high = safer)")
ax.set_ylabel("actual default (bad) rate (%)")
ax.set_title("The scorecard ranks risk: bad rate falls as score rises")
for b, v in zip(bars, dec.bad_rate * 100):
    ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.1f}", ha="center", va="bottom", fontsize=9)
save(fig, "bad_rate_by_score_decile.png")

# 2. Calibration — predicted vs observed PD by bucket ------------------------
cal = pd.read_csv(SC / "11_calibration_table.csv").reset_index(drop=True)
fig, ax = plt.subplots(figsize=(6.2, 6.0))
lim = max(cal.avg_predicted_pd.max(), cal.observed_bad_rate.max()) * 100 * 1.05
ax.plot([0, lim], [0, lim], "--", color=ACCENT, linewidth=1, label="perfect calibration")
ax.scatter(cal.avg_predicted_pd * 100, cal.observed_bad_rate * 100,
           s=90, color=BAD, zorder=3, label="PD buckets")
ax.set_xlabel("predicted PD (%)")
ax.set_ylabel("observed default rate (%)")
ax.set_title("Calibration: predicted PD vs reality")
ax.set_xlim(0, lim); ax.set_ylim(0, lim)
ax.legend(frameon=False, loc="upper left")
ax.set_aspect("equal")
save(fig, "pd_calibration.png")

# 3. Top predictors by Information Value -------------------------------------
iv = pd.read_csv(SC / "01_iv_summary.csv").sort_values("iv").tail(10)
fig, ax = plt.subplots(figsize=(7.6, 4.8))
ax.barh(iv.feature, iv.iv, color=GOOD, edgecolor="white")
for y, v in enumerate(iv.iv):
    ax.text(v, y, f" {v:.2f}", va="center", fontsize=10)
ax.set_xlabel("Information Value (predictive strength)")
ax.set_title("Top predictors of default by Information Value")
ax.grid(axis="y", alpha=0)
save(fig, "top_predictors_by_iv.png")

# 4. Score band -> policy decision -------------------------------------------
pol = pd.read_csv(SC / "12_policy_table.csv").sort_values("avg_score")
band_color = {"A": "#1a9850", "B": "#66bd63", "C": "#fee08b", "D": "#f46d43", "E": "#a50026"}
fig, ax = plt.subplots(figsize=(7.0, 4.6))
bars = ax.bar(pol.score_band, pol.bad_rate * 100,
              color=[band_color.get(b, ACCENT) for b in pol.score_band],
              width=0.66, edgecolor="white")
for b, v, n in zip(bars, pol.bad_rate * 100, pol.observations):
    ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.1f}%", ha="center", va="bottom", fontweight="bold")
ax.set_xlabel("score band (A = best → E = worst)")
ax.set_ylabel("default (bad) rate (%)")
ax.set_title("Score bands drive the lending decision")
save(fig, "score_band_policy.png")

# 5. Expected Loss by rating grade -------------------------------------------
el = pd.read_csv(SC / "19_el_summary_by_grade.csv")
elg = el[el.grade != "PORTFOLIO"].copy()
fig, ax = plt.subplots(figsize=(7.4, 4.6))
bars = ax.bar(elg.grade, elg.total_expected_loss / 1e6,
              color=plt.cm.RdYlGn_r([i / (len(elg) - 1) for i in range(len(elg))]),
              width=0.74, edgecolor="white")
for b, bps in zip(bars, elg.el_rate_bps):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{bps:.0f}bps",
            ha="center", va="bottom", fontsize=9)
ax.set_xlabel("rating grade (G1 = riskiest → G8 = safest)")
ax.set_ylabel("expected loss ($m)")
ax.set_title("Expected Loss by grade (EL = PD × LGD × EAD)")
save(fig, "el_by_grade.png")

# 6. Satellite stress — base vs stressed PD by grade -------------------------
ST = ROOT / "stress_test" / "outputs"
sp = ST / "tables" / "scenario_stressed_pd_by_grade.csv"
if sp.exists():
    SFIG = ST / "charts"
    SFIG.mkdir(parents=True, exist_ok=True)
    s = pd.read_csv(sp)
    base = s[s.scenario == "baseline"].set_index("grade")["base_pd"]
    mild = s[s.scenario == "mild recession"].set_index("grade")["stressed_pd"]
    sev = s[s.scenario == "severe recession"].set_index("grade")["stressed_pd"]
    order = list(base.index)
    x = range(len(order))
    fig, ax = plt.subplots(figsize=(7.8, 4.8))
    ax.plot(x, [base[g] * 100 for g in order], "-o", color=GOOD, label="baseline")
    ax.plot(x, [mild[g] * 100 for g in order], "-o", color="#f4a020", label="mild recession")
    ax.plot(x, [sev[g] * 100 for g in order], "-o", color=BAD, label="severe recession")
    ax.set_xticks(list(x)); ax.set_xticklabels(order)
    ax.set_xlabel("rating grade (G1 = riskiest → G8 = safest)")
    ax.set_ylabel("PD (%)")
    ax.set_title("Satellite macro stress: stressed PD by grade")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(SFIG / "stressed_pd_by_grade.png")
    plt.close(fig)
    print("wrote", SFIG / "stressed_pd_by_grade.png")

print("\nAll figures written to", FIG)
