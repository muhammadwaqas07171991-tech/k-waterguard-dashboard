# Literature-Based Algae Scenario Matrix

These scenarios are prepared for the final calibrated HSPF `HEAT/OXRX/NUTR/PLNK` model. A preliminary 2010 HSPF PLNK scenario set has now been run for Reach 6/Jinyang Lake using the currently runnable monthly-chunk workflow.

## Calibration Criteria

Use Moriasi et al. watershed-model guidance as the minimum hydrology screen:

- streamflow `NSE > 0.50`;
- `RSR <= 0.70`;
- streamflow `PBIAS` within about `+/-25%`.

The current seven-reach HYDR model does not yet meet this standard.

## Scenario Set

| ID | Scenario | HSPF Lever | Literature/Study Reason |
| --- | --- | --- | --- |
| S0 | Baseline calibrated 2010-2025 | calibrated HYDR/HEAT/OXRX/NUTR/PLNK | Reference condition for all comparisons |
| S1 | TP load reduction 20% | reduce point/nonpoint PO4/TP inputs | Namgang Chl-a study reports TP as a major algal-growth factor |
| S2 | TP load reduction 40% | reduce point/nonpoint PO4/TP inputs | Strong nutrient-management case |
| S3 | TN and TP reduction 40% | reduce N and P inputs | Lake/reservoir literature supports N/P co-limitation under high bloom states |
| S4 | Point-source nutrient reduction 50% | reduce wastewater/point-source N/P | Management scenario for WWTP upgrades |
| S5 | Agricultural/nonpoint nutrient reduction 30% | reduce cropland PQUAL/NQUAL loads | Tests watershed BMP influence |
| S6 | Warming +2 C | increase air/water temperature forcing | Namgang Chl-a has positive association with water temperature |
| S7 | Warming +2 C plus TP reduction 40% | combine S2 and S6 | Tests whether nutrient control offsets warming stress |
| S8 | Increased flushing/reduced residence time | dam operation/routing scenario | Reservoir bloom literature identifies residence time/flushing as bloom control |
| S9 | Drought/low-flow bloom risk | lower inflow/increase residence time | Tests high-risk bloom conditions |

## Current HSPF Scenario Status

Observed-data scenario screening has been run in this folder. HSPF PLNK scenario execution has also been completed for 2010 baseline, `tp20`, and `tnp40` cases.

- HSPF hourly output: `04_hspf_model/outputs/namgang_plnk_2010_scenario_hourly_chla.csv`
- Annual scenario summary: `05_analysis/algae_scenarios/hspf_plnk_2010_scenario_summary.csv`
- Monthly scenario summary: `05_analysis/algae_scenarios/hspf_plnk_2010_scenario_monthly.csv`
- Scenario report: `05_analysis/algae_scenarios/HSPF_PLNK_2010_SCENARIO_RESULTS.md`

The current HSPF scenario outputs should be treated as preliminary sensitivity results, not final management forecasts, because 2010 bloom-season Chl-a calibration remains weak and upstream hydrology/source-load calibration still needs improvement.
