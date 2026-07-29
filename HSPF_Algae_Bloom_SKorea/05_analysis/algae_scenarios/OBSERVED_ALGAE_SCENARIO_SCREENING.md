# Observed Algae Scenario Screening

This is an observed-data screening analysis for scenario design while the HSPF HYDR/dam routing model is being calibrated. It is not a replacement for calibrated HSPF `PLNK` output.

Scenario summary:

| scenario | mean Chl-a ug/L | P90 Chl-a ug/L | >25 ug/L samples | relative mean |
| --- | ---: | ---: | ---: | ---: |
| baseline_observed_conditions | 4.28 | 6.03 | 0 | 1.000 |
| tp_reduction_20 | 4.09 | 5.67 | 0 | 0.955 |
| tp_reduction_40 | 3.91 | 5.32 | 0 | 0.912 |
| tn_tp_reduction_40 | 3.65 | 5.01 | 0 | 0.853 |
| warming_plus_2c | 4.62 | 6.47 | 0 | 1.078 |
| warming_plus_2c_tp_reduction_40 | 4.22 | 5.72 | 0 | 0.984 |

Use these as scenario priorities for the final HSPF water-quality model:
- phosphorus reduction scenarios first, because Namgang literature identifies TP as a major Chl-a factor;
- combined TN/TP reduction for high-bloom conditions;
- warming sensitivity because water temperature is positively associated with Chl-a;
- flushing/residence-time scenarios only after dam routing is represented correctly.