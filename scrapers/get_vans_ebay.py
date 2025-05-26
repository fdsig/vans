#!/usr/bin/env python3
"""
Scrape and Analyse Ford Transit L2 H2 Listings from eBay UK
==========================================================

*Enhanced eBay scraping system with intelligent postcode management, 
concurrent scraping with proxy support, and advanced geographic intelligence.*

This script supports these sub‑commands:

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

**1) Basic scraping (single postcode)**
```bash
python get_vans_ebay.py scrape --postcode G23NX --pages 15 --outfile transit_l2h2_ebay.csv
```

**2) Smart multi-postcode scraping**
```bash
# Use commercial hubs strategy across 30 postcodes
python get_vans_ebay.py scrape-multi --strategy commercial_hubs --postcode-limit 30 \
    --pages-per-postcode 5 --outfile transit_commercial_ebay.csv

# Geographic focus: 50km radius around Manchester
python get_vans_ebay.py scrape-multi --strategy geographic_spread --center-postcode "M1 1AA" \
    --radius-km 50 --postcode-limit 20 --outfile transit_manchester_area_ebay.csv

# Use custom postcodes with proxy rotation
python get_vans_ebay.py scrape-multi --postcodes "SW1A 1AA" "M1 1AA" "B1 1AA" \
    --proxy-file proxies.txt --pages-per-postcode 10
```

**3) UK-wide scraping (optimized command)**
```bash
# Scrape the whole UK focusing on commercial/industrial areas
python get_vans_ebay.py scrape-uk --outfile ford_transit_uk_complete_ebay.csv

# Include mixed density areas for broader coverage
python get_vans_ebay.py scrape-uk --include-mixed --pages-per-postcode 8 --postcode-limit 150

# Use proxies for large-scale scraping
python get_vans_ebay.py scrape-uk --proxy-file proxies.txt --max-browsers 10 --max-pages 40
```

**4) Analysis**
```bash
# Quick scatter plots and medians
python get_vans_ebay.py analyse transit_commercial_ebay.csv
```

----
Advanced Features
-----------------

**Concurrent Scraping:**
- Configurable browser and page concurrency limits
- Intelligent proxy rotation with failure handling
- Human-like delays and behavior simulation

**eBay-specific Intelligence:**
- Handles both auction and Buy It Now listings
- Extracts seller ratings and feedback
- Monitors watch counts and bid counts
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
        logging.FileHandler('logs/ebay_scraping.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Ensure data directory exists
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Configuration for eBay UK
# ---------------------------------------------------------------------------

REQUEST_DELAY_RANGE = (2.0, 5.0)  # Slightly longer delays for eBay
MAX_CONCURRENT_BROWSERS = 5
MAX_CONCURRENT_PAGES = 20

# eBay UK search URL template
EBAY_URL_TEMPLATE = (
    "https://www.ebay.co.uk/sch/Cars-Trucks/6001/i.html?"
    "_nkw=ford+transit&"
    "_sacat=6001&"
    "_udhi={max_price}&"
    "_udlo=1000&"
    "_sop=7&"  # Sort by ending soonest
    "_fcid=3&"  # UK only
    "_stpos={postcode}&"
    "_sadis=50&"  # 50 mile radius
    "_pgn={page}"
    "{extra}"
)

HEADLESS = True
PAGE_TIMEOUT_MS = 90_000  # Longer timeout for eBay
THROTTLE_MS = 2_000

# eBay-specific CSS selectors
SELECTORS = {
    "listing": ".s-item, .srp-results .s-item",
    "title": ".s-item__title, .it-ttl a, h3.s-item__title",
    "price": ".s-item__price, .s-item__detail--primary .notranslate, .s-item__price .notranslate",
    "shipping": ".s-item__shipping, .s-item__logisticsCost",
    "location": ".s-item__location, .s-item__itemLocation",
    "link": ".s-item__link, .it-ttl a",
    "image": ".s-item__image img, .img img",
    "condition": ".s-item__subtitle, .s-item__condition",
    "time_left": ".s-item__time-left, .s-item__timeLeft",
    "watchers": ".s-item__watchers, .s-item__watchCountTotal",
    "bids": ".s-item__bids, .s-item__bidCount, .s-item__dynamic",
    "buy_now": ".s-item__purchase-options-with-icon",
    "seller": ".s-item__seller-info, .s-item__seller",
    "sponsored": ".s-item__title--tagblock .SPONSORED",
}

# eBay-specific regex patterns
PRICE_RE = re.compile(r"£([\d,]+(?:\.\d{2})?)", re.I)
MILEAGE_RE = re.compile(r"([\d,]+)\s*(?:miles?|mileage)", re.I)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
BID_RE = re.compile(r"(\d+)\s*bids?", re.I)
WATCHERS_RE = re.compile(r"(\d+)\s*watchers?", re.I)
POSTCODE_RE = re.compile(r"\b[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}\b", re.I)

# ---------------------------------------------------------------------------
# Proxy and Core Infrastructure (Reused from AutoTrader version)
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
        
        self.used_postcodes = set()
        self.success_rates = {}  # postcode -> success_rate
        
    def get_postcodes(self, 
                     strategy: PostcodeStrategy = PostcodeStrategy.MIXED_DENSITY,
                     limit: int = 50,
                     custom_postcodes: List[str] = None,
                     exclude_used: bool = True,
                     geographic_radius_km: Optional[float] = None,
                     center_postcode: Optional[str] = None) -> List[str]:
        """Get postcodes based on specified strategy"""
        
        if strategy == PostcodeStrategy.CUSTOM and custom_postcodes:
            postcodes = custom_postcodes[:limit]
        else:
            # Filter areas based on strategy
            filtered_areas = self._filter_by_strategy(strategy)
            area_codes = [area.code for area in filtered_areas]
            
            # Apply geographic filtering if specified
            if center_postcode and geographic_radius_km:
                area_codes = self._filter_by_geography(area_codes, center_postcode, geographic_radius_km)
            
            # Sort by effectiveness (success rate)
            area_codes = self._sort_by_effectiveness(area_codes)
            
            # Generate full postcodes
            postcodes = self._generate_full_postcodes(area_codes, limit)
        
        # Exclude used postcodes if requested
        if exclude_used:
            postcodes = [pc for pc in postcodes if pc not in self.used_postcodes]
        
        # Format postcodes properly
        postcodes = self._format_postcodes(postcodes)
        
        return postcodes[:limit]
    
    def _filter_by_strategy(self, strategy: PostcodeStrategy) -> List[PostcodeArea]:
        """Filter postcode areas based on strategy"""
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
        """Filter postcodes by geographic distance"""
        center_coords = None
        for area in self.postcode_areas:
            if area.code.lower() in center.lower().replace(" ", ""):
                center_coords = area.coordinates
                break
        
        if not center_coords:
            logger.warning(f"Could not find coordinates for center postcode: {center}")
            return postcodes
        
        filtered = []
        for pc in postcodes:
            for area in self.postcode_areas:
                if area.code.lower() in pc.lower().replace(" ", ""):
                    distance = self._calculate_distance(center_coords, area.coordinates)
                    if distance <= radius_km:
                        filtered.append(pc)
                    break
        
        return filtered
    
    def _calculate_distance(self, coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """Calculate distance between two coordinates using Haversine formula"""
        lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
        lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth's radius in kilometers
        r = 6371
        
        return c * r
    
    def _select_geographically_distributed(self, areas: List[PostcodeArea]) -> List[PostcodeArea]:
        """Select geographically distributed postcodes"""
        regions = {}
        for area in areas:
            if area.region not in regions:
                regions[area.region] = []
            regions[area.region].append(area)
        
        # Take up to 3 areas from each region
        distributed = []
        for region_areas in regions.values():
            # Prioritize high commercial activity areas
            region_areas.sort(key=lambda x: (x.commercial_activity == "high", x.population_density == "high"), reverse=True)
            distributed.extend(region_areas[:3])
        
        return distributed
    
    def _sort_by_effectiveness(self, postcodes: List[str]) -> List[str]:
        """Sort postcodes by effectiveness (success rate)"""
        def effectiveness_score(pc: str) -> float:
            # Base score from historical success rate
            base_score = self.success_rates.get(pc, 0.5)  # Default 50% success rate
            
            # Bonus for commercial areas
            for area in self.postcode_areas:
                if area.code.lower() in pc.lower().replace(" ", ""):
                    if area.commercial_activity == "high":
                        base_score += 0.2
                    elif area.commercial_activity == "medium":
                        base_score += 0.1
                    break
            
            return base_score
        
        return sorted(postcodes, key=effectiveness_score, reverse=True)
    
    def _generate_full_postcodes(self, area_codes: List[str], limit: int) -> List[str]:
        """Generate full postcodes from area codes"""
        postcodes = []
        
        # Common postcode endings for different areas
        common_endings = {
            'london': ['1AA', '2BB', '3CC', '4DD', '5EE', '6FF', '7GG', '8HH', '9JJ', '0KK'],
            'commercial': ['1AB', '2CD', '3EF', '4GH', '5JK', '6LM', '7NP', '8QR', '9ST', '0UV'],
            'residential': ['1WX', '2YZ', '3AA', '4BB', '5CC', '6DD', '7EE', '8FF', '9GG', '0HH'],
        }
        
        for area_code in area_codes:
            # Find the area type
            area_type = 'residential'  # default
            for area in self.postcode_areas:
                if area.code == area_code:
                    if 'London' in area.region:
                        area_type = 'london'
                    elif area.commercial_activity == 'high':
                        area_type = 'commercial'
                    break
            
            # Generate multiple postcodes per area
            endings = common_endings.get(area_type, common_endings['residential'])
            for ending in endings:
                if len(postcodes) >= limit:
                    break
                postcodes.append(f"{area_code} {ending}")
            
            if len(postcodes) >= limit:
                break
        
        return postcodes
    
    def _format_postcodes(self, postcodes: List[str]) -> List[str]:
        """Format postcodes consistently"""
        formatted = []
        for pc in postcodes:
            # Remove extra spaces and ensure proper format
            pc = re.sub(r'\s+', ' ', pc.strip().upper())
            
            # Ensure space between area and district codes
            if ' ' not in pc and len(pc) >= 5:
                pc = pc[:-3] + ' ' + pc[-3:]
            
            formatted.append(pc)
        
        return formatted
    
    def record_success_rate(self, postcode: str, listings_found: int, source: str):
        """Record success rate for a postcode"""
        # Simple success rate based on listings found
        # More than 10 listings = high success, 5-10 = medium, <5 = low
        if listings_found >= 10:
            success_rate = 0.9
        elif listings_found >= 5:
            success_rate = 0.7
        else:
            success_rate = 0.3
        
        self.success_rates[postcode] = success_rate
        self.used_postcodes.add(postcode)
        
        logger.info(f"Recorded success rate for {postcode}: {success_rate:.1%} ({listings_found} listings) from {source}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the postcode database"""
        return {
            "total_areas": len(self.postcode_areas),
            "regions": len(set(area.region for area in self.postcode_areas)),
            "high_commercial": len([a for a in self.postcode_areas if a.commercial_activity == "high"]),
            "used_postcodes": len(self.used_postcodes),
            "success_rates": dict(self.success_rates)
        }

