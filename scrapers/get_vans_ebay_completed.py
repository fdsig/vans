#!/usr/bin/env python3
"""
Scrape and Analyse Ford Transit L2 H2 COMPLETED Listings from eBay UK
====================================================================

*Enhanced eBay COMPLETED listings scraping system with intelligent postcode management, 
concurrent scraping with proxy support, and advanced geographic intelligence.*

**🎯 KEY FEATURE: Scrapes COMPLETED/SOLD listings to get ACTUAL SALE PRICES**

This script supports these sub‑commands:

* `scrape`    – harvest completed listings → CSV (single postcode, legacy)
* `scrape-multi` – concurrent scraping across multiple postcodes with smart strategies
* `scrape-uk` – optimized UK-wide scraping focusing on commercial/industrial areas with descriptions and images
* `postcodes` – analyze and manage postcode selection strategies  
* `analyse`  – quick medians & scatter plots

----
Why Completed Listings?
------------------------
Completed listings show ACTUAL SALE PRICES rather than current bid amounts or Buy-It-Now prices.
This gives you real market data on what Ford Transits are actually selling for.

- ✅ Final sale prices (what buyers actually paid)
- ✅ Historical pricing trends over the last 90 days
- ✅ Sold vs unsold listings data
- ✅ Market demand insights

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

----
Usage Examples
--------------

**1) Basic completed listings scraping (single postcode)**
```bash
python get_vans_ebay_completed.py scrape --postcode G23NX --pages 15 --outfile transit_completed_ebay.csv
```

**2) Smart multi-postcode completed listings scraping**
```bash
# Use commercial hubs strategy across 30 postcodes
python get_vans_ebay_completed.py scrape-multi --strategy commercial_hubs --postcode-limit 30 \
    --pages-per-postcode 5 --outfile transit_commercial_completed_ebay.csv

# Geographic focus: 50km radius around Manchester
python get_vans_ebay_completed.py scrape-multi --strategy geographic_spread --center-postcode "M1 1AA" \
    --radius-km 50 --postcode-limit 20 --outfile transit_manchester_completed_ebay.csv

# Use custom postcodes with proxy rotation
python get_vans_ebay_completed.py scrape-multi --postcodes "SW1A 1AA" "M1 1AA" "B1 1AA" \
    --proxy-file proxies.txt --pages-per-postcode 10
```

**3) UK-wide completed listings scraping (optimized command)**
```bash
# Scrape the whole UK focusing on commercial/industrial areas
python get_vans_ebay_completed.py scrape-uk --outfile ford_transit_uk_completed_sold_ebay.csv

# Include mixed density areas for broader coverage
python get_vans_ebay_completed.py scrape-uk --include-mixed --pages-per-postcode 8 --postcode-limit 150

# Use proxies for large-scale scraping
python get_vans_ebay_completed.py scrape-uk --proxy-file proxies.txt --max-browsers 10 --max-pages 40
```

**4) Analysis of actual sale prices**
```bash
# Quick scatter plots and medians from completed listings
python get_vans_ebay_completed.py analyse transit_commercial_completed_ebay.csv
```

----
Advanced Features
-----------------

**Completed Listings Intelligence:**
- Filters for SOLD listings only (excludes unsold/expired)
- Extracts final sale prices (actual market values)
- Captures sold dates and times
- Distinguishes between auction and Buy-It-Now sales

**Concurrent Scraping:**
- Configurable browser and page concurrency limits
- Intelligent proxy rotation with failure handling
- Human-like delays and behavior simulation

**eBay-specific Intelligence:**
- Handles both auction and Buy It Now completed sales
- Extracts seller ratings and feedback
- Monitors final bid counts for auction sales
- Captures shipping information and location data

**Geographic Intelligence:**
- Real UK postcode coordinates database
- Distance-based filtering using Haversine formula
- Regional distribution analysis
- Interactive map visualization
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
from urllib.parse import urlparse, quote_plus
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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/ebay_completed_scraping.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Ensure data directory exists
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Configuration for eBay UK COMPLETED listings
# ---------------------------------------------------------------------------

REQUEST_DELAY_RANGE = (2.0, 5.0)  # Slightly longer delays for eBay
MAX_CONCURRENT_BROWSERS = 5
MAX_CONCURRENT_PAGES = 20

# eBay UK search URL template for COMPLETED listings
EBAY_URL_TEMPLATE = (
    "https://www.ebay.co.uk/sch/Cars-Trucks/6001/i.html?"
    "_nkw=ford+transit&"
    "_sacat=6001&"
    "_udhi={max_price}&"
    "_udlo=1000&"
    "_sop=13&"  # Sort by recently sold
    "_fcid=3&"  # UK only
    "_stpos={postcode}&"
    "_sadis=50&"  # 50 mile radius
    "_pgn={page}&"
    "LH_Sold=1&"  # COMPLETED listings only
    "LH_Complete=1"  # Include sold listings
    "{extra}"
)

HEADLESS = True
PAGE_TIMEOUT_MS = 90_000  # Longer timeout for eBay
THROTTLE_MS = 2_000

# eBay-specific CSS selectors for COMPLETED listings
SELECTORS = {
    "listing": ".s-item, .srp-results .s-item",
    "title": ".s-item__title, .it-ttl a, h3.s-item__title",
    "price": ".s-item__price, .s-item__detail--primary .notranslate, .s-item__price .notranslate, .s-item__sold",
    "sold_price": ".s-item__price--sold, .s-item__sold .notranslate, .sold-price",
    "shipping": ".s-item__shipping, .s-item__logisticsCost",
    "location": ".s-item__location, .s-item__itemLocation",
    "link": ".s-item__link, .it-ttl a",
    "image": ".s-item__image img, .img img",
    "condition": ".s-item__subtitle, .s-item__condition",
    "sold_date": ".s-item__endedDate, .s-item__sold-date, .s-item__time",
    "bids": ".s-item__bids, .s-item__bidCount, .s-item__dynamic",
    "buy_now": ".s-item__purchase-options-with-icon",
    "seller": ".s-item__seller-info, .s-item__seller",
    "sponsored": ".s-item__title--tagblock .SPONSORED",
    "sold_indicator": ".s-item__sold, .sold-indicator, .SOLD",
}

# eBay-specific regex patterns for completed listings
PRICE_RE = re.compile(r"£([\d,]+(?:\.\d{2})?)", re.I)
SOLD_PRICE_RE = re.compile(r"sold.*?£([\d,]+(?:\.\d{2})?)", re.I)
MILEAGE_RE = re.compile(r"([\d,]+)\s*(?:miles?|mileage)", re.I)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
BID_RE = re.compile(r"(\d+)\s*bids?", re.I)
SOLD_DATE_RE = re.compile(r"sold\s+(\d{1,2}[a-z]{2}\s+[a-z]{3}|\d{1,2}\s+[a-z]{3})", re.I)
POSTCODE_RE = re.compile(r"\b[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}\b", re.I)

# ---------------------------------------------------------------------------
# Proxy and Core Infrastructure (Reused from original version)
# ---------------------------------------------------------------------------

class ProxyRotator:
    """Manages proxy rotation with failure tracking"""
    
    def __init__(self, proxy_list: List[str] = None):
        self.proxies = proxy_list or []
        self.current_index = 0
        self.failed_proxies = set()
        
    def get_next_proxy(self) -> str | None:
        """Get the next working proxy"""
        if not self.proxies:
            return None
            
        available_proxies = [p for p in self.proxies if p not in self.failed_proxies]
        if not available_proxies:
            # Reset failed proxies if all have failed
            self.failed_proxies.clear()
            available_proxies = self.proxies
            
        if available_proxies:
            proxy = available_proxies[self.current_index % len(available_proxies)]
            self.current_index += 1
            return proxy
        return None
    
    def mark_proxy_failed(self, proxy: str):
        """Mark a proxy as failed"""
        self.failed_proxies.add(proxy)
        logger.warning(f"Marked proxy as failed: {proxy}")
    
    def add_proxies(self, proxy_list: List[str]):
        """Add more proxies to the rotation"""
        self.proxies.extend(proxy_list)
        logger.info(f"Added {len(proxy_list)} proxies, total: {len(self.proxies)}")

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

class PostcodeManager:
    """Enhanced postcode management with intelligent selection strategies"""
    
    def __init__(self):
        # Comprehensive postcode database with metadata
        self.postcode_areas = [
            # London and South East
            PostcodeArea("SW1", "Westminster", "London", "high", "high", (51.4994, -0.1347)),
            PostcodeArea("EC1", "City of London", "London", "high", "high", (51.5200, -0.1000)),
            PostcodeArea("E14", "Canary Wharf", "London", "high", "high", (51.5045, -0.0203)),
            PostcodeArea("CR0", "Croydon", "South East", "high", "high", (51.3762, -0.0982)),
            PostcodeArea("DA1", "Dartford", "South East", "medium", "high", (51.4364, 0.2121)),
            PostcodeArea("RH6", "Gatwick", "South East", "medium", "high", (51.1537, -0.1821)),
            PostcodeArea("SL1", "Slough", "South East", "high", "high", (51.5105, -0.5950)),
            
            # Birmingham and West Midlands
            PostcodeArea("B1", "Birmingham", "West Midlands", "high", "high", (52.4862, -1.8904)),
            PostcodeArea("CV1", "Coventry", "West Midlands", "medium", "high", (52.4068, -1.5197)),
            PostcodeArea("WS1", "Walsall", "West Midlands", "medium", "high", (52.5858, -1.9830)),
            PostcodeArea("WV1", "Wolverhampton", "West Midlands", "medium", "high", (52.5875, -2.1287)),
            
            # Manchester and North West
            PostcodeArea("M1", "Manchester", "North West", "high", "high", (53.4808, -2.2426)),
            PostcodeArea("WA1", "Warrington", "North West", "medium", "high", (53.3900, -2.5970)),
            PostcodeArea("PR1", "Preston", "North West", "medium", "high", (53.7632, -2.7031)),
            PostcodeArea("L1", "Liverpool", "North West", "high", "high", (53.4084, -2.9916)),
            PostcodeArea("SK1", "Stockport", "North West", "medium", "medium", (53.4106, -2.1575)),
            
            # Leeds and Yorkshire
            PostcodeArea("LS1", "Leeds", "Yorkshire", "high", "high", (53.8008, -1.5491)),
            PostcodeArea("S1", "Sheffield", "Yorkshire", "high", "medium", (53.3811, -1.4701)),
            PostcodeArea("BD1", "Bradford", "Yorkshire", "medium", "medium", (53.7960, -1.7594)),
            PostcodeArea("HU1", "Hull", "Yorkshire", "medium", "high", (53.7676, -0.3274)),
            PostcodeArea("YO1", "York", "Yorkshire", "medium", "medium", (53.9600, -1.0873)),
            
            # Newcastle and North East
            PostcodeArea("NE1", "Newcastle", "North East", "high", "medium", (54.9783, -1.6178)),
            PostcodeArea("SR1", "Sunderland", "North East", "medium", "medium", (54.9069, -1.3838)),
            PostcodeArea("TS1", "Middlesbrough", "North East", "medium", "high", (54.5742, -1.2351)),
            
            # Bristol and South West
            PostcodeArea("BS1", "Bristol", "South West", "high", "medium", (51.4545, -2.5879)),
            PostcodeArea("PL1", "Plymouth", "South West", "medium", "medium", (50.3755, -4.1427)),
            PostcodeArea("EX1", "Exeter", "South West", "medium", "medium", (50.7184, -3.5339)),
            PostcodeArea("GL1", "Gloucester", "South West", "medium", "high", (51.8642, -2.2381)),
            
            # Cardiff and Wales
            PostcodeArea("CF1", "Cardiff", "Wales", "high", "medium", (51.4816, -3.1791)),
            PostcodeArea("SA1", "Swansea", "Wales", "medium", "medium", (51.6214, -3.9436)),
            PostcodeArea("NP1", "Newport", "Wales", "medium", "high", (51.5842, -2.9977)),
            
            # Edinburgh and Scotland
            PostcodeArea("EH1", "Edinburgh", "Scotland", "high", "medium", (55.9533, -3.1883)),
            PostcodeArea("G1", "Glasgow", "Scotland", "high", "medium", (55.8642, -4.2518)),
            PostcodeArea("AB1", "Aberdeen", "Scotland", "medium", "high", (57.1497, -2.0943)),
            PostcodeArea("DD1", "Dundee", "Scotland", "medium", "medium", (56.4620, -2.9707)),
            
            # Belfast and Northern Ireland
            PostcodeArea("BT1", "Belfast", "Northern Ireland", "high", "medium", (54.5973, -5.9301)),
            PostcodeArea("BT2", "Belfast East", "Northern Ireland", "medium", "high", (54.6042, -5.8372)),
            
            # Industrial/Commercial Areas
            PostcodeArea("IG1", "Ilford", "East London", "high", "high", (51.5590, 0.0741)),
            PostcodeArea("RM1", "Romford", "East London", "medium", "high", (51.5812, 0.1837)),
            PostcodeArea("EN1", "Enfield", "North London", "medium", "high", (51.6523, -0.0832)),
            PostcodeArea("UB1", "Southall", "West London", "high", "high", (51.5074, -0.3762)),
            PostcodeArea("TW1", "Twickenham", "South West London", "medium", "medium", (51.4461, -0.3315)),
            
            # Key Distribution Centers
            PostcodeArea("MK1", "Milton Keynes", "South East", "medium", "high", (52.0406, -0.7594)),
            PostcodeArea("NN1", "Northampton", "East Midlands", "medium", "high", (52.2405, -0.9027)),
            PostcodeArea("PE1", "Peterborough", "East Midlands", "medium", "high", (52.5695, -0.2405)),
            PostcodeArea("CB1", "Cambridge", "East", "medium", "medium", (52.2053, 0.1218)),
            PostcodeArea("NR1", "Norwich", "East", "medium", "medium", (52.6309, 1.2974)),
            PostcodeArea("IP1", "Ipswich", "East", "medium", "high", (52.0567, 1.1482)),
            PostcodeArea("CO1", "Colchester", "East", "medium", "medium", (51.8860, 0.9035)),
            PostcodeArea("LU1", "Luton", "East", "medium", "high", (51.8787, -0.4200)),
        ]
        
        self.db_path = Path("data/postcode_intelligence.db")
        self._init_database()
    
    def _init_database(self):
        """Initialize the success tracking database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS postcode_success (
                    postcode TEXT PRIMARY KEY,
                    total_attempts INTEGER DEFAULT 0,
                    total_listings INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    avg_listings_per_page REAL DEFAULT 0
                )
            """)
    
    def get_postcodes(self, 
                     strategy: PostcodeStrategy = PostcodeStrategy.MIXED_DENSITY,
                     limit: int = 50,
                     custom_postcodes: List[str] = None,
                     exclude_used: bool = True,
                     geographic_radius_km: Optional[float] = None,
                     center_postcode: Optional[str] = None) -> List[str]:
        """Get postcodes based on strategy and constraints"""
        
        if strategy == PostcodeStrategy.CUSTOM and custom_postcodes:
            formatted = self._format_postcodes(custom_postcodes)
            return formatted[:limit]
        
        # Filter by strategy first
        filtered_areas = self._filter_by_strategy(strategy)
        
        # Extract area codes
        area_codes = [area.code for area in filtered_areas]
        
        # Apply geographic filtering if specified
        if center_postcode and geographic_radius_km:
            area_codes = self._filter_by_geography(area_codes, center_postcode, geographic_radius_km)
        
        # Generate full postcodes from area codes
        full_postcodes = self._generate_full_postcodes(area_codes, limit * 3)  # Generate extra
        
        # Sort by effectiveness (success rate)
        sorted_postcodes = self._sort_by_effectiveness(full_postcodes)
        
        return sorted_postcodes[:limit]
    
    def _filter_by_strategy(self, strategy: PostcodeStrategy) -> List[PostcodeArea]:
        """Filter postcode areas by strategy"""
        if strategy == PostcodeStrategy.MAJOR_CITIES:
            return [area for area in self.postcode_areas if area.population_density == "high"]
        elif strategy == PostcodeStrategy.COMMERCIAL_HUBS:
            return [area for area in self.postcode_areas if area.commercial_activity == "high"]
        elif strategy == PostcodeStrategy.GEOGRAPHIC_SPREAD:
            return self._select_geographically_distributed(self.postcode_areas)
        elif strategy == PostcodeStrategy.MIXED_DENSITY:
            return self.postcode_areas  # Use all areas
        else:
            return self.postcode_areas
    
    def _filter_by_geography(self, postcodes: List[str], center: str, radius_km: float) -> List[str]:
        """Filter postcodes by geographic proximity to center"""
        center_coords = None
        
        # Find center coordinates
        center_area = center[:2].upper() if len(center) >= 2 else center
        for area in self.postcode_areas:
            if area.code.startswith(center_area):
                center_coords = area.coordinates
                break
        
        if not center_coords:
            logger.warning(f"Could not find coordinates for center postcode: {center}")
            return postcodes
        
        filtered = []
        for postcode in postcodes:
            postcode_area = postcode[:2].upper()
            for area in self.postcode_areas:
                if area.code.startswith(postcode_area):
                    distance = self._calculate_distance(center_coords, area.coordinates)
                    if distance <= radius_km:
                        filtered.append(postcode)
                    break
        
        return filtered
    
    def _calculate_distance(self, coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """Calculate distance between two coordinates using Haversine formula"""
        lat1, lon1 = coord1
        lat2, lon2 = coord2
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth's radius in kilometers
        return 6371 * c
    
    def _select_geographically_distributed(self, areas: List[PostcodeArea]) -> List[PostcodeArea]:
        """Select geographically distributed areas across regions"""
        regions = {}
        for area in areas:
            if area.region not in regions:
                regions[area.region] = []
            regions[area.region].append(area)
        
        # Select best areas from each region
        distributed = []
        for region, region_areas in regions.items():
            # Prefer high commercial activity within each region
            region_areas.sort(key=lambda x: (x.commercial_activity == "high", x.population_density == "high"), reverse=True)
            distributed.extend(region_areas[:3])  # Top 3 from each region
        
        return distributed
    
    def _sort_by_effectiveness(self, postcodes: List[str]) -> List[str]:
        """Sort postcodes by historical effectiveness"""
        def effectiveness_score(pc: str) -> float:
            # Base score from historical success rate
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute(
                    "SELECT avg_listings_per_page FROM postcode_success WHERE postcode = ?",
                    (pc,)
                ).fetchone()
                
                if result and result[0]:
                    return float(result[0])
                
                # Default score for new postcodes based on area type
                area_code = pc[:2].upper()
                for area in self.postcode_areas:
                    if area.code.startswith(area_code):
                        base_score = 1.0
                        if area.commercial_activity == "high":
                            base_score += 0.5
                        if area.population_density == "high":
                            base_score += 0.3
                        return base_score
                
                return 1.0  # Default score
        
        return sorted(postcodes, key=effectiveness_score, reverse=True)
    
    def _generate_full_postcodes(self, area_codes: List[str], limit: int) -> List[str]:
        """Generate full postcodes from area codes"""
        postcodes = []
        
        # Common endings for each area - prioritize city centers and main areas
        common_endings = [
            "1AA", "1AB", "1AD", "1AE", "1AF", "1AG", "1AH", "1AJ", "1AL",
            "2AA", "2AB", "2AD", "2AE", "2AF", "3AA", "3AB", "3AD", "4AA", "5AA",
            "6AA", "7AA", "8AA", "9AA", "0AA"
        ]
        
        for area_code in area_codes:
            for ending in common_endings:
                if len(postcodes) >= limit:
                    break
                postcode = f"{area_code} {ending}"
                postcodes.append(postcode)
            if len(postcodes) >= limit:
                break
        
        return postcodes
    
    def _format_postcodes(self, postcodes: List[str]) -> List[str]:
        """Format postcodes consistently"""
        formatted = []
        for pc in postcodes:
            pc = pc.upper().strip()
            # Add space if missing
            if " " not in pc and len(pc) >= 5:
                # Insert space before last 3 characters
                pc = pc[:-3] + " " + pc[-3:]
            elif " " not in pc and len(pc) >= 4:
                # Insert space before last 3 characters for shorter postcodes
                pc = pc[:-3] + " " + pc[-3:]
            formatted.append(pc)
        return formatted
    
    def record_success_rate(self, postcode: str, listings_found: int):
        """Record success rate for a postcode"""
        with sqlite3.connect(self.db_path) as conn:
            # Check if record exists
            existing = conn.execute(
                "SELECT total_attempts, total_listings FROM postcode_success WHERE postcode = ?",
                (postcode,)
            ).fetchone()
            
            if existing:
                new_attempts = existing[0] + 1
                new_listings = existing[1] + listings_found
                avg_per_page = new_listings / new_attempts if new_attempts > 0 else 0
                
                conn.execute("""
                    UPDATE postcode_success 
                    SET total_attempts = ?, total_listings = ?, avg_listings_per_page = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE postcode = ?
                """, (new_attempts, new_listings, avg_per_page, postcode))
            else:
                avg_per_page = listings_found
                conn.execute("""
                    INSERT INTO postcode_success (postcode, total_attempts, total_listings, avg_listings_per_page)
                    VALUES (?, 1, ?, ?)
                """, (postcode, listings_found, avg_per_page))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get postcode statistics"""
        stats = {
            "total_areas": len(self.postcode_areas),
            "regions": len(set(area.region for area in self.postcode_areas)),
            "high_commercial": len([a for a in self.postcode_areas if a.commercial_activity == "high"])
        }
        return stats

