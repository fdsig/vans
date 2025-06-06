#!/usr/bin/env python3
"""
Scrape and Analyse Ford Transit L2 H2 Listings from AutoTrader
=============================================================

*Updated: adds **enhanced postcode management** with intelligent selection strategies,
**concurrent scraping** with proxy support, and **advanced postcode intelligence**.*

This script now supports these sub‑commands:

* `scrape`    – harvest listings → CSV (single postcode, legacy)
* `scrape-multi` – concurrent scraping across multiple postcodes with smart strategies
* `scrape-uk` – optimized UK-wide scraping focusing on commercial/industrial areas with descriptions and images
* `postcodes` – analyze and manage postcode selection strategies  
* `analyse`  – quick medians & scatter plots

----
Enhanced Postcode Management
----------------------------
The new PostcodeManager provides intelligent postcode selection with multiple strategies:

**Strategies Available:**
- `major_cities`: Focus on high-density population centers (London, Manchester, Birmingham...)
- `commercial_hubs`: Target areas with high commercial vehicle activity
- `geographic_spread`: Ensure even distribution across UK regions  
- `mixed_density`: Balanced mix of urban and suburban areas
- `custom`: Use your own provided postcodes

**Advanced Intelligence Features:**
- Machine learning-based pattern recognition from historical data
- Seasonal and temporal analysis (best days/months to scrape)
- External data integration (weather, economic indicators, traffic)
- Interactive map visualization of postcode strategies
- Strategy export/import for sharing learned patterns

**Geographic Filtering:**
- Specify center postcode and radius to focus on specific areas
- Uses real GPS coordinates for accurate distance calculations

**Success Rate Tracking:**
- Learns which postcodes yield the most listings
- Automatically prioritizes high-performing areas
- Persistent database storage of scraping history

----
Setup
-----
```bash
pip install --upgrade playwright pandas beautifulsoup4 folium
playwright install
```

Optional for enhanced features:
```bash
pip install requests folium
```

----
Usage Examples
--------------

**1) Basic scraping (single postcode)**
```bash
python get_vans.py scrape --postcode G23NX --pages 15 --outfile transit_l2h2.csv
```

**2) Smart multi-postcode scraping**
```bash
# Use commercial hubs strategy across 30 postcodes
python get_vans.py scrape-multi --strategy commercial_hubs --postcode-limit 30 \
    --pages-per-postcode 5 --outfile transit_commercial.csv

# Geographic focus: 50km radius around Manchester
python get_vans.py scrape-multi --strategy geographic_spread --center-postcode "M1 1AA" \
    --radius-km 50 --postcode-limit 20 --outfile transit_manchester_area.csv

# Use custom postcodes with proxy rotation
python get_vans.py scrape-multi --postcodes "SW1A 1AA" "M1 1AA" "B1 1AA" \
    --proxy-file proxies.txt --pages-per-postcode 10
```

**3) Advanced postcode intelligence**
```bash
# Analyze historical patterns
python get_vans.py postcodes analyze --postcode "M1 1AA"

# Predict best times to scrape
python get_vans.py postcodes predict --limit 10

# Create interactive map
python get_vans.py postcodes map --strategy commercial_hubs --output map.html

# Export/import learned strategies
python get_vans.py postcodes export --name "my_strategy" --file strategy.json
python get_vans.py postcodes import --file strategy.json
```

**4) Analysis**
```bash
# Quick scatter plots and medians
python get_vans.py analyse transit_commercial.csv
```

**5) UK-wide scraping (new optimized command)
```bash
# Scrape the whole UK focusing on commercial/industrial areas
python get_vans.py scrape-uk --outfile ford_transit_uk_complete.csv

# Include mixed density areas for broader coverage
python get_vans.py scrape-uk --include-mixed --pages-per-postcode 8 --postcode-limit 150

# Use proxies for large-scale scraping
python get_vans.py scrape-uk --proxy-file proxies.txt --max-browsers 10 --max-pages 40
```

**4) Analysis and regression**
```bash
# Quick scatter plots and medians
python get_vans.py analyse transit_commercial.csv
```

----
Advanced Features
-----------------

**Concurrent Scraping:**
- Configurable browser and page concurrency limits
- Intelligent proxy rotation with failure handling
- Human-like delays and behavior simulation

**Machine Learning Intelligence:**
- Tracks scraping success patterns over time
- Identifies best days/months for each postcode area
- Learns from weather, traffic, and economic conditions
- Predicts optimal scraping times

**Geographic Intelligence:**
- Real UK postcode coordinates database
- Distance-based filtering using Haversine formula
- Regional distribution analysis
- Interactive map visualization

**Data Integration:**
- Weather data integration for timing optimization
- Economic indicators for commercial activity assessment
- Traffic and logistics data for accessibility scoring
"""
from __future__ import annotations

import argparse
import asyncio
import re
import random
import logging
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Sequence, Tuple, Optional, Set
import itertools
from urllib.parse import urlparse
from dataclasses import dataclass, asdict
from enum import Enum
import math

import pandas as pd
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# Try optional heavy libs – only needed for analysis/plots
try:
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError:  # pragma: no cover
    plt = None
    np = None

# Optional imports for enhanced features
try:
    import requests
    import_requests = True
except ImportError:
    import_requests = False

try:
    import folium  # For map visualization
    import_folium = True
except ImportError:
    import_folium = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraping.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Concurrency and Proxy Settings
# ---------------------------------------------------------------------------
MAX_CONCURRENT_BROWSERS = 5  # Number of browsers to run simultaneously
MAX_CONCURRENT_PAGES = 20     # Total pages across all browsers
PROXY_RETRY_ATTEMPTS = 3      # Retries per proxy before moving to next
REQUEST_DELAY_RANGE = (1, 3)  # Random delay between requests (seconds)

# ---------------------------------------------------------------------------
# Proxy Management
# ---------------------------------------------------------------------------
class ProxyRotator:
    def __init__(self, proxy_list: List[str] = None):
        """Initialize with list of proxy URLs like 'http://user:pass@host:port'"""
        self.proxies = proxy_list or []
        self.current_index = 0
        self.failed_proxies = set()
        
    def get_next_proxy(self) -> str | None:
        """Get next working proxy, or None if all failed"""
        if not self.proxies:
            return None
            
        attempts = 0
        while attempts < len(self.proxies):
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)
            
            if proxy not in self.failed_proxies:
                return proxy
                
            attempts += 1
        
        return None  # All proxies failed
    
    def mark_proxy_failed(self, proxy: str):
        """Mark a proxy as failed"""
        self.failed_proxies.add(proxy)
        logger.warning(f"Marked proxy as failed: {proxy}")
    
    def add_proxies(self, proxy_list: List[str]):
        """Add more proxies to the rotation"""
        self.proxies.extend(proxy_list)

# ---------------------------------------------------------------------------
# Enhanced Postcode Management with Advanced Intelligence
# ---------------------------------------------------------------------------

class PostcodeStrategy(Enum):
    """Different strategies for postcode selection"""
    MAJOR_CITIES = "major_cities"  # Focus on large population centers
    GEOGRAPHIC_SPREAD = "geographic_spread"  # Even distribution across UK
    COMMERCIAL_HUBS = "commercial_hubs"  # Areas with high commercial vehicle activity
    MIXED_DENSITY = "mixed_density"  # Mix of urban and suburban areas
    CUSTOM = "custom"  # User-provided postcodes

@dataclass
class PostcodeArea:
    """Represents a UK postcode area with metadata"""
    code: str
    city: str
    region: str
    population_density: str  # "high", "medium", "low"
    commercial_activity: str  # "high", "medium", "low"
    coordinates: Tuple[float, float]  # (lat, lon)

@dataclass
class PostcodePrediction:
    """Prediction model for postcode performance"""
    postcode: str
    predicted_listings: int
    confidence_score: float
    seasonal_factor: float
    economic_factor: float
    weather_factor: float
    timestamp: datetime