def generate_uk_postcodes(limit: int = 100) -> List[str]:
    """Legacy function for backward compatibility"""
    manager = PostcodeManager()
    return manager.get_postcodes(strategy=PostcodeStrategy.MIXED_DENSITY, limit=limit)

# ---------------------------------------------------------------------------
# Enhanced eBay Scraper Core
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
                '--disable-notifications',
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

async def _scrape_page_core(page, url: str, proxy: str = None) -> List[Dict[str, Any]]:
    """Core eBay page scraping logic"""
    try:
        # Random delay to appear more human-like
        delay = random.uniform(*REQUEST_DELAY_RANGE)
        await asyncio.sleep(delay)
        
        await page.goto(url, timeout=PAGE_TIMEOUT_MS)
        await page.wait_for_timeout(3000)  # Wait for dynamic content
        
        # Check for eBay protection or errors
        page_title = await page.title()
        logger.info(f"Page title: {page_title} (Proxy: {proxy or 'None'})")
        
        if "security measure" in page_title.lower() or "blocked" in page_title.lower():
            logger.warning("eBay security protection detected - waiting longer...")
            await page.wait_for_timeout(10000)
        
        # Try to find listings
        try:
            await page.wait_for_selector(SELECTORS["listing"], timeout=30000)
            listings = await page.query_selector_all(SELECTORS["listing"])
        except PlaywrightTimeout:
            logger.warning(f"Timeout waiting for listings selector: {SELECTORS['listing']}")
            # Try alternative selectors
            alternatives = [
                ".srp-results .s-item",
                "[data-view='mi:1686|iid:1']",
                ".srp-item",
                ".x-refine__main__list .s-item",
            ]
            listings = []
            for alt in alternatives:
                found = await page.query_selector_all(alt)
                if found:
                    logger.info(f"Found {len(found)} listings with selector: {alt}")
                    listings = found
                    break
            
            if not listings:
                logger.warning("No listings found with any selector")
                return []
        
        logger.info(f"Found {len(listings)} potential listings")
        
        # Filter out sponsored and non-vehicle listings
        vehicle_listings = []
        for listing in listings:
            listing_text = await listing.inner_text()
            
            # Skip sponsored listings (optional)
            sponsored = await listing.query_selector(SELECTORS["sponsored"])
            
            # Check if this looks like a Ford Transit listing
            has_ford_transit = 'ford transit' in listing_text.lower()
            has_price = '£' in listing_text
            is_too_short = len(listing_text.strip()) < 20  # Too short to be a real listing
            
            if has_ford_transit and has_price and not is_too_short:
                vehicle_listings.append(listing)
        
        logger.info(f"Filtered to {len(vehicle_listings)} Ford Transit listings")
        
        rows = []
        for listing in vehicle_listings:
            try:
                # Extract title
                title = None
                for title_sel in SELECTORS["title"].split(", "):
                    title_elem = await listing.query_selector(title_sel)
                    if title_elem:
                        title_text = await title_elem.inner_text()
                        if title_text and len(title_text.strip()) > 5:
                            title = title_text.strip()
                            break
                
                # Extract price
                price = None
                for price_sel in SELECTORS["price"].split(", "):
                    price_elem = await listing.query_selector(price_sel)
                    if price_elem:
                        price_text = await price_elem.inner_text()
                        price_match = PRICE_RE.search(price_text or "")
                        if price_match:
                            price_str = price_match.group(1).replace(",", "")
                            try:
                                price = float(price_str)
                            except ValueError:
                                continue
                            break
                
                # If no price found via selectors, search in listing text
                if not price:
                    listing_text = await listing.inner_text()
                    price_match = PRICE_RE.search(listing_text)
                    if price_match:
                        try:
                            price = float(price_match.group(1).replace(",", ""))
                        except ValueError:
                            pass
                
                # Extract year and mileage from title/description
                year = mileage = None
                listing_text = await listing.inner_text()
                
                year_match = YEAR_RE.search(listing_text)
                if year_match:
                    year_candidate = int(year_match.group())
                    if 1990 <= year_candidate <= datetime.now().year:
                        year = year_candidate
                
                mileage_match = MILEAGE_RE.search(listing_text)
                if mileage_match:
                    try:
                        mileage = int(mileage_match.group(1).replace(",", ""))
                    except ValueError:
                        pass
                
                # Extract condition
                condition = None
                condition_elem = await listing.query_selector(SELECTORS["condition"])
                if condition_elem:
                    condition = await condition_elem.inner_text()
                
                # Extract location
                location = None
                location_elem = await listing.query_selector(SELECTORS["location"])
                if location_elem:
                    location = await location_elem.inner_text()
                
                # Extract shipping info
                shipping = None
                shipping_elem = await listing.query_selector(SELECTORS["shipping"])
                if shipping_elem:
                    shipping = await shipping_elem.inner_text()
                
                # Extract bids/watchers
                bids = watchers = None
                
                bids_elem = await listing.query_selector(SELECTORS["bids"])
                if bids_elem:
                    bids_text = await bids_elem.inner_text()
                    bids_match = BID_RE.search(bids_text)
                    if bids_match:
                        bids = int(bids_match.group(1))
                
                watchers_elem = await listing.query_selector(SELECTORS["watchers"])
                if watchers_elem:
                    watchers_text = await watchers_elem.inner_text()
                    watchers_match = WATCHERS_RE.search(watchers_text)
                    if watchers_match:
                        watchers = int(watchers_match.group(1))
                
                # Extract time left for auctions
                time_left = None
                time_elem = await listing.query_selector(SELECTORS["time_left"])
                if time_elem:
                    time_left = await time_elem.inner_text()
                
                # Extract image URL
                image_url = None
                img_elem = await listing.query_selector(SELECTORS["image"])
                if img_elem:
                    img_src = await img_elem.get_attribute('src')
                    if img_src and ('http' in img_src or img_src.startswith('//')):
                        if img_src.startswith('//'):
                            image_url = f"https:{img_src}"
                        else:
                            image_url = img_src
                
                # Extract listing URL
                link_elem = await listing.query_selector(SELECTORS["link"])
                link = await link_elem.get_attribute('href') if link_elem else None
                if link and not link.startswith('http'):
                    link = f"https://www.ebay.co.uk{link}"
                
                # Determine listing type (auction vs buy-it-now)
                listing_type = "auction"
                buy_now_elem = await listing.query_selector(SELECTORS["buy_now"])
                if buy_now_elem or "buy it now" in listing_text.lower():
                    listing_type = "buy_it_now"
                
                # Extract seller info
                seller = None
                seller_elem = await listing.query_selector(SELECTORS["seller"])
                if seller_elem:
                    seller = await seller_elem.inner_text()
                
                # Build comprehensive description
                description_parts = []
                if condition:
                    description_parts.append(f"Condition: {condition}")
                if location:
                    description_parts.append(f"Location: {location}")
                if shipping:
                    description_parts.append(f"Shipping: {shipping}")
                if seller:
                    description_parts.append(f"Seller: {seller}")
                if bids is not None:
                    description_parts.append(f"Bids: {bids}")
                if watchers is not None:
                    description_parts.append(f"Watchers: {watchers}")
                if time_left:
                    description_parts.append(f"Time left: {time_left}")
                
                description = "; ".join(description_parts) if description_parts else title or "No description available"
                
                # Detect VAT status from listing text
                from van_scraping_utils import detect_vat_status
                vat_included = detect_vat_status(listing_text, "ebay")
                
                rows.append({
                    "title": title,
                    "year": year,
                    "mileage": mileage,
                    "price": price,
                    "description": description,
                    "condition": condition,
                    "location": location,
                    "shipping": shipping,
                    "listing_type": listing_type,
                    "vat_included": vat_included,
                    "bids": bids,
                    "watchers": watchers,
                    "time_left": time_left,
                    "seller": seller,
                    "image_url": image_url,
                    "url": link,
                    "postcode": None,  # Will be added by worker
                    "age": datetime.now().year - year if year else None,
                    "scraped_at": datetime.now().isoformat(),
                })
                
            except Exception as e:
                logger.warning(f"Error processing listing: {str(e)}")
                continue
        
        logger.info(f"Successfully extracted {len(rows)} listings")
        return rows
        
    except Exception as e:
        logger.error(f"Error scraping page {url}: {str(e)}")
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
    """Worker function to scrape a single postcode"""
    async with async_playwright() as p:
        try:
            browser, context, page, proxy = await create_browser_context(p, proxy_rotator)
            
            all_listings = []
            max_price = 100000  # £100k max
            
            for page_num in range(1, pages_per_postcode + 1):
                url = EBAY_URL_TEMPLATE.format(
                    postcode=quote_plus(postcode),
                    page=page_num,
                    max_price=max_price,
                    extra=""
                )
                
                logger.info(f"Scraping {postcode} page {page_num}: {url}")
                
                listings = await _scrape_page_enhanced(page, url, proxy, semaphore)
                
                if not listings:
                    logger.warning(f"No listings found for {postcode} page {page_num}")
                    break
                
                # Add postcode to each listing
                for listing in listings:
                    listing["postcode"] = postcode
                
                all_listings.extend(listings)
                
                # Small delay between pages
                await asyncio.sleep(random.uniform(1, 3))
            
            await results_queue.put((postcode, all_listings))
            logger.info(f"Completed scraping {postcode}: {len(all_listings)} listings")
            
        except Exception as e:
            logger.error(f"Error in worker for postcode {postcode}: {str(e)}")
            await results_queue.put((postcode, []))
        finally:
            try:
                await context.close()
                await browser.close()
            except:
                pass