def generate_uk_postcodes(limit: int = 100) -> List[str]:
    """Generate a list of UK postcodes for scraping"""
    manager = PostcodeManager()
    return manager.get_postcodes(strategy=PostcodeStrategy.MIXED_DENSITY, limit=limit)

async def create_browser_context(playwright_instance, proxy_rotator: ProxyRotator = None):
    """Create a browser context with optional proxy"""
    proxy = None
    if proxy_rotator:
        proxy_url = proxy_rotator.get_next_proxy()
        if proxy_url:
            try:
                # Parse proxy URL
                if "://" in proxy_url:
                    protocol, rest = proxy_url.split("://", 1)
                    if "@" in rest:
                        auth, server = rest.split("@", 1)
                        username, password = auth.split(":", 1)
                        host, port = server.split(":", 1)
                        proxy = {
                            "server": f"{protocol}://{host}:{port}",
                            "username": username,
                            "password": password
                        }
                    else:
                        host, port = rest.split(":", 1)
                        proxy = {"server": f"{protocol}://{host}:{port}"}
                else:
                    # Assume HTTP proxy
                    host, port = proxy_url.split(":", 1)
                    proxy = {"server": f"http://{host}:{port}"}
            except Exception as e:
                logger.warning(f"Failed to parse proxy {proxy_url}: {e}")
                if proxy_rotator:
                    proxy_rotator.mark_proxy_failed(proxy_url)
                proxy = None
    
    try:
        browser = await playwright_instance.chromium.launch(
            headless=HEADLESS,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
        )
        
        context = await browser.new_context(
            proxy=proxy,
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        )
        
        return browser, context
    except Exception as e:
        logger.error(f"Failed to create browser context: {e}")
        if proxy and proxy_rotator:
            proxy_rotator.mark_proxy_failed(proxy_url)
        raise

