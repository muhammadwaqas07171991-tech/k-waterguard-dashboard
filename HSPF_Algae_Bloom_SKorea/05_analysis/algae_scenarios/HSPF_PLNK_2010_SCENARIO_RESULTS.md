# HSPF PLNK 2010 Scenario Results

These are HSPF `PLNK` scenario runs using the currently runnable Reach 6 algae setup. Chlorophyll-a is estimated from `PHYTO` using the 2010 fitted baseline conversion from `PLNK_2010_CHLA_CALIBRATION.md`.

Scenario basis: TP reduction and combined TN/TP reduction are included because the Namgang/Jinyang literature and lake nutrient guidance identify phosphorus, nutrients, temperature, oxygen, and residence time as important bloom controls.

- Hourly scenario output: `04_hspf_model/outputs/namgang_plnk_2010_scenario_hourly_chla.csv`
- Annual summary CSV: `05_analysis/algae_scenarios/hspf_plnk_2010_scenario_summary.csv`
- Monthly summary CSV: `05_analysis/algae_scenarios/hspf_plnk_2010_scenario_monthly.csv`

## Annual Summary

| scenario | rows | mean_chla_ug_l | p90_chla_ug_l | p95_chla_ug_l | max_chla_ug_l | hours_gt_10ug_l | hours_gt_25ug_l | mean_no3_mg_l | mean_tam_mg_l | mean_po4_mg_l | relative_mean_vs_baseline | percent_mean_change | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 8760 | 5.26155 | 18.1913 | 21.6417 | 27.2827 | 2074 | 36 | 0.65881 | 0.00666732 | 0.00133636 | 1 | 0 | 2010 calibrated PLNK baseline using observed monthly WQ boundary loads |
| tnp40 | 8760 | 4.7373 | 17.9344 | 21.3408 | 26.1703 | 1785 | 21 | 0.585139 | 0.0053857 | 0.00120068 | 0.900362 | -9.96376 | HSPF PLNK scenario with 40% TN/NO3/NH3 and TP/PO4 load reduction |
| tp20 | 8760 | 4.87669 | 17.9725 | 21.4314 | 26.7374 | 1874 | 24 | 0.659369 | 0.00610192 | 0.00122014 | 0.926856 | -7.31442 | HSPF PLNK scenario with 20% TP/PO4 load reduction |

## Monthly Summary

| scenario | month | mean_chla_ug_l | p95_chla_ug_l | hours_gt_10ug_l | hours_gt_25ug_l | baseline_mean_chla_ug_l | percent_mean_change |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 2010-01-01 | 4.14919 | 21.5011 | 140 | 0 | 4.14919 | 0 |
| baseline | 2010-02-01 | 4.10618 | 20.8625 | 126 | 0 | 4.10618 | 0 |
| baseline | 2010-03-01 | 4.65171 | 21.2683 | 166 | 0 | 4.65171 | 0 |
| baseline | 2010-04-01 | 3.75837 | 19.4434 | 129 | 0 | 3.75837 | 0 |
| baseline | 2010-05-01 | 3.33116 | 19.3527 | 107 | 2 | 3.33116 | 0 |
| baseline | 2010-06-01 | 3.39494 | 19.6717 | 106 | 3 | 3.39494 | 0 |
| baseline | 2010-07-01 | 7.26409 | 22.1782 | 245 | 4 | 7.26409 | 0 |
| baseline | 2010-08-01 | 3.8364 | 19.8433 | 114 | 9 | 3.8364 | 0 |
| baseline | 2010-09-01 | 13.9107 | 23.4712 | 533 | 13 | 13.9107 | 0 |
| baseline | 2010-10-01 | 6.53177 | 21.8173 | 136 | 3 | 6.53177 | 0 |
| baseline | 2010-11-01 | 4.10992 | 21.5901 | 133 | 2 | 4.10992 | 0 |
| baseline | 2010-12-01 | 4.11544 | 20.3574 | 139 | 0 | 4.11544 | 0 |
| tnp40 | 2010-01-01 | 4.06718 | 21.0991 | 138 | 0 | 4.14919 | -1.97659 |
| tnp40 | 2010-02-01 | 4.09065 | 20.7805 | 126 | 0 | 4.10618 | -0.378389 |
| tnp40 | 2010-03-01 | 4.60564 | 21.206 | 165 | 0 | 4.65171 | -0.99038 |
| tnp40 | 2010-04-01 | 3.65091 | 19.0201 | 125 | 0 | 3.75837 | -2.85913 |
| tnp40 | 2010-05-01 | 3.29223 | 19.3482 | 107 | 2 | 3.33116 | -1.16861 |
| tnp40 | 2010-06-01 | 3.36929 | 19.666 | 105 | 2 | 3.39494 | -0.755499 |
| tnp40 | 2010-07-01 | 7.07999 | 21.8123 | 235 | 3 | 7.26409 | -2.53446 |
| tnp40 | 2010-08-01 | 3.61064 | 19.7208 | 113 | 7 | 3.8364 | -5.88463 |
| tnp40 | 2010-09-01 | 10.6675 | 22.8741 | 273 | 6 | 13.9107 | -23.3147 |
| tnp40 | 2010-10-01 | 4.3762 | 21.0758 | 129 | 0 | 6.53177 | -33.0013 |
| tnp40 | 2010-11-01 | 4.02525 | 21.5123 | 132 | 1 | 4.10992 | -2.05998 |
| tnp40 | 2010-12-01 | 4.03869 | 20.115 | 137 | 0 | 4.11544 | -1.86497 |
| tp20 | 2010-01-01 | 4.06895 | 21.1026 | 138 | 0 | 4.14919 | -1.93374 |
| tp20 | 2010-02-01 | 4.09479 | 20.8016 | 126 | 0 | 4.10618 | -0.277395 |
| tp20 | 2010-03-01 | 4.63611 | 21.2363 | 166 | 0 | 4.65171 | -0.335264 |
| tp20 | 2010-04-01 | 3.65417 | 19.0292 | 125 | 0 | 3.75837 | -2.77248 |
| tp20 | 2010-05-01 | 3.29378 | 19.3512 | 107 | 2 | 3.33116 | -1.12215 |
| tp20 | 2010-06-01 | 3.37017 | 19.6662 | 105 | 2 | 3.39494 | -0.72962 |
| tp20 | 2010-07-01 | 7.08537 | 21.8125 | 235 | 3 | 7.26409 | -2.46033 |
| tp20 | 2010-08-01 | 3.62499 | 19.7283 | 113 | 7 | 3.8364 | -5.51076 |
| tp20 | 2010-09-01 | 11.7665 | 22.9675 | 358 | 8 | 13.9107 | -15.4141 |
| tp20 | 2010-10-01 | 4.89262 | 21.3021 | 132 | 1 | 6.53177 | -25.095 |
| tp20 | 2010-11-01 | 4.02525 | 21.5123 | 132 | 1 | 4.10992 | -2.05999 |
| tp20 | 2010-12-01 | 4.03869 | 20.115 | 137 | 0 | 4.11544 | -1.86494 |

## Interpretation

The current PLNK model is useful for controlled sensitivity testing, but these should be treated as preliminary scenario responses until bloom-season hydrology, nutrient speciation, and PLNK parameters are further calibrated.