async def scrape_multiple_postcodes(postcodes: List[str], pages_per_postcode: int = 3, 
                                  proxy_list: List[str] = None, outfile: Path = None) -> pd.DataFrame:
    """Scrape multiple postcodes concurrently"""
    
    proxy_rotator = ProxyRotator(proxy_list) if proxy_list else None
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_PAGES)
    results_queue = asyncio.Queue()
    
    # Create worker tasks
    tasks = []
    for postcode in postcodes:
        task = asyncio.create_task(
            scrape_postcode_worker(postcode, pages_per_postcode, semaphore, proxy_rotator, results_queue)
        )
        tasks.append(task)
    
    # Wait for all tasks to complete
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect all results
    all_listings = []
    postcode_manager = PostcodeManager()
    
    while not results_queue.empty():
        postcode, listings = await results_queue.get()
        all_listings.extend(listings)
        
        # Record success rate
        postcode_manager.record_success_rate(postcode, len(listings), "ebay")
    
    # Convert to DataFrame
    if all_listings:
        df = pd.DataFrame(all_listings)
        
        # Clean and process data
        if 'price' in df.columns:
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
        if 'year' in df.columns:
            df['year'] = pd.to_numeric(df['year'], errors='coerce')
        if 'mileage' in df.columns:
            df['mileage'] = pd.to_numeric(df['mileage'], errors='coerce')
        
        # Save to file if specified
        if outfile:
            df.to_csv(outfile, index=False)
            logger.info(f"Saved {len(df)} listings to {outfile}")
        
        return df
    else:
        logger.warning("No listings found")
        return pd.DataFrame()