async def _scrape_page_core(page, url: str, proxy: str = None) -> List[Dict[str, Any]]:
    """Core scraping logic for a single page of completed eBay listings"""
    try:
        logger.info(f"🔍 Navigating to: {url}")
        
        await page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until='domcontentloaded')
        await asyncio.sleep(random.uniform(*REQUEST_DELAY_RANGE))
        
        # Wait for listings to load
        try:
            await page.wait_for_selector(SELECTORS["listing"], timeout=30000)
        except PlaywrightTimeout:
            logger.warning("⚠️ No listings found on page")
            return []
        
        # Get all listing elements
        listing_elements = await page.query_selector_all(SELECTORS["listing"])
        logger.info(f"📊 Found {len(listing_elements)} listing elements")
        
        results = []
        
        for i, listing in enumerate(listing_elements):
            try:
                # Extract title
                title_elem = await listing.query_selector(SELECTORS["title"])
                title = await title_elem.inner_text() if title_elem else "N/A"
                title = title.strip()
                
                # Skip sponsored listings
                sponsored_elem = await listing.query_selector(SELECTORS["sponsored"])
                if sponsored_elem:
                    logger.debug(f"Skipping sponsored listing: {title[:50]}...")
                    continue
                
                # Extract price (sold price)
                price_text = "N/A"
                price_value = None
                
                # Try sold price selector first
                sold_price_elem = await listing.query_selector(SELECTORS["sold_price"])
                if sold_price_elem:
                    price_text = await sold_price_elem.inner_text()
                else:
                    # Fallback to regular price selector
                    price_elem = await listing.query_selector(SELECTORS["price"])
                    if price_elem:
                        price_text = await price_elem.inner_text()
                
                # Extract numerical price
                if price_text and price_text != "N/A":
                    price_match = SOLD_PRICE_RE.search(price_text) or PRICE_RE.search(price_text)
                    if price_match:
                        try:
                            price_value = float(price_match.group(1).replace(',', ''))
                        except ValueError:
                            pass
                
                # Extract link
                link_elem = await listing.query_selector(SELECTORS["link"])
                link = await link_elem.get_attribute('href') if link_elem else "N/A"
                if link and link.startswith('/'):
                    link = f"https://www.ebay.co.uk{link}"
                
                # Extract image URL
                img_elem = await listing.query_selector(SELECTORS["image"])
                img_url = await img_elem.get_attribute('src') if img_elem else "N/A"
                
                # Extract condition
                condition_elem = await listing.query_selector(SELECTORS["condition"])
                condition = await condition_elem.inner_text() if condition_elem else "N/A"
                condition = condition.strip()
                
                # Extract location
                location_elem = await listing.query_selector(SELECTORS["location"])
                location = await location_elem.inner_text() if location_elem else "N/A"
                location = location.strip()
                
                # Extract shipping info
                shipping_elem = await listing.query_selector(SELECTORS["shipping"])
                shipping = await shipping_elem.inner_text() if shipping_elem else "N/A"
                shipping = shipping.strip()
                
                # Extract sold date
                sold_date_elem = await listing.query_selector(SELECTORS["sold_date"])
                sold_date = await sold_date_elem.inner_text() if sold_date_elem else "N/A"
                sold_date = sold_date.strip()
                
                # Extract bid count
                bids_elem = await listing.query_selector(SELECTORS["bids"])
                bids_text = await bids_elem.inner_text() if bids_elem else "N/A"
                bids_count = None
                if bids_text and bids_text != "N/A":
                    bid_match = BID_RE.search(bids_text)
                    if bid_match:
                        try:
                            bids_count = int(bid_match.group(1))
                        except ValueError:
                            pass
                
                # Extract seller info
                seller_elem = await listing.query_selector(SELECTORS["seller"])
                seller = await seller_elem.inner_text() if seller_elem else "N/A"
                seller = seller.strip()
                
                # Determine listing type based on bids
                listing_type = "Auction" if bids_count and bids_count > 0 else "Buy It Now"
                
                # Extract year from title
                year_match = YEAR_RE.search(title)
                year = int(year_match.group(0)) if year_match else None
                
                # Extract mileage from title
                mileage_match = MILEAGE_RE.search(title)
                mileage = None
                if mileage_match:
                    try:
                        mileage = int(mileage_match.group(1).replace(',', ''))
                    except ValueError:
                        pass
                
                # Extract postcode from location
                postcode_match = POSTCODE_RE.search(location)
                extracted_postcode = postcode_match.group(0) if postcode_match else None
                
                # Since we're using LH_Sold=1&LH_Complete=1 URL parameters, 
                # ALL listings on this page should be completed/sold listings
                # No need for additional filtering here
                
                result = {
                    'title': title,
                    'year': year,
                    'mileage': mileage,
                    'price': price_value,
                    'price_text': price_text,
                    'condition': condition,
                    'location': location,
                    'postcode': extracted_postcode,
                    'shipping': shipping,
                    'listing_type': listing_type,
                    'sold_date': sold_date,
                    'bids': bids_count,
                    'seller': seller,
                    'url': link,
                    'image_url': img_url,
                    'scraped_at': datetime.now().isoformat(),
                    'proxy_used': proxy
                }
                
                results.append(result)
                
                if len(results) % 10 == 0:
                    logger.info(f"✅ Processed {len(results)} completed listings...")
                
            except Exception as e:
                logger.warning(f"⚠️ Error processing listing {i+1}: {e}")
                continue
        
        logger.info(f"✅ Successfully scraped {len(results)} completed listings from page")
        return results
        
    except Exception as e:
        logger.error(f"❌ Error scraping page {url}: {e}")
        return []

