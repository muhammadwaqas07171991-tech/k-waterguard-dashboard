# K-WaterGuard AI Technical Build Manual

Version: 1.0  
Project file: `Claude.py`  
Target platform: Windows local execution and GitHub Pages public dashboard  
Primary region: South Korea  

## 1. Purpose

K-WaterGuard AI is an agentic water-quality monitoring system. It collects Korean water-quality monitoring data, stores historical CSV records, generates daily plots and spatial maps, builds an interactive dashboard, and prepares a static web bundle for GitHub Pages or Google Sites embedding.

The system is designed as a single Python automation agent with four major responsibilities:

1. Data collection from the Korean public water-quality API.
2. Data cleaning, station/location enrichment, and CSV export.
3. Visualization generation using Matplotlib and Seaborn.
4. Static dashboard generation with optional chatbot integration.

## 2. High-Level Architecture

```text
                         +------------------------------+
                         | Windows Task Scheduler       |
                         | or GitHub Actions Cron       |
                         +---------------+--------------+
                                         |
                                         v
                             +-----------+-----------+
                             | Claude.py Agent       |
                             +-----------+-----------+
                                         |
          +------------------------------+------------------------------+
          |                              |                              |
          v                              v                              v
+---------+---------+          +---------+---------+          +---------+---------+
| Data Collector    |          | Data Manager      |          | Plot Generator   |
| API + WFS Parser  |          | CSV + Archives    |          | Charts + Maps    |
+---------+---------+          +---------+---------+          +---------+---------+
          |                              |                              |
          +------------------------------+------------------------------+
                                         |
                                         v
                             +-----------+-----------+
                             | Dashboard Generator   |
                             | HTML + PWA + Assets   |
                             +-----------+-----------+
                                         |
                         +---------------+---------------+
                         |                               |
                         v                               v
           Local dashboard.html              google_site_dashboard/
                                             for GitHub Pages
```

## 3. Technology Stack

| Layer | Technology |
| --- | --- |
| Runtime | Python 3.11+ recommended |
| HTTP data access | `requests` |
| Data processing | `pandas`, `numpy` |
| Plotting | `matplotlib`, `seaborn` |
| Spatial projection | `pyproj` |
| Scheduling inside Python | `apscheduler` |
| Optional location lookup | `reverse_geocoder` |
| Static deployment | GitHub Pages |
| External scheduler | Windows Task Scheduler or GitHub Actions |

The project also includes a South Korea shapefile:

```text
ctprvn.shp
ctprvn.shx
ctprvn.dbf
```

These files are used by the map plotting code.

## 4. Recommended Project Layout

Current working layout:

```text
AI_Agent_Try/
  Claude.py
  requirements.txt
  run_water_agent.bat
  SETUP_GUIDE.md
  CHATBOT_SETUP_GUIDE.md
  GOOGLE_SITE_DASHBOARD_GUIDE.md
  HOURLY_GOOGLE_SITE_SETUP.md
  Kwater.png
  KwGAI logo.png
  KwGAI logo2.png
  cover.png
  ctprvn.shp
  ctprvn.shx
  ctprvn.dbf
  .github/
    workflows/
      update-dashboard-pages.yml
  water_quality_data/
    water_quality_records.csv
    dashboard.html
    agent_log.txt
    plots/
    location_exports/
    run_archives/
    daily_outputs/
    google_site_dashboard/
```

Recommended cleaner layout for a future refactor:

```text
k-waterguard-ai/
  app/
    config.py
    collector.py
    data_manager.py
    plots.py
    dashboard.py
    agent.py
  assets/
    Kwater.png
    KwGAI logo.png
    cover.png
  maps/
    ctprvn.shp
    ctprvn.shx
    ctprvn.dbf
  scripts/
    run_water_agent.bat
  docs/
    K_WaterGuard_AI_Technical_Manual.md
  .github/
    workflows/
      update-dashboard-pages.yml
  requirements.txt
  README.md
```

The current single-file design is easier for quick execution. The refactored layout is better for long-term maintenance.

## 5. Main Code Modules In `Claude.py`

### 5.1 Dependency Installer

Function:

```python
def ensure_dependencies():
    required_packages = ["requests", "pandas", "matplotlib", "seaborn", "apscheduler", "pyproj"]
    optional_packages = ["reverse_geocoder"]
```

