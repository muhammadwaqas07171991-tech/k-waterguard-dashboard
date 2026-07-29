# K-WaterGuard AI Dashboard

K-WaterGuard AI is an automated South Korea water-quality intelligence dashboard for farmers, watershed managers, lake and reservoir operators, researchers, and environmental decision makers.

The dashboard combines latest daily monitoring records, corrected station coverage, historical station archives, Mann-Kendall trend screening, Sen slope summaries, spatial maps, downloadable datasets, and Korean algal-bloom alert screening into one deployable GitHub Pages site.

Live dashboard:

https://muhammadwaqas07171991-tech.github.io/k-waterguard-dashboard/

Project page:

https://sites.google.com/view/rwer/k-waterguard-ai

## What The Dashboard Provides

- Daily South Korea water-quality status with station, city, province, and watershed summaries.
- Corrected station counts using station identity and coordinate de-duplication.
- Download pages for latest daily CSVs, historical annual station datasets, and station metadata.
- Historical cleaning summaries, annual trend plots, Mann-Kendall statistics, and Sen slope estimates.
- Algal bloom screening using Korean alert thresholds and chlorophyll-a proxy signals where cyanobacteria counts are unavailable.
- Watershed and lake/reservoir focus tables for algal-bloom risk interpretation.
- Spatial maps using a consistent white, Korean blue, Korean red, and coolwarm visual style.

## Repository Structure

```text
.
├── Claude.py
├── requirements.txt
├── .github/workflows/update-dashboard-pages.yml
├── dashboard_static_data/
│   ├── historical_annual_station_measurements.csv
│   ├── south_korea_water_quality_station_metadata.csv
│   └── download_manifest.json
├── HSPF_Algae_Bloom_SKorea/05_analysis/algae_scenarios/
│   ├── observed_chla_scenario_screening.csv
│   ├── hspf_plnk_2010_scenario_summary.csv
│   └── supporting scenario summaries
├── ctprvn.shp / ctprvn.shx / ctprvn.dbf
├── Kwater.png
└── KwGAI logo.png
```

Generated pages, plots, daily records, logs, caches, and local `water_quality_data/` outputs are intentionally not committed. GitHub Actions rebuilds the deployable site automatically.

## Daily Automation

The dashboard is rebuilt by GitHub Actions:

- On every push to `main`
- Once per day at `00:07 UTC` using Korea time settings
- Manually through `workflow_dispatch`

The workflow verifies that historical and algae support datasets are present before deployment. If required support files are missing, the build fails instead of publishing empty trend or algal-bloom pages.

## Local Build

```powershell
python -m pip install -r requirements.txt
python Claude.py
```

The generated website bundle is written to:

```text
water_quality_data/google_site_dashboard/
```

## Maintainer Notes

- Keep source files and support datasets in the repository.
- Do not commit generated HTML, generated PNG plots, daily run CSVs, logs, `.env`, or `water_quality_data/`.
- Historical support data should remain in `dashboard_static_data/`.
- Algal-bloom scenario support files should remain in `HSPF_Algae_Bloom_SKorea/05_analysis/algae_scenarios/`.
- The visual system is defined inside `Claude.py` so each daily build produces consistent pages.