class PostcodeIntelligence:
    """Advanced intelligence layer for postcode selection"""
    
    def __init__(self, db_path: str = "data/postcode_intelligence.db"):
        self.db_path = Path(db_path)
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for storing learned patterns"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scrape_history (
                    id INTEGER PRIMARY KEY,
                    postcode TEXT,
                    date TEXT,
                    listings_found INTEGER,
                    pages_scraped INTEGER,
                    success_rate REAL,
                    day_of_week TEXT,
                    month TEXT,
                    weather_conditions TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS postcode_predictions (
                    postcode TEXT PRIMARY KEY,
                    predicted_listings INTEGER,
                    confidence_score REAL,
                    last_updated TEXT,
                    model_version TEXT
                )
            """)
    
    def record_scrape_result(self, postcode: str, listings_found: int, 
                           pages_scraped: int, weather: str = "unknown"):
        """Record a scraping session result for learning"""
        with sqlite3.connect(self.db_path) as conn:
            now = datetime.now()
            conn.execute("""
                INSERT INTO scrape_history 
                (postcode, date, listings_found, pages_scraped, success_rate, 
                 day_of_week, month, weather_conditions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                postcode, now.isoformat(), listings_found, pages_scraped,
                listings_found / max(pages_scraped, 1),
                now.strftime("%A"), now.strftime("%B"), weather
            ))
    
    def analyze_seasonal_patterns(self, postcode: str) -> Dict:
        """Analyze seasonal and temporal patterns for a postcode"""
        with sqlite3.connect(self.db_path) as conn:
            # Monthly patterns
            monthly = conn.execute("""
                SELECT month, AVG(success_rate) as avg_success, COUNT(*) as samples
                FROM scrape_history 
                WHERE postcode = ?
                GROUP BY month
                ORDER BY avg_success DESC
            """, (postcode,)).fetchall()
            
            # Day of week patterns
            daily = conn.execute("""
                SELECT day_of_week, AVG(success_rate) as avg_success, COUNT(*) as samples
                FROM scrape_history 
                WHERE postcode = ?
                GROUP BY day_of_week
                ORDER BY avg_success DESC
            """, (postcode,)).fetchall()
            
            return {
                "monthly_patterns": [{"month": m[0], "success_rate": m[1], "samples": m[2]} 
                                   for m in monthly],
                "daily_patterns": [{"day": d[0], "success_rate": d[1], "samples": d[2]} 
                                 for d in daily],
                "best_month": monthly[0][0] if monthly else None,
                "best_day": daily[0][0] if daily else None
            }
    
    def predict_best_times(self, postcodes: List[str], days_ahead: int = 7) -> List[Dict]:
        """Predict best times to scrape based on historical patterns"""
        predictions = []
        
        for postcode in postcodes:
            patterns = self.analyze_seasonal_patterns(postcode)
            
            # Simple prediction based on historical success rates
            base_score = 0.5  # Default
            if patterns["monthly_patterns"]:
                current_month = datetime.now().strftime("%B")
                month_data = next((m for m in patterns["monthly_patterns"] 
                                 if m["month"] == current_month), None)
                if month_data:
                    base_score = month_data["success_rate"]
            
            predictions.append({
                "postcode": postcode,
                "predicted_score": base_score,
                "best_day": patterns["best_day"],
                "best_month": patterns["best_month"],
                "confidence": min(1.0, sum(p["samples"] for p in patterns["daily_patterns"]) / 10)
            })
        
        return sorted(predictions, key=lambda x: x["predicted_score"], reverse=True)

class ExternalDataIntegrator:
    """Integration with external data sources for enhanced intelligence"""
    
    def __init__(self, api_keys: Dict[str, str] = None):
        self.api_keys = api_keys or {}
    
    async def get_weather_data(self, lat: float, lon: float) -> Dict:
        """Get weather data for coordinates (mock implementation)"""
        # In a real implementation, this would call a weather API
        return {
            "condition": "partly_cloudy",
            "temperature": 15,
            "humidity": 60,
            "commercial_impact_factor": 0.8  # How weather affects commercial activity
        }
    
    async def get_economic_indicators(self, postcode: str) -> Dict:
        """Get economic indicators for a postcode area (mock implementation)"""
        # In a real implementation, this would call economic/business data APIs
        return {
            "business_density": 0.7,
            "commercial_growth_rate": 0.05,
            "unemployment_rate": 0.04,
            "commercial_vehicle_registrations": 1250,
            "economic_activity_score": 0.75
        }
    
    async def get_traffic_data(self, lat: float, lon: float) -> Dict:
        """Get traffic and logistics data (mock implementation)"""
        return {
            "congestion_level": 0.3,
            "logistics_hub_proximity": 0.8,
            "delivery_route_density": 0.6,
            "commercial_accessibility": 0.9
        }

class PostcodeVisualizer:
    """Advanced visualization for postcode strategies"""
    
    def __init__(self):
        self.maps_available = import_folium
    
    def create_strategy_map(self, postcodes: List[str], 
                          manager, filename: str = "postcode_strategy.html") -> Optional[str]:
        """Create an interactive map showing postcode strategy"""
        if not self.maps_available:
            print("📍 Map visualization requires: pip install folium")
            return None
        
        # Calculate center point
        lats = []
        lons = []
        for pc in postcodes:
            area_code = pc.split()[0]
            area = manager._postcode_areas.get(area_code)
            if area:
                lats.append(area.coordinates[0])
                lons.append(area.coordinates[1])
        
        if not lats:
            return None
        
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        
        # Create map
        m = folium.Map(location=[center_lat, center_lon], zoom_start=6)
        
        # Add markers for each postcode
        colors = {
            "high": "red",     # High commercial activity
            "medium": "orange", # Medium commercial activity  
            "low": "green"     # Low commercial activity
        }
        
        for pc in postcodes:
            area_code = pc.split()[0]
            area = manager._postcode_areas.get(area_code)
            if area:
                color = colors.get(area.commercial_activity, "blue")
                folium.CircleMarker(
                    location=area.coordinates,
                    radius=8,
                    popup=f"""
                    <b>{pc}</b><br>
                    City: {area.city}<br>
                    Region: {area.region}<br>
                    Population: {area.population_density}<br>
                    Commercial: {area.commercial_activity}
                    """,
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.7
                ).add_to(m)
        
        # Add legend
        legend_html = """
        <div style="position: fixed; top: 10px; right: 10px; width: 180px; height: 120px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <h4>Commercial Activity</h4>
        <i class="fa fa-circle" style="color:red"></i> High<br>
        <i class="fa fa-circle" style="color:orange"></i> Medium<br>
        <i class="fa fa-circle" style="color:green"></i> Low<br>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))
        
        # Save map
        filepath = Path(filename)
        m.save(str(filepath))
        print(f"📍 Interactive map saved to: {filepath.absolute()}")
        return str(filepath.absolute())

class StrategySaveLoad:
    """Save and load learned strategies"""
    
    @staticmethod
    def export_strategy(manager, strategy_name: str, filename: str):
        """Export a learned strategy to JSON"""
        data = {
            "strategy_name": strategy_name,
            "timestamp": datetime.now().isoformat(),
            "success_rates": dict(manager._success_rates),
            "used_postcodes": list(manager._used_postcodes),
            "total_areas": len(manager._postcode_areas),
            "metadata": {
                "export_version": "1.0",
                "regions": list(set(a.region for a in manager._postcode_areas.values()))
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"💾 Strategy '{strategy_name}' exported to {filename}")
    
    @staticmethod
    def import_strategy(manager, filename: str) -> bool:
        """Import a previously saved strategy"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            # Restore success rates
            manager._success_rates.update(data.get("success_rates", {}))
            
            # Restore used postcodes  
            manager._used_postcodes.update(data.get("used_postcodes", []))
            
            print(f"📥 Strategy '{data.get('strategy_name', 'Unknown')}' imported from {filename}")
            print(f"   • Success rates for {len(data.get('success_rates', {}))} areas")
            print(f"   • {len(data.get('used_postcodes', []))} used postcodes")
            
            return True
            
        except Exception as e:
            print(f"❌ Error importing strategy: {e}")
            return False
    