Purpose:

- Checks required Python packages.
- Installs missing packages with `pip`.
- Tries to install optional reverse geocoding support.

Production recommendation: install packages from `requirements.txt` before running the agent, and avoid runtime package installation in locked-down environments.

### 5.2 `Config`

Class:

```python
class Config:
```

Purpose:

- Defines data folders.
- Defines dashboard paths.
- Defines GitHub Pages URL.
- Defines chatbot settings.
- Defines Korean water-quality alert thresholds.
- Defines API endpoint and service key.
- Defines update interval.
- Defines shapefile settings.

Important paths:

```python
DATA_DIR = Path(os.environ.get("WATER_QUALITY_DATA_DIR", str(Path.home() / "water_quality_data")))
CSV_FILE = DATA_DIR / "water_quality_records.csv"
PLOTS_DIR = DATA_DIR / "plots"
DASHBOARD_FILE = DATA_DIR / "dashboard.html"
WORKSPACE_DASHBOARD_FILE = Path(__file__).resolve().parent / "Claude_dashboard.html"
SITE_DASHBOARD_DIR = DATA_DIR / "google_site_dashboard"
```

Important environment variables:

```text
WATER_QUALITY_DATA_DIR
GITHUB_PAGES_BASE_URL
CHATBOT_API_URL
CHATBOT_ENABLED
```

### 5.3 `WaterQualityCollector`

Class:

```python
class WaterQualityCollector:
```

Purpose:

- Calls the Korean water-quality WFS API.
- Parses XML features.
- Extracts station metadata.
- Extracts and converts coordinates.
- Normalizes water-quality parameters.
- Builds a fallback placeholder record if API data is unavailable.

Key methods:

```python
fetch_data()
_fetch_api_data()
_parse_wfs_response(xml_text)
_find_feature_elements(root)
_extract_feature_record(feature)
_extract_coordinates(feature)
_transform_coordinates(x, y)
_infer_location_from_coordinates(record)
_extract_parameter_value(record, column_name)
```

Data source configuration:

```python
WATER_API_URL = "http://apis.data.go.kr/1480523/WaterqualityServices/getIvstgWFS"
WFS_SRS_NAME = "EPSG:5179"
WFS_MAX_FEATURES = 5000
WFS_RESULT_TYPE = "results"
```

Coordinate flow:

```text
API geometry in EPSG:5179
        |
        v
pyproj Transformer
        |
        v
longitude / latitude in EPSG:4326
```

### 5.4 `DataManager`

Class:

```python
class DataManager:
```

Purpose:

- Saves new records to the master CSV.
- Adds date-wise output folders.
- Saves latest run archives.
- Saves location-specific exports.
- Cleans old data based on retention period.
- Provides recent data for plots and dashboards.

Key methods:

```python
save_data(new_records)
_save_location_exports(df)
_save_run_archive(df_new)
_enrich_location_columns(df)
_prepare_export_dataframe(df)
_apply_station_display_numbers(df)
_save_daily_exports(df)
_cleanup_old_data(df)
get_latest_data(days=7)
```

Master output:

```text
water_quality_data/water_quality_records.csv
```

Daily output:

```text
water_quality_data/daily_outputs/YYYY-MM-DD/data/water_quality_records_YYYY-MM-DD.csv
water_quality_data/daily_outputs/YYYY-MM-DD/runs/water_quality_run_YYYYMMDD_HHMMSS_KST.csv
```

### 5.5 `PlotGenerator`

Class:

```python
class PlotGenerator:
```

Purpose:

- Reads recent data.
- Generates summary charts.
- Generates alert boards.
- Generates station coverage maps.
- Generates spatial maps per parameter.

Key methods:

```python
generate_all_plots()
_plot_regional_comparison(df)
_plot_quality_heatmap(df)
_plot_parameter_distributions(df)
_plot_water_quality_signal_board(df)
_plot_alert_hotspot_matrix(df)
_plot_parameter_maps(df)
_plot_station_coverage_map(df)
_plot_quality_summary(df)
```

Expected chart outputs:

