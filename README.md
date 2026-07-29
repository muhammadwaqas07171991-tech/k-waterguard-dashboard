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
- Download pages for latest daily CSVs, historical annual station datasets, station metadata, and cyanobacteria support datasets.
- Historical cleaning summaries, annual trend plots, Mann-Kendall statistics, and Sen slope estimates.
- Algal bloom screening using measured harmful cyanobacteria cell counts, Korean alert thresholds, and watershed-based spatial maps.
- Watershed and lake/reservoir focus tables for algal-bloom risk interpretation.
- Spatial maps using a consistent white, Korean blue, Korean red, and coolwarm visual style.

## Repository Structure

```text
.
├── ai_water_guard_agent/
│   ├── AI_Water_Guard_Agent.py
│   ├── dashboard_static_data/
│   │   ├── historical_annual_station_measurements.csv
│   │   ├── south_korea_water_quality_station_metadata.csv
│   │   └── download_manifest.json
│   ├── algal_bloom_data/
│   │   ├── cyanobacteria_station_cells_per_ml.csv
│   │   ├── harmful_cyanobacteria_lakewide_cells_per_ml.csv
│   │   └── namgang_station_latlon.csv
│   ├── watershed_shapes/korea_major_subbasins/
│   ├── HSPF_Algae_Bloom_SKorea/05_analysis/algae_scenarios/
│   ├── ctprvn.shp / ctprvn.shx / ctprvn.dbf
│   ├── Kwater.png
│   └── KwGAI logo.png
├── .github/workflows/update-dashboard-pages.yml
├── requirements.txt
└── social-preview.png
```

Generated pages, plots, daily records, logs, caches, and local `water_quality_data/` outputs are intentionally not committed. GitHub Actions rebuilds the deployable site automatically.

## Daily Automation

The dashboard is rebuilt by GitHub Actions:

- On every push to `main`
- Once per day at `00:07 UTC` using Korea time settings
- Manually through `workflow_dispatch`

The workflow verifies that historical data, harmful cyanobacteria CSVs, station coordinates, watershed shapefiles, and algae scenario support files are present before deployment. If required support files are missing, the build fails instead of publishing empty trend or algal-bloom pages.

## Local Build

```powershell
python -m pip install -r requirements.txt
python ai_water_guard_agent/AI_Water_Guard_Agent.py
```

The generated website bundle is written to:

```text
water_quality_data/google_site_dashboard/
```

## Maintainer Notes

- Keep source files and support datasets inside `ai_water_guard_agent/`.
- Do not commit generated HTML, generated PNG plots, daily run CSVs, logs, `.env`, or `water_quality_data/`.
- Historical support data should remain in `ai_water_guard_agent/dashboard_static_data/`.
- Harmful cyanobacteria data should remain in `ai_water_guard_agent/algal_bloom_data/`.
- Watershed shapefiles should remain in `ai_water_guard_agent/watershed_shapes/`.
- Algal-bloom scenario support files should remain in `ai_water_guard_agent/HSPF_Algae_Bloom_SKorea/05_analysis/algae_scenarios/`.
- The visual system is defined inside `ai_water_guard_agent/AI_Water_Guard_Agent.py` so each daily build produces consistent pages.
- `social-preview.png` is prepared for the GitHub repository Social preview setting.
- Issue templates and pull request templates are stored in `.github/`.
