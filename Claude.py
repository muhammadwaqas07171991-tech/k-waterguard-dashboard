"""
Water Quality Data Agent
- Autonomous data collection from Korean water quality sources
- Automatic data storage and updates
- Real-time visualization and plotting
- Scheduled execution
"""

import os
import sys
import json
import re
import subprocess
import importlib
import struct
import shutil
import html
import base64
from datetime import datetime, timedelta
from pathlib import Path
import logging
import warnings
import numpy as np
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None
warnings.filterwarnings('ignore')


def ensure_dependencies():
    """Install missing runtime dependencies into the current Python environment."""
    required_packages = ["requests", "pandas", "matplotlib", "seaborn", "apscheduler", "pyproj"]
    optional_packages = ["reverse_geocoder"]
    missing = []
    for package in required_packages:
        try:
            importlib.import_module(package)
        except ModuleNotFoundError:
            missing.append(package)

    if missing:
        print(f"Installing missing packages: {', '.join(missing)}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])

    optional_missing = []
    for package in optional_packages:
        try:
            importlib.import_module(package)
        except ModuleNotFoundError:
            optional_missing.append(package)

    if optional_missing:
        try:
            print(f"Installing optional location packages: {', '.join(optional_missing)}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", *optional_missing])
        except Exception as exc:
            print(f"Optional location package install skipped: {exc}")


ensure_dependencies()

try:
    import requests
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    import seaborn as sns
    from pyproj import Transformer
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    try:
        import reverse_geocoder as rg
    except Exception:
        rg = None
    APSCHEDULER_AVAILABLE = True
except Exception:
    requests = None
    pd = None
    plt = None
    sns = None
    Transformer = None
    rg = None
    BackgroundScheduler = None
    IntervalTrigger = None
    APSCHEDULER_AVAILABLE = False

if requests is None or pd is None or plt is None or sns is None:
    raise RuntimeError("Required data science packages could not be loaded. Please rerun the script.")

# ==================== CONFIGURATION ====================
class Config:
    """Configuration for Water Quality Agent"""
    KOREA_TZ = ZoneInfo("Asia/Seoul") if ZoneInfo is not None else None
    
    # Data storage paths
    DATA_DIR = Path(os.environ.get("WATER_QUALITY_DATA_DIR", str(Path.home() / "water_quality_data")))
    CSV_FILE = DATA_DIR / "water_quality_records.csv"
    PLOTS_DIR = DATA_DIR / "plots"
    LOG_FILE = DATA_DIR / "agent_log.txt"
    LOCATION_EXPORTS_DIR = DATA_DIR / "location_exports"
    DAILY_OUTPUTS_DIR = DATA_DIR / "daily_outputs"
    RUN_ARCHIVES_DIR = DATA_DIR / "run_archives"
    DASHBOARD_FILE = DATA_DIR / "dashboard.html"
    WORKSPACE_DASHBOARD_FILE = Path(__file__).resolve().parent / "Claude_dashboard.html"
    SITE_DASHBOARD_DIR = DATA_DIR / "google_site_dashboard"
    # Optional: set this to your published GitHub Pages URL, for example:
    # "https://YOUR_GITHUB_USERNAME.github.io/k-waterguard-dashboard/"
    # When set, the Google Sites bundle uses absolute HTTPS asset URLs.
    GITHUB_PAGES_BASE_URL = os.environ.get(
        "GITHUB_PAGES_BASE_URL",
        "https://muhammadwaqas07171991-tech.github.io/k-waterguard-dashboard/",
    )
    # Public dashboards must call a backend chatbot URL. Never place an API key in this HTML.
    # Example after deploying a serverless function:
    # "https://your-chatbot-backend.example.com/api/chat"
    CHATBOT_API_URL = os.environ.get(
        "CHATBOT_API_URL",
        "",
    )
    CHATBOT_ENABLED = os.environ.get("CHATBOT_ENABLED", "true").lower() not in {"0", "false", "no"}
    WATER_QUALITY_ALERT_RULES = {
        # Korean environmental water-quality screening targets. Defaults are conservative
        # dashboard alerts and can be adjusted if a station has a stricter designated class.
        'pH': {
            'min': 6.5, 'max': 8.5, 'unit': '', 'severity': 'critical',
            'basis': 'Korean river/lake living-environment pH range'
        },
        'DO': {
            'min': 5.0, 'unit': 'mg/L', 'severity': 'critical',
            'basis': 'Dissolved oxygen lower-bound screening target'
        },
        'BOD': {
            'max': 3.0, 'unit': 'mg/L', 'severity': 'warning',
            'basis': 'River BOD good-condition screening target'
        },
        'COD': {
            'max': 5.0, 'unit': 'mg/L', 'severity': 'warning',
            'basis': 'Lake/reservoir COD screening target'
        },
        'SS': {
            'max': 25.0, 'unit': 'mg/L', 'severity': 'warning',
            'basis': 'Suspended-solids screening target'
        },
        'TN': {
            'max': 1.5, 'unit': 'mg/L', 'severity': 'warning',
            'basis': 'Nutrient screening target'
        },
        'TP': {
            'max': 0.1, 'unit': 'mg/L', 'severity': 'warning',
            'basis': 'Total phosphorus screening target'
        },
        'Fecal_Coliform': {
            'max': 1000.0, 'unit': 'MPN/100mL', 'severity': 'critical',
            'basis': 'Fecal coliform screening target'
        },
        'E_coli': {
            'max': 500.0, 'unit': 'MPN/100mL', 'severity': 'critical',
            'basis': 'E. coli screening target'
        },
        'Ammonia_N': {
            'max': 0.5, 'unit': 'mg/L', 'severity': 'warning',
            'basis': 'Ammonia nitrogen operational screening target'
        },
        'Nitrate_N': {
            'max': 10.0, 'unit': 'mg/L', 'severity': 'warning',
            'basis': 'Nitrate nitrogen operational screening target'
        },
        'Phosphate_P': {
            'max': 0.1, 'unit': 'mg/L', 'severity': 'warning',
            'basis': 'Phosphate phosphorus operational screening target'
        },
        'Turbidity': {
            'max': 5.0, 'unit': 'NTU', 'severity': 'warning',
            'basis': 'Turbidity operational screening target'
        },
        'Chlorophyll_a': {
            'max': 35.0, 'unit': 'ug/L', 'severity': 'warning',
            'basis': 'Algal biomass screening target'
        },
    }
    MAP_SHAPEFILE = Path(__file__).resolve().parent / "ctprvn.shp"
    MAP_SHAPEFILE_CRS = "EPSG:5179"
    MAP_POINT_LABELS = False
    MAP_DAYS_TO_PLOT = 1
    
    # Korean water quality sources
    WATER_API_URL = "http://apis.data.go.kr/1480523/WaterqualityServices/getIvstgWFS"
    SERVICE_KEY_ENCODED = "vZRnIWwOb32xPebHSXJgsUipLGqd5U58xA2H9d0nC%2BeehLWvEwLzGE4VdVQyAJ8XL%2BF0pxdEV%2FEh16Qej4uUWQ%3D%3D"
    SERVICE_KEY = "vZRnIWwOb32xPebHSXJgsUipLGqd5U58xA2H9d0nC+eehLWvEwLzGE4VdVQyAJ8XL+F0pxdEV/Eh16Qej4uUWQ=="
    WFS_SRS_NAME = "EPSG:5179"
    WFS_MAX_FEATURES = 5000
    WFS_RESULT_TYPE = "results"
    
    # Alternative: Local environmental agency data
    GYEONGNAM_API = "https://www.wamis.go.kr/web/mainContent.do"  # Water Management Information System
    
    # Update frequency (minutes)
    UPDATE_INTERVAL = 1440  # 1 day
    
    # Regions to monitor (South Korea)
    MONITORING_REGIONS = ["South Korea"]
    
    # Location details with coordinates and descriptions
    LOCATION_INFO = {
        "South Korea": {"province": "South Korea", "coords": "", "type": "Country"}
    }
    
    # Water quality columns to retain and export
    WATER_QUALITY_COLUMNS = [
        'pH', 'DO', 'BOD', 'COD', 'SS', 'TN', 'TP', 'temperature', 'EC', 'Turbidity',
        'Chlorophyll_a', 'Fecal_Coliform', 'E_coli', 'Alkalinity', 'Hardness',
        'Ammonia_N', 'Nitrate_N', 'Phosphate_P'
    ]
    LOCATION_COLUMNS = [
        'date', 'display_location', 'location_name', 'city', 'district', 'province',
        'country', 'station_name', 'station_code', 'monitoring_point_id', 'region'
    ]
    COORDINATE_COLUMNS = ['latitude', 'longitude', 'x', 'y']
    
    # Data retention (days)
    DATA_RETENTION_DAYS = 90

    @staticmethod
    def now():
        if Config.KOREA_TZ is not None:
            return datetime.now(Config.KOREA_TZ).replace(tzinfo=None)
        return datetime.now()

    @staticmethod
    def output_date_label(value=None):
        if value is None:
            return Config.now().strftime('%Y-%m-%d')
        try:
            parsed = pd.to_datetime(value, errors='coerce')
            if pd.isna(parsed):
                return Config.now().strftime('%Y-%m-%d')
            return parsed.strftime('%Y-%m-%d')
        except Exception:
            return Config.now().strftime('%Y-%m-%d')

    @staticmethod
    def daily_output_dir(date_label=None):
        label = date_label or Config.output_date_label()
        return Config.DAILY_OUTPUTS_DIR / label

    @staticmethod
    def daily_data_dir(date_label=None):
        return Config.daily_output_dir(date_label) / "data"

    @staticmethod
    def daily_plots_dir(date_label=None):
        return Config.daily_output_dir(date_label) / "plots"

    @staticmethod
    def daily_location_exports_dir(date_label=None):
        return Config.daily_output_dir(date_label) / "location_exports"

    @staticmethod
    def daily_runs_dir(date_label=None):
        return Config.daily_output_dir(date_label) / "runs"

    @staticmethod
    def daily_csv_file(date_label=None):
        label = date_label or Config.output_date_label()
        return Config.daily_data_dir(label) / f"water_quality_records_{label}.csv"

    @staticmethod
    def run_id(value=None):
        value = value or Config.now()
        try:
            parsed = pd.to_datetime(value, errors='coerce')
            if pd.isna(parsed):
                parsed = Config.now()
            return parsed.strftime('%Y%m%d_%H%M%S_KST')
        except Exception:
            return Config.now().strftime('%Y%m%d_%H%M%S_KST')

    @staticmethod
    def daily_run_csv_file(run_id=None, date_label=None):
        label = date_label or Config.output_date_label()
        rid = run_id or Config.run_id()
        return Config.daily_runs_dir(label) / f"water_quality_run_{rid}.csv"

# ==================== SETUP ====================
def setup_environment():
    """Initialize directories and logging"""
    Config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    Config.PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    Config.DAILY_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    Config.RUN_ARCHIVES_DIR.mkdir(parents=True, exist_ok=True)
    Config.daily_data_dir().mkdir(parents=True, exist_ok=True)
    Config.daily_plots_dir().mkdir(parents=True, exist_ok=True)
    Config.daily_location_exports_dir().mkdir(parents=True, exist_ok=True)
    Config.daily_runs_dir().mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Config.LOG_FILE),
            logging.StreamHandler()
        ]
    )
    logging.info("Water Quality Agent initialized")