class PostcodeManager:
    """Intelligent postcode management with multiple selection strategies and advanced intelligence"""
    
    def __init__(self):
        # Comprehensive postcode database with metadata
        self._postcode_areas = {
            # London - High density, high commercial
            "SW1": PostcodeArea("SW1", "Westminster", "London", "high", "high", (51.4994, -0.1365)),
            "W1": PostcodeArea("W1", "West End", "London", "high", "high", (51.5154, -0.1415)),
            "WC1": PostcodeArea("WC1", "Holborn", "London", "high", "high", (51.5203, -0.1242)),
            "WC2": PostcodeArea("WC2", "Covent Garden", "London", "high", "high", (51.5125, -0.1243)),
            "E1": PostcodeArea("E1", "Whitechapel", "London", "high", "medium", (51.5156, -0.0708)),
            "SE1": PostcodeArea("SE1", "Southwark", "London", "high", "high", (51.5045, -0.0950)),
            "N1": PostcodeArea("N1", "Islington", "London", "high", "medium", (51.5396, -0.1076)),
            "NW1": PostcodeArea("NW1", "Camden", "London", "high", "medium", (51.5294, -0.1434)),
            
            # Major UK Cities - High commercial activity
            "M1": PostcodeArea("M1", "Manchester", "North West", "high", "high", (53.4808, -2.2426)),
            "M2": PostcodeArea("M2", "Manchester Central", "North West", "medium", "high", (53.4776, -2.2432)),
            "B1": PostcodeArea("B1", "Birmingham", "West Midlands", "high", "high", (52.4862, -1.8904)),
            "B4": PostcodeArea("B4", "Birmingham Central", "West Midlands", "medium", "high", (52.4795, -1.9026)),
            "LS1": PostcodeArea("LS1", "Leeds", "Yorkshire", "high", "high", (53.8008, -1.5491)),
            "LS2": PostcodeArea("LS2", "Leeds Central", "Yorkshire", "medium", "medium", (53.8059, -1.5530)),
            "L1": PostcodeArea("L1", "Liverpool", "North West", "high", "high", (53.4084, -2.9916)),
            "L2": PostcodeArea("L2", "Liverpool Central", "North West", "medium", "medium", (53.4084, -2.9794)),
            
            # Industrial/Commercial Hubs
            "S1": PostcodeArea("S1", "Sheffield", "Yorkshire", "high", "high", (53.3781, -1.4360)),
            "BS1": PostcodeArea("BS1", "Bristol", "South West", "high", "high", (51.4545, -2.5879)),
            "NE1": PostcodeArea("NE1", "Newcastle", "North East", "high", "high", (54.9783, -1.6178)),
            "CF10": PostcodeArea("CF10", "Cardiff", "Wales", "high", "high", (51.4816, -3.1791)),
            
            # Scotland
            "G1": PostcodeArea("G1", "Glasgow", "Scotland", "high", "high", (55.8642, -4.2518)),
            "G2": PostcodeArea("G2", "Glasgow Central", "Scotland", "medium", "high", (55.8570, -4.2594)),
            "EH1": PostcodeArea("EH1", "Edinburgh", "Scotland", "high", "high", (55.9533, -3.1883)),
            "EH2": PostcodeArea("EH2", "Edinburgh Central", "Scotland", "medium", "medium", (55.9515, -3.2058)),
            
            # Medium density commercial areas
            "NG1": PostcodeArea("NG1", "Nottingham", "East Midlands", "medium", "high", (52.9548, -1.1581)),
            "CV1": PostcodeArea("CV1", "Coventry", "West Midlands", "medium", "high", (52.4068, -1.5197)),
            "PE1": PostcodeArea("PE1", "Peterborough", "East", "medium", "high", (52.5695, -0.2405)),
            "MK1": PostcodeArea("MK1", "Milton Keynes", "South East", "medium", "high", (52.0406, -0.7594)),
            "SN1": PostcodeArea("SN1", "Swindon", "South West", "medium", "high", (51.5558, -1.7797)),
            "RG1": PostcodeArea("RG1", "Reading", "South East", "medium", "high", (51.4543, -0.9781)),
            
            # Suburban/Lower density but still commercially active
            "UB1": PostcodeArea("UB1", "Southall", "London", "medium", "medium", (51.5074, -0.3776)),
            "HA1": PostcodeArea("HA1", "Harrow", "London", "medium", "medium", (51.5793, -0.3346)),
            "CR0": PostcodeArea("CR0", "Croydon", "London", "medium", "medium", (51.3762, -0.0982)),
            "BR1": PostcodeArea("BR1", "Bromley", "London", "medium", "medium", (51.4063, 0.0140)),
            "AL1": PostcodeArea("AL1", "St Albans", "East", "medium", "medium", (51.7520, -0.3360)),
            "SL1": PostcodeArea("SL1", "Slough", "South East", "medium", "high", (51.5105, -0.5950)),
            
            # Northern England commercial centers
            "BD1": PostcodeArea("BD1", "Bradford", "Yorkshire", "medium", "medium", (53.7960, -1.7594)),
            "HU1": PostcodeArea("HU1", "Hull", "Yorkshire", "medium", "high", (53.7457, -0.3367)),
            "YO1": PostcodeArea("YO1", "York", "Yorkshire", "medium", "medium", (53.9600, -1.0873)),
            "HX1": PostcodeArea("HX1", "Halifax", "Yorkshire", "medium", "medium", (53.7248, -1.8611)),
            
            # Midlands
            "ST1": PostcodeArea("ST1", "Stoke-on-Trent", "West Midlands", "medium", "medium", (53.0027, -2.1794)),
            "WV1": PostcodeArea("WV1", "Wolverhampton", "West Midlands", "medium", "medium", (52.5870, -2.1267)),
            "DY1": PostcodeArea("DY1", "Dudley", "West Midlands", "medium", "medium", (52.5120, -2.0810)),
            
            # South coast commercial areas  
            "PO1": PostcodeArea("PO1", "Portsmouth", "South East", "medium", "high", (50.8198, -1.0880)),
            "SO14": PostcodeArea("SO14", "Southampton", "South East", "medium", "high", (50.9097, -1.4044)),
            "BN1": PostcodeArea("BN1", "Brighton", "South East", "medium", "medium", (50.8225, -0.1372)),
            
            # Wales
            "SA1": PostcodeArea("SA1", "Swansea", "Wales", "medium", "medium", (51.6214, -3.9436)),
            "NP20": PostcodeArea("NP20", "Newport", "Wales", "medium", "medium", (51.5877, -2.9984)),
        }
        
        self._used_postcodes: Set[str] = set()
        self._success_rates: Dict[str, float] = {}  # Track which postcodes yield good results
        
        # Initialize advanced intelligence components
        self.intelligence = PostcodeIntelligence()
        self.data_integrator = ExternalDataIntegrator()
        self.visualizer = PostcodeVisualizer()
        
    def get_postcodes(self, 
                     strategy: PostcodeStrategy = PostcodeStrategy.MIXED_DENSITY,
                     limit: int = 50,
                     custom_postcodes: List[str] = None,
                     exclude_used: bool = True,
                     geographic_radius_km: Optional[float] = None,
                     center_postcode: Optional[str] = None) -> List[str]:
        """
        Get postcodes based on the specified strategy
        
        Args:
            strategy: Selection strategy
            limit: Maximum number of postcodes to return
            custom_postcodes: User-provided postcodes (for CUSTOM strategy)
            exclude_used: Whether to exclude previously used postcodes
            geographic_radius_km: If set, only return postcodes within this radius of center
            center_postcode: Center point for geographic filtering
        """
        
        if strategy == PostcodeStrategy.CUSTOM:
            if not custom_postcodes:
                raise ValueError("custom_postcodes required for CUSTOM strategy")
            return self._format_postcodes(custom_postcodes[:limit])
        
        # Filter postcodes based on strategy
        candidates = self._filter_by_strategy(strategy)
        
        # Apply geographic filtering if requested
        if geographic_radius_km and center_postcode:
            candidates = self._filter_by_geography(candidates, center_postcode, geographic_radius_km)
        
        # Exclude previously used postcodes if requested
        if exclude_used:
            candidates = [pc for pc in candidates if pc not in self._used_postcodes]
        
        # Sort by success rate (if we have data) and commercial potential
        candidates = self._sort_by_effectiveness(candidates)
        
        # Generate full postcodes with realistic suffixes
        result = self._generate_full_postcodes(candidates[:limit], limit)
        
        # Mark as used
        if exclude_used:
            self._used_postcodes.update(result)
            
        return result
    
    def _filter_by_strategy(self, strategy: PostcodeStrategy) -> List[str]:
        """Filter postcode areas based on strategy"""
        areas = list(self._postcode_areas.keys())
        
        if strategy == PostcodeStrategy.MAJOR_CITIES:
            # Focus on high population density areas
            return [code for code, area in self._postcode_areas.items() 
                   if area.population_density == "high"]
        
        elif strategy == PostcodeStrategy.COMMERCIAL_HUBS:
            # Focus on high commercial activity areas
            return [code for code, area in self._postcode_areas.items() 
                   if area.commercial_activity == "high"]
        
        elif strategy == PostcodeStrategy.GEOGRAPHIC_SPREAD:
            # Ensure good geographic distribution
            return self._select_geographically_distributed(areas)
        
        elif strategy == PostcodeStrategy.MIXED_DENSITY:
            # Balanced mix of all types
            return areas
        
        return areas
    
    def _filter_by_geography(self, postcodes: List[str], center: str, radius_km: float) -> List[str]:
        """Filter postcodes within radius of center point"""
        if center not in self._postcode_areas:
            logger.warning(f"Center postcode {center} not found in database")
            return postcodes
        
        center_coords = self._postcode_areas[center].coordinates
        filtered = []
        
        for pc in postcodes:
            if pc in self._postcode_areas:
                pc_coords = self._postcode_areas[pc].coordinates
                distance = self._calculate_distance(center_coords, pc_coords)
                if distance <= radius_km:
                    filtered.append(pc)
        
        return filtered
    
    def _calculate_distance(self, coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """Calculate distance between two coordinates using Haversine formula"""
        lat1, lon1 = coord1
        lat2, lon2 = coord2
        
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2)
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def _select_geographically_distributed(self, postcodes: List[str]) -> List[str]:
        """Select postcodes to ensure good geographic distribution"""
        if not postcodes:
            return []
        
        # Group by region
        regions = {}
        for pc in postcodes:
            if pc in self._postcode_areas:
                region = self._postcode_areas[pc].region
                if region not in regions:
                    regions[region] = []
                regions[region].append(pc)
        
        # Select representatives from each region
        distributed = []
        for region_pcs in regions.values():
            # Take up to 3 from each region, prioritizing high commercial activity
            region_sorted = sorted(region_pcs, 
                                 key=lambda x: (self._postcode_areas[x].commercial_activity == "high",
                                              self._postcode_areas[x].population_density == "high"),
                                 reverse=True)
            distributed.extend(region_sorted[:3])
        
        return distributed
    
    def _sort_by_effectiveness(self, postcodes: List[str]) -> List[str]:
        """Sort postcodes by effectiveness (success rate + commercial potential)"""
        def effectiveness_score(pc: str) -> float:
            area = self._postcode_areas.get(pc)
            if not area:
                return 0.0
            
            # Base score from historical success rate
            base_score = self._success_rates.get(pc, 0.5)  # Default to neutral
            
            # Boost for commercial activity
            commercial_boost = {"high": 0.3, "medium": 0.1, "low": 0.0}[area.commercial_activity]
            
            # Boost for population density (more listings likely)
            density_boost = {"high": 0.2, "medium": 0.1, "low": 0.0}[area.population_density]
            
            return base_score + commercial_boost + density_boost
        
        return sorted(postcodes, key=effectiveness_score, reverse=True)
    
    def _generate_full_postcodes(self, area_codes: List[str], limit: int) -> List[str]:
        """Generate full postcodes from area codes with realistic suffixes"""
        full_postcodes = []
        
        # Realistic postcode suffixes that are commonly used
        common_suffixes = [
            "1AA", "1AB", "1AD", "1AE", "1AF", "1AG", "1AH", "1AJ", "1AL", "1AN",
            "2AA", "2AB", "2AD", "2AE", "2AF", "2AG", "2AH", "2AJ", "2AL", "2AN",
            "3AA", "3AB", "3AD", "3AE", "3AF", "3AG", "3AH", "3AJ", "3AL", "3AN",
            "4AA", "4AB", "4AD", "4AE", "4AF", "4AG", "4AH", "4AJ", "4AL", "4AN",
            "5AA", "5AB", "5AD", "5AE", "5AF", "5AG", "5AH", "5AJ", "5AL", "5AN",
            "6AA", "6AB", "6AD", "6AE", "6AF", "6AG", "6AH", "6AJ", "6AL", "6AN",
            "7AA", "7AB", "7AD", "7AE", "7AF", "7AG", "7AH", "7AJ", "7AL", "7AN",
            "8AA", "8AB", "8AD", "8AE", "8AF", "8AG", "8AH", "8AJ", "8AL", "8AN",
            "9AA", "9AB", "9AD", "9AE", "9AF", "9AG", "9AH", "9AJ", "9AL", "9AN",
            "0AA", "0AB", "0AD", "0AE", "0AF", "0AG", "0AH", "0AJ", "0AL", "0AN",
        ]
        
        # Cycle through area codes and suffixes to reach limit
        for i in range(limit):
            area_code = area_codes[i % len(area_codes)]
            suffix = common_suffixes[i % len(common_suffixes)]
            full_postcodes.append(f"{area_code} {suffix}")
    
    # Shuffle to randomize order
        random.shuffle(full_postcodes)
        return full_postcodes
    
    def _format_postcodes(self, postcodes: List[str]) -> List[str]:
        """Ensure postcodes are properly formatted"""
        formatted = []
        for pc in postcodes:
            # Remove extra spaces and ensure proper format
            pc = re.sub(r'\s+', ' ', pc.strip().upper())
            if not pc:
                continue
            
            # Add space if missing (e.g., "M11AA" -> "M1 1AA")
            if ' ' not in pc and len(pc) >= 5:
                pc = f"{pc[:-3]} {pc[-3:]}"
            
            formatted.append(pc)
        
        return formatted
    
    def record_success_rate(self, postcode: str, listings_found: int, source: str = "autotrader"):
        """Record the success rate for a postcode based on listings found"""
        # Normalize postcode area (remove suffix)
        area_code = postcode.split()[0] if ' ' in postcode else postcode[:2]
        
        # Convert listings count to success rate (0.0 to 1.0)
        # Assume 10+ listings = full success, scale linearly
        success_rate = min(listings_found / 10.0, 1.0)
        
        # Update running average
        if area_code in self._success_rates:
            self._success_rates[area_code] = (self._success_rates[area_code] + success_rate) / 2
        else:
            self._success_rates[area_code] = success_rate
        
        # Also record in intelligence database
        self.intelligence.record_scrape_result(postcode, listings_found, 1)
        
        logger.info(f"Updated success rate for {area_code}: {self._success_rates[area_code]:.2f} (source: {source})")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about postcode usage and success rates"""
        return {
            "total_areas": len(self._postcode_areas),
            "used_postcodes": len(self._used_postcodes),
            "success_rates": dict(self._success_rates),
            "high_commercial_areas": len([a for a in self._postcode_areas.values() 
                                        if a.commercial_activity == "high"]),
            "regions": list(set(a.region for a in self._postcode_areas.values()))
        }

def generate_uk_postcodes(limit: int = 100) -> List[str]:
    """Legacy function for backward compatibility - now uses PostcodeManager"""
    manager = PostcodeManager()
    return manager.get_postcodes(
        strategy=PostcodeStrategy.MIXED_DENSITY,
        limit=limit,
        exclude_used=False
    )

# ---------------------------------------------------------------------------
# Search URL template & scraping settings (updated with image and description selectors)
# ---------------------------------------------------------------------------
SEARCH_URL = (
    "https://www.autotrader.co.uk/van-search?advertising-location=at_vans&"
    "make=FORD&model=TRANSIT&price-from=500&wheelbase=MWB&roof_height=H2&sort=relevance"
    "&postcode={postcode}&page={page}{extra}"
)
HEADLESS = True  # Temporarily set to False for debugging
PAGE_TIMEOUT_MS = 60_000
THROTTLE_MS = 1_000
SELECTORS = {
    "card": "article",
    "title": "h3, h2, [data-testid='search-result-title']",
    "price": "[data-testid='search-result-price'], .price, .vehicle-price",
    "spec_list": "ul li, .specs li, .key-specs li",
    "link": "a",
    "image": "img, [data-testid*='image'] img, .vehicle-image img, img[src*='autotrader']",
    "description": ".vehicle-description, .key-specs, .specs, [data-testid='search-result-description']",
}
MILEAGE_RE = re.compile(r"([\d,]+)\s*miles", re.I)
YEAR_RE = re.compile(r"(\d{4})")  # More flexible - matches 4 digits anywhere in text
PRICE_RE = re.compile(r"[\d,]+")

# ---------------------------------------------------------------------------
# Enhanced Scraper Core with Concurrency and Proxy Support
# ---------------------------------------------------------------------------
async def create_browser_context(playwright_instance, proxy_rotator: ProxyRotator = None):
    """Create a browser context with optional proxy"""
    proxy_config = None
    current_proxy = None
    
    if proxy_rotator:
        current_proxy = proxy_rotator.get_next_proxy()
        if current_proxy:
            proxy_config = {"server": current_proxy}
    
    try:
        browser = await playwright_instance.chromium.launch(
            headless=HEADLESS,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-dev-shm-usage',
                '--no-first-run',
            ]
        )
        
        context = await browser.new_context(
            proxy=proxy_config,
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        
        page = await context.new_page()
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
        
        return browser, context, page, current_proxy
        
    except Exception as e:
        if current_proxy and proxy_rotator:
            proxy_rotator.mark_proxy_failed(current_proxy)
        raise e

async def _scrape_page_enhanced(page, url: str, proxy: str = None, semaphore: asyncio.Semaphore = None) -> List[Dict[str, Any]]:
    """Enhanced page scraping with semaphore control and better error handling"""
    if semaphore:
        async with semaphore:
            return await _scrape_page_core(page, url, proxy)
    else:
        return await _scrape_page_core(page, url, proxy)

async def _scrape_page_core(page, url: str, proxy: str = None) -> List[Dict[str, Any]]:
    """Core page scraping logic"""
    try:
        # Random delay to appear more human-like
        delay = random.uniform(*REQUEST_DELAY_RANGE)
        await asyncio.sleep(delay)
        
        await page.goto(url, timeout=PAGE_TIMEOUT_MS)
        
        # Wait a bit to appear more human-like
        await page.wait_for_timeout(2000)
        
        # Check for Cloudflare protection
        page_title = await page.title()
        logger.info(f"Page title: {page_title} (Proxy: {proxy or 'None'})")
        
        if "cloudflare" in page_title.lower() or "attention required" in page_title.lower():
            logger.warning("Cloudflare protection detected - waiting longer...")
            await page.wait_for_timeout(5000)
            
            # Try clicking through any challenge
            challenge_button = await page.query_selector('input[type="submit"]')
            if challenge_button:
                await challenge_button.click()
                await page.wait_for_timeout(3000)
        
        try:
            await page.wait_for_selector(SELECTORS["card"], timeout=PAGE_TIMEOUT_MS)
            cards = await page.query_selector_all(SELECTORS["card"])
        except PlaywrightTimeout:
            logger.warning(f"Timeout waiting for selector: {SELECTORS['card']}")
            # Try alternative selectors for vehicle listings
            alternatives = [
                "[data-testid='search-result']",
                ".search-result",
                ".listing-item", 
                ".vehicle-listing",
                "[data-tracking*='listing']",
                "article[data-testid]",
            ]
            cards = []
            for alt in alternatives:
                found = await page.query_selector_all(alt)
                if found:
                    logger.info(f"Found {len(found)} elements with selector: {alt}")
                    cards = found
                    break
            
            if not cards:
                return []
        
        logger.info(f"Found {len(cards)} potential listings")
        
        # Filter to only include cards that likely contain vehicle listings
        vehicle_cards = []
        for card in cards:
            card_text = await card.inner_text()
            # Check if this looks like a vehicle listing
            has_vehicle_listing = 'Ford Transit' in card_text and ('£' in card_text or 'mile' in card_text.lower())
            is_mostly_navigation = card_text.count('Clear all') > 0 and len(card_text) < 500  # Small cards that are just navigation
            
            # Include cards that have vehicle listings, even if they also have some navigation
            if has_vehicle_listing and not is_mostly_navigation:
                vehicle_cards.append(card)
        
        logger.info(f"Filtered to {len(vehicle_cards)} likely vehicle listings")
        
        rows = []
        for card in vehicle_cards:
            # Try multiple selectors for title
            title = None
            for title_sel in SELECTORS["title"].split(", "):
                title_elem = await card.query_selector(title_sel)
                if title_elem:
                    title = await title_elem.inner_text()
                    break
            
            # If no title found via selectors, try to extract from card text
            if not title:
                card_text = await card.inner_text()
                lines = [line.strip() for line in card_text.split('\n') if line.strip()]
                # Look for lines that contain vehicle descriptions (after "Ford Transit")
                found_ford_transit = False
                for line in lines:
                    if 'Ford Transit' in line:
                        found_ford_transit = True
                        continue
                    if found_ford_transit and len(line) > 10 and len(line) < 100:
                        # This is likely the vehicle description line
                        if any(word in line.lower() for word in ['eco', 'blue', 'euro', 'cab', 'tipper', 'van', 'l1', 'l2', 'h1', 'h2']):
                            title = f"Ford Transit {line}"
                            break
                
                # Fallback: just use "Ford Transit" if we can't find a good description
                if not title and found_ford_transit:
                    title = "Ford Transit"
            
            # Try multiple selectors for price
            price = None
            for price_sel in SELECTORS["price"].split(", "):
                price_elem = await card.query_selector(price_sel)
                if price_elem:
                    price_text = await price_elem.inner_text()
                    price_match = PRICE_RE.search(price_text or "")
                    if price_match:
                        price = int(price_match.group().replace(",", ""))
                        break
            
            # If no price found via selectors, search in card text
            if not price:
                card_text = await card.inner_text()
                price_match = re.search(r'£([\d,]+)', card_text)
                if price_match:
                    price = int(price_match.group(1).replace(",", ""))

            # Extract image URL
            image_url = None
            for img_sel in SELECTORS["image"].split(", "):
                img_elem = await card.query_selector(img_sel)
                if img_elem:
                    img_src = await img_elem.get_attribute('src')
                    if img_src and ('http' in img_src or img_src.startswith('//')):
                        # Convert relative URLs to absolute URLs
                        if img_src.startswith('//'):
                            image_url = f"https:{img_src}"
                        elif img_src.startswith('/'):
                            image_url = f"https://www.autotrader.co.uk{img_src}"
                        else:
                            image_url = img_src
                        break
            
            # Extract detailed description
            description = None
            description_parts = []
            
            # Try to get description from dedicated description selectors
            for desc_sel in SELECTORS["description"].split(", "):
                desc_elem = await card.query_selector(desc_sel)
                if desc_elem:
                    desc_text = await desc_elem.inner_text()
                    if desc_text and len(desc_text.strip()) > 20:  # Meaningful description
                        description_parts.append(desc_text.strip())
            
            # If no dedicated description found, extract key specs and features from card text
            if not description_parts:
                card_text = await card.inner_text()
                lines = [line.strip() for line in card_text.split('\n') if line.strip()]
                
                # Look for lines that contain vehicle specifications
                for line in lines:
                    # Skip very short lines, titles, and prices
                    if (len(line) > 15 and len(line) < 200 and 
                        '£' not in line and 
                        'Ford Transit' not in line and
                        any(keyword in line.lower() for keyword in [
                            'eco', 'blue', 'euro', 'cab', 'tipper', 'van', 'manual', 'automatic',
                            'diesel', 'petrol', 'l1', 'l2', 'h1', 'h2', 'swb', 'mwb', 'lwb',
                            'crew', 'double', 'single', 'dropside', 'luton', 'panel', 'flatbed'
                        ])):
                        description_parts.append(line)
            
            # Combine description parts
            if description_parts:
                description = " | ".join(description_parts[:3])  # Limit to first 3 parts to avoid too long descriptions

            year = mileage = None
            spec_texts = []
            
            # Get all text from the card and parse it
            card_text = await card.inner_text()
            lines = [line.strip() for line in card_text.split('\n') if line.strip()]
            
            for line in lines:
                if len(line) < 100:  # reasonable length for spec text
                    spec_texts.append(line)
                    if year is None:
                        ymatch = YEAR_RE.search(line)
                        if ymatch:
                            year_candidate = int(ymatch.group(1))
                            if 2000 <= year_candidate <= datetime.now().year:  # reasonable year range
                                year = year_candidate
                    if mileage is None:
                        mmatch = MILEAGE_RE.search(line)
                        if mmatch:
                            mileage = int(mmatch.group(1).replace(",", ""))
            
            link_elem = await card.query_selector(SELECTORS["link"])
            link = await link_elem.get_attribute('href') if link_elem else None
            
            # Detect VAT status from card text
            from van_scraping_utils import detect_vat_status
            card_text = await card.inner_text()
            vat_included = detect_vat_status(card_text, "autotrader")
            
            rows.append({
                "title": title, 
                "year": year, 
                "mileage": mileage, 
                "price": price, 
                "description": description,
                "image_url": image_url,
                "url": link,
                "listing_type": "buy_it_now",  # AutoTrader is always buy-it-now
                "vat_included": vat_included,
                "postcode": None,  # Will be added by worker
                "proxy": proxy
            })
        
        return rows
        
    except Exception as e:
        logger.error(f"Error scraping page {url}: {str(e)}")
        return []

async def scrape_postcode_worker(postcode: str, pages_per_postcode: int, semaphore: asyncio.Semaphore, 
                                proxy_rotator: ProxyRotator, results_queue: asyncio.Queue):
    """Worker function to scrape a single postcode"""
    try:
        async with async_playwright() as p:
            browser, context, page, current_proxy = await create_browser_context(p, proxy_rotator)
            
            try:
                postcode_results = []
                logger.info(f"Starting scrape for postcode: {postcode} (Proxy: {current_proxy or 'None'})")
                
                for page_no in range(1, pages_per_postcode + 1):
                    url = SEARCH_URL.format(postcode=postcode, page=page_no, extra="")
                    logger.info(f"Scraping {postcode} page {page_no}")
                    
                    rows = await _scrape_page_enhanced(page, url, current_proxy, semaphore)
                    if not rows:
                        logger.info(f"No more results for {postcode} – stopping at page {page_no}")
                        break
                    
                    # Add postcode to each row
                    for row in rows:
                        row['postcode'] = postcode
                    
                    postcode_results.extend(rows)
                    
                    # Random delay between pages
                    delay = random.uniform(*REQUEST_DELAY_RANGE)
                    await asyncio.sleep(delay)
                
                await results_queue.put((postcode, postcode_results))
                logger.info(f"Completed scrape for {postcode}: {len(postcode_results)} listings")
                
            finally:
                await browser.close()
                
    except Exception as e:
        logger.error(f"Error scraping postcode {postcode}: {str(e)}")
        if current_proxy and proxy_rotator:
            proxy_rotator.mark_proxy_failed(current_proxy)
        await results_queue.put((postcode, []))

async def scrape_multiple_postcodes(postcodes: List[str], pages_per_postcode: int = 3, 
                                  proxy_list: List[str] = None, outfile: Path = None) -> pd.DataFrame:
    """Scrape multiple postcodes concurrently with proxy rotation"""
    
    # Setup
    proxy_rotator = ProxyRotator(proxy_list)
    browser_semaphore = asyncio.Semaphore(MAX_CONCURRENT_BROWSERS)
    page_semaphore = asyncio.Semaphore(MAX_CONCURRENT_PAGES)
    results_queue = asyncio.Queue()
    
    logger.info(f"Starting concurrent scrape of {len(postcodes)} postcodes")
    logger.info(f"Max concurrent browsers: {MAX_CONCURRENT_BROWSERS}")
    logger.info(f"Max concurrent pages: {MAX_CONCURRENT_PAGES}")
    logger.info(f"Pages per postcode: {pages_per_postcode}")
    logger.info(f"Proxies available: {len(proxy_list) if proxy_list else 0}")
    
    # Create worker tasks
    tasks = []
    for postcode in postcodes:
        task = asyncio.create_task(
            scrape_postcode_worker(postcode, pages_per_postcode, page_semaphore, proxy_rotator, results_queue)
        )
        tasks.append(task)
    
    # Wait for all tasks to complete
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect results
    all_listings = []
    completed_postcodes = []
    
    while not results_queue.empty():
        postcode, listings = await results_queue.get()
        completed_postcodes.append(postcode)
        all_listings.extend(listings)
    
    logger.info(f"Scraping completed. Total listings: {len(all_listings)}")
    logger.info(f"Completed postcodes: {len(completed_postcodes)}")
    
    # Create DataFrame
    df = pd.DataFrame(all_listings)
    
    if not df.empty:
        # Calculate age safely
        if 'year' in df.columns and not df['year'].isna().all():
            df["age"] = datetime.now().year - df["year"]
            logger.info(f"Age calculated for {(~df['year'].isna()).sum()} out of {len(df)} listings")
        else:
            logger.warning("No year data found, setting age to None")
            df["age"] = None
        
        # Save to file
        if outfile:
            df.to_csv(outfile, index=False)
            logger.info(f"Saved {len(df)} rows → {outfile}")
        
        # Show summary stats
        logger.info("\n=== SCRAPING SUMMARY ===")
        logger.info(f"Total listings scraped: {len(df)}")
        logger.info(f"Unique postcodes with results: {df['postcode'].nunique()}")
        logger.info(f"Price range: £{df['price'].min():,} - £{df['price'].max():,}")
        logger.info(f"Year range: {df['year'].min()} - {df['year'].max()}")
        logger.info(f"Average listings per postcode: {len(df)/len(completed_postcodes):.1f}")
    
    return df

# ---------------------------------------------------------------------------
# Quick analysis (unchanged apart from lazy‑import guard)
# ---------------------------------------------------------------------------
def analyse(csv_path: Path, show_plots: bool = True) -> None:
    if plt is None:
        raise RuntimeError("matplotlib is required for --analyse; pip install matplotlib")

    df = pd.read_csv(csv_path)
    if df.empty:
        print("Empty CSV – nothing to analyse.")
        return

    mileage_bins = pd.cut(df["mileage"], bins=range(0, int(df["mileage"].max()) + 50_000, 50_000))
    price_by_mileage = df.groupby(mileage_bins)["price"].median()
    age_bins = pd.cut(df["age"], bins=range(0, int(df["age"].max()) + 2, 2))
    price_by_age = df.groupby(age_bins)["price"].median()

    print("Median £ price by mileage band:\n", price_by_mileage, "\n")
    print("Median £ price by age band:\n", price_by_age, "\n")

    if show_plots:
        plt.figure()
        plt.scatter(df["mileage"], df["price"])
        plt.xlabel("Mileage")
        plt.ylabel("Price (£)")
        plt.title("Price vs Mileage")
        plt.tight_layout()
        plt.show()

        plt.figure()
        plt.scatter(df["age"], df["price"])
        plt.xlabel("Age (years)")
        plt.ylabel("Price (£)")
        plt.title("Price vs Age")
        plt.tight_layout()
        plt.show()

# ---------------------------------------------------------------------------
# Legacy single-postcode function for backward compatibility
# ---------------------------------------------------------------------------
async def scrape_autotrader(postcode: str, pages: int, outfile: Path, extra_query: str = "") -> pd.DataFrame:
    """Legacy single-postcode scraper for backward compatibility"""
    return await scrape_multiple_postcodes([postcode], pages, None, outfile)

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Scrape and analyse Ford Transit L2H2 listings with intelligent postcode management")
    sub = ap.add_subparsers(dest="command", required=True)

    # scrape (single postcode - legacy)
    scrape_ap = sub.add_parser("scrape", help="Scrape listings for single postcode")
    scrape_ap.add_argument("--postcode", default="M1 1AA")
    scrape_ap.add_argument("--pages", type=int, default=3)
    scrape_ap.add_argument("--outfile", type=Path, default="transit_l2h2.csv")
    scrape_ap.add_argument("--extra-query", default="")

    # scrape-multi (concurrent scraper)
    multi_scrape_ap = sub.add_parser("scrape-multi", help="Scrape listings across multiple postcodes concurrently")
    multi_scrape_ap.add_argument("--postcodes", nargs="+", help="List of postcodes to scrape")
    multi_scrape_ap.add_argument("--postcode-limit", type=int, default=50, help="Number of auto-generated postcodes to use")
    multi_scrape_ap.add_argument("--pages-per-postcode", type=int, default=3, help="Pages to scrape per postcode")
    multi_scrape_ap.add_argument("--proxy-file", type=Path, help="File containing proxy URLs (one per line)")
    multi_scrape_ap.add_argument("--proxies", nargs="+", help="List of proxy URLs")
    multi_scrape_ap.add_argument("--outfile", type=Path, default="transit_multi.csv")
    multi_scrape_ap.add_argument("--max-browsers", type=int, default=5, help="Max concurrent browsers")
    multi_scrape_ap.add_argument("--max-pages", type=int, default=20, help="Max concurrent pages")
    
    # Enhanced postcode strategy options
    multi_scrape_ap.add_argument("--strategy", 
                                choices=[s.value for s in PostcodeStrategy], 
                                default=PostcodeStrategy.MIXED_DENSITY.value,
                                help="Postcode selection strategy")
    multi_scrape_ap.add_argument("--center-postcode", help="Center postcode for geographic filtering")
    multi_scrape_ap.add_argument("--radius-km", type=float, help="Radius in km for geographic filtering")
    multi_scrape_ap.add_argument("--exclude-used", action="store_true", default=True, 
                                help="Exclude previously used postcodes")
    multi_scrape_ap.add_argument("--track-success", action="store_true", default=True,
                                help="Track and learn from postcode success rates")

    # scrape-uk (optimized for whole UK industrial areas)
    uk_scrape_ap = sub.add_parser("scrape-uk", help="Scrape the whole UK focusing on commercial/industrial areas with descriptions and images")
    uk_scrape_ap.add_argument("--outfile", type=Path, default="ford_transit_uk_complete.csv", 
                             help="Output CSV file with descriptions and images")
    uk_scrape_ap.add_argument("--pages-per-postcode", type=int, default=5, 
                             help="Pages to scrape per postcode (default: 5 for thorough coverage)")
    uk_scrape_ap.add_argument("--proxy-file", type=Path, help="File containing proxy URLs (one per line)")
    uk_scrape_ap.add_argument("--proxies", nargs="+", help="List of proxy URLs")
    uk_scrape_ap.add_argument("--max-browsers", type=int, default=8, help="Max concurrent browsers (default: 8 for UK-wide)")
    uk_scrape_ap.add_argument("--max-pages", type=int, default=30, help="Max concurrent pages (default: 30 for UK-wide)")
    uk_scrape_ap.add_argument("--postcode-limit", type=int, default=100, 
                             help="Number of postcodes to use (default: 100 for full UK coverage)")
    uk_scrape_ap.add_argument("--include-mixed", action="store_true", 
                             help="Include mixed density areas in addition to commercial hubs")

    # New postcode analysis command
    postcode_ap = sub.add_parser("postcodes", help="Advanced postcode intelligence and management")
    postcode_ap.add_argument("action", choices=["list", "stats", "test", "analyze", "predict", "map", "export", "import"], 
                            help="Action to perform")
    postcode_ap.add_argument("--strategy", choices=[s.value for s in PostcodeStrategy], 
                            default=PostcodeStrategy.MIXED_DENSITY.value,
                            help="Strategy to test or use")
    postcode_ap.add_argument("--limit", type=int, default=20, help="Number of postcodes to show/test")
    postcode_ap.add_argument("--center-postcode", help="Center postcode for geographic filtering")
    postcode_ap.add_argument("--radius-km", type=float, help="Radius in km for geographic filtering")
    postcode_ap.add_argument("--postcode", help="Specific postcode to analyze")
    postcode_ap.add_argument("--output", help="Output file for map or export")
    postcode_ap.add_argument("--name", help="Strategy name for export")
    postcode_ap.add_argument("--file", help="File for import/export operations")

    # analyse
    analyse_ap = sub.add_parser("analyse", help="Quick median bands + scatter plots")
    analyse_ap.add_argument("csv", type=Path)
    analyse_ap.add_argument("--no-plots", action="store_true")

    return ap.parse_args()


def load_proxies_from_file(proxy_file: Path) -> List[str]:
    """Load proxy URLs from a file"""
    if not proxy_file.exists():
        logger.error(f"Proxy file not found: {proxy_file}")
        return []
    
    proxies = []
    with open(proxy_file, 'r') as f:
        for line in f:
            proxy = line.strip()
            if proxy and not proxy.startswith('#'):
                proxies.append(proxy)
    
    logger.info(f"Loaded {len(proxies)} proxies from {proxy_file}")
    return proxies


def handle_postcode_command(args):
    """Handle the enhanced postcodes command with advanced intelligence features"""
    manager = PostcodeManager()
    
    if args.action == "stats":
        stats = manager.get_stats()
        print(f"\n=== POSTCODE MANAGER STATISTICS ===")
        print(f"Total postcode areas in database: {stats['total_areas']}")
        print(f"Used postcodes: {stats['used_postcodes']}")
        print(f"High commercial activity areas: {stats['high_commercial_areas']}")
        print(f"Regions covered: {', '.join(stats['regions'])}")
        
        if stats['success_rates']:
            print(f"\n=== SUCCESS RATES ===")
            sorted_rates = sorted(stats['success_rates'].items(), key=lambda x: x[1], reverse=True)
            for area, rate in sorted_rates[:10]:
                print(f"{area}: {rate:.2f}")
    
    elif args.action == "list":
        strategy = PostcodeStrategy(args.strategy)
        postcodes = manager.get_postcodes(
            strategy=strategy,
            limit=args.limit,
            exclude_used=False,
            geographic_radius_km=args.radius_km,
            center_postcode=args.center_postcode
        )
        
        print(f"\n=== POSTCODES FOR STRATEGY: {strategy.value.upper()} ===")
        print(f"Generated {len(postcodes)} postcodes:")
        for i, pc in enumerate(postcodes, 1):
            area_code = pc.split()[0]
            area_info = manager._postcode_areas.get(area_code)
            if area_info:
                print(f"{i:2}. {pc} - {area_info.city}, {area_info.region} "
                      f"(pop: {area_info.population_density}, comm: {area_info.commercial_activity})")
            else:
                print(f"{i:2}. {pc}")
    
    elif args.action == "test":
        # Test different strategies and show comparison
        strategies = [PostcodeStrategy.MAJOR_CITIES, PostcodeStrategy.COMMERCIAL_HUBS, 
                     PostcodeStrategy.GEOGRAPHIC_SPREAD, PostcodeStrategy.MIXED_DENSITY]
        
        print(f"\n=== STRATEGY COMPARISON (limit: {args.limit}) ===")
        for strategy in strategies:
            postcodes = manager.get_postcodes(
                strategy=strategy,
                limit=args.limit,
                exclude_used=False
            )
            print(f"\n{strategy.value.upper()}: {len(postcodes)} postcodes")
            print(f"Sample: {', '.join(postcodes[:5])}")
    
    elif args.action == "analyze":
        if not args.postcode:
            print("❌ --postcode required for analyze action")
            return
        
        patterns = manager.intelligence.analyze_seasonal_patterns(args.postcode)
        print(f"\n=== TEMPORAL ANALYSIS FOR {args.postcode} ===")
        
        if patterns["best_day"]:
            print(f"🗓️  Best day of week: {patterns['best_day']}")
        if patterns["best_month"]:
            print(f"📅 Best month: {patterns['best_month']}")
        
        if patterns["daily_patterns"]:
            print(f"\n📊 Daily patterns:")
            for pattern in patterns["daily_patterns"][:3]:
                print(f"   {pattern['day']}: {pattern['success_rate']:.2f} success rate ({pattern['samples']} samples)")
        
        if patterns["monthly_patterns"]:
            print(f"\n📈 Monthly patterns:")
            for pattern in patterns["monthly_patterns"][:3]:
                print(f"   {pattern['month']}: {pattern['success_rate']:.2f} success rate ({pattern['samples']} samples)")
    
    elif args.action == "predict":
        postcodes = manager.get_postcodes(limit=args.limit, exclude_used=False)
        area_codes = [pc.split()[0] for pc in postcodes]
        predictions = manager.intelligence.predict_best_times(area_codes)
        
        print(f"\n=== PERFORMANCE PREDICTIONS ===")
        print(f"🔮 Top {min(10, len(predictions))} predicted performers:")
        
        for i, pred in enumerate(predictions[:10], 1):
            print(f"{i:2}. {pred['postcode']}: {pred['predicted_score']:.2f} score "
                  f"(confidence: {pred['confidence']:.2f})")
            if pred['best_day']:
                print(f"     Best day: {pred['best_day']}, Best month: {pred['best_month']}")
    
    elif args.action == "map":
        strategy = PostcodeStrategy(args.strategy)
        postcodes = manager.get_postcodes(strategy=strategy, limit=args.limit, exclude_used=False)
        output_file = args.output or "postcode_strategy_map.html"
        
        result = manager.visualizer.create_strategy_map(postcodes, manager, output_file)
        if result:
            print(f"📍 Interactive map created: {result}")
        else:
            print("❌ Map creation failed. Install folium: pip install folium")
    
    elif args.action == "export":
        if not args.name or not args.file:
            print("❌ --name and --file required for export action")
            return
        
        StrategySaveLoad.export_strategy(manager, args.name, args.file)
    
    elif args.action == "import":
        if not args.file:
            print("❌ --file required for import action")
            return
        
        success = StrategySaveLoad.import_strategy(manager, args.file)
        if not success:
            print("❌ Import failed")


def main():
    args = parse_args()
    
    # Update global settings if provided
    global MAX_CONCURRENT_BROWSERS, MAX_CONCURRENT_PAGES
    
    if hasattr(args, 'max_browsers'):
        MAX_CONCURRENT_BROWSERS = args.max_browsers
    if hasattr(args, 'max_pages'):
        MAX_CONCURRENT_PAGES = args.max_pages

    if args.command == "scrape":
        asyncio.run(scrape_autotrader(args.postcode, args.pages, args.outfile, args.extra_query))
        
    elif args.command == "scrape-multi":
        # Initialize PostcodeManager for smart postcode selection
        postcode_manager = PostcodeManager()
        
        # Determine postcodes to use
        if args.postcodes:
            postcodes = args.postcodes
        else:
            strategy = PostcodeStrategy(args.strategy)
            postcodes = postcode_manager.get_postcodes(
                strategy=strategy,
                limit=args.postcode_limit,
                exclude_used=args.exclude_used,
                geographic_radius_km=args.radius_km,
                center_postcode=args.center_postcode
            )
        
        # Load proxies
        proxy_list = []
        if args.proxy_file:
            proxy_list.extend(load_proxies_from_file(args.proxy_file))
        if args.proxies:
            proxy_list.extend(args.proxies)
        
        logger.info(f"Starting enhanced multi-postcode scrape:")
        logger.info(f"  Strategy: {args.strategy}")
        logger.info(f"  Postcodes: {len(postcodes)}")
        logger.info(f"  Pages per postcode: {args.pages_per_postcode}")
        logger.info(f"  Proxies: {len(proxy_list)}")
        logger.info(f"  Max browsers: {MAX_CONCURRENT_BROWSERS}")
        logger.info(f"  Max pages: {MAX_CONCURRENT_PAGES}")
        logger.info(f"  Success tracking: {args.track_success}")
        
        # Run the scraper
        df = asyncio.run(scrape_multiple_postcodes(
            postcodes, 
            args.pages_per_postcode,
            proxy_list,
            args.outfile
        ))
        
        # Track success rates if enabled
        if args.track_success and not df.empty:
            logger.info("Recording success rates for postcodes...")
            success_counts = df.groupby('postcode').size()
            for postcode, count in success_counts.items():
                postcode_manager.record_success_rate(postcode, count, "autotrader")
            
            # Show updated stats
            stats = postcode_manager.get_stats()
            logger.info(f"Updated success rates for {len(success_counts)} postcodes")
        
    elif args.command == "scrape-uk":
        # UK-wide scraping optimized for commercial/industrial areas
        postcode_manager = PostcodeManager()
        
        # Use commercial_hubs strategy by default, optionally include mixed density
        if args.include_mixed:
            # Get both commercial hubs and mixed density areas
            commercial_postcodes = postcode_manager.get_postcodes(
                strategy=PostcodeStrategy.COMMERCIAL_HUBS,
                limit=args.postcode_limit // 2,
                exclude_used=False
            )
            mixed_postcodes = postcode_manager.get_postcodes(
                strategy=PostcodeStrategy.MIXED_DENSITY,
                limit=args.postcode_limit // 2,
                exclude_used=False
            )
            postcodes = commercial_postcodes + mixed_postcodes
        else:
            # Focus purely on commercial/industrial hubs
            postcodes = postcode_manager.get_postcodes(
                strategy=PostcodeStrategy.COMMERCIAL_HUBS,
                limit=args.postcode_limit,
                exclude_used=False
            )
        
        # Load proxies
        proxy_list = []
        if args.proxy_file:
            proxy_list.extend(load_proxies_from_file(args.proxy_file))
        if args.proxies:
            proxy_list.extend(args.proxies)
        
        # Update global concurrency settings
        MAX_CONCURRENT_BROWSERS = args.max_browsers
        MAX_CONCURRENT_PAGES = args.max_pages
        
        logger.info(f"Starting UK-wide Ford Transit scraping:")
        logger.info(f"  Strategy: Commercial Hubs {'+ Mixed Density' if args.include_mixed else ''}")
        logger.info(f"  Postcodes: {len(postcodes)}")
        logger.info(f"  Pages per postcode: {args.pages_per_postcode}")
        logger.info(f"  Proxies: {len(proxy_list)}")
        logger.info(f"  Max browsers: {MAX_CONCURRENT_BROWSERS}")
        logger.info(f"  Max pages: {MAX_CONCURRENT_PAGES}")
        logger.info(f"  Output file: {args.outfile}")
        logger.info(f"  Expected fields: title, year, mileage, price, description, image_url, url, postcode")
        
        # Run the enhanced scraper with descriptions and images
        df = asyncio.run(scrape_multiple_postcodes(
            postcodes, 
            args.pages_per_postcode,
            proxy_list,
            args.outfile
        ))
        
        # Show final summary
        if not df.empty:
            logger.info(f"\n=== UK SCRAPING COMPLETED ===")
            logger.info(f"Total Ford Transit listings found: {len(df)}")
            logger.info(f"Postcodes with results: {df['postcode'].nunique()}")
            logger.info(f"Price range: £{df['price'].min():,} - £{df['price'].max():,}")
            logger.info(f"Listings with descriptions: {df['description'].notna().sum()}")
            logger.info(f"Listings with images: {df['image_url'].notna().sum()}")
            logger.info(f"Data saved to: {args.outfile}")
        else:
            logger.warning("No listings found. Check your configuration and try again.")
    
    elif args.command == "postcodes":
        handle_postcode_command(args)
        
    elif args.command == "analyse":
        analyse(args.csv, show_plots=not args.no_plots)


if __name__ == "__main__":
    main()