def analyse(csv_path: Path, show_plots: bool = True) -> None:
    """Quick analysis of scraped eBay data"""
    if not plt or not np:
        logger.error("matplotlib and numpy required for analysis")
        return
    
    df = pd.read_csv(csv_path)
    
    if df.empty:
        logger.error("No data found in CSV file")
        return
    
    # Clean data
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df['year'] = pd.to_numeric(df['year'], errors='coerce')
    df['mileage'] = pd.to_numeric(df['mileage'], errors='coerce')
    
    # Filter reasonable values
    df = df[
        (df['price'] >= 1000) & (df['price'] <= 100000) &
        (df['year'] >= 2000) & (df['year'] <= datetime.now().year) &
        (df['mileage'] >= 0) & (df['mileage'] <= 500000)
    ]
    
    print(f"\n📊 eBay Ford Transit Analysis ({len(df)} listings)")
    print("=" * 50)
    
    # Price statistics
    print(f"💰 Price Statistics:")
    print(f"   Median: £{df['price'].median():,.0f}")
    print(f"   Mean: £{df['price'].mean():,.0f}")
    print(f"   Range: £{df['price'].min():,.0f} - £{df['price'].max():,.0f}")
    
    # Year statistics
    print(f"\n🚗 Year Statistics:")
    print(f"   Median: {df['year'].median():.0f}")
    print(f"   Range: {df['year'].min():.0f} - {df['year'].max():.0f}")
    
    # Mileage statistics
    print(f"\n🛣️  Mileage Statistics:")
    print(f"   Median: {df['mileage'].median():,.0f} miles")
    print(f"   Mean: {df['mileage'].mean():,.0f} miles")
    print(f"   Range: {df['mileage'].min():,.0f} - {df['mileage'].max():,.0f} miles")
    
    # Listing type breakdown
    if 'listing_type' in df.columns:
        print(f"\n📈 Listing Types:")
        type_counts = df['listing_type'].value_counts()
        for listing_type, count in type_counts.items():
            print(f"   {listing_type}: {count} ({count/len(df)*100:.1f}%)")
    
    # Top locations
    if 'location' in df.columns:
        print(f"\n📍 Top Locations:")
        location_counts = df['location'].value_counts().head(10)
        for location, count in location_counts.items():
            if pd.notna(location):
                print(f"   {location}: {count}")
    
    if show_plots:
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('eBay Ford Transit Analysis', fontsize=16)
        
        # Price distribution
        axes[0,0].hist(df['price'], bins=30, alpha=0.7, color='green')
        axes[0,0].set_title('Price Distribution')
        axes[0,0].set_xlabel('Price (£)')
        axes[0,0].set_ylabel('Count')
        
        # Price vs Year
        axes[0,1].scatter(df['year'], df['price'], alpha=0.6, color='blue')
        axes[0,1].set_title('Price vs Year')
        axes[0,1].set_xlabel('Year')
        axes[0,1].set_ylabel('Price (£)')
        
        # Price vs Mileage
        axes[1,0].scatter(df['mileage'], df['price'], alpha=0.6, color='red')
        axes[1,0].set_title('Price vs Mileage')
        axes[1,0].set_xlabel('Mileage (miles)')
        axes[1,0].set_ylabel('Price (£)')
        
        # Year distribution
        axes[1,1].hist(df['year'], bins=20, alpha=0.7, color='orange')
        axes[1,1].set_title('Year Distribution')
        axes[1,1].set_xlabel('Year')
        axes[1,1].set_ylabel('Count')
        
        plt.tight_layout()
        plt.show()