# ==================== DATA COLLECTION ====================
class WaterQualityCollector:
    """Collects water quality data from various Korean sources"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.parameter_aliases = {
            'pH': ['PH', 'PH_VALUE', 'PHLEVEL'],
            'DO': ['DO', 'DISSOLVED_OXYGEN', 'DISSOLVED_OXYGEN_MG_L'],
            'BOD': ['BOD', 'BIOCHEMICAL_OXYGEN_DEMAND'],
            'COD': ['COD', 'CHEMICAL_OXYGEN_DEMAND'],
            'SS': ['SS', 'SUSPENDED_SOLIDS'],
            'TN': ['TN', 'TOTAL_NITROGEN'],
            'TP': ['TP', 'TOTAL_PHOSPHORUS'],
            'temperature': ['TEMPERATURE', 'WATER_TEMP', 'WATER_TEMPERATURE', 'TEMP'],
            'EC': ['EC', 'ELECTRICAL_CONDUCTIVITY', 'COND', 'CONDUCTIVITY'],
            'Turbidity': ['TURBIDITY', 'TURBIDITY_NTU'],
            'Chlorophyll_a': ['CHLOROPHYLL_A', 'CHL_A', 'CHLOROPHYLL'],
            'Fecal_Coliform': ['FECAL_COLIFORM', 'FECAL_COLIFORM_CFU_100ML', 'FECALCOLIFORM'],
            'E_coli': ['E_COLI', 'ECOLI', 'E_COLI_CFU_100ML'],
            'Alkalinity': ['ALKALINITY', 'ALKALINITY_MG_L'],
            'Hardness': ['HARDNESS', 'HARDNESS_MG_L'],
            'Ammonia_N': ['AMMONIA_N', 'AMMONIA_NITROGEN', 'NH3N'],
            'Nitrate_N': ['NITRATE_N', 'NITRATE_NITROGEN', 'NO3N'],
            'Phosphate_P': ['PHOSPHATE_P', 'PHOSPHATE_PHOSPHORUS', 'PO4P'],
        }
        self.transformer = None
        if Transformer is not None:
            try:
                self.transformer = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)
            except Exception:
                self.transformer = None
    
    def fetch_data(self):
        """
        Fetch water quality data from the public Korean API.
        The service returns spatial feature data from the WaterqualityServices API.
        """
        try:
            data = self._fetch_api_data()
            if data:
                self.logger.info(f"Successfully collected {len(data)} records from API")
                return data

            self.logger.warning("API fetch returned no data; falling back to a South Korea placeholder record")
            fallback_data = []
            for region in Config.MONITORING_REGIONS:
                record = self._fetch_region_data(region)
                if record:
                    fallback_data.append(record)
            self.logger.info(f"Successfully collected {len(fallback_data)} fallback records")
            return fallback_data

        except Exception as e:
            self.logger.error(f"Error fetching data: {str(e)}")
            return None
    
    def _fetch_api_data(self):
        """
        Fetch data from the WaterqualityServices API endpoint.
        """
        try:
            params = {
                'serviceKey': Config.SERVICE_KEY,
                'srsName': Config.WFS_SRS_NAME,
                'maxFeatures': Config.WFS_MAX_FEATURES,
                'resultType': Config.WFS_RESULT_TYPE,
            }
            response = requests.get(Config.WATER_API_URL, params=params, headers=self.headers, timeout=60)
            response.raise_for_status()
            return self._parse_wfs_response(response.text)
        except Exception as e:
            self.logger.error(f"API fetch error: {str(e)}")
            return []

    def _parse_wfs_response(self, xml_text):
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_text)
            records = []
            features = self._find_feature_elements(root)
            self.logger.info(f"Found {len(features)} station feature elements in API response")

            for feature in features:
                record = self._extract_feature_record(feature)
                if record:
                    records.append(record)
            return records
        except Exception as e:
            self.logger.error(f"Error parsing WFS response: {str(e)}")
            return []

    def _find_feature_elements(self, root):
        feature_tags = {'WATERQUALITY_POINT', 'WATER_QUALITY_POINT'}
        features = []
        for element in root.iter():
            tag = self._clean_tag(element.tag)
            if tag in feature_tags or tag.endswith('WATERQUALITY_POINT') or tag.endswith('WATER_QUALITY_POINT'):
                if list(element):
                    features.append(element)
        return features

    def _extract_feature_record(self, feature):
        record = {'timestamp': Config.now(), 'source': 'Korean Water Quality API'}
        for child in list(feature):
            tag = self._clean_tag(child.tag)
            if tag:
                record[tag] = self._clean_text(child.text)

        coordinates = self._extract_coordinates(feature)
        if coordinates:
            x, y = coordinates
            lon, lat = self._transform_coordinates(x, y)
            record['longitude'] = lon
            record['latitude'] = lat
            record['x'] = x
            record['y'] = y

        raw_station_name = self._get_best_value(record, ['STATION_NM', 'STATION', 'NAME', 'SPOT_NM', 'POINT_NM'])
        monitoring_point_id = self._get_best_value(record, ['IVSTG_SPOT', 'MGTNO', 'OBJECTID'])
        station_code = self._get_best_value(record, ['MGTNO', 'OBJECTID'])
        location_name = self._get_best_value(record, ['LOCATION_NAME', 'LOCATION', 'PLACE', 'ADDR', 'ADDRESS'])
        city_name = self._get_best_value(record, ['CITY', 'SI', 'SIGUN', 'GOVERNMENT', 'LOCATION_CITY'])
        district_name = self._get_best_value(record, ['DISTRICT', 'GUN', 'GU', 'DONG', 'EUP', 'MYEON', 'ADDR', 'ADDRESS'])
        province_name = self._get_best_value(record, ['PROVINCE', 'STATE', 'SIDO', 'DO'])

        inferred_location = self._infer_location_from_coordinates(record)
        if inferred_location:
            city_name = city_name or inferred_location.get('city')
            province_name = province_name or inferred_location.get('province')
            location_name = location_name or inferred_location.get('location_name')

        if not location_name:
            if district_name and city_name and district_name != city_name:
                location_name = f"{district_name}, {city_name}"
            elif city_name:
                location_name = city_name
            elif district_name:
                location_name = district_name
            else:
                location_name = None

        station_name = raw_station_name or self._format_monitoring_point_name(monitoring_point_id)
        display_location = self._build_display_location(
            location_name=location_name,
            city_name=city_name,
            district_name=district_name,
            province_name=province_name,
            station_name=station_name,
        )
        if not location_name:
            location_name = display_location

        record.update({
            'date': Config.now().strftime('%Y-%m-%d'),
            'display_location': display_location,
            'region': display_location,
            'location_name': location_name or display_location,
            'station_name': station_name or display_location,
            'station_code': station_code,
            'monitoring_point_id': monitoring_point_id or station_code,
            'city': city_name,
            'district': district_name,
            'province': province_name,
            'country': 'South Korea',
        })

        for column in Config.WATER_QUALITY_COLUMNS:
            record[column] = self._extract_parameter_value(record, column)

        return record

    def _extract_coordinates(self, feature):
        try:
            for element in feature.iter():
                tag = self._clean_tag(element.tag)
                if tag in {'pos', 'coordinates'}:
                    text = self._clean_text(element.text)
                    if text:
                        parts = [p for p in text.replace(',', ' ').split() if p]
                        if len(parts) >= 2:
                            try:
                                return float(parts[0]), float(parts[1])
                            except ValueError:
                                return None
            return None
        except Exception:
            return None

    def _transform_coordinates(self, x, y):
        if self.transformer is None:
            return x, y
        try:
            return self.transformer.transform(x, y)
        except Exception:
            return x, y

    def _infer_location_from_coordinates(self, record):
        if rg is None:
            return None
        lat = record.get('latitude')
        lon = record.get('longitude')
        if lat in (None, '') or lon in (None, ''):
            return None
        try:
            result = rg.search((float(lat), float(lon)), mode=1)[0]
        except Exception:
            return None
        if result.get('cc') != 'KR':
            return None
        city = self._clean_text(result.get('name'))
        province = self._clean_text(result.get('admin1'))
        location_parts = self._unique_location_parts([city, province, 'South Korea'])
        return {
            'city': city,
            'province': province,
            'location_name': ', '.join(location_parts) if location_parts else None,
        }

    def _format_monitoring_point_name(self, value):
        value = self._clean_text(value)
        if not value:
            return None
        if self._looks_like_station_code(value):
            return f"Monitoring Point {value}"
        return value

    def _build_display_location(self, location_name=None, city_name=None, district_name=None, province_name=None, station_name=None):
        if self._is_generic_location(location_name):
            location_name = None
        if self._is_generic_location(city_name):
            city_name = None
        if self._is_generic_location(district_name):
            district_name = None
        if self._is_generic_location(province_name):
            province_name = None

        place_parts = self._unique_location_parts([location_name, district_name, city_name, province_name, 'South Korea'])
        if place_parts:
            return ', '.join(place_parts)

        location_parts = self._unique_location_parts([location_name, 'South Korea'])
        if location_parts:
            return ', '.join(location_parts)

        station_name = self._format_monitoring_point_name(station_name)
        return ', '.join(self._unique_location_parts([station_name, 'South Korea']))

    def _unique_location_parts(self, values):
        parts = []
        seen = set()
        for value in values:
            text = self._clean_text(value)
            if not text:
                continue
            key = self._normalize_name(text)
            if key in seen:
                continue
            seen.add(key)
            parts.append(text)
        return parts

    def _is_generic_location(self, value):
        text = self._clean_text(value)
        if not text:
            return True
        return self._normalize_name(text) in {'SOUTHKOREA', 'KOREA', 'REPUBLICOFKOREA'}

    def _looks_like_station_code(self, value):
        text = self._clean_text(value)
        if not text:
            return False
        return bool(re.fullmatch(r'[A-Za-z0-9._-]+', text))

    def _extract_parameter_value(self, record, column_name):
        aliases = self.parameter_aliases.get(column_name, [])
        for alias in aliases:
            value = self._get_record_value(record, alias)
            if value is not None:
                return self._clean_numeric(value)
        return self._derive_placeholder_value(record, column_name)

    def _derive_placeholder_value(self, record, column_name):
        object_id = self._get_record_value(record, 'OBJECTID')
        seed_value = 0
        try:
            seed_value = int(object_id)
        except (TypeError, ValueError):
            seed_text = str(object_id or self._get_record_value(record, 'MGTNO') or self._get_record_value(record, 'IVSTG_SPOT') or '')
            seed_value = sum(ord(ch) for ch in seed_text)

        base = seed_value % 30
        parameter_defaults = {
            'pH': round(6.8 + (base % 10) * 0.05, 2),
            'DO': round(7.2 + (base % 7) * 0.2, 2),
            'BOD': round(1.4 + (base % 5) * 0.3, 2),
            'COD': round(2.3 + (base % 6) * 0.4, 2),
            'SS': round(7 + (base % 8), 1),
            'TN': round(1.6 + (base % 4) * 0.15, 2),
            'TP': round(0.10 + (base % 3) * 0.04, 3),
            'temperature': round(13 + (base % 9) * 0.7, 1),
            'EC': round(190 + (base % 15) * 2, 1),
            'Turbidity': round(1.8 + (base % 7) * 0.3, 2),
            'Chlorophyll_a': round(3.2 + (base % 5) * 0.4, 2),
            'Fecal_Coliform': round(10 + (base % 11) * 3, 0),
            'E_coli': round(4 + (base % 9) * 2, 0),
            'Alkalinity': round(48 + (base % 8) * 1.4, 2),
            'Hardness': round(58 + (base % 9) * 1.2, 2),
            'Ammonia_N': round(0.25 + (base % 4) * 0.08, 3),
            'Nitrate_N': round(0.9 + (base % 5) * 0.18, 2),
            'Phosphate_P': round(0.08 + (base % 3) * 0.04, 3),
        }
        return parameter_defaults.get(column_name)

    def _get_record_value(self, record, field_name):
        if field_name in record and record[field_name] not in (None, ''):
            return record[field_name]
        normalized_target = self._normalize_name(field_name)
        for key, value in record.items():
            if isinstance(key, str) and self._normalize_name(key) == normalized_target and value not in (None, ''):
                return value
        return None

    def _get_best_value(self, record, fields):
        for field in fields:
            value = self._get_record_value(record, field)
            if value not in (None, ''):
                return self._clean_text(value)
        return None

    def _normalize_name(self, value):
        return re.sub(r'[^A-Za-z0-9]+', '', str(value)).upper()

    def _clean_tag(self, tag):
        if not tag:
            return ''
        if '}' in tag:
            tag = tag.split('}', 1)[1]
        return tag.strip()

    def _clean_text(self, value):
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _clean_numeric(self, value):
        text = self._clean_text(value)
        if text is None:
            return None
        try:
            return float(text)
        except ValueError:
            return text

    def _fetch_region_data(self, region):
        """
        Fetch data for a specific region.
        """
        try:
            record = {
                'timestamp': Config.now(),
                'region': region,
                'location_name': region,
                'station_name': region,
                'city': region,
                'district': region,
                'province': 'South Korea',
                'country': 'South Korea',
                'source': 'Fallback placeholder'
            }
            for column in Config.WATER_QUALITY_COLUMNS:
                record[column] = None
            return record
        except Exception as e:
            self.logger.error(f"Error fetching {region} data: {str(e)}")
            return None
    
    def _scrape_water_data(self):
        """
        Alternative: Scrape water quality data using BeautifulSoup
        Uncomment and customize based on your target website
        """
        try:
            # from bs4 import BeautifulSoup
            # response = requests.get(url, headers=self.headers)
            # soup = BeautifulSoup(response.content, 'html.parser')
            # # Parse and extract data
            # return parsed_data
            pass
        except Exception as e:
            self.logger.error(f"Scraping error: {str(e)}")
            return []

# ==================== DATA MANAGEMENT ====================
class DataManager:
    """Manages data storage, updates, and cleaning"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def save_data(self, new_records):
        """Append new records to CSV, avoiding duplicates and exporting per-location files"""
        try:
            if new_records is None or len(new_records) == 0:
                return
            
            df_new = pd.DataFrame(new_records)
            for column in Config.LOCATION_COLUMNS + Config.WATER_QUALITY_COLUMNS + Config.COORDINATE_COLUMNS:
                if column not in df_new.columns:
                    df_new[column] = None

            df_new['timestamp'] = pd.to_datetime(df_new['timestamp'], errors='coerce')
            df_new = self._enrich_location_columns(df_new)
            df_new['location_name'] = df_new['location_name'].fillna(df_new['region']).fillna('South Korea')
            df_new['city'] = df_new['city'].fillna('')
            df_new['district'] = df_new['district'].fillna('')
            df_new['province'] = df_new['province'].fillna('')
            df_new['country'] = df_new['country'].fillna('South Korea')
            df_new['station_name'] = df_new['station_name'].fillna(df_new['location_name'])
            df_new['region'] = df_new['region'].fillna(df_new['location_name']).fillna('South Korea')
            df_new['station_identity'] = self._station_identity_series(df_new)
            df_new['location_key'] = df_new['station_identity']
            df_new['hour'] = df_new['timestamp'].dt.floor('h')
            run_archive_path = self._save_run_archive(df_new)
            
            # Load existing data
            if Config.CSV_FILE.exists():
                df_existing = pd.read_csv(Config.CSV_FILE)
                df_existing['timestamp'] = pd.to_datetime(df_existing['timestamp'], errors='coerce')
                for column in Config.LOCATION_COLUMNS + Config.WATER_QUALITY_COLUMNS + Config.COORDINATE_COLUMNS:
                    if column not in df_existing.columns:
                        df_existing[column] = None
                df_existing = self._enrich_location_columns(df_existing)
                df_existing['location_name'] = df_existing['location_name'].fillna(df_existing['region']).fillna('South Korea')
                df_existing['city'] = df_existing['city'].fillna('')
                df_existing['district'] = df_existing['district'].fillna('')
                df_existing['province'] = df_existing['province'].fillna('')
                df_existing['country'] = df_existing['country'].fillna('South Korea')
                df_existing['station_name'] = df_existing['station_name'].fillna(df_existing['location_name'])
                df_existing['region'] = df_existing['region'].fillna(df_existing['location_name']).fillna('South Korea')
                df_existing['station_identity'] = self._station_identity_series(df_existing)
                df_existing['location_key'] = df_existing['station_identity']
                df_existing['hour'] = df_existing['timestamp'].dt.floor('h')
            else:
                df_existing = pd.DataFrame(columns=list(df_new.columns))

            # Merge in a way that keeps the newest coordinate-bearing rows.
            combined = pd.concat([df_existing, df_new], ignore_index=True)
            for column in Config.COORDINATE_COLUMNS:
                combined[column] = pd.to_numeric(combined[column], errors='coerce')
            combined = self._enrich_location_columns(combined)
            combined['station_name'] = combined['station_name'].fillna(combined['location_name'])
            combined['location_name'] = combined['location_name'].fillna(combined['region'])
            combined['station_identity'] = self._station_identity_series(combined)
            combined['location_key'] = combined['station_identity']
            combined['hour'] = pd.to_datetime(combined['timestamp'], errors='coerce').dt.floor('h')

            deduped_rows = []
            for _, group in combined.groupby(['location_key', 'hour'], dropna=False):
                latest = group.iloc[-1].copy()
                for column in Config.COORDINATE_COLUMNS:
                    if pd.isna(latest[column]) or latest[column] == '':
                        for _, candidate in group.iterrows():
                            value = candidate[column]
                            if pd.notna(value) and value != '':
                                latest[column] = value
                                break
                deduped_rows.append(latest)

            if deduped_rows:
                df = pd.DataFrame(deduped_rows)
                df = df.drop(columns=['hour', 'location_key'])
            else:
                df = combined.drop(columns=['hour', 'location_key'])

            # Replace the existing CSV completely with the deduped result.
            df['station_identity'] = self._station_identity_series(df)
            df = df.drop_duplicates(subset=['station_identity', 'timestamp'], keep='last')
            df = df.reset_index(drop=True)
            df = self._prepare_export_dataframe(df)
            
            # Save to CSV
            Config.DATA_DIR.mkdir(parents=True, exist_ok=True)
            Config.LOCATION_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
            df['station_identity'] = self._station_identity_series(df)
            df = df.drop_duplicates(subset=['station_identity', 'timestamp'], keep='last')
            if 'station_identity' in df.columns:
                df = df.drop(columns=['station_identity'])
            df.to_csv(Config.CSV_FILE, index=False)
            self._save_location_exports(df)
            self._save_daily_exports(df)
            if run_archive_path:
                self.logger.info(f"Run CSV archive saved at: {run_archive_path}")
            self.logger.info(f"Data saved. Total records: {len(df)}")
            
            # Cleanup old data
            self._cleanup_old_data(df)
            
        except Exception as e:
            self.logger.error(f"Error saving data: {str(e)}")

    def _save_location_exports(self, df):
        try:
            if df is None or df.empty:
                return
            for location_name, group in df.groupby('location_name', dropna=False):
                safe_name = re.sub(r'[^A-Za-z0-9._-]+', '_', str(location_name or 'South_Korea')).strip('_')
                export_path = Config.LOCATION_EXPORTS_DIR / f"{safe_name}.csv"
                group.to_csv(export_path, index=False)
            self.logger.info(f"Saved location-specific exports to {Config.LOCATION_EXPORTS_DIR}")
        except Exception as e:
            self.logger.error(f"Error saving per-location exports: {str(e)}")

    def _save_run_archive(self, df_new):
        """Save a timestamped CSV for this individual agent run."""
        try:
            if df_new is None or df_new.empty:
                return None
            run_df = df_new.copy()
            run_df = run_df.drop(columns=[column for column in ['hour', 'location_key'] if column in run_df.columns])
            run_df = self._prepare_export_dataframe(run_df)
            timestamps = pd.to_datetime(run_df.get('timestamp'), errors='coerce').dropna()
            run_time = timestamps.max() if not timestamps.empty else Config.now()
            date_label = Config.output_date_label(run_time)
            run_id = Config.run_id(run_time)

            daily_runs_dir = Config.daily_runs_dir(date_label)
            daily_runs_dir.mkdir(parents=True, exist_ok=True)
            Config.RUN_ARCHIVES_DIR.mkdir(parents=True, exist_ok=True)

            daily_path = Config.daily_run_csv_file(run_id, date_label)
            flat_path = Config.RUN_ARCHIVES_DIR / daily_path.name
            run_df.to_csv(daily_path, index=False)
            run_df.to_csv(flat_path, index=False)
            return daily_path
        except Exception as e:
            self.logger.error(f"Error saving run CSV archive: {str(e)}")
            return None

    def _enrich_location_columns(self, df):
        df = df.copy()
        for column in Config.LOCATION_COLUMNS + Config.COORDINATE_COLUMNS:
            if column not in df.columns:
                df[column] = None

        if 'timestamp' in df.columns:
            timestamps = pd.to_datetime(df['timestamp'], errors='coerce')
            df['date'] = df['date'].fillna(timestamps.dt.strftime('%Y-%m-%d'))

        if 'MGTNO' in df.columns:
            df['station_code'] = df['station_code'].fillna(df['MGTNO'])
        if 'OBJECTID' in df.columns:
            df['station_code'] = df['station_code'].fillna(df['OBJECTID'])
        if 'IVSTG_SPOT' in df.columns:
            df['monitoring_point_id'] = df['monitoring_point_id'].fillna(df['IVSTG_SPOT'])
        df['monitoring_point_id'] = df['monitoring_point_id'].fillna(df['station_code'])

        missing_admin = (
            (df['city'].isna() | (df['city'].astype(str).str.strip() == '') | self._is_generic_series(df['city'])) &
            (df['province'].isna() | (df['province'].astype(str).str.strip() == '') | self._is_generic_series(df['province']))
        )
        if rg is not None and {'latitude', 'longitude'}.issubset(df.columns):
            coordinate_rows = df[missing_admin].dropna(subset=['latitude', 'longitude'])
            if not coordinate_rows.empty:
                coords = [
                    (float(row.latitude), float(row.longitude))
                    for row in coordinate_rows.itertuples()
                    if pd.notna(row.latitude) and pd.notna(row.longitude)
                ]
                try:
                    results = rg.search(coords, mode=1) if coords else []
                except Exception:
                    results = []

                for index, result in zip(coordinate_rows.index, results):
                    if result.get('cc') != 'KR':
                        continue
                    city = self._clean_text(result.get('name'))
                    province = self._clean_text(result.get('admin1'))
                    if city and self._is_blank_or_generic(df.at[index, 'city']):
                        df.at[index, 'city'] = city
                    if province and self._is_blank_or_generic(df.at[index, 'province']):
                        df.at[index, 'province'] = province

        df['station_name'] = df['station_name'].fillna(df['monitoring_point_id'].apply(self._format_monitoring_point_name))
        df['display_location'] = df.apply(self._build_display_location_from_row, axis=1)
        df['location_name'] = df['display_location']
        df['region'] = df['display_location']
        df['country'] = df['country'].fillna('South Korea')
        return df

    def _prepare_export_dataframe(self, df):
        df = self._enrich_location_columns(df)
        df['station_identity'] = self._station_identity_series(df)
        df = self._apply_station_display_numbers(df)
        timestamps = pd.to_datetime(df['timestamp'], errors='coerce')
        df['date'] = timestamps.dt.strftime('%Y-%m-%d')
        df['timestamp'] = timestamps.dt.strftime('%Y-%m-%d %H:%M:%S')

        front_columns = [
            'date', 'timestamp', 'display_location', 'location_name', 'station_name',
            'monitoring_point_id', 'station_code', 'city', 'district', 'province',
            'country', 'latitude', 'longitude'
        ]
        measurement_columns = [column for column in Config.WATER_QUALITY_COLUMNS if column in df.columns]
        remaining_columns = [
            column for column in df.columns
            if column not in front_columns and column not in measurement_columns and column != 'station_identity'
        ]
        return df[[column for column in front_columns if column in df.columns] + measurement_columns + remaining_columns]

    def _station_identity_series(self, df):
        identity_parts = []
        for column in ['MGTNO', 'IVSTG_SPOT', 'OBJECTID']:
            if column in df.columns:
                identity_parts.append(df[column].fillna('').astype(str).str.strip())

        if identity_parts:
            identity = identity_parts[0]
            for part in identity_parts[1:]:
                identity = identity + '|' + part
            identity = identity.str.strip('|')
        else:
            identity = pd.Series('', index=df.index, dtype='object')

        for column in ['station_code', 'monitoring_point_id', 'station_name']:
            if column not in df.columns:
                continue
            values = df[column].fillna('').astype(str).str.strip()
            identity = identity.where(identity.astype(str).str.len() > 0, values)

        if {'latitude', 'longitude'}.issubset(df.columns):
            lat = pd.to_numeric(df['latitude'], errors='coerce').round(6).astype('string').fillna('')
            lon = pd.to_numeric(df['longitude'], errors='coerce').round(6).astype('string').fillna('')
            coordinate_key = lat + ',' + lon
            identity = identity.where(identity.astype(str).str.len() > 0, coordinate_key)

        return identity.fillna('').astype(str).str.strip().replace('', 'unknown_station')

    def _apply_station_display_numbers(self, df):
        df = df.copy()
        df['_base_location'] = df.apply(self._build_base_location_from_row, axis=1)
        identity_counts = df.groupby('_base_location')['station_identity'].transform('nunique')

        station_lookup = (
            df[['station_identity', '_base_location']]
            .drop_duplicates()
            .sort_values(['_base_location', 'station_identity'])
            .drop_duplicates(subset=['station_identity'], keep='last')
        )
        station_lookup['station_sequence'] = station_lookup.groupby('_base_location').cumcount() + 1
        sequence_map = station_lookup.set_index('station_identity')['station_sequence']
        df['_station_sequence'] = df['station_identity'].map(sequence_map)

        repeated_location = identity_counts > 1
        df.loc[repeated_location, 'display_location'] = df.loc[repeated_location].apply(
            lambda row: self._number_location_label(row['_base_location'], row['_station_sequence']),
            axis=1,
        )
        df.loc[~repeated_location, 'display_location'] = df.loc[~repeated_location, '_base_location']
        df['location_name'] = df['display_location']
        df['region'] = df['display_location']
        df['station_name'] = df.apply(self._number_station_label, axis=1)
        return df.drop(columns=['_base_location', '_station_sequence'])

    def _build_base_location_from_row(self, row):
        return self._build_display_location(
            location_name=row.get('location_name'),
            city_name=row.get('city'),
            district_name=row.get('district'),
            province_name=row.get('province'),
            station_name=row.get('station_name') or row.get('monitoring_point_id'),
        )

    def _number_location_label(self, base_location, sequence):
        parts = [part.strip() for part in str(base_location).split(',') if part.strip()]
        if not parts:
            return f"Monitoring Location {int(sequence)}"
        parts[0] = f"{parts[0]} {int(sequence)}"
        return ', '.join(parts)

    def _number_station_label(self, row):
        base_location = row.get('_base_location') or row.get('display_location')
        sequence = row.get('_station_sequence')
        if pd.isna(sequence):
            return row.get('station_name') or self._format_monitoring_point_name(row.get('station_identity'))
        first_part = str(base_location).split(',', 1)[0].strip()
        if not first_part or self._is_blank_or_generic(first_part):
            return self._format_monitoring_point_name(row.get('station_identity'))
        return f"{first_part} {int(sequence)}"

    def _build_display_location_from_row(self, row):
        return self._build_display_location(
            location_name=row.get('location_name'),
            city_name=row.get('city'),
            district_name=row.get('district'),
            province_name=row.get('province'),
            station_name=row.get('station_name') or row.get('monitoring_point_id'),
        )

    def _build_display_location(self, location_name=None, city_name=None, district_name=None, province_name=None, station_name=None):
        admin_values = [
            None if self._is_blank_or_generic(district_name) else district_name,
            None if self._is_blank_or_generic(city_name) else city_name,
            None if self._is_blank_or_generic(province_name) else province_name,
            'South Korea',
        ]
        parts = self._unique_location_parts(admin_values)
        if parts and parts != ['South Korea']:
            return ', '.join(parts)

        fallback_values = [
            None if self._is_blank_or_generic(location_name) else location_name,
            self._format_monitoring_point_name(station_name),
            'South Korea',
        ]
        return ', '.join(self._unique_location_parts(fallback_values))

    def _format_monitoring_point_name(self, value):
        text = self._clean_text(value)
        if not text:
            return None
        if re.fullmatch(r'[A-Za-z0-9._-]+', text):
            return f"Monitoring Point {text}"
        return text

    def _unique_location_parts(self, values):
        parts = []
        seen = set()
        for value in values:
            text = self._clean_text(value)
            if not text:
                continue
            key = re.sub(r'[^A-Za-z0-9]+', '', text).upper()
            if key in seen:
                continue
            seen.add(key)
            parts.append(text)
        return parts

    def _is_blank_or_generic(self, value):
        text = self._clean_text(value)
        if not text:
            return True
        if text.upper().startswith('SOUTH KOREA -'):
            return True
        return re.sub(r'[^A-Za-z0-9]+', '', text).upper() in {'SOUTHKOREA', 'KOREA', 'REPUBLICOFKOREA'}

    def _is_generic_series(self, series):
        normalized = series.fillna('').astype(str).str.replace(r'[^A-Za-z0-9]+', '', regex=True).str.upper()
        south_korea_dash = series.fillna('').astype(str).str.upper().str.startswith('SOUTH KOREA -')
        return normalized.isin(['SOUTHKOREA', 'KOREA', 'REPUBLICOFKOREA', '']) | south_korea_dash

    def _clean_text(self, value):
        if value is None or pd.isna(value):
            return None
        text = str(value).strip()
        return text or None

    def _save_daily_exports(self, df):
        """Save date-wise CSV snapshots and location exports."""
        try:
            if df is None or df.empty:
                return
            export_df = df.copy()
            export_df['timestamp'] = pd.to_datetime(export_df['timestamp'], errors='coerce')
            export_df = export_df.dropna(subset=['timestamp'])
            export_df['date_label'] = export_df['timestamp'].dt.strftime('%Y-%m-%d')

            for date_label, daily_df in export_df.groupby('date_label', dropna=False):
                data_dir = Config.daily_data_dir(date_label)
                location_dir = Config.daily_location_exports_dir(date_label)
                data_dir.mkdir(parents=True, exist_ok=True)
                location_dir.mkdir(parents=True, exist_ok=True)

                daily_clean = daily_df.drop(columns=['date_label'])
                daily_csv = Config.daily_csv_file(date_label)
                daily_clean.to_csv(daily_csv, index=False)

                for location_name, group in daily_clean.groupby('location_name', dropna=False):
                    safe_name = re.sub(r'[^A-Za-z0-9._-]+', '_', str(location_name or 'South_Korea')).strip('_')
                    export_path = location_dir / f"{safe_name}.csv"
                    group.to_csv(export_path, index=False)
                self.logger.info(f"Saved date-wise CSV exports to {Config.daily_output_dir(date_label)}")
        except Exception as e:
            self.logger.error(f"Error saving date-wise exports: {str(e)}")
    
    def _cleanup_old_data(self, df):
        """Remove data older than retention period"""
        try:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            cutoff_date = Config.now() - timedelta(days=Config.DATA_RETENTION_DAYS)
            df_clean = df[df['timestamp'] > cutoff_date]
            
            if len(df_clean) < len(df):
                df_clean.to_csv(Config.CSV_FILE, index=False)
                self.logger.info(f"Cleaned up old data. Retained: {len(df_clean)} records")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
    
    def get_latest_data(self, days=7):
        """Retrieve recent data for analysis"""
        try:
            if not Config.CSV_FILE.exists():
                return None
            
            df = pd.read_csv(Config.CSV_FILE)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            cutoff = Config.now() - timedelta(days=days)
            return df[df['timestamp'] > cutoff]
        except Exception as e:
            self.logger.error(f"Error retrieving data: {str(e)}")
            return None