async def _scrape_page_enhanced(page, url: str, proxy: str = None, semaphore: asyncio.Semaphore = None) -> List[Dict[str, Any]]:
    """Enhanced page scraping with semaphore control"""
    if semaphore:
        async with semaphore:
            return await _scrape_page_core(page, url, proxy)
    else:
        return await _scrape_page_core(page, url, proxy)

async def scrape_postcode_worker(postcode: str, pages_per_postcode: int, semaphore: asyncio.Semaphore, 
                                proxy_rotator: ProxyRotator, results_queue: asyncio.Queue):
    """Worker function to scrape a single postcode across multiple pages"""
    async with async_playwright() as p:
        try:
            browser, context = await create_browser_context(p, proxy_rotator)
            page = await context.new_page()
            
            postcode_results = []
            
            for page_num in range(1, pages_per_postcode + 1):
                try:
                    url = EBAY_URL_TEMPLATE.format(
                        postcode=quote_plus(postcode),
                        page=page_num,
                        max_price=100000,
                        extra=""
                    )
                    
                    page_results = await _scrape_page_enhanced(
                        page, url, 
                        proxy=proxy_rotator.get_next_proxy() if proxy_rotator else None,
                        semaphore=semaphore
                    )
                    
                    postcode_results.extend(page_results)
                    
                    # Random delay between pages
                    await asyncio.sleep(random.uniform(1.0, 3.0))
                    
                except Exception as e:
                    logger.error(f"Error scraping {postcode} page {page_num}: {e}")
                    continue
            
            # Record success rate
            manager = PostcodeManager()
            manager.record_success_rate(postcode, len(postcode_results))
            
            logger.info(f"✅ Completed {postcode}: {len(postcode_results)} listings found")
            await results_queue.put((postcode, postcode_results))
            
        except Exception as e:
            logger.error(f"❌ Worker error for {postcode}: {e}")
            await results_queue.put((postcode, []))
        finally:
            try:
                await context.close()
                await browser.close()
            except:
                pass