```text
quality_summary.png
water_quality_signal_board.png
alert_hotspot_matrix.png
station_coverage_map.png
regional_comparison.png
quality_heatmap.png
distributions.png
*_map_YYYY_MM_DD.png
```

### 5.6 `DashboardGenerator`

Class:

```python
class DashboardGenerator:
```

Purpose:

- Builds the final HTML dashboard.
- Embeds local image/file references.
- Builds public static bundle for GitHub Pages.
- Adds PWA files such as manifest and service worker.
- Adds optional chatbot widget.

Key methods:

```python
generate()
_prepare_dashboard_data(df)
_render_html(all_df, latest_df, latest_station_df, latest_date, alerts_df)
_chatbot_html()
_chatbot_script()
_evaluate_alerts(df)
_parameter_cards(df, alerts_df)
_alert_rows(alerts_df)
_station_rows(df)
_province_rows(df)
_mini_korea_map(latest_station_df, alerts_df)
_write_google_site_bundle(html_text, date_label)
_write_pwa_files(bundle_dir)
```

Dashboard outputs:

```text
water_quality_data/dashboard.html
Claude_dashboard.html
water_quality_data/google_site_dashboard/index.html
```

### 5.7 `WaterQualityAgent`

Class:

```python
class WaterQualityAgent:
```

Purpose:

- Orchestrates one full cycle.
- Can run once or continuously using APScheduler.

Main cycle:

```python
def execute_cycle(self):
    data = self.collector.fetch_data()
    if data:
        self.data_manager.save_data(data)
    self.plot_generator.generate_all_plots()
    self.dashboard_generator.generate()
```

Entry point:

```python
if __name__ == "__main__":
    main()
```

## 6. Build From Scratch

### Step 1: Create the project folder

```powershell
mkdir C:\Users\USER\Desktop\AI_Agent_Try
cd C:\Users\USER\Desktop\AI_Agent_Try
```

### Step 2: Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### Step 3: Create `requirements.txt`

```text
numpy
requests
pandas
matplotlib
seaborn
apscheduler
pyproj
reverse_geocoder
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Step 4: Add required project files

Place these files in the project root:

```text
Claude.py
Kwater.png
KwGAI logo.png
cover.png
ctprvn.shp
ctprvn.shx
ctprvn.dbf
requirements.txt
run_water_agent.bat
```

### Step 5: Configure environment variables

For local Windows PowerShell:

```powershell
$env:WATER_QUALITY_DATA_DIR = "C:\Users\USER\Desktop\AI_Agent_Try\water_quality_data"
$env:GITHUB_PAGES_BASE_URL = "https://YOUR_GITHUB_USERNAME.github.io/k-waterguard-dashboard/"
$env:CHATBOT_ENABLED = "true"
$env:CHATBOT_API_URL = ""
```

To keep the dashboard chatbot hidden:

```powershell
$env:CHATBOT_ENABLED = "false"
```

### Step 6: Run the agent

```powershell
python Claude.py
```

Expected terminal behavior:

```text
Water Quality Data Agent
South Korea
Collecting water quality data from all available API monitoring stations in South Korea...
Generating visualizations and plots...
Process completed successfully!
```

### Step 7: Open generated dashboard

Local dashboard:

```text
water_quality_data/dashboard.html
```

Workspace copy:

```text
Claude_dashboard.html
```

GitHub Pages bundle:

```text
water_quality_data/google_site_dashboard/index.html
```

## 7. Runtime Output Layout

After a successful run, the data folder should look like this:

```text
water_quality_data/
  agent_log.txt
  dashboard.html
  water_quality_records.csv
  plots/
    quality_summary.png
    station_coverage_map.png
    regional_comparison.png
    quality_heatmap.png
    distributions.png
  location_exports/
  run_archives/
    water_quality_run_YYYYMMDD_HHMMSS_KST.csv
  daily_outputs/
    YYYY-MM-DD/
      data/
        water_quality_records_YYYY-MM-DD.csv
      plots/
        quality_summary.png
        station_coverage_map.png
      runs/
        water_quality_run_YYYYMMDD_HHMMSS_KST.csv
  google_site_dashboard/
    index.html
    manifest.webmanifest
    sw.js
    .nojekyll
    assets/
    plots/
    data/
    history/