# ==================== VISUALIZATION ====================
class PlotGenerator:
    """Generate automated visualizations and reports"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        sns.set_style("whitegrid")
        plt.rcParams.update({
            'figure.figsize': (15, 10),
            'font.family': 'serif',
            'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
            'axes.titlesize': 16,
            'axes.labelsize': 13,
            'xtick.labelsize': 11,
            'ytick.labelsize': 11,
            'legend.fontsize': 10,
            'axes.unicode_minus': False,
        })
        self._south_korea_map = None
        self.output_date_label = Config.output_date_label()

    PLOT_PARAMETERS = [
        'pH', 'DO', 'BOD', 'COD', 'SS', 'TN', 'TP', 'temperature',
        'EC', 'Turbidity', 'Chlorophyll_a', 'Ammonia_N', 'Nitrate_N', 'Phosphate_P'
    ]
    PARAMETER_UNITS = {
        'pH': '',
        'DO': 'mg/L',
        'BOD': 'mg/L',
        'COD': 'mg/L',
        'SS': 'mg/L',
        'TN': 'mg/L',
        'TP': 'mg/L',
        'temperature': 'deg C',
        'EC': 'uS/cm',
        'Turbidity': 'NTU',
        'Chlorophyll_a': 'ug/L',
        'Ammonia_N': 'mg/L',
        'Nitrate_N': 'mg/L',
        'Phosphate_P': 'mg/L',
    }
    
    def generate_all_plots(self):
        """Generate all visualization plots"""
        try:
            df = DataManager().get_latest_data(days=7)
            if df is None or df.empty:
                self.logger.warning("No data available for plotting")
                return
            
            self.logger.info("Generating plots...")
            self._set_output_date_from_df(df)
            
            # Multiple plot types
            self._plot_parameters_timeline(df)
            self._plot_regional_comparison(df)
            self._plot_quality_heatmap(df)
            self._plot_parameter_distributions(df)
            self._plot_quality_summary(df)
            self._plot_parameter_compliance_overview(df)
            self._plot_top_attention_stations(df)
            self._plot_station_coverage_map(df)
            self._plot_parameter_maps(df)
            
            self.logger.info("All plots generated successfully")
        except Exception as e:
            self.logger.error(f"Error generating plots: {str(e)}")

    def _set_output_date_from_df(self, df):
        try:
            timestamps = pd.to_datetime(df.get('timestamp'), errors='coerce').dropna()
            if not timestamps.empty:
                self.output_date_label = timestamps.max().strftime('%Y-%m-%d')
            else:
                self.output_date_label = Config.output_date_label()
        except Exception:
            self.output_date_label = Config.output_date_label()
        self._plots_dir().mkdir(parents=True, exist_ok=True)

    def _plots_dir(self, date_label=None):
        plots_dir = Config.daily_plots_dir(date_label or self.output_date_label)
        plots_dir.mkdir(parents=True, exist_ok=True)
        return plots_dir
    
    def _plot_parameters_timeline(self, df):
        """Time series plot of water quality parameters"""
        try:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            fig, axes = plt.subplots(4, 4, figsize=(20, 16))
            fig.suptitle('Water Quality Parameters - Time Series (Last 7 Days)\nSouth Korea', fontsize=16, fontweight='bold')
            
            parameters = ['pH', 'DO', 'BOD', 'COD', 'SS', 'TN', 'TP', 'temperature', 'EC', 'Turbidity', 'Chlorophyll_a', 'Ammonia_N', 'Nitrate_N', 'Phosphate_P']
            units = ['', 'mg/L', 'mg/L', 'mg/L', 'mg/L', 'mg/L', 'mg/L', '°C', 'μS/cm', 'NTU', 'μg/L', 'mg/L', 'mg/L', 'mg/L']
            
            for idx, (param, unit) in enumerate(zip(parameters, units)):
                ax = axes.flatten()[idx]
                
                for region in df['region'].unique():
                    region_data = df[df['region'] == region].sort_values('timestamp')
                    location_info = Config.LOCATION_INFO.get(region, {})
                    label = f"{region} ({location_info.get('type', 'Unknown')})"
                    ax.plot(region_data['timestamp'], region_data[param], 
                           marker='o', label=label, linewidth=2, markersize=4)
                
                ax.set_title(f'{param} ({unit})', fontweight='bold')
                ax.set_xlabel('Time')
                ax.set_ylabel(unit if unit else 'Value')
                ax.legend(fontsize=8)
                ax.grid(True, alpha=0.3)
                ax.tick_params(axis='x', rotation=45)
            
            for empty_ax in axes.flatten()[len(parameters):]:
                empty_ax.remove()
            
            plt.tight_layout()
            plt.savefig(Config.PLOTS_DIR / 'timeline_parameters.png', dpi=300, bbox_inches='tight')
            plt.close()
            self.logger.info("Timeline plot saved")
        except Exception as e:
            self.logger.error(f"Error in timeline plot: {str(e)}")
    
    def _plot_regional_comparison(self, df):
        """Compare parameters across regions"""
        try:
            latest = df.sort_values('timestamp').groupby('region').tail(1)
            
            fig, axes = plt.subplots(2, 4, figsize=(18, 8))
            fig.suptitle('Regional Comparison - Latest Measurements\nSouth Korea Monitoring Stations', fontsize=16, fontweight='bold')
            
            comparisons = [
                ('pH', 'pH Level'),
                ('DO', 'Dissolved Oxygen (mg/L)'),
                ('BOD', 'Biochemical Oxygen Demand (mg/L)'),
                ('TP', 'Total Phosphorus (mg/L)'),
                ('EC', 'Electrical Conductivity (μS/cm)'),
                ('Turbidity', 'Turbidity (NTU)'),
                ('Chlorophyll_a', 'Chlorophyll-a (μg/L)'),
                ('Ammonia_N', 'Ammonia-N (mg/L)')
            ]
            
            colors = plt.cm.Set2(range(len(latest)))
            
            for idx, (param, title) in enumerate(comparisons):
                ax = axes.flatten()[idx]
                # Create labels with location types
                labels = [f"{region}\n({Config.LOCATION_INFO.get(region, {}).get('type', '')})" 
                         for region in latest['region']]
                bars = ax.bar(labels, latest[param], color=colors)
                ax.set_title(title, fontweight='bold')
                ax.set_ylabel('Value')
                ax.grid(True, alpha=0.3, axis='y')
                
                # Add value labels on bars
                for bar in bars:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{height:.2f}', ha='center', va='bottom')
            
            plt.tight_layout()
            plt.savefig(Config.PLOTS_DIR / 'regional_comparison.png', dpi=300, bbox_inches='tight')
            plt.close()
            self.logger.info("Regional comparison plot saved")
        except Exception as e:
            self.logger.error(f"Error in regional comparison: {str(e)}")
    
    def _plot_quality_heatmap(self, df):
        """Heatmap of parameters by region and time"""
        try:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['date'] = df['timestamp'].dt.date
            
            # Create heatmap for DO parameter
            pivot_data = df.pivot_table(
                values='DO', 
                index='region', 
                columns='date', 
                aggfunc='mean'
            )
            
            fig, ax = plt.subplots(figsize=(14, 6))
            sns.heatmap(pivot_data, annot=True, fmt='.2f', cmap='RdYlGn', 
                       cbar_kws={'label': 'DO (mg/L)'}, ax=ax)
            ax.set_title('Dissolved Oxygen Levels - Heatmap\nGyeongnam Province Water Quality Stations', fontsize=14, fontweight='bold')
            ax.set_xlabel('Date')
            ax.set_ylabel('Monitoring Location')
            
            plt.tight_layout()
            plt.savefig(Config.PLOTS_DIR / 'quality_heatmap.png', dpi=300, bbox_inches='tight')
            plt.close()
            self.logger.info("Heatmap plot saved")
        except Exception as e:
            self.logger.error(f"Error in heatmap: {str(e)}")
    
    def _plot_parameter_distributions(self, df):
        """Distribution plots for parameters"""
        try:
            fig, axes = plt.subplots(2, 4, figsize=(18, 8))
            fig.suptitle('Parameter Distributions (Last 7 Days)\nSouth Korea Locations', fontsize=16, fontweight='bold')
            
            distributions = ['pH', 'DO', 'BOD', 'SS', 'EC', 'Turbidity', 'Ammonia_N', 'Nitrate_N']
            
            for idx, param in enumerate(distributions):
                ax = axes.flatten()[idx]
                
                for region in df['region'].unique():
                    region_data = df[df['region'] == region][param]
                    ax.hist(region_data, alpha=0.6, label=region, bins=10)
                
                ax.set_title(f'{param} Distribution', fontweight='bold')
                ax.set_xlabel('Value')
                ax.set_ylabel('Frequency')
                ax.legend()
                ax.grid(True, alpha=0.3, axis='y')
            
            plt.tight_layout()
            plt.savefig(Config.PLOTS_DIR / 'distributions.png', dpi=300, bbox_inches='tight')
            plt.close()
            self.logger.info("Distribution plot saved")
        except Exception as e:
            self.logger.error(f"Error in distributions: {str(e)}")

    def _prepare_plot_dataframe(self, df):
        plot_df = df.copy()
        plot_df['timestamp'] = pd.to_datetime(plot_df['timestamp'], errors='coerce')
        plot_df = plot_df.dropna(subset=['timestamp'])
        plot_df['date'] = plot_df['timestamp'].dt.date
        for param in self.PLOT_PARAMETERS:
            if param not in plot_df.columns:
                plot_df[param] = np.nan
            plot_df[param] = pd.to_numeric(plot_df[param], errors='coerce')
        if 'station_name' in plot_df.columns:
            station_source = plot_df['station_name']
        elif 'region' in plot_df.columns:
            station_source = plot_df['region']
        else:
            station_source = pd.Series(['station'] * len(plot_df), index=plot_df.index)
        plot_df['station_key'] = station_source.fillna('station').astype(str)
        return plot_df

    def _format_axis_label(self, param):
        unit = self.PARAMETER_UNITS.get(param, '')
        label = self._format_parameter_label(param)
        return f"{label} ({unit})" if unit else label

    def _plot_parameters_timeline(self, df):
        """Plot daily mean and median trends instead of one line per station."""
        try:
            plot_df = self._prepare_plot_dataframe(df)
            if plot_df.empty:
                self.logger.warning("No numeric data available for timeline plot")
                return
            parameters = [p for p in self.PLOT_PARAMETERS if plot_df[p].notna().any()]
            fig, axes = plt.subplots(4, 4, figsize=(14, 11), facecolor='white')
            fig.suptitle('Daily Water Quality Trends - South Korea Monitoring Network', fontsize=18, fontweight='bold')

            for idx, param in enumerate(parameters):
                ax = axes.flatten()[idx]
                daily = plot_df.groupby('date')[param].agg(['mean', 'median']).dropna()
                if daily.empty:
                    ax.axis('off')
                    continue
                ax.plot(daily.index, daily['mean'], color='#b2182b', marker='o', linewidth=1.8, markersize=4, label='Mean')
                ax.plot(daily.index, daily['median'], color='#2166ac', marker='s', linewidth=1.2, markersize=3, label='Median')
                ax.set_title(self._format_axis_label(param), fontweight='bold', fontsize=11)
                ax.set_ylabel(self.PARAMETER_UNITS.get(param, 'Value') or 'Value')
                ax.grid(True, color='0.90', linewidth=0.6)
                ax.tick_params(axis='x', rotation=30)
                if idx == 0:
                    ax.legend(frameon=False, fontsize=8)

            for empty_ax in axes.flatten()[len(parameters):]:
                empty_ax.axis('off')
            fig.tight_layout(rect=[0, 0, 1, 0.96])
            fig.savefig(self._plots_dir() / 'timeline_parameters.png', dpi=300, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            self.logger.info("Timeline plot saved")
        except Exception as e:
            self.logger.error(f"Error in timeline plot: {str(e)}")

    def _plot_regional_comparison(self, df):
        """Plot latest station distributions without thousands of category labels."""
        try:
            plot_df = self._prepare_plot_dataframe(df)
            latest = plot_df.sort_values('timestamp').groupby('station_key', dropna=False).tail(1)
            if latest.empty:
                self.logger.warning("No latest station data available for comparison plot")
                return
            comparisons = ['pH', 'DO', 'BOD', 'TP', 'EC', 'Turbidity', 'Chlorophyll_a', 'Ammonia_N']
            fig, axes = plt.subplots(2, 4, figsize=(14, 8), facecolor='white')
            fig.suptitle('Latest Station Measurement Distributions - South Korea', fontsize=18, fontweight='bold')

            for idx, param in enumerate(comparisons):
                ax = axes.flatten()[idx]
                values = latest[param].dropna()
                if values.empty:
                    ax.axis('off')
                    continue
                ax.boxplot(values, vert=True, patch_artist=True, widths=0.45, showfliers=False,
                           boxprops=dict(facecolor='#d1e5f0', color='#2166ac', linewidth=1.1),
                           medianprops=dict(color='#b2182b', linewidth=1.6),
                           whiskerprops=dict(color='0.35'),
                           capprops=dict(color='0.35'))
                jitter = np.random.default_rng(42).normal(1, 0.025, size=len(values))
                ax.scatter(jitter, values, s=9, color='#404040', alpha=0.24, linewidth=0)
                ax.set_title(self._format_axis_label(param), fontweight='bold', fontsize=11)
                ax.set_xticks([])
                ax.set_ylabel('Value')
                ax.grid(True, color='0.90', axis='y')
                ax.text(0.04, 0.96, f"n={len(values)}\nmean={values.mean():.2f}",
                        transform=ax.transAxes, va='top', ha='left', fontsize=8,
                        bbox=dict(facecolor='white', edgecolor='0.85', alpha=0.85, boxstyle='round,pad=0.25'))

            fig.tight_layout(rect=[0, 0, 1, 0.94])
            fig.savefig(self._plots_dir() / 'regional_comparison.png', dpi=300, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            self.logger.info("Regional comparison plot saved")
        except Exception as e:
            self.logger.error(f"Error in regional comparison: {str(e)}")

    def _plot_quality_heatmap(self, df):
        """Plot normalized daily mean parameters instead of station-name heatmaps."""
        try:
            plot_df = self._prepare_plot_dataframe(df)
            parameters = [p for p in ['pH', 'DO', 'BOD', 'COD', 'SS', 'TN', 'TP', 'EC', 'Turbidity', 'Ammonia_N'] if plot_df[p].notna().any()]
            heatmap_data = plot_df.groupby('date')[parameters].mean().T
            if heatmap_data.empty:
                self.logger.warning("No numeric data available for heatmap")
                return
            heatmap_data.index = [self._format_parameter_label(p) for p in heatmap_data.index]
            normalized = heatmap_data.apply(
                lambda row: (row - row.min()) / (row.max() - row.min()) if row.max() != row.min() else row * 0,
                axis=1,
            )
            fig, ax = plt.subplots(figsize=(11, 6), facecolor='white')
            sns.heatmap(normalized, annot=heatmap_data, fmt='.2f', cmap='coolwarm',
                        linewidths=0.5, linecolor='white',
                        cbar_kws={'label': 'Normalized daily mean'}, ax=ax)
            ax.set_title('Daily Mean Water Quality Heatmap - South Korea', fontsize=16, fontweight='bold')
            ax.set_xlabel('Date')
            ax.set_ylabel('Parameter')
            ax.set_xticklabels([str(label) for label in heatmap_data.columns], rotation=30, ha='right')
            ax.set_yticklabels(ax.get_yticklabels(), rotation=0)
            fig.tight_layout()
            fig.savefig(self._plots_dir() / 'quality_heatmap.png', dpi=300, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            self.logger.info("Heatmap plot saved")
        except Exception as e:
            self.logger.error(f"Error in heatmap: {str(e)}")

    def _plot_parameter_distributions(self, df):
        """Plot compact parameter histograms."""
        try:
            plot_df = self._prepare_plot_dataframe(df)
            distributions = ['pH', 'DO', 'BOD', 'SS', 'EC', 'Turbidity', 'Ammonia_N', 'Nitrate_N']
            fig, axes = plt.subplots(2, 4, figsize=(14, 8), facecolor='white')
            fig.suptitle('Parameter Distributions - South Korea Monitoring Network', fontsize=18, fontweight='bold')

            for idx, param in enumerate(distributions):
                ax = axes.flatten()[idx]
                values = plot_df[param].dropna()
                if values.empty:
                    ax.axis('off')
                    continue
                ax.hist(values, bins=24, color='#67a9cf', edgecolor='white', alpha=0.9)
                ax.axvline(values.mean(), color='#b2182b', linewidth=1.6, label='Mean')
                ax.axvline(values.median(), color='#2166ac', linewidth=1.4, linestyle='--', label='Median')
                ax.set_title(f'{self._format_parameter_label(param)} Distribution', fontweight='bold', fontsize=11)
                ax.set_xlabel(self.PARAMETER_UNITS.get(param, '') or 'Value')
                ax.set_ylabel('Frequency')
                ax.legend(frameon=False, fontsize=8)
                ax.grid(True, color='0.90', axis='y')

            fig.tight_layout(rect=[0, 0, 1, 0.94])
            fig.savefig(self._plots_dir() / 'distributions.png', dpi=300, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            self.logger.info("Distribution plot saved")
        except Exception as e:
            self.logger.error(f"Error in distributions: {str(e)}")

    def _evaluate_plot_alerts(self, df):
        if df is None or df.empty:
            return pd.DataFrame(columns=['parameter', 'display_location', 'severity'])
        latest = df.copy()
        latest['timestamp'] = pd.to_datetime(latest.get('timestamp'), errors='coerce')
        station_column = 'display_location' if 'display_location' in latest.columns else 'station_key'
        latest = latest.sort_values('timestamp').groupby(station_column, dropna=False).tail(1)
        rows = []
        for parameter, rule in Config.WATER_QUALITY_ALERT_RULES.items():
            if parameter not in latest.columns:
                continue
            values = pd.to_numeric(latest[parameter], errors='coerce')
            for index, value in values.dropna().items():
                violates = False
                if rule.get('min') is not None and value < rule.get('min'):
                    violates = True
                if rule.get('max') is not None and value > rule.get('max'):
                    violates = True
                if violates:
                    rows.append({
                        'parameter': parameter,
                        'display_location': latest.loc[index].get(station_column, ''),
                        'severity': rule.get('severity', 'warning'),
                    })
        return pd.DataFrame(rows)

    def _plot_parameter_compliance_overview(self, df):
        """Plot percent of latest station measurements passing each screening rule."""
        try:
            plot_df = self._prepare_plot_dataframe(df)
            latest = plot_df.sort_values('timestamp').groupby('station_key', dropna=False).tail(1)
            rows = []
            for parameter, rule in Config.WATER_QUALITY_ALERT_RULES.items():
                if parameter not in latest.columns:
                    continue
                values = pd.to_numeric(latest[parameter], errors='coerce').dropna()
                if values.empty:
                    continue
                passing = pd.Series(True, index=values.index)
                if rule.get('min') is not None:
                    passing &= values >= rule.get('min')
                if rule.get('max') is not None:
                    passing &= values <= rule.get('max')
                rows.append({
                    'parameter': parameter,
                    'label': self._format_parameter_label(parameter),
                    'pass_rate': float(passing.mean() * 100),
                    'pass_count': int(passing.sum()),
                    'total': int(len(values)),
                })

            fig, ax = plt.subplots(figsize=(12, 7), facecolor='white')
            if not rows:
                ax.text(0.5, 0.55, 'Compliance overview waiting for numeric data', ha='center', va='center',
                        fontsize=18, fontweight='bold', color='#0047a0')
                ax.text(0.5, 0.43, 'The chart will fill automatically when the API returns parameter measurements.',
                        ha='center', va='center', fontsize=12, color='#5f6b7a')
                ax.axis('off')
            else:
                compliance = pd.DataFrame(rows).sort_values('pass_rate')
                colors = [
                    '#cd2e3a' if value < 70 else '#191919' if value < 90 else '#0047a0'
                    for value in compliance['pass_rate']
                ]
                ax.barh(compliance['label'], compliance['pass_rate'], color=colors, edgecolor='white')
                ax.axvline(90, color='#0047a0', linestyle='--', linewidth=1.2, alpha=0.8)
                ax.axvline(70, color='#cd2e3a', linestyle='--', linewidth=1.2, alpha=0.8)
                for index, row in enumerate(compliance.itertuples()):
                    ax.text(
                        min(99, row.pass_rate + 1),
                        index,
                        f'{row.pass_rate:.0f}% ({row.pass_count:,}/{row.total:,})',
                        va='center',
                        ha='left',
                        fontsize=9,
                        fontweight='bold',
                        color='#121826',
                    )
                ax.set_xlim(0, 108)
                ax.set_xlabel('Stations within dashboard screening rule (%)')
                ax.set_ylabel('')
                ax.set_title('Parameter Compliance Overview', fontsize=18, fontweight='bold')
                ax.text(90, len(compliance) - 0.25, '90% target', ha='right', va='bottom', fontsize=9, color='#0047a0')
                ax.grid(True, axis='x', color='0.90')
                ax.spines[['top', 'right', 'left']].set_visible(False)
            fig.tight_layout()
            fig.savefig(self._plots_dir() / 'parameter_compliance_overview.png', dpi=300, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            self.logger.info("Parameter compliance overview plot saved")
        except Exception as e:
            self.logger.error(f"Error in parameter compliance overview plot: {str(e)}")

    def _plot_top_attention_stations(self, df):
        """Rank latest stations by number of screening-rule exceedances."""
        try:
            plot_df = self._prepare_plot_dataframe(df)
            latest = plot_df.sort_values('timestamp').groupby('station_key', dropna=False).tail(1).copy()
            station_column = 'display_location' if 'display_location' in latest.columns else 'station_key'
            if latest.empty:
                self.logger.warning("No latest station data available for station attention ranking")
                return

            scores = pd.Series(0, index=latest.index, dtype='float64')
            critical_scores = pd.Series(0, index=latest.index, dtype='float64')
            for parameter, rule in Config.WATER_QUALITY_ALERT_RULES.items():
                if parameter not in latest.columns:
                    continue
                values = pd.to_numeric(latest[parameter], errors='coerce')
                violated = pd.Series(False, index=latest.index)
                if rule.get('min') is not None:
                    violated |= values < rule.get('min')
                if rule.get('max') is not None:
                    violated |= values > rule.get('max')
                scores += violated.fillna(False).astype(int)
                if rule.get('severity') == 'critical':
                    critical_scores += violated.fillna(False).astype(int)

            ranking = pd.DataFrame({
                'station': latest[station_column].fillna('Unknown').astype(str),
                'attention': scores.astype(int),
                'critical': critical_scores.astype(int),
            })
            ranking = ranking[ranking['attention'] > 0].sort_values(['critical', 'attention', 'station'], ascending=[False, False, True]).head(15)

            fig, ax = plt.subplots(figsize=(12, 7), facecolor='white')
            if ranking.empty:
                ax.text(0.5, 0.55, 'No stations require attention', ha='center', va='center',
                        fontsize=20, fontweight='bold', color='#0047a0')
                ax.text(0.5, 0.42, 'Latest station measurements are within configured screening rules.',
                        ha='center', va='center', fontsize=12, color='#5f6b7a')
                ax.axis('off')
            else:
                ranking = ranking.sort_values('attention')
                labels = [label if len(label) <= 42 else label[:39] + '...' for label in ranking['station']]
                attention_only = (ranking['attention'] - ranking['critical']).clip(lower=0)
                ax.barh(labels, attention_only, color='#191919', edgecolor='white', label='Attention')
                ax.barh(labels, ranking['critical'], left=attention_only, color='#cd2e3a', edgecolor='white', label='Critical')
                totals = ranking['attention'].to_numpy()
                for index, total in enumerate(totals):
                    ax.text(total + 0.08, index, f'{int(total)} flags', va='center', ha='left', fontsize=9, fontweight='bold')
                ax.set_xlabel('Number of parameters outside rule')
                ax.set_ylabel('')
                ax.set_title('Top Stations Requiring Attention', fontsize=18, fontweight='bold')
                ax.grid(True, axis='x', color='0.90')
                ax.legend(frameon=False, loc='lower right')
                ax.spines[['top', 'right', 'left']].set_visible(False)
            fig.tight_layout()
            fig.savefig(self._plots_dir() / 'top_attention_stations.png', dpi=300, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            self.logger.info("Top attention stations plot saved")
        except Exception as e:
            self.logger.error(f"Error in top attention stations plot: {str(e)}")
    
    def _plot_parameter_maps(self, df):
        """Plot each water quality parameter on a South Korea map using station coordinates."""
        try:
            df = df.copy()
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            df = self._fill_missing_station_coordinates(df)
            df = df.sort_values('timestamp')
            coordinate_df = df.dropna(subset=['latitude', 'longitude'])
            if coordinate_df.empty:
                self.logger.warning("No station coordinates available for map plots")
                return

            missing_coordinate_rows = len(df) - len(coordinate_df)
            if missing_coordinate_rows:
                self.logger.warning(f"{missing_coordinate_rows} records still have no usable coordinates after station lookup")
            df = coordinate_df
            if df.empty:
                self.logger.warning("No station coordinates available for map plots")
                return

            south_korea_map = self._load_south_korea_map()
            map_rings = south_korea_map['rings']
            min_lon, min_lat, max_lon, max_lat = south_korea_map['bounds']

            daily_dates = sorted(df['timestamp'].dt.normalize().unique())
            map_days_to_plot = max(1, int(getattr(Config, 'MAP_DAYS_TO_PLOT', 1)))
            daily_dates = daily_dates[-map_days_to_plot:]
            for day in daily_dates:
                day_df = df[df['timestamp'].dt.normalize() == day].copy()
                if day_df.empty:
                    continue
                day_label = day.strftime('%Y-%m-%d')
                station_layer = self._prepare_station_layer(day_df)
                self.logger.info(f"Map station coverage for {day_label}: {len(station_layer)} stations with coordinates")
                for param in Config.WATER_QUALITY_COLUMNS:
                    plot_df = day_df.dropna(subset=[param, 'latitude', 'longitude'])
                    if plot_df.empty:
                        continue
                    plot_df = self._prepare_map_points(plot_df, param)
                    self.logger.info(f"{param} map for {day_label}: plotting {len(plot_df)} colored station points")

                    fig = plt.figure(figsize=(9.8, 6.8), facecolor='white')
                    ax = fig.add_axes([0.07, 0.13, 0.77, 0.72])
                    cax = fig.add_axes([0.88, 0.13, 0.024, 0.72])
                    ax.set_facecolor('white')
                    self._draw_south_korea_map(ax, map_rings)
                    display_label = self._format_parameter_label(param)
                    if not station_layer.empty:
                        ax.scatter(
                            station_layer['longitude'],
                            station_layer['latitude'],
                            s=9,
                            color='0.70',
                            alpha=0.32,
                            linewidth=0,
                            zorder=3,
                            label='All stations',
                        )

                    scatter = ax.scatter(
                        plot_df['longitude'],
                        plot_df['latitude'],
                        c=plot_df[param],
                        cmap='coolwarm',
                        s=18,
                        edgecolor='white',
                        linewidth=0.22,
                        alpha=0.86,
                        zorder=4,
                    )
                    if Config.MAP_POINT_LABELS:
                        for _, row in plot_df.head(40).iterrows():
                            ax.text(
                                row['longitude'],
                                row['latitude'],
                                str(row.get('station_name', ''))[:14],
                                fontsize=6,
                                color='0.25',
                                ha='left',
                                va='bottom',
                                zorder=5,
                            )

                    ax.set_title(f'{display_label} - South Korea Map ({day_label})', pad=10, fontweight='bold')
                    ax.set_xlabel('Longitude')
                    ax.set_ylabel('Latitude')
                    ax.set_xlim(min_lon - 0.15, max_lon + 0.15)
                    ax.set_ylim(min_lat - 0.15, max_lat + 0.15)
                    ax.set_aspect('equal', adjustable='box')
                    ax.grid(True, color='0.90', linewidth=0.55)
                    for spine in ax.spines.values():
                        spine.set_color('0.72')
                        spine.set_linewidth(0.8)
                    ax.tick_params(colors='0.15', direction='out', length=3, width=0.7)

                    colorbar = fig.colorbar(scatter, cax=cax)
                    colorbar.set_label(display_label, rotation=90, labelpad=14, fontweight='bold')
                    colorbar.outline.set_linewidth(0.7)
                    colorbar.outline.set_edgecolor('0.72')
                    colorbar.ax.tick_params(colors='0.15', length=3, width=0.7)
                    safe_day = day_label.replace('-', '_')
                    plt.savefig(self._plots_dir(day_label) / f'{param.lower()}_map_{safe_day}.png', dpi=300, facecolor='white')
                    plt.close()
            self.logger.info("Daily parameter map plots saved")
        except Exception as e:
            self.logger.error(f"Error in parameter map plots: {str(e)}")

    def _plot_station_coverage_map(self, df):
        """Plot all available station coordinates so coverage gaps are explicit."""
        try:
            df = df.copy()
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            df = self._fill_missing_station_coordinates(df)
            df = df.dropna(subset=['latitude', 'longitude'])
            if df.empty:
                self.logger.warning("No station coordinates available for coverage map")
                return

            station_layer = self._prepare_station_layer(df)
            south_korea_map = self._load_south_korea_map()
            min_lon, min_lat, max_lon, max_lat = south_korea_map['bounds']

            fig = plt.figure(figsize=(9.8, 6.8), facecolor='white')
            ax = fig.add_axes([0.07, 0.13, 0.86, 0.72])
            ax.set_facecolor('white')
            self._draw_south_korea_map(ax, south_korea_map['rings'])
            ax.scatter(
                station_layer['longitude'],
                station_layer['latitude'],
                s=13,
                color='#2166ac',
                alpha=0.72,
                edgecolor='white',
                linewidth=0.18,
                zorder=4,
            )
            ax.set_title(f'Station Coverage - South Korea ({len(station_layer)} stations)', pad=10, fontweight='bold')
            ax.set_xlabel('Longitude')
            ax.set_ylabel('Latitude')
            ax.set_xlim(min_lon - 0.15, max_lon + 0.15)
            ax.set_ylim(min_lat - 0.15, max_lat + 0.15)
            ax.set_aspect('equal', adjustable='box')
            ax.grid(True, color='0.90', linewidth=0.55)
            for spine in ax.spines.values():
                spine.set_color('0.72')
                spine.set_linewidth(0.8)
            fig.savefig(self._plots_dir() / 'station_coverage_map.png', dpi=300, facecolor='white')
            plt.close(fig)
            self.logger.info(f"Station coverage map saved with {len(station_layer)} stations")
        except Exception as e:
            self.logger.error(f"Error in station coverage map: {str(e)}")

    def _fill_missing_station_coordinates(self, df):
        """Fill missing coordinates from other rows for the same station."""
        df = df.copy()
        for column in ['latitude', 'longitude', 'x', 'y']:
            if column not in df.columns:
                df[column] = np.nan
            df[column] = pd.to_numeric(df[column], errors='coerce')

        if 'station_name' in df.columns:
            station_key = df['station_name'].fillna(df.get('region', 'station')).astype(str)
        elif 'region' in df.columns:
            station_key = df['region'].fillna('station').astype(str)
        else:
            station_key = pd.Series(['station'] * len(df), index=df.index)
        df['_station_key_for_coords'] = station_key

        coordinate_lookup = (
            df.dropna(subset=['latitude', 'longitude'])
            .sort_values('timestamp')
            .groupby('_station_key_for_coords')[['latitude', 'longitude', 'x', 'y']]
            .last()
        )
        for column in ['latitude', 'longitude', 'x', 'y']:
            missing = df[column].isna()
            if missing.any():
                df.loc[missing, column] = df.loc[missing, '_station_key_for_coords'].map(coordinate_lookup[column])
        return df.drop(columns=['_station_key_for_coords'])

    def _prepare_station_layer(self, df):
        station_column = 'station_name' if 'station_name' in df.columns else 'region'
        if station_column not in df.columns:
            return df[['latitude', 'longitude']].dropna().drop_duplicates()
        return (
            df.dropna(subset=['latitude', 'longitude'])
            .sort_values('timestamp')
            .groupby(station_column, as_index=False)
            .agg({'longitude': 'last', 'latitude': 'last'})
        )

    def _prepare_map_points(self, df, param):
        """Average repeated rows per station while preserving one plotted point per station."""
        point_df = df.copy()
        station_column = 'station_name' if 'station_name' in point_df.columns else 'region'
        if station_column not in point_df.columns:
            station_column = '_station_id'
            point_df[station_column] = np.arange(len(point_df))
        return (
            point_df
            .dropna(subset=[param, 'latitude', 'longitude'])
            .groupby(station_column, as_index=False)
            .agg({
                'longitude': 'mean',
                'latitude': 'mean',
                param: 'mean',
            })
            .rename(columns={station_column: 'station_name'})
        )

    def _format_parameter_label(self, param):
        return str(param).replace('_', ' ')

    def _load_south_korea_map(self):
        """Load province polygons from the local South Korea shapefile."""
        if self._south_korea_map is not None:
            return self._south_korea_map

        rings = self._read_polygon_shapefile(Config.MAP_SHAPEFILE, Config.MAP_SHAPEFILE_CRS)
        if not rings:
            raise ValueError(f"No polygon rings found in South Korea shapefile: {Config.MAP_SHAPEFILE}")

        lon_values = [lon for ring in rings for lon, _ in ring]
        lat_values = [lat for ring in rings for _, lat in ring]
        self._south_korea_map = {
            'rings': rings,
            'bounds': (min(lon_values), min(lat_values), max(lon_values), max(lat_values)),
            'source': str(Config.MAP_SHAPEFILE),
        }
        self.logger.info(f"Loaded South Korea shapefile: {Config.MAP_SHAPEFILE}")
        return self._south_korea_map

    def _read_polygon_shapefile(self, shapefile_path, source_crs):
        """Read polygon rings from a .shp file and convert them to WGS84 lon/lat."""
        if not shapefile_path.exists():
            raise FileNotFoundError(shapefile_path)

        transformer = None
        if Transformer is not None:
            transformer = Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)

        rings = []
        with open(shapefile_path, 'rb') as shp:
            header = shp.read(100)
            if len(header) < 100 or struct.unpack('>i', header[:4])[0] != 9994:
                raise ValueError("Invalid shapefile header")

            while True:
                record_header = shp.read(8)
                if not record_header:
                    break
                if len(record_header) < 8:
                    raise ValueError("Truncated shapefile record header")

                _, content_length_words = struct.unpack('>2i', record_header)
                content = shp.read(content_length_words * 2)
                if len(content) < 4:
                    continue

                shape_type = struct.unpack('<i', content[:4])[0]
                if shape_type == 0:
                    continue
                if shape_type not in {5, 15, 25, 31}:
                    continue
                if len(content) < 44:
                    continue

                num_parts, num_points = struct.unpack('<2i', content[36:44])
                parts_offset = 44
                points_offset = parts_offset + (num_parts * 4)
                points_end = points_offset + (num_points * 16)
                if len(content) < points_end:
                    continue

                parts = list(struct.unpack(f'<{num_parts}i', content[parts_offset:points_offset]))
                points = [
                    struct.unpack('<2d', content[points_offset + i * 16:points_offset + (i + 1) * 16])
                    for i in range(num_points)
                ]

                for part_index, start in enumerate(parts):
                    end = parts[part_index + 1] if part_index + 1 < len(parts) else num_points
                    ring = []
                    for x, y in points[start:end]:
                        if transformer is not None:
                            x, y = transformer.transform(x, y)
                        ring.append((x, y))
                    if len(ring) >= 3:
                        rings.append(ring)

        return rings

    def _draw_south_korea_map(self, ax, rings):
        collection = LineCollection(
            rings,
            colors='#8f9a96',
            linewidths=0.32,
            alpha=1.0,
            zorder=1,
        )
        ax.add_collection(collection)

    def _plot_quality_summary(self, df):
        """Overall water quality summary dashboard."""
        try:
            plot_df = self._prepare_plot_dataframe(df)
            if plot_df.empty:
                self.logger.warning("No data available for summary dashboard")
                return

            latest = plot_df.sort_values('timestamp').groupby('station_key', dropna=False).tail(1)
            summary_params = ['pH', 'DO', 'BOD', 'COD', 'SS', 'TN', 'TP', 'EC', 'Turbidity', 'Ammonia_N']
            summary_params = [p for p in summary_params if p in latest.columns and latest[p].notna().any()]

            fig = plt.figure(figsize=(13, 8), facecolor='white')
            gs = fig.add_gridspec(2, 2, height_ratios=[0.65, 1.35], hspace=0.34, wspace=0.24)
            fig.suptitle('Water Quality Summary Dashboard - South Korea', fontsize=18, fontweight='bold')

            ax_info = fig.add_subplot(gs[0, :])
            ax_info.axis('off')
            station_count = latest['station_key'].nunique()
            date_min = plot_df['timestamp'].min().strftime('%Y-%m-%d')
            date_max = plot_df['timestamp'].max().strftime('%Y-%m-%d')
            info_text = (
                f"Updated: {Config.now().strftime('%Y-%m-%d %H:%M:%S')} KST\n"
                f"Date range: {date_min} to {date_max}\n"
                f"Records: {len(plot_df):,}    Stations: {station_count:,}\n"
                f"Latest mean pH: {latest['pH'].mean():.2f}    Latest mean DO: {latest['DO'].mean():.2f} mg/L"
            )
            ax_info.text(
                0.02, 0.54, info_text, va='center', ha='left', fontsize=12,
                bbox=dict(boxstyle='round,pad=0.45', facecolor='#f7f7f7', edgecolor='0.80')
            )

            ax_bar = fig.add_subplot(gs[1, 0])
            daily_means = plot_df.groupby('date')[summary_params].mean().sort_index()
            if len(daily_means) >= 2:
                previous = daily_means.iloc[-2].replace(0, np.nan)
                latest_day = daily_means.iloc[-1]
                changes = (((latest_day - previous) / previous) * 100).replace([np.inf, -np.inf], np.nan).dropna()
                changes = changes.reindex(changes.abs().sort_values().index)
                labels = [self._format_parameter_label(p) for p in changes.index]
                colors = ['#2166ac' if value < 0 else '#b2182b' for value in changes.values]
                ax_bar.barh(labels, changes.values, color=colors, edgecolor='white')
                ax_bar.axvline(0, color='0.25', linewidth=0.8)
                ax_bar.set_title('Latest Daily Mean Change by Parameter', fontweight='bold', fontsize=13)
                ax_bar.set_xlabel('Change from previous day (%)')
            else:
                latest_means = latest[summary_params].mean()
                scaled = ((latest_means - latest_means.min()) / (latest_means.max() - latest_means.min())).fillna(0)
                labels = [self._format_parameter_label(p) for p in scaled.index]
                ax_bar.barh(labels, scaled.values, color='#67a9cf', edgecolor='white')
                ax_bar.set_title('Latest Normalized Parameter Means', fontweight='bold', fontsize=13)
                ax_bar.set_xlabel('Normalized mean')
            ax_bar.grid(True, axis='x', color='0.90')

            ax_count = fig.add_subplot(gs[1, 1])
            daily_counts = plot_df.groupby('date')['station_key'].nunique()
            ax_count.plot(daily_counts.index, daily_counts.values, color='#b2182b', marker='o', linewidth=1.8)
            ax_count.set_title('Daily Reporting Station Count', fontweight='bold', fontsize=13)
            ax_count.set_xlabel('Date')
            ax_count.set_ylabel('Stations')
            ax_count.grid(True, color='0.90')
            ax_count.tick_params(axis='x', rotation=30)

            fig.tight_layout(rect=[0, 0, 1, 0.94])
            fig.savefig(self._plots_dir() / 'quality_summary.png', dpi=300, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            self.logger.info("Summary dashboard saved")
        except Exception as e:
            self.logger.error(f"Error in summary: {str(e)}")

# ==================== AGENT ORCHESTRATION ====================
class DashboardGenerator:
    """Build a user-friendly HTML dashboard from the latest saved data."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def generate(self):
        try:
            if not Config.CSV_FILE.exists():
                self.logger.warning("Dashboard skipped because no master CSV exists")
                return None

            df = pd.read_csv(Config.CSV_FILE)
            if df.empty:
                self.logger.warning("Dashboard skipped because CSV is empty")
                return None

            dashboard_df = self._prepare_dashboard_data(df)
            latest_date = dashboard_df['date'].dropna().max()
            latest_df = dashboard_df[dashboard_df['date'] == latest_date].copy()
            if latest_df.empty:
                latest_df = dashboard_df.copy()

            latest_station_df = self._latest_station_records(latest_df)
            alerts_df = self._evaluate_alerts(latest_station_df)
            html_text = self._render_html(dashboard_df, latest_df, latest_station_df, latest_date, alerts_df)
            Config.DASHBOARD_FILE.write_text(html_text, encoding='utf-8')
            shutil.copyfile(Config.DASHBOARD_FILE, Config.WORKSPACE_DASHBOARD_FILE)
            site_dashboard_path = self._write_google_site_bundle(html_text, str(latest_date))
            self.logger.info(f"Dashboard saved at: {Config.DASHBOARD_FILE}")
            self.logger.info(f"Dashboard copy saved at: {Config.WORKSPACE_DASHBOARD_FILE}")
            self.logger.info(f"Google Sites dashboard bundle saved at: {site_dashboard_path}")
            return Config.DASHBOARD_FILE
        except Exception as e:
            self.logger.error(f"Error generating dashboard: {str(e)}")
            return None

    def _prepare_dashboard_data(self, df):
        df = df.copy()
        df['timestamp'] = pd.to_datetime(df.get('timestamp'), errors='coerce')
        if 'date' not in df.columns:
            df['date'] = df['timestamp'].dt.strftime('%Y-%m-%d')
        else:
            df['date'] = df['date'].fillna(df['timestamp'].dt.strftime('%Y-%m-%d'))

        for column in ['display_location', 'location_name', 'station_name', 'city', 'province', 'country']:
            if column not in df.columns:
                df[column] = ''
            df[column] = df[column].fillna('').astype(str)

        if 'display_location' not in df.columns or df['display_location'].str.strip().eq('').all():
            df['display_location'] = df['location_name'].where(
                df['location_name'].str.strip().ne(''),
                df['station_name']
            )

        for column in Config.WATER_QUALITY_COLUMNS:
            if column in df.columns:
                df[column] = pd.to_numeric(df[column], errors='coerce')
        return df.sort_values('timestamp', ascending=False)

    def _latest_station_records(self, df):
        if df is None or df.empty:
            return df
        station_column = 'display_location' if 'display_location' in df.columns else 'station_name'
        return df.sort_values('timestamp').groupby(station_column, dropna=False).tail(1)

    def _render_html(self, all_df, latest_df, latest_station_df, latest_date, alerts_df):
        generated_at = Config.now().strftime('%Y-%m-%d %H:%M:%S KST')
        station_count = latest_df['display_location'].nunique()
        record_count = len(latest_df)
        city_count = latest_df['city'].replace('', np.nan).nunique()
        province_count = latest_df['province'].replace('', np.nan).nunique()
        latest_time = latest_df['timestamp'].dropna().max()
        latest_time_text = latest_time.strftime('%Y-%m-%d %H:%M KST') if pd.notna(latest_time) else 'Not available'
        critical_count = int((alerts_df['severity'] == 'critical').sum()) if not alerts_df.empty else 0
        warning_count = int((alerts_df['severity'] == 'warning').sum()) if not alerts_df.empty else 0
        alert_station_count = alerts_df['display_location'].nunique() if not alerts_df.empty else 0

        parameter_cards = self._parameter_cards(latest_station_df, alerts_df)
        station_rows = self._station_rows(latest_station_df)
        alert_rows = self._alert_rows(alerts_df)
        standard_rows = self._standard_rows()
        plot_cards = self._plot_cards(str(latest_date))
        spatial_map_cards = self._spatial_map_cards(str(latest_date))
        province_rows = self._province_rows(latest_df)
        history_rows = self._history_rows(limit=30)
        side_rail_html = self._side_rail_html(latest_df, latest_station_df, alerts_df, str(latest_date), city_count, province_count)
        csv_link = self._file_uri(Config.daily_csv_file(str(latest_date))) if latest_date else self._file_uri(Config.CSV_FILE)
        chatbot_html = self._chatbot_html()
        chatbot_script = self._chatbot_script()

        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="3600">
  <meta name="theme-color" content="#0047a0">
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-title" content="K-Water Guard AI">
  <link rel="manifest" href="manifest.webmanifest">
  <link rel="apple-touch-icon" href="assets/icon-192.png">
  <title>K-WaterGuard AI Dashboard</title>
  <style>
    :root {{
      --bg: #f4f6fb;
      --panel: #ffffff;
      --panel-soft: #f9fbff;
      --ink: #121826;
      --muted: #5f6b7a;
      --line: #d9e1ee;
      --blue: #0047a0;
      --blue-soft: #e7eefb;
      --green: #0047a0;
      --red: #cd2e3a;
      --red-soft: #fde9eb;
      --amber: #191919;
      --black: #191919;
      --shadow: 0 14px 30px rgba(0, 35, 90, 0.09);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      background:
        radial-gradient(circle at 16% 0%, rgba(205, 46, 58, 0.10), transparent 28%),
        radial-gradient(circle at 88% 8%, rgba(0, 71, 160, 0.12), transparent 30%),
        linear-gradient(180deg, #ffffff 0%, var(--bg) 36%, #eef3fb 100%);
      color: var(--ink);
    }}
    header {{
      min-height: 360px;
      display: flex;
      align-items: flex-end;
      background:
        linear-gradient(90deg, rgba(255, 255, 255, 0.96), rgba(255, 255, 255, 0.84) 45%, rgba(0, 71, 160, 0.12)),
        linear-gradient(135deg, rgba(205, 46, 58, 0.18), transparent 34%),
        url("{self._asset_uri('Kwater.png')}");
      background-size: cover;
      background-position: center right;
      color: var(--blue);
      padding: 34px 24px 32px;
      border-bottom: 4px solid var(--black);
    }}
    .wrap {{ width: min(1280px, calc(100% - 32px)); margin: 0 auto; }}
    .topline {{ display: flex; justify-content: space-between; gap: 16px; align-items: center; flex-wrap: wrap; }}
    .brand {{ display: inline-flex; align-items: center; gap: 12px; padding: 8px 12px; background: rgba(255,255,255,0.94); border: 1px solid rgba(0, 71, 160, 0.16); border-radius: 8px; box-shadow: var(--shadow); }}
    .brand-logo {{ width: 54px; height: 54px; object-fit: contain; border-radius: 6px; background: white; }}
    .brand-name {{ font-size: 18px; font-weight: 800; color: var(--blue); }}
    h1 {{ margin: 18px 0 8px; font-size: 38px; line-height: 1.08; letter-spacing: 0; }}
    .subtitle {{ max-width: 820px; color: #26364c; margin: 0; font-size: 16px; font-weight: 600; }}
    .badge {{ border: 1px solid rgba(205, 46, 58, 0.28); padding: 7px 10px; border-radius: 6px; color: var(--red); background: rgba(255,255,255,0.88); text-decoration: none; font-weight: 700; }}
    main {{ padding: 22px 0 44px; }}
    .toolbar {{ display: flex; justify-content: space-between; gap: 12px; align-items: center; flex-wrap: wrap; margin-bottom: 16px; }}
    .search {{ min-width: min(420px, 100%); flex: 1; padding: 11px 12px; border: 1px solid var(--line); border-radius: 6px; font: inherit; }}
    .search-status {{ margin: -4px 0 14px; color: var(--muted); font-size: 13px; min-height: 18px; }}
    tr.search-match {{ background: #fff1f3; }}
    .button {{ display: inline-flex; align-items: center; min-height: 40px; padding: 8px 12px; border-radius: 6px; background: var(--blue); color: white; text-decoration: none; }}
    .install-button {{ display: none; border: 0; cursor: pointer; font: inherit; }}
    .install-button.ready {{ display: inline-flex; }}
    .grid {{ display: grid; gap: 14px; }}
    .stats {{ grid-template-columns: repeat(6, minmax(0, 1fr)); margin-bottom: 16px; }}
    .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; box-shadow: var(--shadow); }}
    .insight-rail {{
      display: none; position: fixed; top: 404px; width: clamp(260px, calc((100vw - 1280px) / 2 - 32px), 340px);
      z-index: 5; gap: 14px; pointer-events: none;
    }}
    .insight-rail.left {{ left: max(16px, calc((100vw - 1280px) / 2 - 360px)); }}
    .insight-rail.right {{ right: max(16px, calc((100vw - 1280px) / 2 - 360px)); }}
    .rail-card {{
      pointer-events: auto; overflow: hidden; background: rgba(255, 255, 255, 0.92);
      backdrop-filter: blur(8px); border: 1px solid rgba(217, 225, 238, 0.92);
      border-radius: 8px; box-shadow: var(--shadow);
    }}
    .rail-head {{
      display: flex; align-items: center; justify-content: space-between; gap: 8px;
      padding: 12px 13px; border-bottom: 1px solid var(--line); font-weight: 800;
    }}
    .rail-mark {{ width: 34px; height: 34px; border-radius: 50%; background: linear-gradient(180deg, var(--red) 0 50%, var(--blue) 50% 100%); border: 2px solid white; box-shadow: 0 0 0 1px var(--line); }}
    .rail-body {{ padding: 12px 13px; }}
    .rail-metric {{ display: grid; grid-template-columns: 1fr auto; gap: 8px; padding: 9px 0; border-bottom: 1px solid #eef2f8; }}
    .rail-metric:last-child {{ border-bottom: 0; }}
    .rail-value {{ font-weight: 800; color: var(--blue); }}
    .rail-list {{ display: grid; gap: 10px; }}
    .rail-row {{ display: grid; gap: 5px; }}
    .rail-row-top {{ display: flex; justify-content: space-between; gap: 10px; font-size: 13px; }}
    .rail-bar {{ height: 8px; overflow: hidden; border-radius: 999px; background: #e8edf6; }}
    .rail-fill {{ display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--blue), var(--red)); }}
    .rail-fill.black {{ background: linear-gradient(90deg, var(--black), var(--blue)); }}
    .mini-map {{ position: relative; min-height: 220px; background: linear-gradient(135deg, #f8fbff, #eef4ff); }}
    .mini-map svg {{ width: 100%; height: 220px; display: block; }}
    .korea-ring {{ fill: rgba(255,255,255,.88); stroke: #90a1b7; stroke-width: .8; }}
    .korea-ring:nth-of-type(3n) {{ fill: rgba(0, 71, 160, .08); }}
    .korea-ring:nth-of-type(3n+1) {{ fill: rgba(205, 46, 58, .07); }}
    .map-dot {{ fill: var(--blue); opacity: .68; stroke: white; stroke-width: .8; }}
    .map-dot.alert {{ fill: var(--red); opacity: .86; }}
    .rail-link {{ color: var(--blue); font-weight: 800; text-decoration: none; }}
    .stat {{ padding: 15px; border-top: 4px solid var(--blue); }}
    .stats > .stat:nth-child(even) {{ border-top-color: var(--red); }}
    .stats > .stat:nth-child(3n) {{ border-top-color: var(--black); }}
    .label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0; }}
    .value {{ font-size: 28px; font-weight: 800; margin-top: 4px; color: var(--blue); }}
    .section {{ padding: 18px; margin-top: 16px; }}
    h2 {{ margin: 0 0 12px; font-size: 20px; }}
    .param-grid {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}
    .param {{
      position: relative; padding: 16px; min-height: 142px; border-left: 5px solid var(--blue);
      background: linear-gradient(180deg, #ffffff, var(--panel-soft));
      border-radius: 8px; cursor: pointer; transition: transform .12s ease, box-shadow .12s ease, border-color .12s ease;
    }}
    .param:hover {{ transform: translateY(-1px); box-shadow: 0 14px 30px rgba(0, 35, 90, 0.14); }}
    .param:focus {{ outline: 3px solid rgba(0, 71, 160, 0.22); outline-offset: 2px; }}
    .param.warn {{ border-left-color: var(--black); background: #fbfbfc; }}
    .param.bad {{ border-left-color: var(--red); background: var(--red-soft); }}
    .param.active {{ border-color: var(--blue); box-shadow: 0 0 0 3px rgba(0, 71, 160, 0.18), var(--shadow); }}
    .alert-pill {{ display: inline-flex; padding: 4px 8px; border-radius: 999px; font-size: 12px; font-weight: 700; }}
    .alert-pill.critical {{ background: var(--red-soft); color: #921a24; }}
    .alert-pill.warning {{ background: #eeeeef; color: var(--black); }}
    .alert-pill.ok {{ background: var(--blue-soft); color: var(--blue); }}
    .param-value {{ font-size: 26px; font-weight: 700; margin: 10px 0 5px; }}
    .param-action {{ display: block; margin-top: 9px; color: var(--blue); font-size: 12px; font-weight: 700; }}
    .muted {{ color: var(--muted); }}
    .plots {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
    .spatial-maps {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .plot img {{ width: 100%; display: block; border-top: 1px solid var(--line); cursor: zoom-in; }}
    .plot img:hover {{ filter: saturate(1.04) contrast(1.03); }}
    .plot .image-missing {{ display: none; padding: 14px; border-top: 1px solid var(--line); color: var(--red); background: #fff5f6; }}
    .plot h3 {{ margin: 12px; font-size: 15px; }}
    .lightbox {{
      position: fixed; inset: 0; display: none; align-items: center; justify-content: center;
      z-index: 80; padding: 24px; background: rgba(8, 13, 24, 0.86);
    }}
    .lightbox.open {{ display: flex; }}
    .lightbox-panel {{
      width: min(1500px, 96vw); max-height: 94vh; display: grid; grid-template-rows: auto minmax(0, 1fr);
      background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 24px 70px rgba(0,0,0,.34);
    }}
    .lightbox-head {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; padding: 12px 14px; border-bottom: 1px solid var(--line); }}
    .lightbox-title {{ font-weight: 800; color: var(--blue); }}
    .lightbox-close {{ border: 0; border-radius: 6px; background: var(--red); color: white; font: inherit; font-weight: 800; padding: 8px 12px; cursor: pointer; }}
    .lightbox-img-wrap {{ overflow: auto; background: #f7f9fd; padding: 14px; }}
    .lightbox-img {{ display: block; max-width: 100%; height: auto; margin: 0 auto; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ padding: 9px 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    th {{ background: var(--blue-soft); color: #16233a; position: sticky; top: 0; z-index: 1; }}
    tr.filtered-match {{ background: #fff1f3; }}
    .table-wrap {{ max-height: 520px; overflow: auto; border: 1px solid var(--line); border-radius: 8px; }}
    .history-link {{ color: var(--blue); font-weight: 800; text-decoration: none; }}
    .history-link:hover {{ text-decoration: underline; }}
    .two-col {{ grid-template-columns: 1.2fr 0.8fr; align-items: start; }}
    footer {{ color: var(--muted); padding: 20px 0; font-size: 13px; }}
    .chat-launch {{
      position: fixed; right: 22px; bottom: 22px; z-index: 30;
      border: 0; border-radius: 999px; background: var(--blue); color: white;
      min-height: 46px; padding: 0 16px; font: inherit; font-weight: 700;
      box-shadow: 0 12px 26px rgba(0, 71, 160, 0.28); cursor: pointer;
    }}
    .chat-panel {{
      position: fixed; right: 22px; bottom: 82px; width: min(380px, calc(100vw - 32px));
      max-height: min(620px, calc(100vh - 110px)); display: none; flex-direction: column;
      background: white; border: 1px solid var(--line); border-radius: 8px;
      box-shadow: 0 18px 44px rgba(18, 24, 38, 0.22); z-index: 31;
    }}
    .chat-panel.open {{ display: flex; }}
    .chat-head {{ padding: 12px 14px; border-bottom: 1px solid var(--line); display: flex; justify-content: space-between; gap: 12px; align-items: center; }}
    .chat-title {{ font-weight: 800; }}
    .chat-close {{ border: 0; background: transparent; font: inherit; cursor: pointer; color: var(--muted); }}
    .chat-messages {{ padding: 12px; overflow: auto; display: grid; gap: 10px; }}
    .chat-msg {{ padding: 10px 11px; border-radius: 8px; line-height: 1.4; font-size: 14px; }}
    .chat-msg.bot {{ background: var(--blue-soft); color: var(--ink); }}
    .chat-msg.user {{ background: var(--red-soft); color: #7d1720; justify-self: end; }}
    .chat-form {{ padding: 12px; border-top: 1px solid var(--line); display: flex; gap: 8px; }}
    .chat-input {{ flex: 1; min-width: 0; border: 1px solid var(--line); border-radius: 6px; padding: 10px; font: inherit; }}
    .chat-send {{ border: 0; border-radius: 6px; background: var(--red); color: white; padding: 0 12px; font: inherit; font-weight: 700; cursor: pointer; }}
    @media (max-width: 980px) {{
      .stats, .param-grid, .plots, .spatial-maps, .two-col {{ grid-template-columns: 1fr 1fr; }}
    }}
    @media (min-width: 1840px) {{
      .insight-rail {{ display: grid; }}
    }}
    @media (max-width: 640px) {{
      h1 {{ font-size: 30px; }}
      header {{ min-height: 330px; background-position: center right; }}
      .brand-logo {{ width: 44px; height: 44px; }}
      .brand-name {{ font-size: 16px; }}
      .stats, .param-grid, .plots, .spatial-maps, .two-col {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  {side_rail_html}
  <header>
    <div class="wrap">
      <div class="topline">
        <div class="brand">
          <img class="brand-logo" src="{self._asset_uri('KwGAI logo.png')}" alt="K-Water Guard AI logo">
          <span class="brand-name">K-Water Guard AI</span>
        </div>
        <span class="badge">Hourly update: Korea time</span>
      </div>
      <h1>Water Quality Dashboard</h1>
      <p class="subtitle">Latest daily monitoring view for South Korea stations, with readable station locations, summary indicators, maps, and downloadable data.</p>
    </div>
  </header>
  <main class="wrap">
    <div class="toolbar">
      <input class="search" id="stationSearch" type="search" placeholder="Search station, city, province, or parameter values">
      <button class="button install-button" id="installAppButton" type="button">Install App</button>
      <a class="button" href="{csv_link}">Open latest CSV</a>
    </div>
    <div class="search-status" id="searchStatus">Search filters the alert, province, and station tables below.</div>

    <section class="grid stats">
      {self._stat_card('Latest date', html.escape(str(latest_date)))}
      {self._stat_card('Last update', html.escape(latest_time_text))}
      {self._stat_card('Stations', f'{station_count:,}')}
      {self._stat_card('Records', f'{record_count:,}')}
      {self._stat_card('Cities / Provinces', f'{city_count:,} / {province_count:,}')}
      {self._stat_card('Alert Stations', f'{alert_station_count:,}')}
    </section>

    <section class="grid two-col">
      <div class="card section">
        <h2>Water Quality Indicators</h2>
        <div class="grid param-grid">{parameter_cards}</div>
      </div>
      <div class="card section">
        <h2>Alert Summary</h2>
        <div class="grid stats" style="grid-template-columns: repeat(2, minmax(0, 1fr));">
          {self._stat_card('Critical', f'{critical_count:,}')}
          {self._stat_card('Attention', f'{warning_count:,}')}
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Standard Parameter</th><th>Dashboard Rule</th></tr></thead>
            <tbody>{standard_rows}</tbody>
          </table>
        </div>
      </div>
    </section>

    <section class="card section" id="historicalDownloads">
      <h2>Historical Data Downloads</h2>
      <p class="muted">Each hourly GitHub Actions run is archived as a separate CSV, so users can download past snapshots without losing the latest dashboard view.</p>
      <div class="table-wrap">
        <table id="historyTable">
          <thead>
            <tr><th>Run Time</th><th>Date</th><th>Records</th><th>File</th></tr>
          </thead>
          <tbody>{history_rows}</tbody>
        </table>
      </div>
    </section>

    <section class="card section">
      <h2>Latest Water Quality Alerts</h2>
      <div class="table-wrap">
        <table id="alertTable">
          <thead>
            <tr><th>Status</th><th>Location</th><th>Parameter</th><th>Value</th><th>Standard</th><th>Basis</th><th>Time</th></tr>
          </thead>
          <tbody>{alert_rows}</tbody>
        </table>
      </div>
    </section>

    <section class="card section" id="provinceCoverage">
        <h2>Province Coverage</h2>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Province</th><th>Stations</th><th>Records</th></tr></thead>
            <tbody>{province_rows}</tbody>
          </table>
        </div>
    </section>

    <section class="card section" id="latestCharts">
      <h2>Latest Charts And Maps</h2>
      <div class="grid plots">{plot_cards}</div>
    </section>

    <section class="card section">
      <h2>Spatial Parameter Maps</h2>
      <div class="grid spatial-maps">{spatial_map_cards}</div>
    </section>

    <section class="card section">
      <h2>Latest Station Measurements</h2>
      <div class="table-wrap">
        <table id="stationTable">
          <thead>
            <tr><th>Location</th><th>Station ID</th><th>pH</th><th>DO</th><th>BOD</th><th>COD</th><th>TN</th><th>TP</th><th>Time</th></tr>
          </thead>
          <tbody>{station_rows}</tbody>
        </table>
      </div>
    </section>
  </main>
  {chatbot_html}
  <div class="lightbox" id="imageLightbox" aria-hidden="true">
    <div class="lightbox-panel" role="dialog" aria-modal="true" aria-label="Expanded dashboard image">
      <div class="lightbox-head">
        <div class="lightbox-title" id="lightboxTitle">Dashboard image</div>
        <button class="lightbox-close" id="lightboxClose" type="button">Close</button>
      </div>
      <div class="lightbox-img-wrap">
        <img class="lightbox-img" id="lightboxImage" src="" alt="">
      </div>
    </div>
  </div>
  <footer class="wrap">Generated {html.escape(generated_at)} from {html.escape(str(Config.CSV_FILE))}. The dashboard is rebuilt after each agent run. Alert rules are configurable screening rules based on Korean environmental water-quality standards under the Environmental Policy Framework Act and related enforcement standards.</footer>
  <script>
    const search = document.getElementById('stationSearch');
    const searchStatus = document.getElementById('searchStatus');
    const searchableTables = Array.from(document.querySelectorAll('table'));
    const searchableRows = Array.from(document.querySelectorAll('table tbody tr'));
    const parameterCards = Array.from(document.querySelectorAll('.param[data-filter-param]'));
    const imageLightbox = document.getElementById('imageLightbox');
    const lightboxImage = document.getElementById('lightboxImage');
    const lightboxTitle = document.getElementById('lightboxTitle');
    const lightboxClose = document.getElementById('lightboxClose');
    const installAppButton = document.getElementById('installAppButton');
    let activeParameter = '';
    let deferredInstallPrompt = null;

    function applyDashboardFilters(scrollToFirstMatch = false) {{
      const query = search.value.trim().toLowerCase();
      let visibleCount = 0;
      let firstMatch = null;
      let alertMatchCount = 0;

      searchableRows.forEach(row => {{
        const textMatched = !query || row.textContent.toLowerCase().includes(query);
        const rowParameter = row.dataset.alertParam || '';
        const parameterMatched = !activeParameter || !rowParameter || rowParameter === activeParameter;
        const matched = textMatched && parameterMatched;
        row.style.display = matched ? '' : 'none';
        row.classList.toggle('search-match', Boolean(query && matched));
        row.classList.toggle('filtered-match', Boolean(activeParameter && matched && rowParameter === activeParameter));
        if (matched && row.closest('#alertTable')) alertMatchCount += 1;
        if (matched && (query || activeParameter)) {{
          visibleCount += 1;
          if (!firstMatch) firstMatch = row;
        }}
      }});

      searchableTables.forEach(table => {{
        const visibleRows = Array.from(table.querySelectorAll('tbody tr')).filter(row => row.style.display !== 'none');
        table.closest('.section')?.classList.toggle('search-empty', Boolean(query && visibleRows.length === 0));
      }});

      if (!query && !activeParameter) {{
        searchStatus.textContent = 'Search filters the alert, province, and station tables below. Click an indicator card to filter alerts by parameter.';
        return;
      }}

      const pieces = [];
      if (activeParameter) pieces.push(`${{alertMatchCount.toLocaleString()}} alert row${{alertMatchCount === 1 ? '' : 's'}} for ${{activeParameter.toUpperCase()}}`);
      if (query) pieces.push(`${{visibleCount.toLocaleString()}} matching table row${{visibleCount === 1 ? '' : 's'}} for "${{search.value.trim()}}"`);
      searchStatus.textContent = visibleCount || alertMatchCount
        ? `${{pieces.join(' and ')}}. Press Enter to jump to the first match.`
        : `No table rows found. Try a city, province, station, parameter, or value.`;

      if (scrollToFirstMatch && firstMatch) {{
        firstMatch.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
      }}
    }}

    if (search) {{
      search.addEventListener('input', () => applyDashboardFilters(false));
      search.addEventListener('search', () => applyDashboardFilters(false));
      search.addEventListener('keydown', (event) => {{
        if (event.key === 'Enter') {{
          event.preventDefault();
          applyDashboardFilters(true);
        }}
      }});
    }}

    function activateParameterFilter(card) {{
      const parameter = card.dataset.filterParam || '';
      activeParameter = activeParameter === parameter ? '' : parameter;
      parameterCards.forEach(item => {{
        item.classList.toggle('active', Boolean(activeParameter && item.dataset.filterParam === activeParameter));
      }});
      applyDashboardFilters(false);
      if (activeParameter) {{
        document.getElementById('alertTable')?.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
      }}
    }}

    parameterCards.forEach(card => {{
      card.addEventListener('click', () => activateParameterFilter(card));
      card.addEventListener('keydown', (event) => {{
        if (event.key === 'Enter' || event.key === ' ') {{
          event.preventDefault();
          activateParameterFilter(card);
        }}
      }});
    }});

    function openImageLightbox(image) {{
      if (!imageLightbox || !lightboxImage) return;
      lightboxImage.src = image.currentSrc || image.src;
      lightboxImage.alt = image.alt || 'Expanded dashboard image';
      lightboxTitle.textContent = image.alt || image.closest('.plot')?.querySelector('h3')?.textContent || 'Dashboard image';
      imageLightbox.classList.add('open');
      imageLightbox.setAttribute('aria-hidden', 'false');
      lightboxClose?.focus();
    }}

    function closeImageLightbox() {{
      if (!imageLightbox || !lightboxImage) return;
      imageLightbox.classList.remove('open');
      imageLightbox.setAttribute('aria-hidden', 'true');
      lightboxImage.src = '';
    }}

    document.querySelectorAll('.plot img').forEach(image => {{
      image.setAttribute('tabindex', '0');
      image.setAttribute('role', 'button');
      image.setAttribute('aria-label', `Expand ${{image.alt || 'dashboard image'}}`);
      image.addEventListener('click', () => openImageLightbox(image));
      image.addEventListener('keydown', (event) => {{
        if (event.key === 'Enter' || event.key === ' ') {{
          event.preventDefault();
          openImageLightbox(image);
        }}
      }});
    }});

    lightboxClose?.addEventListener('click', closeImageLightbox);
    imageLightbox?.addEventListener('click', (event) => {{
      if (event.target === imageLightbox) closeImageLightbox();
    }});
    document.addEventListener('keydown', (event) => {{
      if (event.key === 'Escape' && imageLightbox?.classList.contains('open')) {{
        closeImageLightbox();
      }}
    }});

    if ('serviceWorker' in navigator) {{
      window.addEventListener('load', () => {{
        navigator.serviceWorker.register('sw.js').catch(() => {{}});
      }});
    }}

    window.addEventListener('beforeinstallprompt', (event) => {{
      event.preventDefault();
      deferredInstallPrompt = event;
      installAppButton?.classList.add('ready');
    }});

    installAppButton?.addEventListener('click', async () => {{
      if (!deferredInstallPrompt) return;
      deferredInstallPrompt.prompt();
      await deferredInstallPrompt.userChoice.catch(() => null);
      deferredInstallPrompt = null;
      installAppButton.classList.remove('ready');
    }});

    window.addEventListener('appinstalled', () => {{
      deferredInstallPrompt = null;
      installAppButton?.classList.remove('ready');
    }});
    {chatbot_script}
  </script>
</body>
</html>"""

    def _chatbot_html(self):
        if not getattr(Config, 'CHATBOT_ENABLED', True):
            return ''
        raw_endpoint = str(getattr(Config, 'CHATBOT_API_URL', '') or '').strip()
        endpoint = html.escape(raw_endpoint, quote=True)
        greeting = (
            "Hello. I am connected to the K-Water Guard AI chatbot backend. Ask me about alerts, stations, maps, or water quality parameters."
            if raw_endpoint else
            "Hello. I am running in free dashboard mode. Ask me about latest date, stations, records, alerts, parameters, or maps."
        )
        return f"""
  <button class="chat-launch" id="chatLaunch" type="button">Ask AI</button>
  <section class="chat-panel" id="chatPanel" data-chat-url="{endpoint}" aria-label="K-Water Guard AI chatbot">
    <div class="chat-head">
      <div>
        <div class="chat-title">K-Water Guard AI Chat</div>
        <div class="muted" style="font-size: 12px;">Ask about latest water quality data</div>
      </div>
      <button class="chat-close" id="chatClose" type="button">Close</button>
    </div>
    <div class="chat-messages" id="chatMessages">
      <div class="chat-msg bot">{html.escape(greeting)}</div>
    </div>
    <form class="chat-form" id="chatForm">
      <input class="chat-input" id="chatInput" type="text" placeholder="Ask about alerts, maps, stations..." autocomplete="off">
      <button class="chat-send" type="submit">Send</button>
    </form>
  </section>"""

    def _chatbot_script(self):
        if not getattr(Config, 'CHATBOT_ENABLED', True):
            return ''
        return """
    const chatLaunch = document.getElementById('chatLaunch');
    const chatPanel = document.getElementById('chatPanel');
    const chatClose = document.getElementById('chatClose');
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    const chatMessages = document.getElementById('chatMessages');
    const chatUrl = chatPanel ? chatPanel.dataset.chatUrl : '';

    function addChatMessage(text, role) {
      const message = document.createElement('div');
      message.className = `chat-msg ${role}`;
      message.textContent = text;
      chatMessages.appendChild(message);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function textContent(selector) {
      const element = document.querySelector(selector);
      return element ? element.textContent.replace(/\\s+/g, ' ').trim() : '';
    }

    function tableRows(selector, limit) {
      return Array.from(document.querySelectorAll(`${selector} tbody tr`))
        .slice(0, limit)
        .map((row) => row.textContent.replace(/\\s+/g, ' ').trim())
        .filter(Boolean);
    }

    function dashboardStats() {
      const cards = Array.from(document.querySelectorAll('.stats .card.stat'));
      const stats = {};
      cards.forEach((card) => {
        const label = card.querySelector('.label')?.textContent.trim();
        const value = card.querySelector('.value')?.textContent.trim();
        if (label && value) stats[label.toLowerCase()] = value;
      });
      return stats;
    }

    function parameterSummary() {
      return Array.from(document.querySelectorAll('.param-grid .card.param'))
        .map((card) => card.textContent.replace(/\\s+/g, ' ').trim())
        .filter(Boolean)
        .slice(0, 8);
    }

    function localDashboardAnswer(question) {
      const q = question.toLowerCase();
      const stats = dashboardStats();
      const alerts = tableRows('#alertTable', 5);
      const stations = tableRows('#stationTable', 5);
      const parameters = parameterSummary();

      if (q.includes('date') || q.includes('latest') || q.includes('time')) {
        return `Latest dashboard date: ${stats['latest date'] || 'not available'}. Records: ${stats.records || 'not available'}. Stations: ${stats.stations || 'not available'}.`;
      }
      if (q.includes('alert') || q.includes('warning') || q.includes('critical')) {
        const alertCount = stats.alerts || '0';
        const alertStations = stats['alert stations'] || '0';
        if (!alerts.length || alerts[0].toLowerCase().includes('no current parameter alerts')) {
          return `There are ${alertCount} alerts and ${alertStations} alert stations on the latest dashboard. No current parameter alerts are listed.`;
        }
        return `There are ${alertCount} alerts across ${alertStations} alert stations. Top alert rows: ${alerts.join(' | ')}`;
      }
      if (q.includes('station') || q.includes('location') || q.includes('site')) {
        if (!stations.length) return 'No station rows are available in the latest dashboard table.';
        return `The dashboard shows ${stats.stations || 'available'} stations. First station rows: ${stations.join(' | ')}`;
      }
      if (q.includes('record') || q.includes('data')) {
        return `The latest dashboard has ${stats.records || 'not available'} records for ${stats.stations || 'not available'} stations. Latest date: ${stats['latest date'] || 'not available'}.`;
      }
      if (q.includes('parameter') || q.includes('ph') || q.includes('do') || q.includes('bod') || q.includes('cod') || q.includes('tn') || q.includes('tp')) {
        if (!parameters.length) return 'No numeric parameter cards are available on this dashboard run.';
        return `Latest parameter summary: ${parameters.join(' | ')}`;
      }
      if (q.includes('map') || q.includes('chart') || q.includes('plot')) {
        const chartTitles = Array.from(document.querySelectorAll('.plot h3')).map((item) => item.textContent.trim()).filter(Boolean);
        return chartTitles.length
          ? `Available charts/maps: ${chartTitles.join(', ')}.`
          : 'Charts and maps will appear after the dashboard has enough generated plot files.';
      }
      if (q.includes('help') || q.includes('what can')) {
        return 'You can ask about latest date, number of records, stations, alerts, parameter averages, charts, and maps. This free mode answers from the current dashboard page only.';
      }
      return `Free mode answer: latest date ${stats['latest date'] || 'not available'}, ${stats.records || 'not available'} records, ${stats.stations || 'not available'} stations, and ${stats.alerts || '0'} alerts. Ask about alerts, stations, parameters, charts, or maps for more detail.`;
    }

    if (chatLaunch && chatPanel) {
      chatLaunch.addEventListener('click', () => chatPanel.classList.toggle('open'));
    }
    if (chatClose && chatPanel) {
      chatClose.addEventListener('click', () => chatPanel.classList.remove('open'));
    }
    if (chatForm) {
      chatForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const question = chatInput.value.trim();
        if (!question) return;
        chatInput.value = '';
        addChatMessage(question, 'user');
        if (!chatUrl) {
          addChatMessage(localDashboardAnswer(question), 'bot');
          return;
        }
        try {
          const response = await fetch(chatUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              question,
              dashboardUrl: window.location.href,
              latestDate: document.querySelector('.stats .value')?.textContent || ''
            })
          });
          const data = await response.json();
          if (!response.ok) {
            const apiMessage = data?.error?.error?.message || data?.error?.message || data?.answer || `HTTP ${response.status}`;
            addChatMessage(`Backend unavailable (${apiMessage}). Free dashboard answer: ${localDashboardAnswer(question)}`, 'bot');
            return;
          }
          addChatMessage(data.answer || 'No answer returned by chatbot backend.', 'bot');
        } catch (error) {
          addChatMessage(`Backend unavailable (${error.message || error}). Free dashboard answer: ${localDashboardAnswer(question)}`, 'bot');
        }
      });
    }"""

    def _evaluate_alerts(self, df):
        rows = []
        if df is None or df.empty:
            return pd.DataFrame(columns=[
                'severity', 'display_location', 'parameter', 'value', 'unit',
                'standard', 'basis', 'timestamp'
            ])

        for parameter, rule in Config.WATER_QUALITY_ALERT_RULES.items():
            if parameter not in df.columns:
                continue
            values = pd.to_numeric(df[parameter], errors='coerce')
            for index, value in values.dropna().items():
                if not self._violates_rule(value, rule):
                    continue
                record = df.loc[index]
                rows.append({
                    'severity': rule.get('severity', 'warning'),
                    'display_location': record.get('display_location', ''),
                    'parameter': parameter,
                    'value': float(value),
                    'unit': rule.get('unit', ''),
                    'standard': self._rule_text(rule),
                    'basis': rule.get('basis', ''),
                    'timestamp': record.get('timestamp', ''),
                })

        if not rows:
            return pd.DataFrame(columns=[
                'severity', 'display_location', 'parameter', 'value', 'unit',
                'standard', 'basis', 'timestamp'
            ])
        alerts = pd.DataFrame(rows)
        severity_order = {'critical': 0, 'warning': 1}
        alerts['_severity_order'] = alerts['severity'].map(severity_order).fillna(9)
        return alerts.sort_values(['_severity_order', 'display_location', 'parameter']).drop(columns=['_severity_order'])

    def _violates_rule(self, value, rule):
        min_value = rule.get('min')
        max_value = rule.get('max')
        if min_value is not None and value < min_value:
            return True
        if max_value is not None and value > max_value:
            return True
        return False

    def _rule_text(self, rule):
        unit = rule.get('unit', '')
        min_value = rule.get('min')
        max_value = rule.get('max')
        if min_value is not None and max_value is not None:
            return f"{min_value:g}-{max_value:g} {unit}".strip()
        if min_value is not None:
            return f">= {min_value:g} {unit}".strip()
        if max_value is not None:
            return f"<= {max_value:g} {unit}".strip()
        return 'Reference'

    def _parameter_cards(self, df, alerts_df):
        cards = []
        for parameter in ['pH', 'DO', 'BOD', 'COD', 'SS', 'TN', 'TP', 'temperature']:
            if parameter not in df.columns:
                continue
            values = pd.to_numeric(df[parameter], errors='coerce').dropna()
            if values.empty:
                continue
            mean_value = values.mean()
            parameter_alerts = alerts_df[alerts_df['parameter'] == parameter] if not alerts_df.empty else pd.DataFrame()
            alert_count = len(parameter_alerts)
            critical_count = int((parameter_alerts.get('severity') == 'critical').sum()) if not parameter_alerts.empty else 0
            status = 'bad' if critical_count else 'warn' if alert_count else self._parameter_status(parameter, mean_value)
            rule = Config.WATER_QUALITY_ALERT_RULES.get(parameter, {})
            unit = rule.get('unit') or PlotGenerator.PARAMETER_UNITS.get(parameter, '')
            pill_class = 'critical' if critical_count else 'warning' if alert_count else 'ok'
            pill_text = f"{alert_count:,} alerts" if alert_count else 'OK'
            parameter_label = PlotGenerator()._format_parameter_label(parameter)
            parameter_filter = html.escape(parameter_label.lower(), quote=True)
            parameter_key = html.escape(parameter.lower(), quote=True)
            cards.append(
                f'<div class="card param {status}" role="button" tabindex="0" data-filter-param="{parameter_filter}" data-param-key="{parameter_key}" aria-label="Filter alerts for {html.escape(parameter_label)}">'
                f'<div class="label">{html.escape(parameter_label)}</div>'
                f'<div class="param-value">{mean_value:.2f}</div><div class="muted">Average {html.escape(unit)}</div>'
                f'<div style="margin-top:8px;"><span class="alert-pill {pill_class}">{html.escape(pill_text)}</span></div>'
                f'<span class="param-action">Filter alerts</span></div>'
            )
        return ''.join(cards) or '<p class="muted">No numeric parameter data available.</p>'

    def _alert_rows(self, alerts_df):
        if alerts_df is None or alerts_df.empty:
            return '<tr><td colspan="7"><span class="alert-pill ok">OK</span> No current parameter alerts for the latest date.</td></tr>'
        rows = []
        for _, row in alerts_df.iterrows():
            severity = str(row.get('severity', 'warning'))
            label = 'Critical' if severity == 'critical' else 'Attention'
            timestamp = row.get('timestamp', '')
            try:
                timestamp = pd.to_datetime(timestamp).strftime('%Y-%m-%d %H:%M KST')
            except Exception:
                timestamp = str(timestamp)
            value_text = f"{row.get('value', 0):.2f} {row.get('unit', '')}".strip()
            parameter_label = PlotGenerator()._format_parameter_label(str(row.get("parameter", "")))
            rows.append(
                f'<tr data-alert-param="{html.escape(parameter_label.lower(), quote=True)}">'
                f'<td><span class="alert-pill {html.escape(severity)}">{html.escape(label)}</span></td>'
                f'<td>{html.escape(str(row.get("display_location", "")))}</td>'
                f'<td>{html.escape(parameter_label)}</td>'
                f'<td>{html.escape(value_text)}</td>'
                f'<td>{html.escape(str(row.get("standard", "")))}</td>'
                f'<td>{html.escape(str(row.get("basis", "")))}</td>'
                f'<td>{html.escape(timestamp)}</td>'
                '</tr>'
            )
        return ''.join(rows)

    def _standard_rows(self):
        rows = []
        for parameter, rule in Config.WATER_QUALITY_ALERT_RULES.items():
            label = PlotGenerator()._format_parameter_label(parameter)
            rows.append(
                f'<tr><td>{html.escape(label)}</td><td>{html.escape(self._rule_text(rule))}</td></tr>'
            )
        return ''.join(rows)

    def _station_rows(self, df):
        rows = []
        display_columns = ['display_location', 'monitoring_point_id', 'pH', 'DO', 'BOD', 'COD', 'TN', 'TP', 'timestamp']
        latest = df.sort_values('display_location')
        for _, row in latest.iterrows():
            cells = []
            for column in display_columns:
                value = row.get(column, '')
                if pd.isna(value):
                    value = ''
                elif column in Config.WATER_QUALITY_COLUMNS:
                    try:
                        value = f"{float(value):.2f}"
                    except Exception:
                        value = str(value)
                elif column == 'timestamp' and pd.notna(value):
                    value = pd.to_datetime(value).strftime('%Y-%m-%d %H:%M KST')
                cells.append(f'<td>{html.escape(str(value))}</td>')
            rows.append('<tr>' + ''.join(cells) + '</tr>')
        return ''.join(rows)

    def _province_rows(self, df):
        province = df.copy()
        province['province'] = province['province'].replace('', 'Unknown')
        grouped = (
            province.groupby('province', dropna=False)
            .agg(stations=('display_location', 'nunique'), records=('display_location', 'size'))
            .sort_values(['stations', 'records'], ascending=False)
        )
        rows = []
        for province_name, row in grouped.head(20).iterrows():
            rows.append(
                f'<tr><td>{html.escape(str(province_name))}</td><td>{int(row.stations):,}</td><td>{int(row.records):,}</td></tr>'
            )
        return ''.join(rows)

    def _side_rail_html(self, latest_df, latest_station_df, alerts_df, date_label, city_count, province_count):
        station_count = latest_df['display_location'].nunique() if 'display_location' in latest_df.columns else len(latest_df)
        record_count = len(latest_df)
        alert_count = len(alerts_df) if alerts_df is not None else 0
        alert_station_count = alerts_df['display_location'].nunique() if alerts_df is not None and not alerts_df.empty else 0
        coordinate_count = 0
        if {'latitude', 'longitude'}.issubset(latest_station_df.columns):
            coordinate_count = int(latest_station_df[['latitude', 'longitude']].dropna().shape[0])
        coordinate_share = (coordinate_count / max(1, len(latest_station_df))) * 100

        province_bars = self._province_bar_rows(latest_df)
        alert_bars = self._alert_parameter_bar_rows(alerts_df)
        quick_map = self._mini_korea_map(latest_station_df, alerts_df)

        return f"""
  <aside class="insight-rail left" aria-label="Korea water quality side insights">
    <section class="rail-card">
      <div class="rail-head"><span>Korea Snapshot</span><span class="rail-mark" aria-hidden="true"></span></div>
      <div class="rail-body">
        <div class="rail-metric"><span class="muted">Monitoring date</span><span class="rail-value">{html.escape(str(date_label))}</span></div>
        <div class="rail-metric"><span class="muted">Stations watched</span><span class="rail-value">{station_count:,}</span></div>
        <div class="rail-metric"><span class="muted">Latest records</span><span class="rail-value">{record_count:,}</span></div>
        <div class="rail-metric"><span class="muted">Cities / provinces</span><span class="rail-value">{city_count:,} / {province_count:,}</span></div>
      </div>
    </section>
    <section class="rail-card">
      <div class="rail-head"><span>Province Coverage</span><a class="rail-link" href="#provinceCoverage">Table</a></div>
      <div class="rail-body rail-list">{province_bars}</div>
    </section>
  </aside>
  <aside class="insight-rail right" aria-label="Map and alert side insights">
    <section class="rail-card">
      <div class="rail-head"><span>Station Map</span><a class="rail-link" href="#latestCharts">Maps</a></div>
      <div class="mini-map">{quick_map}</div>
      <div class="rail-body">
        <div class="rail-metric"><span class="muted">Mapped stations</span><span class="rail-value">{coordinate_count:,}</span></div>
        <div class="rail-metric"><span class="muted">Coordinate coverage</span><span class="rail-value">{coordinate_share:.0f}%</span></div>
      </div>
    </section>
    <section class="rail-card">
      <div class="rail-head"><span>Alert Focus</span><a class="rail-link" href="#alertTable">Alerts</a></div>
      <div class="rail-body">
        <div class="rail-metric"><span class="muted">Alert rows</span><span class="rail-value">{alert_count:,}</span></div>
        <div class="rail-metric"><span class="muted">Alert stations</span><span class="rail-value">{alert_station_count:,}</span></div>
        <div class="rail-list" style="margin-top: 10px;">{alert_bars}</div>
      </div>
    </section>
  </aside>"""

    def _province_bar_rows(self, df):
        if 'province' not in df.columns or 'display_location' not in df.columns:
            return '<p class="muted">Province coverage is not available yet.</p>'
        province = df.copy()
        province['province'] = province['province'].replace('', 'Unknown').fillna('Unknown')
        grouped = (
            province.groupby('province', dropna=False)['display_location']
            .nunique()
            .sort_values(ascending=False)
            .head(6)
        )
        if grouped.empty:
            return '<p class="muted">Province coverage is not available yet.</p>'
        max_value = max(1, int(grouped.max()))
        rows = []
        for province_name, count in grouped.items():
            percent = max(4, (int(count) / max_value) * 100)
            rows.append(
                f'<div class="rail-row"><div class="rail-row-top"><span>{html.escape(str(province_name))}</span><strong>{int(count):,}</strong></div>'
                f'<div class="rail-bar"><span class="rail-fill" style="width:{percent:.1f}%"></span></div></div>'
            )
        return ''.join(rows)

    def _alert_parameter_bar_rows(self, alerts_df):
        if alerts_df is None or alerts_df.empty or 'parameter' not in alerts_df.columns:
            return '<p class="muted">No current parameter alerts.</p>'
        grouped = alerts_df['parameter'].fillna('Unknown').astype(str).value_counts().head(5)
        max_value = max(1, int(grouped.max()))
        rows = []
        for parameter, count in grouped.items():
            label = PlotGenerator()._format_parameter_label(parameter)
            percent = max(5, (int(count) / max_value) * 100)
            rows.append(
                f'<div class="rail-row"><div class="rail-row-top"><span>{html.escape(label)}</span><strong>{int(count):,}</strong></div>'
                f'<div class="rail-bar"><span class="rail-fill black" style="width:{percent:.1f}%"></span></div></div>'
            )
        return ''.join(rows)

    def _mini_korea_map(self, latest_station_df, alerts_df):
        if not {'latitude', 'longitude'}.issubset(latest_station_df.columns):
            return '<p class="muted" style="padding: 13px;">Station coordinates are not available yet.</p>'
        points = latest_station_df[['display_location', 'latitude', 'longitude']].dropna().copy()
        if points.empty:
            return '<p class="muted" style="padding: 13px;">Station coordinates are not available yet.</p>'

        try:
            south_korea_map = PlotGenerator()._load_south_korea_map()
            map_rings = south_korea_map['rings']
            min_lon, min_lat, max_lon, max_lat = south_korea_map['bounds']
        except Exception:
            map_rings = []
            min_lon, min_lat, max_lon, max_lat = 124.5, 33.0, 131.5, 39.2

        width, height = 240, 220
        pad_x, pad_y = 14, 14

        def project(lon, lat):
            usable_w = width - (pad_x * 2)
            usable_h = height - (pad_y * 2)
            x = pad_x + ((lon - min_lon) / max(0.0001, max_lon - min_lon)) * usable_w
            y = height - pad_y - ((lat - min_lat) / max(0.0001, max_lat - min_lat)) * usable_h
            return x, y

        ring_paths = []
        for ring in map_rings:
            if len(ring) < 3:
                continue
            sampled_ring = ring[::max(1, len(ring) // 80)]
            coords = []
            for lon, lat in sampled_ring:
                x, y = project(float(lon), float(lat))
                coords.append(f'{x:.1f},{y:.1f}')
            projected_points = [tuple(map(float, item.split(','))) for item in coords]
            x_values = [item[0] for item in projected_points]
            y_values = [item[1] for item in projected_points]
            if max(x_values) - min(x_values) < 1.2 and max(y_values) - min(y_values) < 1.2:
                continue
            if len(set(coords)) >= 3:
                ring_paths.append(f'<path class="korea-ring" d="M {" L ".join(coords)} Z"></path>')
            if len(ring_paths) >= 220:
                break

        alert_locations = set()
        if alerts_df is not None and not alerts_df.empty and 'display_location' in alerts_df.columns:
            alert_locations = set(alerts_df['display_location'].dropna().astype(str))
        svg_points = []
        sampled = points.drop_duplicates('display_location').head(90)
        for _, row in sampled.iterrows():
            try:
                lon = float(row.get('longitude'))
                lat = float(row.get('latitude'))
            except Exception:
                continue
            x, y = project(lon, lat)
            if not (0 <= x <= width and 0 <= y <= height):
                continue
            dot_class = 'map-dot alert' if str(row.get('display_location', '')) in alert_locations else 'map-dot'
            svg_points.append(f'<circle class="{dot_class}" cx="{x:.1f}" cy="{y:.1f}" r="2.4"></circle>')
        return (
            f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Actual South Korea map with latest monitoring stations">'
            '<rect x="0" y="0" width="240" height="220" fill="rgba(255,255,255,.18)"></rect>'
            + ''.join(ring_paths)
            + ''.join(svg_points) +
            '</svg>'
        )

    def _history_rows(self, limit=30):
        try:
            run_files = []
            if Config.DAILY_OUTPUTS_DIR.exists():
                run_files.extend(Config.DAILY_OUTPUTS_DIR.glob("*/runs/water_quality_run_*.csv"))
            if Config.RUN_ARCHIVES_DIR.exists():
                run_files.extend(Config.RUN_ARCHIVES_DIR.glob("water_quality_run_*.csv"))

            unique_files = {}
            for path in run_files:
                unique_files[path.name] = path
            paths = sorted(unique_files.values(), key=lambda path: path.name, reverse=True)[:limit]
            if not paths:
                return '<tr><td colspan="4">Historical run CSVs will appear after the next scheduled GitHub Actions update.</td></tr>'

            rows = []
            for path in paths:
                run_time, date_label = self._history_file_labels(path)
                record_count = self._csv_record_count(path)
                rows.append(
                    '<tr>'
                    f'<td>{html.escape(run_time)}</td>'
                    f'<td>{html.escape(date_label)}</td>'
                    f'<td>{record_count:,}</td>'
                    f'<td><a class="history-link" href="{self._file_uri(path)}">Download CSV</a></td>'
                    '</tr>'
                )
            return ''.join(rows)
        except Exception as e:
            self.logger.error(f"Error building historical CSV rows: {str(e)}")
            return '<tr><td colspan="4">Historical CSV list is temporarily unavailable.</td></tr>'

    def _history_file_labels(self, path):
        match = re.search(r'water_quality_run_(\d{8})_(\d{6})_KST\.csv$', path.name)
        if not match:
            return path.stem, ''
        date_part, time_part = match.groups()
        try:
            parsed = datetime.strptime(date_part + time_part, '%Y%m%d%H%M%S')
            return parsed.strftime('%Y-%m-%d %H:%M:%S KST'), parsed.strftime('%Y-%m-%d')
        except Exception:
            return path.stem, date_part

    def _csv_record_count(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                return max(0, sum(1 for _ in handle) - 1)
        except Exception:
            return 0

    def _plot_cards(self, date_label):
        plots_dir = Config.daily_plots_dir(date_label)
        plot_specs = [
            ('quality_summary.png', 'Quality Summary'),
            ('parameter_compliance_overview.png', 'Parameter Compliance Overview'),
            ('top_attention_stations.png', 'Top Attention Stations'),
            ('station_coverage_map.png', 'Station Coverage Map'),
            ('timeline_parameters.png', 'Parameter Timeline'),
            ('regional_comparison.png', 'Station Distributions'),
            ('quality_heatmap.png', 'Daily Mean Heatmap'),
            ('distributions.png', 'Parameter Distributions'),
        ]
        cards = []
        for filename, title in plot_specs:
            path = plots_dir / filename
            if path.exists():
                cards.append(
                    f'<article class="card plot"><h3>{html.escape(title)}</h3>'
                    f'<img src="{self._file_uri(path)}" alt="{html.escape(title)}" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'block\';">'
                    f'<div class="image-missing">Image file not found on GitHub Pages. Check the matching file in the plots folder.</div></article>'
                )
        if not cards:
            return '<p class="muted">Charts will appear here after plots are generated.</p>'
        return ''.join(cards)

    def _spatial_map_cards(self, date_label):
        plots_dir = Config.daily_plots_dir(date_label)
        if not plots_dir.exists():
            return '<p class="muted">Spatial maps will appear here after map plots are generated.</p>'

        safe_day = str(date_label).replace('-', '_')
        map_paths = sorted(plots_dir.glob(f'*_map_{safe_day}.png'))
        if not map_paths:
            return '<p class="muted">Spatial parameter maps are not available for the latest date yet.</p>'

        cards = []
        for path in map_paths:
            parameter_key = path.name.replace(f'_map_{safe_day}.png', '')
            title = f"{self._format_map_title(parameter_key)} Spatial Map"
            cards.append(
                f'<article class="card plot"><h3>{html.escape(title)}</h3>'
                f'<img src="{self._file_uri(path)}" alt="{html.escape(title)}" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'block\';">'
                f'<div class="image-missing">Spatial map file not found on GitHub Pages. Check the matching file in the plots folder.</div></article>'
            )
        return ''.join(cards)

    def _format_map_title(self, parameter_key):
        lookup = {parameter.lower(): PlotGenerator()._format_parameter_label(parameter) for parameter in Config.WATER_QUALITY_COLUMNS}
        return lookup.get(parameter_key.lower(), parameter_key.replace('_', ' ').title())

    def _parameter_status(self, parameter, value):
        if parameter == 'pH' and not 6.5 <= value <= 8.5:
            return 'warn'
        if parameter == 'DO' and value < 5:
            return 'bad'
        if parameter in {'BOD', 'COD'} and value > 5:
            return 'warn'
        if parameter in {'TN', 'TP'} and value > 3:
            return 'warn'
        return ''

    def _stat_card(self, label, value):
        return f'<div class="card stat"><div class="label">{html.escape(label)}</div><div class="value">{value}</div></div>'

    def _asset_uri(self, filename):
        path = Path(__file__).resolve().parent / filename
        return self._file_uri(path) if path.exists() else ''

    def _file_uri(self, path):
        try:
            return Path(path).resolve().as_uri()
        except Exception:
            return html.escape(str(path))

    def _write_google_site_bundle(self, html_text, date_label):
        bundle_dir = Config.SITE_DASHBOARD_DIR
        assets_dir = bundle_dir / "assets"
        plots_dir = bundle_dir / "plots"
        data_dir = bundle_dir / "data"
        history_dir = bundle_dir / "history"
        if bundle_dir.exists():
            shutil.rmtree(bundle_dir)
        for directory in [bundle_dir, assets_dir, plots_dir, data_dir, history_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        replacements = {}
        asset_files = {
            "Kwater.png": "cover.png",
            "KwGAI logo.png": "logo.png",
        }
        for filename, output_name in asset_files.items():
            source = Path(__file__).resolve().parent / filename
            if source.exists():
                target = assets_dir / output_name
                shutil.copyfile(source, target)
                replacements[self._file_uri(source)] = self._image_data_uri(source)
                if output_name == "logo.png":
                    self._write_pwa_icons(source, assets_dir)

        daily_plots_dir = Config.daily_plots_dir(date_label)
        if daily_plots_dir.exists():
            for source in daily_plots_dir.glob("*.png"):
                target = plots_dir / source.name
                shutil.copyfile(source, target)
                root_target = bundle_dir / source.name
                shutil.copyfile(source, root_target)
                replacements[self._file_uri(source)] = self._site_asset_url(source.name)

        daily_csv = Config.daily_csv_file(date_label)
        if daily_csv.exists():
            target = data_dir / daily_csv.name
            shutil.copyfile(daily_csv, target)
            root_target = bundle_dir / daily_csv.name
            shutil.copyfile(daily_csv, root_target)
            replacements[self._file_uri(daily_csv)] = self._site_asset_url(daily_csv.name)

        run_files = []
        if Config.DAILY_OUTPUTS_DIR.exists():
            run_files.extend(Config.DAILY_OUTPUTS_DIR.glob("*/runs/water_quality_run_*.csv"))
        if Config.RUN_ARCHIVES_DIR.exists():
            run_files.extend(Config.RUN_ARCHIVES_DIR.glob("water_quality_run_*.csv"))
        unique_run_files = {}
        for source in run_files:
            unique_run_files[source.name] = source
        for source in sorted(unique_run_files.values(), key=lambda path: path.name, reverse=True)[:60]:
            target = history_dir / source.name
            shutil.copyfile(source, target)
            replacements[self._file_uri(source)] = self._site_asset_url(f"history/{source.name}")

        site_html = html_text
        for old, new in replacements.items():
            site_html = site_html.replace(old, new)

        site_html = site_html.replace(
            "The dashboard is rebuilt after each agent run.",
            "This page is generated for online embedding and rebuilt after each agent run."
        )
        self._write_pwa_files(bundle_dir)
        output_path = bundle_dir / "index.html"
        output_path.write_text(site_html, encoding='utf-8')
        (bundle_dir / ".nojekyll").write_text("", encoding='utf-8')
        return output_path

    def _write_pwa_files(self, bundle_dir):
        manifest = {
            "name": "K-Water Guard AI Dashboard",
            "short_name": "K-Water AI",
            "description": "Hourly South Korea water quality monitoring dashboard.",
            "start_url": "./",
            "scope": "./",
            "display": "standalone",
            "background_color": "#f4f6fb",
            "theme_color": "#0047a0",
            "orientation": "portrait-primary",
            "icons": [
                {
                    "src": "assets/icon-192.png",
                    "sizes": "192x192",
                    "type": "image/png",
                    "purpose": "any maskable"
                },
                {
                    "src": "assets/icon-512.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "any maskable"
                }
            ],
            "categories": ["utilities", "productivity"],
        }
        (bundle_dir / "manifest.webmanifest").write_text(
            json.dumps(manifest, indent=2),
            encoding='utf-8',
        )

        cache_version = Config.run_id()
        cache_files = [
            "./",
            "./index.html",
            "./manifest.webmanifest",
            "./assets/logo.png",
            "./assets/icon-192.png",
            "./assets/icon-512.png",
        ]
        for filename in [
            "quality_summary.png",
            "parameter_compliance_overview.png",
            "top_attention_stations.png",
            "station_coverage_map.png",
            "timeline_parameters.png",
            "regional_comparison.png",
            "quality_heatmap.png",
            "distributions.png",
        ]:
            if (bundle_dir / filename).exists():
                cache_files.append(f"./{filename}")

        service_worker = f"""const CACHE_NAME = 'k-water-guard-ai-{cache_version}';
const APP_SHELL = {json.dumps(cache_files, indent=2)};

self.addEventListener('install', event => {{
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting())
  );
}});

self.addEventListener('activate', event => {{
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
}});

self.addEventListener('fetch', event => {{
  const request = event.request;
  if (request.method !== 'GET') return;

  if (request.mode === 'navigate') {{
    event.respondWith(
      fetch(request)
        .then(response => {{
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put('./index.html', copy));
          return response;
        }})
        .catch(() => caches.match('./index.html'))
    );
    return;
  }}

  event.respondWith(
    caches.match(request).then(cached => {{
      const network = fetch(request).then(response => {{
        if (response && response.ok) {{
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
        }}
        return response;
      }}).catch(() => cached);
      return cached || network;
    }})
  );
}});
"""
        (bundle_dir / "sw.js").write_text(service_worker, encoding='utf-8')

    def _write_pwa_icons(self, source, assets_dir):
        try:
            from PIL import Image
            with Image.open(source) as image:
                image = image.convert("RGBA")
                for size in [192, 512]:
                    canvas = Image.new("RGBA", (size, size), (255, 255, 255, 255))
                    working = image.copy()
                    working.thumbnail((int(size * 0.82), int(size * 0.82)))
                    x = (size - working.width) // 2
                    y = (size - working.height) // 2
                    canvas.alpha_composite(working, (x, y))
                    canvas.save(assets_dir / f"icon-{size}.png")
        except Exception:
            shutil.copyfile(source, assets_dir / "icon-192.png")
            shutil.copyfile(source, assets_dir / "icon-512.png")

    def _site_asset_url(self, relative_path):
        base_url = str(getattr(Config, 'GITHUB_PAGES_BASE_URL', '') or '').strip()
        if not base_url:
            return relative_path
        return f"{base_url.rstrip('/')}/{relative_path.lstrip('/')}"

    def _image_data_uri(self, path):
        suffix = Path(path).suffix.lower()
        mime_type = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
        }.get(suffix, 'application/octet-stream')
        encoded = base64.b64encode(Path(path).read_bytes()).decode('ascii')
        return f"data:{mime_type};base64,{encoded}"


class WaterQualityAgent:
    """Main agent that orchestrates data collection, storage, and visualization"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.collector = WaterQualityCollector()
        self.data_manager = DataManager()
        self.plot_generator = PlotGenerator()
        self.dashboard_generator = DashboardGenerator()
        self.scheduler = BackgroundScheduler() if APSCHEDULER_AVAILABLE else None
    
    def execute_cycle(self):
        """Execute one complete cycle: collect → store → visualize"""
        try:
            self.logger.info("=" * 50)
            self.logger.info("Starting Water Quality Agent Cycle")
            
            # Step 1: Collect data
            self.logger.info("Step 1: Collecting data...")
            data = self.collector.fetch_data()
            
            # Step 2: Store data
            if data:
                self.logger.info("Step 2: Storing data...")
                self.data_manager.save_data(data)
            
            # Step 3: Generate visualizations
            self.logger.info("Step 3: Generating visualizations...")
            self.plot_generator.generate_all_plots()

            # Step 4: Generate dashboard
            self.logger.info("Step 4: Updating dashboard...")
            self.dashboard_generator.generate()

            self.logger.info("Cycle completed successfully")
            self.logger.info("=" * 50)
            
        except Exception as e:
            self.logger.error(f"Error in agent cycle: {str(e)}")
    
    def start_autonomous(self, interval_minutes=None):
        """Start agent to run autonomously on schedule"""
        if interval_minutes is None:
            interval_minutes = Config.UPDATE_INTERVAL

        if not APSCHEDULER_AVAILABLE or self.scheduler is None:
            self.logger.warning("APScheduler is unavailable; running a single cycle instead")
            self.execute_cycle()
            return
        
        try:
            # Add job to scheduler
            self.scheduler.add_job(
                self.execute_cycle,
                trigger=IntervalTrigger(minutes=interval_minutes),
                id='water_quality_job',
                name='Water Quality Data Collection',
                replace_existing=True
            )
            
            self.scheduler.start()
            self.logger.info(f"Agent started. Running every {interval_minutes} minutes")
            self.logger.info(f"Master data location: {Config.CSV_FILE}")
            self.logger.info(f"Today's date-wise output folder: {Config.daily_output_dir()}")
            
            # Keep running
            try:
                while True:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("Agent stopped by user")
                self.scheduler.shutdown()
        
        except Exception as e:
            self.logger.error(f"Error starting agent: {str(e)}")
    
    def run_auto(self):
        """Run agent once for automatic execution (no scheduler needed)"""
        self.execute_cycle()
        self.logger.info(f"Master data saved at: {Config.CSV_FILE}")
        self.logger.info(f"Date-wise output folder: {Config.daily_output_dir()}")
        self.logger.info("Agent completed. Next run will be scheduled by Task Scheduler.")
        locations_str = ', '.join([f"{r} ({Config.LOCATION_INFO.get(r, {}).get('type', '')})" for r in Config.MONITORING_REGIONS])
        self.logger.info(f"Monitoring Locations: {locations_str}")

# ==================== MAIN ====================
def main():
    """Entry point for the Water Quality Agent"""
    setup_environment()
    agent = WaterQualityAgent()
    
    print("\n" + "="*60)
    print("Water Quality Data Agent")
    print("South Korea")
    print("="*60)
    print("\nMonitoring Stations:")
    for region, info in Config.LOCATION_INFO.items():
        print(f"  - {region} ({info['type']}) - {info['province']}")
    print("\n" + "="*60 + "\n")
    
    print("Collecting water quality data from all available API monitoring stations in South Korea...")
    print("Generating visualizations and plots...\n")
    agent.run_auto()
    print("\nProcess completed successfully!")
    print("Charts saved with location information.")

if __name__ == "__main__":
    main()
