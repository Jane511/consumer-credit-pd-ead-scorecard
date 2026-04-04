# Advanced PD Scorecard Notebooks

These notebooks extend the earlier PD scorecard build and validation workflow.

## Included notebooks

1. `03_Home_Credit_PD_Scorecard_Advanced_Monitoring_and_Stability.ipynb`
   - monotonic manual bin review
   - PSI by score band
   - reject inference discussion
   - time-based validation split
   - calibration to long-run / through-the-cycle PD
   - score-to-grade mapping with portfolio default benchmarks

2. `04_Home_Credit_PD_Scorecard_Model_Risk_and_Portfolio_Governance.ipynb`
   - model limitations
   - monitoring thresholds
   - challenger model framing
   - scorecard policy usage
   - override framework note
   - redevelopment triggers
   - portfolio-ready governance write-up

## Suggested order

Run these after:

- `01_Home_Credit_PD_Scorecard_Build.ipynb`
- `02_Home_Credit_PD_Scorecard_Validation_and_Business_Use.ipynb`

## Notes

- These notebooks are written in portfolio style, with extra markdown explanation.
- You may need to adjust file paths and column names to match your local project outputs.
- Some sections are intentionally discussion-led because they are designed to strengthen interview and GitHub presentation, not only model fit.