async def scrape_ebay_single_postcode(postcode: str, pages: int, outfile: Path, max_price: int = 100000) -> pd.DataFrame:
    """Scrape a single postcode from eBay"""
    async with async_playwright() as p:
        browser, context, page, _ = await create_browser_context(p)
        
        all_listings = []
        
        for page_num in range(1, pages + 1):
            url = EBAY_URL_TEMPLATE.format(
                postcode=quote_plus(postcode),
                page=page_num,
                max_price=max_price,
                extra=""
            )
            
            logger.info(f"Scraping page {page_num}: {url}")
            
            listings = await _scrape_page_core(page, url)
            
            if not listings:
                logger.warning(f"No listings found on page {page_num}")
                break
            
            # Add postcode to each listing
            for listing in listings:
                listing["postcode"] = postcode
            
            all_listings.extend(listings)
            
            await asyncio.sleep(random.uniform(2, 4))
        
        await context.close()
        await browser.close()
        
        if all_listings:
            df = pd.DataFrame(all_listings)
            df.to_csv(outfile, index=False)
            logger.info(f"Saved {len(df)} listings to {outfile}")
            return df
        else:
            logger.warning("No listings found")
            return pd.DataFrame()

def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="eBay UK Ford Transit Scraper")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Scrape command (single postcode)
    scrape_parser = subparsers.add_parser("scrape", help="Scrape single postcode")
    scrape_parser.add_argument("--postcode", required=True, help="UK postcode to search")
    scrape_parser.add_argument("--pages", type=int, default=5, help="Number of pages to scrape")
    scrape_parser.add_argument("--outfile", type=Path, default=Path("data/ebay_transit_listings.csv"), help="Output CSV file")
    
    # Scrape-multi command
    multi_parser = subparsers.add_parser("scrape-multi", help="Scrape multiple postcodes")
    multi_parser.add_argument("--strategy", type=PostcodeStrategy, choices=list(PostcodeStrategy), 
                             default=PostcodeStrategy.MIXED_DENSITY, help="Postcode selection strategy")
    multi_parser.add_argument("--postcode-limit", type=int, default=30, help="Number of postcodes to scrape")
    multi_parser.add_argument("--pages-per-postcode", type=int, default=3, help="Pages per postcode")
    multi_parser.add_argument("--postcodes", nargs="*", help="Custom postcodes to use")
    multi_parser.add_argument("--center-postcode", help="Center postcode for geographic filtering")
    multi_parser.add_argument("--radius-km", type=float, help="Radius in km for geographic filtering")
    multi_parser.add_argument("--outfile", type=Path, default=Path("data/ebay_transit_multi.csv"), help="Output CSV file")
    
    # Scrape-UK command
    uk_parser = subparsers.add_parser("scrape-uk", help="Scrape UK-wide with optimized settings")
    uk_parser.add_argument("--outfile", type=Path, default=Path("data/ebay_ford_transit_uk_complete.csv"), help="Output CSV file")
    uk_parser.add_argument("--include-mixed", action="store_true", help="Include mixed density areas")
    uk_parser.add_argument("--postcode-limit", type=int, default=100, help="Number of postcodes")
    uk_parser.add_argument("--pages-per-postcode", type=int, default=5, help="Pages per postcode")
    uk_parser.add_argument("--proxy-file", type=Path, help="File containing proxy list")
    uk_parser.add_argument("--max-browsers", type=int, default=5, help="Max concurrent browsers")
    uk_parser.add_argument("--max-pages", type=int, default=50, help="Max concurrent pages")
    
    # Postcodes command
    postcodes_parser = subparsers.add_parser("postcodes", help="Postcode management")
    postcodes_subparsers = postcodes_parser.add_subparsers(dest="postcodes_action")
    
    list_parser = postcodes_subparsers.add_parser("list", help="List postcodes")
    list_parser.add_argument("--strategy", choices=[s.value for s in PostcodeStrategy], 
                           default="mixed_density", help="Strategy to list")
    list_parser.add_argument("--limit", type=int, default=20, help="Number to show")
    
    stats_parser = postcodes_subparsers.add_parser("stats", help="Show postcode statistics")
    
    test_parser = postcodes_subparsers.add_parser("test", help="Test postcode strategies")
    test_parser.add_argument("--limit", type=int, default=10, help="Number per strategy")
    
    # Analyse command
    analyse_parser = subparsers.add_parser("analyse", help="Analyze scraped data")
    analyse_parser.add_argument("csv_file", type=Path, help="CSV file to analyze")
    analyse_parser.add_argument("--no-plots", action="store_true", help="Don't show plots")
    
    return parser.parse_args()