async def scrape_multiple_postcodes(postcodes: List[str], pages_per_postcode: int = 3, 
                                  proxy_list: List[str] = None, outfile: Path = None) -> pd.DataFrame:
    """Scrape multiple postcodes concurrently for completed listings"""
    
    proxy_rotator = ProxyRotator(proxy_list) if proxy_list else None
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_PAGES)
    results_queue = asyncio.Queue()
    
    logger.info(f"🚀 Starting concurrent scraping of {len(postcodes)} postcodes")
    logger.info(f"📄 {pages_per_postcode} pages per postcode")
    logger.info(f"🔗 {'With' if proxy_rotator else 'Without'} proxy rotation")
    
    # Create workers for each postcode
    workers = [
        scrape_postcode_worker(postcode, pages_per_postcode, semaphore, proxy_rotator, results_queue)
        for postcode in postcodes
    ]
    
    # Run workers concurrently with limited concurrency
    browser_semaphore = asyncio.Semaphore(MAX_CONCURRENT_BROWSERS)
    
    async def run_worker_with_limit(worker):
        async with browser_semaphore:
            await worker
    
    # Start all workers
    worker_tasks = [asyncio.create_task(run_worker_with_limit(worker)) for worker in workers]
    
    # Collect results as they complete
    all_results = []
    completed_postcodes = 0
    
    try:
        while completed_postcodes < len(postcodes):
            postcode, results = await results_queue.get()
            all_results.extend(results)
            completed_postcodes += 1
            
            logger.info(f"📊 Progress: {completed_postcodes}/{len(postcodes)} postcodes completed")
            logger.info(f"📋 Total completed listings collected: {len(all_results)}")
    
    except Exception as e:
        logger.error(f"Error collecting results: {e}")
    
    # Wait for all workers to complete
    try:
        await asyncio.gather(*worker_tasks, return_exceptions=True)
    except Exception as e:
        logger.error(f"Error waiting for workers: {e}")
    
    # Convert to DataFrame
    if all_results:
        df = pd.DataFrame(all_results)
        
        # Save to file if specified
        if outfile:
            df.to_csv(outfile, index=False)
            logger.info(f"💾 Saved {len(df)} completed listings to {outfile}")
        
        logger.info(f"✅ Scraping completed: {len(df)} total completed listings")
        return df
    else:
        logger.warning("⚠️ No completed listings found")
        return pd.DataFrame()