```

## 8. Data Schema

The exported CSV contains station/location fields, coordinate fields, timestamp fields, source fields, and water-quality parameters.

Core location columns:

```text
date
display_location
location_name
city
district
province
country
station_name
station_code
monitoring_point_id
region
```

Coordinate columns:

```text
latitude
longitude
x
y
```

Water-quality columns:

```text
pH
DO
BOD
COD
SS
TN
TP
temperature
EC
Turbidity
Chlorophyll_a
Fecal_Coliform
E_coli
Alkalinity
Hardness
Ammonia_N
Nitrate_N
Phosphate_P
```

## 9. Alert Rules

Alert rules are defined in `Config.WATER_QUALITY_ALERT_RULES`.

Example:

```python
WATER_QUALITY_ALERT_RULES = {
    "pH": {
        "min": 6.5,
        "max": 8.5,
        "unit": "",
        "severity": "critical",
        "basis": "Korean river/lake living-environment pH range",
    },
    "DO": {
        "min": 5.0,
        "unit": "mg/L",
        "severity": "critical",
        "basis": "Dissolved oxygen lower-bound screening target",
    },
}
```

Rule logic:

```text
If min exists and value < min: alert
If max exists and value > max: alert
If pH has both min and max: alert outside the range
```

## 10. Dashboard Layout

The dashboard is generated as static HTML. A recommended visual structure:

```text
+--------------------------------------------------------------------------------+
| Header: K-WaterGuard AI logo, latest date, station count, alert count           |
+----------------------+---------------------------------------------------------+
| Side rail            | Summary cards                                           |
| - Station stats      | - Parameters                                            |
| - Province stats     | - Alerts                                                |
| - Mini Korea map     | - Charts                                                |
| - History links      | - Spatial maps                                          |
+----------------------+---------------------------------------------------------+
| Footer / metadata                                                              |
+--------------------------------------------------------------------------------+
```

Important dashboard blocks:

```text
Parameter cards
Alert table
Station table
Province summary
Historical CSV downloads
Plot cards
Spatial map cards
Optional chatbot
```

## 11. Optional Chatbot Backend

The dashboard frontend should never contain an OpenAI API key. The dashboard sends user questions to a backend URL configured by:

```python
CHATBOT_API_URL = os.environ.get("CHATBOT_API_URL", "")
```

Expected frontend/backend contract:

Request:

```json
{
  "question": "Which station has the highest turbidity today?"
}
```

Response:

```json
{
  "answer": "Station X has the highest turbidity today..."
}
```

Example FastAPI backend:

```python
import os
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

app = FastAPI()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    question: str

@app.post("/api/chat")
def chat(req: ChatRequest):
    csv_path = os.environ.get("WATER_QUALITY_CSV", "water_quality_records.csv")
    df = pd.read_csv(csv_path)
    latest = df.tail(50).to_csv(index=False)

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "system",
                "content": "You answer questions about K-WaterGuard AI water-quality monitoring data.",
            },
            {
                "role": "user",
                "content": f"Latest CSV rows:\n{latest}\n\nQuestion: {req.question}",
            },
        ],
    )

    return {"answer": response.output_text}
```

Run locally:

```powershell
pip install fastapi uvicorn openai pandas
$env:OPENAI_API_KEY = "YOUR_KEY"
$env:WATER_QUALITY_CSV = "C:\Users\USER\Desktop\AI_Agent_Try\water_quality_data\water_quality_records.csv"
uvicorn main:app --reload --port 8000
```

Then set:

```powershell
$env:CHATBOT_API_URL = "http://localhost:8000/api/chat"
```

For public dashboards, deploy the backend to Vercel, Render, Cloud Run, or another server-side platform.

## 12. Windows Task Scheduler Automation

Batch file:

```bat
@echo off
REM Water Quality Agent - Batch file for Windows Task Scheduler
cd /d "C:\Users\USER\Desktop\AI_Agent_Try"
python Claude.py
pause
```

Recommended production version without pause:

```bat
@echo off
cd /d "C:\Users\USER\Desktop\AI_Agent_Try"
".venv\Scripts\python.exe" Claude.py
```

Task Scheduler settings:

```text
Name: Water Quality Agent
Trigger: Daily or At log on
Action program: C:\Users\USER\Desktop\AI_Agent_Try\run_water_agent.bat
Start in: C:\Users\USER\Desktop\AI_Agent_Try
Settings: Run as soon as possible after a missed start
```

## 13. GitHub Pages Automation

Workflow file:

```text
.github/workflows/update-dashboard-pages.yml
```

Workflow purpose:

- Runs every hour.
- Installs dependencies.
- Restores historical water data cache.
- Runs `python Claude.py`.
- Publishes `water_quality_data/google_site_dashboard` to GitHub Pages.

Core workflow:

```yaml
name: Update Water Dashboard Pages