def load_proxies_from_file(proxy_file: Path) -> List[str]:
    """Load proxies from file"""
    if not proxy_file.exists():
        logger.error(f"Proxy file not found: {proxy_file}")
        return []
    
    proxies = []
    with open(proxy_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if not line.startswith('http'):
                    line = f"http://{line}"
                proxies.append(line)
    
    logger.info(f"Loaded {len(proxies)} proxies from {proxy_file}")
    return proxies

def handle_postcode_command(args):
    """Handle postcode management commands"""
    manager = PostcodeManager()
    
    if args.postcodes_action == "list":
        strategy = PostcodeStrategy(args.strategy)
        postcodes = manager.get_postcodes(strategy=strategy, limit=args.limit)
        
        print(f"\n📍 Postcodes for strategy: {strategy.value}")
        print(f"{'Postcode':<10} {'Area':<15} {'City':<20} {'Region':<15} {'Commercial':<12}")
        print("-" * 75)
        
        for pc in postcodes:
            # Find matching area
            for area in manager.postcode_areas:
                if area.code.lower() in pc.lower().replace(" ", ""):
                    print(f"{pc:<10} {area.code:<15} {area.city:<20} {area.region:<15} {area.commercial_activity:<12}")
                    break
    
    elif args.postcodes_action == "stats":
        stats = manager.get_stats()
        print("\n📊 Postcode Database Statistics:")
        print(f"   Total areas: {stats['total_areas']}")
        print(f"   Regions covered: {stats['regions']}")
        print(f"   High commercial activity areas: {stats['high_commercial']}")
        print(f"   Used postcodes: {stats['used_postcodes']}")
        
        if stats['success_rates']:
            print(f"\n📈 Success Rates:")
            for pc, rate in list(stats['success_rates'].items())[:10]:
                print(f"   {pc}: {rate:.1%}")
    
    elif args.postcodes_action == "test":
        print("\n🧪 Testing Postcode Strategies:")
        print("=" * 50)
        
        for strategy in PostcodeStrategy:
            postcodes = manager.get_postcodes(strategy=strategy, limit=args.limit)
            print(f"\n{strategy.value.upper()} ({len(postcodes)} postcodes):")
            for pc in postcodes[:5]:  # Show first 5
                print(f"   {pc}")
            if len(postcodes) > 5:
                print(f"   ... and {len(postcodes) - 5} more")

def main():
    """Main entry point"""
    args = parse_args()
    
    if args.command == "scrape":
        asyncio.run(scrape_ebay_single_postcode(args.postcode, args.pages, args.outfile))
    
    elif args.command == "scrape-multi":
        # Load postcodes
        if args.postcodes:
            postcodes = args.postcodes
        else:
            manager = PostcodeManager()
            strategy = PostcodeStrategy(args.strategy)
            postcodes = manager.get_postcodes(
                strategy=strategy,
                limit=args.postcode_limit,
                exclude_used=args.exclude_used,
                center_postcode=args.center_postcode,
                geographic_radius_km=args.radius_km
            )
        
        # Load proxies if provided
        proxy_list = None
        if args.proxy_file:
            proxy_list = load_proxies_from_file(args.proxy_file)
        
        logger.info(f"Starting multi-postcode scraping with {len(postcodes)} postcodes")
        asyncio.run(scrape_multiple_postcodes(postcodes, args.pages_per_postcode, proxy_list, args.outfile))
    
    elif args.command == "scrape-uk":
        # UK-wide scraping with optimized settings
        manager = PostcodeManager()
        strategy = PostcodeStrategy.COMMERCIAL_HUBS if not args.include_mixed else PostcodeStrategy.MIXED_DENSITY
        postcodes = manager.get_postcodes(strategy=strategy, limit=args.postcode_limit)
        
        proxy_list = None
        if args.proxy_file:
            proxy_list = load_proxies_from_file(args.proxy_file)
        
        pages_per_postcode = min(args.pages_per_postcode, args.max_pages)
        
        logger.info(f"Starting UK-wide eBay scraping: {len(postcodes)} postcodes, {pages_per_postcode} pages each")
        asyncio.run(scrape_multiple_postcodes(postcodes, pages_per_postcode, proxy_list, args.outfile))
    
    elif args.command == "postcodes":
        handle_postcode_command(args)
    
    elif args.command == "analyse":
        analyse(args.csv_file, show_plots=not args.no_plots)
    
    else:
        logger.error("No command specified. Use --help for available commands.")

if __name__ == "__main__":
    main() 