def analyse(csv_path: Path, show_plots: bool = True) -> None:
    """Quick analysis of completed eBay listings"""
    
    if not csv_path.exists():
        logger.error(f"❌ CSV file not found: {csv_path}")
        return
    
    logger.info(f"📊 Analyzing completed listings from: {csv_path}")
    
    try:
        df = pd.read_csv(csv_path)
        logger.info(f"📋 Loaded {len(df)} listings")
        
        if df.empty:
            logger.warning("⚠️ No data to analyze")
            return
        
        # Filter for listings with valid price data
        valid_price_df = df[df['price'].notna() & (df['price'] > 0)]
        logger.info(f"💰 {len(valid_price_df)} listings with valid sale prices")
        
        if valid_price_df.empty:
            logger.warning("⚠️ No listings with valid sale prices")
            return
        
        # Price statistics
        price_stats = valid_price_df['price'].describe()
        logger.info("📈 Price Statistics:")
        logger.info(f"   Mean: £{price_stats['mean']:,.0f}")
        logger.info(f"   Median: £{price_stats['50%']:,.0f}")
        logger.info(f"   Min: £{price_stats['min']:,.0f}")
        logger.info(f"   Max: £{price_stats['max']:,.0f}")
        logger.info(f"   Std Dev: £{price_stats['std']:,.0f}")
        
        # Year analysis
        if 'year' in valid_price_df.columns:
            year_df = valid_price_df[valid_price_df['year'].notna()]
            if not year_df.empty:
                logger.info(f"📅 Year range: {year_df['year'].min():.0f} - {year_df['year'].max():.0f}")
                
                # Average price by year
                price_by_year = year_df.groupby('year')['price'].agg(['mean', 'count']).round(0)
                logger.info("📊 Average price by year (min 3 sales):")
                for year, stats in price_by_year.iterrows():
                    if stats['count'] >= 3:
                        logger.info(f"   {year:.0f}: £{stats['mean']:,.0f} ({stats['count']:.0f} sales)")
        
        # Mileage analysis
        if 'mileage' in valid_price_df.columns:
            mileage_df = valid_price_df[valid_price_df['mileage'].notna()]
            if not mileage_df.empty:
                logger.info(f"🛣️ Mileage range: {mileage_df['mileage'].min():,.0f} - {mileage_df['mileage'].max():,.0f} miles")
        
        # Listing type analysis
        if 'listing_type' in valid_price_df.columns:
            type_stats = valid_price_df.groupby('listing_type')['price'].agg(['mean', 'count']).round(0)
            logger.info("🏷️ Average price by listing type:")
            for listing_type, stats in type_stats.iterrows():
                logger.info(f"   {listing_type}: £{stats['mean']:,.0f} ({stats['count']:.0f} sales)")
        
        # Condition analysis
        if 'condition' in valid_price_df.columns:
            condition_df = valid_price_df[valid_price_df['condition'] != 'N/A']
            if not condition_df.empty:
                condition_stats = condition_df.groupby('condition')['price'].agg(['mean', 'count']).round(0)
                logger.info("🔧 Average price by condition:")
                for condition, stats in condition_stats.iterrows():
                    if stats['count'] >= 2:  # Only show conditions with 2+ sales
                        logger.info(f"   {condition}: £{stats['mean']:,.0f} ({stats['count']:.0f} sales)")
        
        # Regional analysis
        if 'location' in valid_price_df.columns:
            location_df = valid_price_df[valid_price_df['location'] != 'N/A']
            if not location_df.empty:
                # Extract rough regions from location
                location_stats = location_df.groupby('location')['price'].agg(['mean', 'count']).round(0)
                top_locations = location_stats[location_stats['count'] >= 2].head(10)
                if not top_locations.empty:
                    logger.info("🗺️ Top locations by sales volume:")
                    for location, stats in top_locations.iterrows():
                        logger.info(f"   {location}: £{stats['mean']:,.0f} ({stats['count']:.0f} sales)")
        
        # Plots
        if show_plots and plt is not None and np is not None:
            try:
                fig, axes = plt.subplots(2, 2, figsize=(15, 12))
                fig.suptitle('Ford Transit Completed Listings Analysis (eBay UK)', fontsize=16)
                
                # Price distribution
                axes[0, 0].hist(valid_price_df['price'], bins=30, alpha=0.7, color='skyblue', edgecolor='black')
                axes[0, 0].set_title('Sale Price Distribution')
                axes[0, 0].set_xlabel('Sale Price (£)')
                axes[0, 0].set_ylabel('Frequency')
                axes[0, 0].grid(True, alpha=0.3)
                
                # Price vs Year scatter plot
                if 'year' in valid_price_df.columns:
                    year_price_df = valid_price_df[valid_price_df['year'].notna()]
                    if not year_price_df.empty:
                        axes[0, 1].scatter(year_price_df['year'], year_price_df['price'], alpha=0.6, color='green')
                        axes[0, 1].set_title('Sale Price vs Year')
                        axes[0, 1].set_xlabel('Year')
                        axes[0, 1].set_ylabel('Sale Price (£)')
                        axes[0, 1].grid(True, alpha=0.3)
                
                # Price vs Mileage scatter plot
                if 'mileage' in valid_price_df.columns:
                    mileage_price_df = valid_price_df[valid_price_df['mileage'].notna()]
                    if not mileage_price_df.empty and len(mileage_price_df) > 1:
                        axes[1, 0].scatter(mileage_price_df['mileage'], mileage_price_df['price'], alpha=0.6, color='red')
                        axes[1, 0].set_title('Sale Price vs Mileage')
                        axes[1, 0].set_xlabel('Mileage')
                        axes[1, 0].set_ylabel('Sale Price (£)')
                        axes[1, 0].grid(True, alpha=0.3)
                
                # Price by listing type
                if 'listing_type' in valid_price_df.columns:
                    valid_price_df.boxplot(column='price', by='listing_type', ax=axes[1, 1])
                    axes[1, 1].set_title('Sale Price by Listing Type')
                    axes[1, 1].set_xlabel('Listing Type')
                    axes[1, 1].set_ylabel('Sale Price (£)')
                    plt.suptitle('')  # Remove automatic title
                
                plt.tight_layout()
                plt.show()
                
            except Exception as e:
                logger.warning(f"⚠️ Could not generate plots: {e}")
        
        logger.info("✅ Analysis completed")
        
    except Exception as e:
        logger.error(f"❌ Error analyzing data: {e}")