on:
  schedule:
    - cron: "7 * * * *"
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  build:
    runs-on: ubuntu-latest
    env:
      WATER_QUALITY_DATA_DIR: ${{ github.workspace }}/water_quality_data
      GITHUB_PAGES_BASE_URL: https://${{ github.repository_owner }}.github.io/${{ github.event.repository.name }}/
      TZ: Asia/Seoul

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"
      - run: python -m pip install -r requirements.txt
      - run: python Claude.py
      - run: |
          test -f "$WATER_QUALITY_DATA_DIR/google_site_dashboard/index.html"
          cp -R "$WATER_QUALITY_DATA_DIR/google_site_dashboard" site
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site

  deploy:
    runs-on: ubuntu-latest
    needs: build
    steps:
      - uses: actions/deploy-pages@v4
```

Enable GitHub Pages:

```text
Repository Settings > Pages > Source > GitHub Actions
```

Expected URL:

```text
https://YOUR_GITHUB_USERNAME.github.io/k-waterguard-dashboard/
```

## 14. Google Sites Embedding

Google Sites cannot embed a local file path. It must embed a public HTTPS URL.

Recommended flow:

```text
Claude.py
  -> google_site_dashboard/index.html
  -> GitHub Pages
  -> Google Sites Embed by URL
```

Google Sites steps:

1. Open the Google Site editor.
2. Choose `Insert`.
3. Choose `Embed`.
4. Paste the GitHub Pages URL.
5. Resize the frame.
6. Publish the site.

## 15. Security Recommendations

Current code contains API configuration directly in `Claude.py`. For production, move secrets to environment variables.

Recommended pattern:

```python
SERVICE_KEY = os.environ.get("KOREA_WATER_API_KEY", "")
```

Then set it locally:

```powershell
$env:KOREA_WATER_API_KEY = "YOUR_SERVICE_KEY"
```

Never expose these in frontend HTML:

```text
OpenAI API key
Private service keys
Database passwords
Cloud credentials
```

## 16. Testing Checklist

Run syntax check:

```powershell
python -m py_compile Claude.py
```

Run one full cycle:

```powershell
python Claude.py
```

Verify files:

```powershell
Test-Path water_quality_data\water_quality_records.csv
Test-Path water_quality_data\dashboard.html
Test-Path water_quality_data\google_site_dashboard\index.html
```

Verify generated plots:

```powershell
Get-ChildItem water_quality_data\daily_outputs -Recurse -Filter *.png
```

Verify dashboard bundle:

```powershell
Get-ChildItem water_quality_data\google_site_dashboard
```

## 17. Troubleshooting

### API returns no data

Possible causes:

```text
Invalid service key
API endpoint unavailable
Network timeout
Changed XML structure
Rate limit
```

Check:

```python
response = requests.get(Config.WATER_API_URL, params=params, timeout=60)
print(response.status_code)
print(response.text[:500])
```

### Maps do not render

Check that these files exist:

```text
ctprvn.shp
ctprvn.shx
ctprvn.dbf
```

Check CRS:

```python
MAP_SHAPEFILE_CRS = "EPSG:5179"
```

### GitHub Pages shows missing images

Check that the image exists in the published site:

```text
https://YOUR_GITHUB_USERNAME.github.io/k-waterguard-dashboard/quality_summary.png
```

Set:

```powershell
$env:GITHUB_PAGES_BASE_URL = "https://YOUR_GITHUB_USERNAME.github.io/k-waterguard-dashboard/"
```

Then regenerate and redeploy.

### Chatbot button appears but does not answer

Check:

```text
CHATBOT_ENABLED=true
CHATBOT_API_URL is not empty
Backend supports POST /api/chat
Backend returns {"answer": "..."}
CORS allows the dashboard domain
```

### Task Scheduler opens and waits forever

Remove `pause` from `run_water_agent.bat` for unattended execution.

## 18. Maintenance Plan

Recommended daily/hourly checks:

```text
Confirm latest CSV date
Confirm dashboard timestamp
Confirm GitHub Actions workflow success
Confirm no API errors in agent_log.txt
Confirm generated plots are present
```

Recommended monthly checks:

```text
Rotate or verify API keys
Check dependency updates
Review alert thresholds
Check GitHub Pages storage size
Archive old CSV files
Validate shapefile and map rendering
```

## 19. Future Improvements

Suggested improvements:

```text
Split Claude.py into smaller modules
Move API secrets to environment variables
Add unit tests for XML parsing and alert evaluation
Add structured logging
Add retry/backoff for API failures
Add database storage for long-term history
Add authenticated chatbot backend
Add station search and parameter filters in dashboard
Add downloadable PDF report generation
```

## 20. Minimal Rebuild Code Skeleton

This is a simplified version of the system structure. It shows how to rebuild the agent if starting from a blank project.

```python
from pathlib import Path
from datetime import datetime
import requests
import pandas as pd
import matplotlib.pyplot as plt

class Config:
    DATA_DIR = Path("water_quality_data")
    CSV_FILE = DATA_DIR / "water_quality_records.csv"
    PLOTS_DIR = DATA_DIR / "plots"
    DASHBOARD_FILE = DATA_DIR / "dashboard.html"
    WATER_API_URL = "http://apis.data.go.kr/1480523/WaterqualityServices/getIvstgWFS"
    SERVICE_KEY = "YOUR_SERVICE_KEY"

class WaterQualityCollector:
    def fetch_data(self):
        params = {
            "serviceKey": Config.SERVICE_KEY,
            "srsName": "EPSG:5179",
            "maxFeatures": 5000,
            "resultType": "results",
        }
        response = requests.get(Config.WATER_API_URL, params=params, timeout=60)
        response.raise_for_status()
        return self.parse_response(response.text)

    def parse_response(self, xml_text):
        # Replace with the full WFS parser from Claude.py.
        return [{
            "timestamp": datetime.now(),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "display_location": "South Korea",
            "pH": None,
            "DO": None,
            "BOD": None,
        }]

class DataManager:
    def save_data(self, records):
        Config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        df_new = pd.DataFrame(records)
        if Config.CSV_FILE.exists():
            df_old = pd.read_csv(Config.CSV_FILE)
            df = pd.concat([df_old, df_new], ignore_index=True)
        else:
            df = df_new
        df.to_csv(Config.CSV_FILE, index=False)

class PlotGenerator:
    def generate_all_plots(self):
        Config.PLOTS_DIR.mkdir(parents=True, exist_ok=True)
        df = pd.read_csv(Config.CSV_FILE)
        numeric_cols = [c for c in ["pH", "DO", "BOD"] if c in df.columns]
        df[numeric_cols].plot(kind="box")
        plt.tight_layout()
        plt.savefig(Config.PLOTS_DIR / "quality_summary.png")
        plt.close()

class DashboardGenerator:
    def generate(self):
        html = """
        <html>
          <head><title>K-WaterGuard AI</title></head>
          <body>
            <h1>K-WaterGuard AI Dashboard</h1>
            <img src="plots/quality_summary.png" alt="Quality Summary">
          </body>
        </html>
        """
        Config.DASHBOARD_FILE.write_text(html, encoding="utf-8")

class WaterQualityAgent:
    def __init__(self):
        self.collector = WaterQualityCollector()
        self.data_manager = DataManager()
        self.plot_generator = PlotGenerator()
        self.dashboard_generator = DashboardGenerator()

    def execute_cycle(self):
        records = self.collector.fetch_data()
        self.data_manager.save_data(records)
        self.plot_generator.generate_all_plots()
        self.dashboard_generator.generate()

if __name__ == "__main__":
    agent = WaterQualityAgent()
    agent.execute_cycle()
```

Use the full `Claude.py` implementation for production because it includes location enrichment, alert rules, spatial maps, daily archives, PWA generation, and GitHub Pages support.