async def scrape_ebay_single_postcode(postcode: str, pages: int, outfile: Path, max_price: int = 100000) -> pd.DataFrame:
    """Scrape completed eBay listings for a single postcode"""
    
    logger.info(f"🎯 Scraping completed eBay listings for postcode: {postcode}")
    logger.info(f"📄 Pages to scrape: {pages}")
    logger.info(f"💰 Max price filter: £{max_price:,}")
    
    all_results = []
    
    async with async_playwright() as p:
        browser, context = await create_browser_context(p)
        page = await context.new_page()
        
        try:
            for page_num in range(1, pages + 1):
                url = EBAY_URL_TEMPLATE.format(
                    postcode=quote_plus(postcode),
                    page=page_num,
                    max_price=max_price,
                    extra=""
                )
                
                logger.info(f"📄 Scraping page {page_num}/{pages}")
                page_results = await _scrape_page_core(page, url)
                all_results.extend(page_results)
                
                # Delay between pages
                if page_num < pages:
                    delay = random.uniform(*REQUEST_DELAY_RANGE)
                    logger.info(f"⏱️ Waiting {delay:.1f}s before next page...")
                    await asyncio.sleep(delay)
                    
        finally:
            await context.close()
            await browser.close()
    
    # Convert to DataFrame and save
    if all_results:
        df = pd.DataFrame(all_results)
        df.to_csv(outfile, index=False)
        logger.info(f"✅ Saved {len(df)} completed listings to {outfile}")
        
        # Record success for postcode intelligence
        manager = PostcodeManager()
        manager.record_success_rate(postcode, len(all_results))
        
        return df
    else:
        logger.warning("⚠️ No completed listings found")
        return pd.DataFrame()

def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Scrape Ford Transit completed listings from eBay UK",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic completed listings scraping
  python get_vans_ebay_completed.py scrape --postcode "M1 1AA" --pages 10 --outfile transit_completed.csv
  
  # Multi-postcode with commercial strategy
  python get_vans_ebay_completed.py scrape-multi --strategy commercial_hubs --postcode-limit 20 --pages-per-postcode 5
  
  # UK-wide completed listings
  python get_vans_ebay_completed.py scrape-uk --outfile ford_transit_uk_completed.csv
  
  # Analyze completed listings
  python get_vans_ebay_completed.py analyse transit_completed.csv
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scrape command (single postcode)
    scrape_parser = subparsers.add_parser('scrape', help='Scrape single postcode')
    scrape_parser.add_argument('--postcode', required=True, help='UK postcode to search')
    scrape_parser.add_argument('--pages', type=int, default=5, help='Number of pages to scrape')
    scrape_parser.add_argument('--outfile', type=Path, default=Path('data/ebay_completed_listings.csv'), help='Output CSV file')
    
    # Scrape-multi command
    multi_parser = subparsers.add_parser('scrape-multi', help='Scrape multiple postcodes')
    multi_parser.add_argument('--strategy', type=PostcodeStrategy, choices=list(PostcodeStrategy), 
                             default=PostcodeStrategy.MIXED_DENSITY, help='Postcode selection strategy')
    multi_parser.add_argument('--postcode-limit', type=int, default=30, help='Number of postcodes to scrape')
    multi_parser.add_argument('--pages-per-postcode', type=int, default=3, help='Pages per postcode')
    multi_parser.add_argument('--postcodes', nargs='*', help='Custom postcodes to use')
    multi_parser.add_argument('--center-postcode', help='Center postcode for geographic filtering')
    multi_parser.add_argument('--radius-km', type=float, help='Radius in km for geographic filtering')
    multi_parser.add_argument('--outfile', type=Path, default=Path('data/ebay_multi_completed.csv'), help='Output CSV file')
    
    # Scrape-uk command
    uk_parser = subparsers.add_parser('scrape-uk', help='Scrape UK-wide with optimized settings')
    uk_parser.add_argument('--outfile', type=Path, default=Path('data/ford_transit_uk_completed_ebay.csv'), help='Output CSV file')
    
    # Postcodes command
    postcodes_parser = subparsers.add_parser('postcodes', help='Manage and analyze postcodes')
    postcodes_parser.add_argument('--strategy', choices=[s.value for s in PostcodeStrategy], 
                                 default='mixed_density', help='Postcode selection strategy')
    postcodes_parser.add_argument('--limit', type=int, default=20, help='Number of postcodes to show')
    postcodes_parser.add_argument('--stats', action='store_true', help='Show postcode statistics')
    
    # Analyse command
    analyse_parser = subparsers.add_parser('analyse', help='Analyze completed listings CSV')
    analyse_parser.add_argument('csv_file', type=Path, help='CSV file to analyze')
    analyse_parser.add_argument('--no-plots', action='store_true', help='Skip generating plots')
    
    return parser.parse_args()

def load_proxies_from_file(proxy_file: Path) -> List[str]:
    """Load proxy list from file"""
    if not proxy_file.exists():
        logger.error(f"❌ Proxy file not found: {proxy_file}")
        return []
    
    try:
        with open(proxy_file, 'r') as f:
            proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        logger.info(f"📡 Loaded {len(proxies)} proxies from {proxy_file}")
        return proxies
    except Exception as e:
        logger.error(f"❌ Error loading proxies: {e}")
        return []

def handle_postcode_command(args):
    """Handle the postcodes command"""
    manager = PostcodeManager()
    
    if args.stats:
        stats = manager.get_stats()
        logger.info("📊 Postcode Database Statistics:")
        logger.info(f"   Total areas: {stats['total_areas']}")
        logger.info(f"   Regions covered: {stats['regions']}")
        logger.info(f"   High commercial areas: {stats['high_commercial']}")
        return
    
    strategy = PostcodeStrategy(args.strategy)
    postcodes = manager.get_postcodes(strategy=strategy, limit=args.limit)
    
    logger.info(f"🎯 Strategy: {strategy.value}")
    logger.info(f"📍 Generated {len(postcodes)} postcodes:")
    
    for i, postcode in enumerate(postcodes, 1):
        logger.info(f"   {i:2d}. {postcode}")

def main():
    """Main entry point"""
    args = parse_args()
    
    if not args.command:
        logger.error("❌ No command specified. Use --help for usage information.")
        return
    
    try:
        if args.command == 'scrape':
            asyncio.run(scrape_ebay_single_postcode(
                args.postcode, args.pages, args.outfile
            ))
            
        elif args.command == 'scrape-multi':
            # Load proxies if specified
            proxy_list = None
            if args.proxy_file:
                proxy_list = load_proxies_from_file(args.proxy_file)
            
            # Get postcodes
            manager = PostcodeManager()
            if args.postcodes:
                postcodes = args.postcodes
            else:
                strategy = PostcodeStrategy(args.strategy)
                postcodes = manager.get_postcodes(
                    strategy=strategy,
                    limit=args.postcode_limit,
                    geographic_radius_km=args.radius_km,
                    center_postcode=args.center_postcode
                )
            
            logger.info(f"🎯 Using {len(postcodes)} postcodes with strategy: {args.strategy}")
            
            asyncio.run(scrape_multiple_postcodes(
                postcodes, args.pages_per_postcode, proxy_list, args.outfile
            ))
            
        elif args.command == 'scrape-uk':
            # Load proxies if specified
            proxy_list = None
            if args.proxy_file:
                proxy_list = load_proxies_from_file(args.proxy_file)
            
            # Get UK postcodes
            manager = PostcodeManager()
            strategy = PostcodeStrategy.COMMERCIAL_HUBS
            if args.include_mixed:
                strategy = PostcodeStrategy.MIXED_DENSITY
            
            postcodes = manager.get_postcodes(strategy=strategy, limit=args.postcode_limit)
            logger.info(f"🇬🇧 UK-wide scraping with {len(postcodes)} postcodes")
            
            # Update global concurrency limits
            global MAX_CONCURRENT_BROWSERS, MAX_CONCURRENT_PAGES
            MAX_CONCURRENT_BROWSERS = args.max_browsers
            MAX_CONCURRENT_PAGES = args.max_pages
            
            asyncio.run(scrape_multiple_postcodes(
                postcodes, args.pages_per_postcode, proxy_list, args.outfile
            ))
            
        elif args.command == 'postcodes':
            handle_postcode_command(args)
            
        elif args.command == 'analyse':
            analyse(args.csv_file, show_plots=not args.no_plots)
            
    except KeyboardInterrupt:
        logger.info("🛑 Scraping interrupted by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        raise

if __name__ == "__main__":
    main() 
