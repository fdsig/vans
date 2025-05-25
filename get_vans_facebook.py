#!/usr/bin/env python3
"""
Scrape and Analyse Ford Transit L2 H2 Listings from Facebook Marketplace UK
===========================================================================

*Enhanced Facebook Marketplace scraping system with intelligent postcode management, 
concurrent scraping with proxy support, and advanced geographic intelligence.*

**🎯 KEY FEATURE: Scrapes CURRENT listings to get ASKING PRICES and market availability**

This script supports these sub‑commands:

* `scrape`    – harvest current listings → CSV (single postcode, legacy)
* `scrape-multi` – concurrent scraping across multiple postcodes with smart strategies
* `scrape-uk` – optimized UK-wide scraping focusing on commercial/industrial areas with descriptions and images
* `postcodes` – analyze and manage postcode selection strategies  
* `analyse`  – quick medians & scatter plots

----
Why Facebook Marketplace?
-------------------------
Facebook Marketplace is a major classified ad platform in the UK, providing extensive coverage of both private and commercial Ford Transit listings.

- ✅ Current asking prices (market availability)
- ✅ Large user base across UK regions
- ✅ Both private and dealer listings
- ✅ Detailed descriptions with image galleries
- ✅ Location-based search capabilities

----
Enhanced Postcode Management
----------------------------
The PostcodeManager provides intelligent postcode selection with multiple strategies:

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

**1) Basic Facebook Marketplace scraping (single postcode)**
```bash
python get_vans_facebook.py scrape --postcode G23NX --pages 15 --outfile transit_facebook.csv
```

**2) Smart multi-postcode Facebook Marketplace scraping**
```bash
# Use commercial hubs strategy across 30 postcodes
python get_vans_facebook.py scrape-multi --strategy commercial_hubs --postcode-limit 30 \
    --pages-per-postcode 5 --outfile transit_commercial_facebook.csv

# Geographic focus: 50km radius around Manchester
python get_vans_facebook.py scrape-multi --strategy geographic_spread --center-postcode "M1 1AA" \
    --radius-km 50 --postcode-limit 20 --outfile transit_manchester_facebook.csv

# Use custom postcodes with proxy rotation
python get_vans_facebook.py scrape-multi --postcodes "SW1A 1AA" "M1 1AA" "B1 1AA" \
    --proxy-file proxies.txt --pages-per-postcode 10
```

**3) UK-wide Facebook Marketplace scraping (optimized command)**
```bash
# Scrape the whole UK focusing on commercial/industrial areas
python get_vans_facebook.py scrape-uk --outfile ford_transit_uk_facebook.csv

# Include mixed density areas for broader coverage
python get_vans_facebook.py scrape-uk --include-mixed --pages-per-postcode 8 --postcode-limit 150

# Use proxies for large-scale scraping
python get_vans_facebook.py scrape-uk --proxy-file proxies.txt --max-browsers 10 --max-pages 40
```

**4) Analysis of asking prices**
```bash
# Quick scatter plots and medians from current listings
python get_vans_facebook.py analyse transit_commercial_facebook.csv
```

----
Advanced Features
-----------------

**Facebook Marketplace Intelligence:**
- Extracts current asking prices and availability
- Handles both private and dealer listings
- Captures detailed descriptions and specifications
- Monitors listing age and posting dates
- Extracts seller information and marketplace metrics

**Concurrent Scraping:**
- Configurable browser and page concurrency limits
- Intelligent proxy rotation with failure handling
- Human-like delays and behavior simulation
- Anti-detection measures for Facebook's security

**Geographic Intelligence:**
- Real UK postcode coordinates database
- Distance-based filtering using Haversine formula
- Regional distribution analysis
- Interactive map visualization

----
Facebook Marketplace Specific Notes
-----------------------------------
Facebook Marketplace has robust anti-scraping measures including:
- Login requirements for some regions
- CAPTCHA challenges
- Rate limiting and IP blocking
- Dynamic content loading

This scraper implements:
- Human-like browsing patterns
- Intelligent wait strategies
- Proxy rotation support
- Session management
- Error recovery mechanisms
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
        logging.FileHandler('facebook_scraping.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration for Facebook Marketplace UK
# ---------------------------------------------------------------------------

REQUEST_DELAY_RANGE = (3.0, 6.0)  # Longer delays for Facebook's anti-scraping
MAX_CONCURRENT_BROWSERS = 3
MAX_CONCURRENT_PAGES = 8

# Facebook Marketplace UK search URL template
FACEBOOK_URL_TEMPLATE = (
    "https://www.facebook.com/marketplace/{location}/search/?"
    "query=ford%20transit%20l2%20h2&"
    "exact=false&"
    "sortBy=creation_time_descend&"
    "filters={filters}"
)

# Alternative search patterns for better results
FACEBOOK_SEARCH_QUERIES = [
    "ford+transit+l2+h2",
    "ford+transit+van+l2h2", 
    "ford+transit+medium+roof",
    "ford+transit+350+l2h2",
    "ford+transit+lwb+medium",
]

HEADLESS = True
PAGE_TIMEOUT_MS = 120_000  # Even longer timeout for Facebook
THROTTLE_MS = 3_000

# Facebook Marketplace-specific CSS selectors
SELECTORS = {
    "listing": "[data-testid='marketplace-search-result-item'], .x9f619.x78zum5.x1q0g3np.x2lwn1j",
    "title": "[data-testid='marketplace-product-item-title'], .x1lliihq.x6ikm8r.x10wlt62.x1n2onr6",
    "price": "[data-testid='marketplace-product-item-price'], .x193iq5w.xeuugli.x13faqbe.x1vvkbs.x1xmvt09.x1lliihq.x1s928wv.xhkezso.x1gmr53x.x1cpjm7i.x1fgarty.x1943h6x.x4zkp8e.x3x7a5m.x1pg5gke.x1sibtaa.xo1l8bm.xi81zsa",
    "description": "[data-testid='marketplace-product-item-description'], .x193iq5w.xeuugli.x13faqbe.x1vvkbs.x1xmvt09.x1lliihq.x1s928wv.xhkezso.x1gmr53x.x1cpjm7i.x1fgarty.x1943h6x.x4zkp8e.x676frb.x1pg5gke.x1sibtaa.xo1l8bm.xi81zsa",
    "location": "[data-testid='marketplace-product-item-location'], .x1i10hfl.xjbqb8w.x6umtig.x1b1mbwd.xaqea5y.xav7gou.x9f619.x1ypdohk.xe8uvvx.xdj266r.x11i5rnm.xat24cr.x1mh8g0r.xexx8yu.x4uap5.x18d9i69.xkhd6sd.x16tdsg8.x1hl2dhg.xggy1nq.x1o1ewxj.x3x9cwd.x1e5q0jg.x13rtm0m.x87ps6o.x1lku1pv.x1a2a7pz.x9f619.x3nfvp2.xdt5ytf.xl56j7k.x1n2onr6.xh8yej3",
    "link": "a[href*='/marketplace/item/']",
    "image": "[data-testid='marketplace-search-result-item'] img, .x1ey2m1c.x9f619.xds687c.x10l6tqk.x17qophe.x13vifvy.x1ey2m1c.x6ikm8r.x10wlt62",
    "posted_date": ".x1i10hfl.xjbqb8w.x6umtig.x1b1mbwd.xaqea5y.xav7gou.x9f619.x1ypdohk.xt0psk2.xe8uvvx.xdj266r.x11i5rnm.xat24cr.x1mh8g0r.xexx8yu.x4uap5.x18d9i69.xkhd6sd.x16tdsg8.x1hl2dhg.xggy1nq.x1a2a7pz.x1heor9g.x1sur9pj.xkrqix3",
    "seller_name": "[data-testid='marketplace-product-item-seller'], .x1i10hfl.xjbqb8w.x6umtig.x1b1mbwd.xaqea5y.xav7gou.x9f619.x1ypdohk.xt0psk2.xe8uvvx.xdj266r.x11i5rnm.xat24cr.x1mh8g0r.xexx8yu.x4uap5.x18d9i69.xkhd6sd.x16tdsg8.x1hl2dhg.xggy1nq.x1a2a7pz.x1heor9g.x1sur9pj.xkrqix3",
    "seller_type": "[data-testid='marketplace-seller-badge']",
    "condition": ".x1lliihq.x6ikm8r.x10wlt62.x1n2onr6.x1j85h84",
    "distance": ".x193iq5w.xeuugli.x13faqbe.x1vvkbs.x1xmvt09.x1lliihq.x1s928wv.xhkezso.x1gmr53x.x1cpjm7i.x1fgarty.x1943h6x.x4zkp8e.x676frb.x1pg5gke.x1sibtaa.xo1l8bm.xi81zsa.x1yc453h",
}

# Facebook Marketplace-specific regex patterns  
PRICE_RE = re.compile(r"£([\d,]+(?:\.\d{2})?)", re.I)
MILEAGE_RE = re.compile(r"([\d,]+)\s*(?:miles?|mileage|mil)", re.I)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
POSTCODE_RE = re.compile(r"\b[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}\b", re.I)
DISTANCE_RE = re.compile(r"([\d.]+)\s*(?:miles?|km)\s*away", re.I)
ENGINE_SIZE_RE = re.compile(r"(\d\.\d)L?|(\d{4})cc", re.I)
DOORS_RE = re.compile(r"(\d)\s*doors?", re.I)


class ProxyRotator:
    """Rotates through a list of proxies with failure tracking"""
    
    def __init__(self, proxy_list: List[str] = None):
        self.proxies = proxy_list or []
        self.current_index = 0
        self.failed_proxies = set()
        logger.info(f"Initialized ProxyRotator with {len(self.proxies)} proxies")
    
    def get_next_proxy(self) -> str | None:
        if not self.proxies:
            return None
            
        available_proxies = [p for p in self.proxies if p not in self.failed_proxies]
        if not available_proxies:
            # Reset failed proxies if all have failed
            logger.warning("All proxies failed, resetting failure tracking")
            self.failed_proxies.clear()
            available_proxies = self.proxies
            
        if not available_proxies:
            return None
            
        proxy = available_proxies[self.current_index % len(available_proxies)]
        self.current_index += 1
        logger.debug(f"Selected proxy: {proxy}")
        return proxy
    
    def mark_proxy_failed(self, proxy: str):
        self.failed_proxies.add(proxy)
        logger.warning(f"Marked proxy as failed: {proxy}")
    
    def add_proxies(self, proxy_list: List[str]):
        self.proxies.extend(proxy_list)
        logger.info(f"Added {len(proxy_list)} proxies. Total: {len(self.proxies)}")


class PostcodeStrategy(Enum):
    """Different strategies for postcode selection"""
    MAJOR_CITIES = "major_cities"
    GEOGRAPHIC_SPREAD = "geographic_spread"
    COMMERCIAL_HUBS = "commercial_hubs"
    MIXED_DENSITY = "mixed_density"
    CUSTOM = "custom"


@dataclass
class PostcodeArea:
    """Represents a UK postcode area with metadata"""
    code: str
    city: str
    region: str
    population_density: str
    commercial_activity: str
    coordinates: Tuple[float, float]


class PostcodeManager:
    """Manages intelligent postcode selection with geographic intelligence"""
    
    def __init__(self):
        # Reuse the same comprehensive postcode database
        self.postcode_areas = [
            # Major Cities - High population density
            PostcodeArea("SW1A", "London", "Greater London", "high", "high", (51.5014, -0.1419)),
            PostcodeArea("EC1A", "London", "Greater London", "high", "high", (51.5177, -0.0968)),
            PostcodeArea("W1A", "London", "Greater London", "high", "high", (51.5154, -0.1447)),
            PostcodeArea("E1", "London", "Greater London", "high", "high", (51.5118, -0.0648)),
            PostcodeArea("M1", "Manchester", "Greater Manchester", "high", "high", (53.4808, -2.2426)),
            PostcodeArea("M2", "Manchester", "Greater Manchester", "high", "medium", (53.4875, -2.2401)),
            PostcodeArea("B1", "Birmingham", "West Midlands", "high", "high", (52.4862, -1.8904)),
            PostcodeArea("B2", "Birmingham", "West Midlands", "high", "high", (52.4796, -1.9026)),
            PostcodeArea("LS1", "Leeds", "West Yorkshire", "high", "high", (53.8008, -1.5491)),
            PostcodeArea("LS2", "Leeds", "West Yorkshire", "high", "medium", (53.8017, -1.5572)),
            PostcodeArea("G1", "Glasgow", "Scotland", "high", "high", (55.8642, -4.2518)),
            PostcodeArea("G2", "Glasgow", "Scotland", "high", "medium", (55.8575, -4.2565)),
            PostcodeArea("NE1", "Newcastle", "Tyne and Wear", "high", "medium", (54.9783, -1.6178)),
            PostcodeArea("L1", "Liverpool", "Merseyside", "high", "medium", (53.4084, -2.9916)),
            PostcodeArea("S1", "Sheffield", "South Yorkshire", "high", "medium", (53.3811, -1.4701)),
            PostcodeArea("NG1", "Nottingham", "Nottinghamshire", "high", "medium", (52.9548, -1.1581)),
            PostcodeArea("LE1", "Leicester", "Leicestershire", "high", "medium", (52.6369, -1.1398)),
            PostcodeArea("CV1", "Coventry", "West Midlands", "high", "medium", (52.4068, -1.5197)),
            PostcodeArea("DE1", "Derby", "Derbyshire", "medium", "high", (52.9225, -1.4746)),
            PostcodeArea("PE1", "Peterborough", "Cambridgeshire", "medium", "high", (52.5695, -0.2405)),
            
            # Commercial Hubs - High commercial vehicle activity
            PostcodeArea("HA9", "Wembley", "Greater London", "high", "high", (51.5630, -0.2833)),
            PostcodeArea("UB7", "West Drayton", "Greater London", "medium", "high", (51.4926, -0.4669)),
            PostcodeArea("TW6", "Heathrow", "Greater London", "medium", "high", (51.4700, -0.4543)),
            PostcodeArea("RH6", "Gatwick", "West Sussex", "low", "high", (51.1481, -0.1903)),
            PostcodeArea("M17", "Trafford Park", "Greater Manchester", "medium", "high", (53.4692, -2.3158)),
            PostcodeArea("WA8", "Widnes", "Cheshire", "medium", "high", (53.3676, -2.7248)),
            PostcodeArea("WA1", "Warrington", "Cheshire", "medium", "high", (53.3900, -2.5970)),
            PostcodeArea("ST15", "Stone", "Staffordshire", "low", "high", (52.9045, -2.1561)),
            PostcodeArea("B69", "Oldbury", "West Midlands", "medium", "high", (52.5089, -2.0142)),
            PostcodeArea("DY4", "Tipton", "West Midlands", "medium", "high", (52.5251, -2.0742)),
            PostcodeArea("WV1", "Wolverhampton", "West Midlands", "medium", "high", (52.5839, -2.1290)),
            PostcodeArea("TF3", "Telford", "Shropshire", "medium", "high", (52.6761, -2.4464)),
            PostcodeArea("SY1", "Shrewsbury", "Shropshire", "low", "medium", (52.7069, -2.7527)),
            PostcodeArea("CW1", "Crewe", "Cheshire", "medium", "high", (53.0958, -2.4414)),
            PostcodeArea("PR7", "Chorley", "Lancashire", "medium", "high", (53.6526, -2.6309)),
            PostcodeArea("BB1", "Blackburn", "Lancashire", "medium", "high", (53.7480, -2.4829)),
            PostcodeArea("BL1", "Bolton", "Greater Manchester", "medium", "high", (53.5768, -2.4282)),
            PostcodeArea("OL1", "Oldham", "Greater Manchester", "medium", "high", (53.5409, -2.1114)),
            PostcodeArea("HD1", "Huddersfield", "West Yorkshire", "medium", "high", (53.6458, -1.7850)),
            PostcodeArea("WF1", "Wakefield", "West Yorkshire", "medium", "high", (53.6833, -1.4977)),
            
            # Geographic Spread - Even distribution
            PostcodeArea("PL1", "Plymouth", "Devon", "medium", "low", (50.3755, -4.1427)),
            PostcodeArea("TR1", "Truro", "Cornwall", "low", "low", (50.2632, -5.0510)),
            PostcodeArea("EX1", "Exeter", "Devon", "medium", "medium", (50.7184, -3.5339)),
            PostcodeArea("BA1", "Bath", "Somerset", "medium", "low", (51.3811, -2.3590)),
            PostcodeArea("BS1", "Bristol", "Somerset", "high", "medium", (51.4545, -2.5879)),
            PostcodeArea("CF10", "Cardiff", "Wales", "high", "medium", (51.4816, -3.1791)),
            PostcodeArea("SA1", "Swansea", "Wales", "medium", "medium", (51.6214, -3.9436)),
            PostcodeArea("LL57", "Bangor", "Wales", "low", "low", (53.2280, -4.1281)),
            PostcodeArea("AB10", "Aberdeen", "Scotland", "medium", "medium", (57.1497, -2.0943)),
            PostcodeArea("EH1", "Edinburgh", "Scotland", "high", "medium", (55.9533, -3.1883)),
            PostcodeArea("IV1", "Inverness", "Scotland", "low", "low", (57.4778, -4.2247)),
            PostcodeArea("PA1", "Paisley", "Scotland", "medium", "medium", (55.8456, -4.4243)),
            PostcodeArea("BT1", "Belfast", "Northern Ireland", "high", "medium", (54.5973, -5.9301)),
            PostcodeArea("BT20", "Bangor", "Northern Ireland", "medium", "low", (54.6669, -5.6681)),
            PostcodeArea("YO1", "York", "North Yorkshire", "medium", "medium", (53.9600, -1.0873)),
            PostcodeArea("HU1", "Hull", "East Yorkshire", "medium", "medium", (53.7457, -0.3367)),
            PostcodeArea("LN1", "Lincoln", "Lincolnshire", "medium", "medium", (53.2307, -0.5406)),
            PostcodeArea("NG1", "Nottingham", "Nottinghamshire", "high", "medium", (52.9548, -1.1581)),
            PostcodeArea("NN1", "Northampton", "Northamptonshire", "medium", "high", (52.2405, -0.9027)),
            PostcodeArea("MK1", "Milton Keynes", "Buckinghamshire", "medium", "high", (52.0406, -0.7594)),
        ]
        
        # Initialize success tracking database
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for tracking postcode effectiveness"""
        try:
            self.db_path = Path("postcode_intelligence.db")
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS postcode_stats (
                    postcode TEXT PRIMARY KEY,
                    total_searches INTEGER DEFAULT 0,
                    total_results INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()
            logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
    
    def get_postcodes(self, 
                     strategy: PostcodeStrategy = PostcodeStrategy.MIXED_DENSITY,
                     limit: int = 50,
                     custom_postcodes: List[str] = None,
                     exclude_used: bool = True,
                     geographic_radius_km: Optional[float] = None,
                     center_postcode: Optional[str] = None) -> List[str]:
        """Get postcodes based on strategy and filters"""
        
        if strategy == PostcodeStrategy.CUSTOM and custom_postcodes:
            return self._format_postcodes(custom_postcodes[:limit])
        
        # Filter by strategy
        filtered_areas = self._filter_by_strategy(strategy)
        
        # Apply geographic filtering if specified
        if center_postcode and geographic_radius_km:
            area_codes = [area.code for area in filtered_areas]
            area_codes = self._filter_by_geography(area_codes, center_postcode, geographic_radius_km)
            filtered_areas = [area for area in filtered_areas if area.code in area_codes]
        
        # Select geographically distributed postcodes
        if len(filtered_areas) > limit:
            filtered_areas = self._select_geographically_distributed(filtered_areas)
        
        # Generate full postcodes from areas
        area_codes = [area.code for area in filtered_areas]
        postcodes = self._generate_full_postcodes(area_codes, limit)
        
        # Sort by effectiveness (success rate)
        postcodes = self._sort_by_effectiveness(postcodes)
        
        return postcodes[:limit]
    
    def _filter_by_strategy(self, strategy: PostcodeStrategy) -> List[PostcodeArea]:
        """Filter postcode areas by strategy"""
        if strategy == PostcodeStrategy.MAJOR_CITIES:
            return [area for area in self.postcode_areas if area.population_density == "high"]
        elif strategy == PostcodeStrategy.COMMERCIAL_HUBS:
            return [area for area in self.postcode_areas if area.commercial_activity == "high"]
        elif strategy == PostcodeStrategy.GEOGRAPHIC_SPREAD:
            # Return a diverse mix from different regions
            return self.postcode_areas
        elif strategy == PostcodeStrategy.MIXED_DENSITY:
            # Balance of all density types
            return self.postcode_areas
        else:
            return self.postcode_areas
    
    def _filter_by_geography(self, postcodes: List[str], center: str, radius_km: float) -> List[str]:
        """Filter postcodes by geographic distance from center"""
        try:
            # Find center coordinates
            center_coords = None
            for area in self.postcode_areas:
                if center.replace(" ", "").upper().startswith(area.code.replace(" ", "").upper()):
                    center_coords = area.coordinates
                    break
            
            if not center_coords:
                logger.warning(f"Could not find coordinates for center postcode: {center}")
                return postcodes
            
            filtered = []
            for postcode in postcodes:
                # Find coordinates for this postcode
                postcode_coords = None
                for area in self.postcode_areas:
                    if postcode.replace(" ", "").upper().startswith(area.code.replace(" ", "").upper()):
                        postcode_coords = area.coordinates
                        break
                
                if postcode_coords:
                    distance = self._calculate_distance(center_coords, postcode_coords)
                    if distance <= radius_km:
                        filtered.append(postcode)
                else:
                    # Include postcodes without coordinates to be safe
                    filtered.append(postcode)
            
            logger.info(f"Geographic filtering: {len(filtered)}/{len(postcodes)} postcodes within {radius_km}km of {center}")
            return filtered
            
        except Exception as e:
            logger.error(f"Geographic filtering failed: {e}")
            return postcodes
    
    def _calculate_distance(self, coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """Calculate distance between two coordinates using Haversine formula"""
        lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
        lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = (math.sin(dlat/2)**2 + 
             math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2)
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth's radius in kilometers
        r = 6371
        
        return c * r
    
    def _select_geographically_distributed(self, areas: List[PostcodeArea]) -> List[PostcodeArea]:
        """Select geographically distributed postcodes to avoid clustering"""
        if len(areas) <= 20:
            return areas
            
        selected = [areas[0]]  # Start with first area
        
        for area in areas[1:]:
            # Check if this area is far enough from all selected areas
            min_distance = min(
                self._calculate_distance(area.coordinates, selected_area.coordinates)
                for selected_area in selected
            )
            
            # Only add if it's at least 50km from nearest selected area
            if min_distance >= 50:
                selected.append(area)
                
            if len(selected) >= 50:  # Reasonable limit
                break
        
        return selected
    
    def _sort_by_effectiveness(self, postcodes: List[str]) -> List[str]:
        """Sort postcodes by historical effectiveness (success rate)"""
        def effectiveness_score(pc: str) -> float:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.execute(
                    "SELECT total_searches, total_results FROM postcode_stats WHERE postcode = ?",
                    (pc,)
                )
                result = cursor.fetchone()
                conn.close()
                
                if result and result[0] > 0:
                    # Success rate with small smoothing factor
                    success_rate = (result[1] + 1) / (result[0] + 2)
                    # Bias towards postcodes with more data
                    confidence = min(result[0] / 10, 1.0)
                    return success_rate * confidence + (1 - confidence) * 0.5
                else:
                    # Default score for postcodes without history
                    return 0.5
            except Exception:
                return 0.5
        
        return sorted(postcodes, key=effectiveness_score, reverse=True)
    
    def _generate_full_postcodes(self, area_codes: List[str], limit: int) -> List[str]:
        """Generate full postcodes from area codes"""
        full_postcodes = []
        
        # Common UK postcode patterns for each area
        common_patterns = {
            1: ["1AA", "1AB", "1AD", "1AE", "1AF", "1AG", "1AH", "1AJ", "1AL", "1AN"],
            2: ["2AA", "2AB", "2AD", "2AE", "2AF", "2AG", "2AH", "2AJ", "2AL", "2AN"],
            3: ["3AA", "3AB", "3AD", "3AE", "3AF", "3AG", "3AH", "3AJ", "3AL", "3AN"],
            4: ["4AA", "4AB", "4AD", "4AE", "4AF", "4AG", "4AH", "4AJ", "4AL", "4AN"],
            5: ["5AA", "5AB", "5AD", "5AE", "5AF", "5AG", "5AH", "5AJ", "5AL", "5AN"],
            6: ["6AA", "6AB", "6AD", "6AE", "6AF", "6AG", "6AH", "6AJ", "6AL", "6AN"],
            7: ["7AA", "7AB", "7AD", "7AE", "7AF", "7AG", "7AH", "7AJ", "7AL", "7AN"],
            8: ["8AA", "8AB", "8AD", "8AE", "8AF", "8AG", "8AH", "8AJ", "8AL", "8AN"],
            9: ["9AA", "9AB", "9AD", "9AE", "9AF", "9AG", "9AH", "9AJ", "9AL", "9AN"],
            10: ["0AA", "0AB", "0AD", "0AE", "0AF", "0AG", "0AH", "0AJ", "0AL", "0AN"],
        }
        
        for area_code in area_codes:
            # Generate realistic postcodes for this area
            for i in range(1, 11):  # Up to 10 postcodes per area
                if len(full_postcodes) >= limit:
                    break
                    
                patterns = common_patterns.get(i, common_patterns[1])
                pattern = random.choice(patterns)
                full_postcode = f"{area_code}{pattern}"
                full_postcodes.append(full_postcode)
            
            if len(full_postcodes) >= limit:
                break
        
        return full_postcodes
    
    def _format_postcodes(self, postcodes: List[str]) -> List[str]:
        """Format postcodes consistently"""
        formatted = []
        for pc in postcodes:
            # Remove spaces and convert to uppercase
            clean_pc = pc.replace(" ", "").upper()
            
            # Add space in correct position for UK postcodes
            if len(clean_pc) >= 5:
                # Insert space before last 3 characters
                formatted_pc = f"{clean_pc[:-3]} {clean_pc[-3:]}"
                formatted.append(formatted_pc)
            else:
                formatted.append(clean_pc)
        
        return formatted
    
    def record_success_rate(self, postcode: str, listings_found: int):
        """Record the success rate for a postcode"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Insert or update postcode stats
            conn.execute("""
                INSERT INTO postcode_stats (postcode, total_searches, total_results, last_updated)
                VALUES (?, 1, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(postcode) DO UPDATE SET
                    total_searches = total_searches + 1,
                    total_results = total_results + ?,
                    last_updated = CURRENT_TIMESTAMP
            """, (postcode, listings_found, listings_found))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Recorded success rate for {postcode}: {listings_found} listings")
            
        except Exception as e:
            logger.error(f"Failed to record success rate for {postcode}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get postcode effectiveness statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            cursor = conn.execute("""
                SELECT COUNT(*) as total_postcodes,
                       AVG(CAST(total_results AS FLOAT) / total_searches) as avg_success_rate,
                       MAX(CAST(total_results AS FLOAT) / total_searches) as max_success_rate,
                       SUM(total_results) as total_listings_found
                FROM postcode_stats 
                WHERE total_searches > 0
            """)
            
            stats = cursor.fetchone()
            conn.close()
            
            return {
                "total_postcodes_tracked": stats[0] or 0,
                "average_success_rate": stats[1] or 0,
                "total_listings_found": stats[3] or 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}


async def create_browser_context(playwright_instance, proxy_rotator: ProxyRotator = None):
    """Create a browser context with appropriate settings for Facebook Marketplace"""
    
    # Random user agent selection for diversity
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
    ]
    
    # Set up proxy if available
    proxy_config = None
    proxy_url = None
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
                    else:
                        username = password = None
                        host, port = rest.split(":", 1)
                else:
                    protocol = "http"
                    if "@" in proxy_url:
                        auth, server = proxy_url.split("@", 1)
                        username, password = auth.split(":", 1)
                        host, port = server.split(":", 1)
                    else:
                        username = password = None
                        host, port = proxy_url.split(":", 1)
                
                proxy_config = {
                    "server": f"{protocol}://{host}:{port}",
                }
                if username and password:
                    proxy_config["username"] = username
                    proxy_config["password"] = password
                    
                logger.info(f"Using proxy: {host}:{port}")
                
            except Exception as e:
                logger.error(f"Failed to parse proxy {proxy_url}: {e}")
                proxy_config = None
    
    # Browser launch options
    browser_options = {
        "headless": HEADLESS,
        "args": [
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-field-trial-config",
        ]
    }
    
    if proxy_config:
        browser_options["proxy"] = proxy_config
    
    try:
        browser = await playwright_instance.chromium.launch(**browser_options)
        
        # Create context with realistic settings
        context = await browser.new_context(
            user_agent=random.choice(user_agents),
            viewport={"width": 1920, "height": 1080},
            locale="en-GB",
            timezone_id="Europe/London",
            permissions=["geolocation"],
            geolocation={"latitude": 51.5074, "longitude": -0.1278},  # London coordinates
            extra_http_headers={
                "Accept-Language": "en-GB,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Cache-Control": "max-age=0"
            }
        )
        
        # Set additional properties to avoid detection
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-GB', 'en'],
            });
            
            window.chrome = {
                runtime: {},
            };
        """)
        
        return browser, context, proxy_url
        
    except Exception as e:
        logger.error(f"Failed to create browser context: {e}")
        if proxy_config and proxy_rotator and proxy_url:
            proxy_rotator.mark_proxy_failed(proxy_url)
        raise


async def _scrape_page_core(page, url: str, proxy: str = None) -> List[Dict[str, Any]]:
    """Core page scraping logic for Facebook Marketplace"""
    
    listings = []
    
    try:
        # Navigate to the page with extended timeout for Facebook
        logger.info(f"Navigating to: {url}")
        
        # Add random delay before navigation
        await asyncio.sleep(random.uniform(*REQUEST_DELAY_RANGE))
        
        await page.goto(url, wait_until="networkidle", timeout=PAGE_TIMEOUT_MS)
        
        # Wait for initial content to load
        await asyncio.sleep(random.uniform(2.0, 4.0))
        
        # Handle potential login popup or cookie consent
        try:
            # Check for cookie consent button
            cookie_button = page.locator("button:has-text('Allow all cookies'), button:has-text('Accept all'), [data-testid='cookie-policy-manage-dialog-accept-button']")
            if await cookie_button.count() > 0:
                await cookie_button.first.click()
                await asyncio.sleep(1)
                logger.info("Accepted cookie consent")
        except Exception as e:
            logger.debug(f"No cookie consent needed: {e}")
        
        # Try to handle location permission request
        try:
            location_button = page.locator("button:has-text('Not now'), button:has-text('Block'), [data-testid='browser_location_permission_dialog_not_now_button']")
            if await location_button.count() > 0:
                await location_button.first.click()
                await asyncio.sleep(1)
                logger.info("Declined location permission")
        except Exception as e:
            logger.debug(f"No location permission request: {e}")
        
        # Scroll to load dynamic content
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
        await asyncio.sleep(2)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(3)
        
        # Wait for listings to load
        try:
            await page.wait_for_selector(SELECTORS["listing"], timeout=20000)
        except PlaywrightTimeout:
            logger.warning("No listings found on page")
            return listings
        
        # Extract listings
        listing_elements = await page.query_selector_all(SELECTORS["listing"])
        logger.info(f"Found {len(listing_elements)} listing elements")
        
        for idx, listing_element in enumerate(listing_elements):
            try:
                listing_data = await _extract_listing_data(listing_element, page)
                if listing_data and listing_data.get("title") and listing_data.get("price"):
                    listings.append(listing_data)
                    logger.debug(f"Extracted listing {idx + 1}: {listing_data.get('title')[:50]}...")
                else:
                    logger.debug(f"Skipped incomplete listing {idx + 1}")
                    
            except Exception as e:
                logger.error(f"Error extracting listing {idx + 1}: {e}")
                continue
        
        logger.info(f"Successfully extracted {len(listings)} listings from page")
        
        # Random delay before leaving page
        await asyncio.sleep(random.uniform(*REQUEST_DELAY_RANGE))
        
        return listings
        
    except PlaywrightTimeout:
        logger.error(f"Timeout loading page: {url}")
        return listings
        
    except Exception as e:
        logger.error(f"Error scraping page {url}: {e}")
        return listings


async def _extract_listing_data(listing_element, page) -> Dict[str, Any]:
    """Extract data from a single Facebook Marketplace listing element"""
    
    listing_data = {
        "title": "",
        "price": "",
        "price_numeric": None,
        "description": "",
        "location": "",
        "distance": "",
        "link": "",
        "image_url": "",
        "posted_date": "",
        "seller_name": "",
        "seller_type": "",
        "condition": "",
        "mileage": "",
        "mileage_numeric": None,
        "year": "",
        "year_numeric": None,
        "engine_size": "",
        "doors": "",
        "scraped_at": datetime.now().isoformat(),
        "source": "facebook_marketplace"
    }
    
    try:
        # Extract title
        title_element = listing_element.query_selector(SELECTORS["title"])
        if title_element:
            title = await title_element.inner_text()
            listing_data["title"] = title.strip()
        
        # Extract price
        price_element = listing_element.query_selector(SELECTORS["price"])
        if price_element:
            price_text = await price_element.inner_text()
            listing_data["price"] = price_text.strip()
            
            # Extract numeric price
            price_match = PRICE_RE.search(price_text)
            if price_match:
                try:
                    price_numeric = float(price_match.group(1).replace(",", ""))
                    listing_data["price_numeric"] = price_numeric
                except (ValueError, AttributeError):
                    pass
        
        # Extract description
        desc_element = listing_element.query_selector(SELECTORS["description"])
        if desc_element:
            description = await desc_element.inner_text()
            listing_data["description"] = description.strip()
        
        # Extract location
        location_element = listing_element.query_selector(SELECTORS["location"])
        if location_element:
            location = await location_element.inner_text()
            listing_data["location"] = location.strip()
        
        # Extract distance
        distance_element = listing_element.query_selector(SELECTORS["distance"])
        if distance_element:
            distance = await distance_element.inner_text()
            listing_data["distance"] = distance.strip()
        
        # Extract link
        link_element = listing_element.query_selector(SELECTORS["link"])
        if link_element:
            href = await link_element.get_attribute("href")
            if href:
                if href.startswith("/"):
                    listing_data["link"] = f"https://www.facebook.com{href}"
                else:
                    listing_data["link"] = href
        
        # Extract image URL
        image_element = listing_element.query_selector(SELECTORS["image"])
        if image_element:
            src = await image_element.get_attribute("src")
            if src:
                listing_data["image_url"] = src
        
        # Extract posted date
        posted_date_element = listing_element.query_selector(SELECTORS["posted_date"])
        if posted_date_element:
            posted_date = await posted_date_element.inner_text()
            listing_data["posted_date"] = posted_date.strip()
        
        # Extract seller name
        seller_name_element = listing_element.query_selector(SELECTORS["seller_name"])
        if seller_name_element:
            seller_name = await seller_name_element.inner_text()
            listing_data["seller_name"] = seller_name.strip()
        
        # Extract seller type
        seller_type_element = listing_element.query_selector(SELECTORS["seller_type"])
        if seller_type_element:
            seller_type = await seller_type_element.inner_text()
            listing_data["seller_type"] = seller_type.strip()
        
        # Extract condition from title/description
        full_text = f"{listing_data['title']} {listing_data['description']}".lower()
        
        # Extract year
        year_match = YEAR_RE.search(full_text)
        if year_match:
            try:
                year = int(year_match.group(0))
                if 1990 <= year <= datetime.now().year + 1:
                    listing_data["year"] = str(year)
                    listing_data["year_numeric"] = year
            except (ValueError, AttributeError):
                pass
        
        # Extract mileage
        mileage_match = MILEAGE_RE.search(full_text)
        if mileage_match:
            try:
                mileage_str = mileage_match.group(1).replace(",", "")
                mileage = int(mileage_str)
                if 0 <= mileage <= 1000000:  # Reasonable mileage range
                    listing_data["mileage"] = f"{mileage:,} miles"
                    listing_data["mileage_numeric"] = mileage
            except (ValueError, AttributeError):
                pass
        
        # Extract engine size
        engine_match = ENGINE_SIZE_RE.search(full_text)
        if engine_match:
            if engine_match.group(1):  # Liter format
                listing_data["engine_size"] = f"{engine_match.group(1)}L"
            elif engine_match.group(2):  # CC format
                cc = int(engine_match.group(2))
                listing_data["engine_size"] = f"{cc}cc"
        
        # Extract doors
        doors_match = DOORS_RE.search(full_text)
        if doors_match:
            listing_data["doors"] = f"{doors_match.group(1)} doors"
        
        # Extract condition from title/description
        if any(word in full_text for word in ["new", "brand new"]):
            listing_data["condition"] = "New"
        elif any(word in full_text for word in ["used", "second hand", "pre-owned"]):
            listing_data["condition"] = "Used"
        
        return listing_data
        
    except Exception as e:
        logger.error(f"Error extracting listing data: {e}")
        return listing_data


async def _scrape_page_enhanced(page, url: str, proxy: str = None, semaphore: asyncio.Semaphore = None) -> List[Dict[str, Any]]:
    """Enhanced page scraping with semaphore control"""
    if semaphore:
        async with semaphore:
            return await _scrape_page_core(page, url, proxy)
    else:
        return await _scrape_page_core(page, url, proxy)


async def scrape_postcode_worker(postcode: str, pages_per_postcode: int, semaphore: asyncio.Semaphore, 
                                proxy_rotator: ProxyRotator, results_queue: asyncio.Queue):
    """Worker function to scrape listings for a single postcode"""
    
    all_listings = []
    successful_pages = 0
    
    try:
        async with async_playwright() as playwright:
            browser, context, proxy_used = await create_browser_context(playwright, proxy_rotator)
            
            try:
                page = await context.new_page()
                
                # Set realistic page settings
                await page.set_viewport_size({"width": 1920, "height": 1080})
                
                for page_num in range(1, pages_per_postcode + 1):
                    try:
                        # Use different search queries for variety
                        search_query = random.choice(FACEBOOK_SEARCH_QUERIES)
                        
                        # Build Facebook Marketplace URL
                        location_part = postcode.replace(" ", "%20")
                        
                        # Facebook Marketplace URL format
                        url = f"https://www.facebook.com/marketplace/{location_part}/search/?query={search_query}&sortBy=creation_time_descend&exact=false"
                        
                        # Add pagination if supported (Facebook uses infinite scroll mostly)
                        if page_num > 1:
                            # Try to simulate scrolling to load more content
                            for scroll in range(page_num - 1):
                                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                                await asyncio.sleep(random.uniform(2.0, 4.0))
                        
                        logger.info(f"Scraping {postcode} page {page_num}: {url}")
                        
                        # Scrape the page
                        page_listings = await _scrape_page_enhanced(page, url, proxy_used, semaphore)
                        
                        if page_listings:
                            all_listings.extend(page_listings)
                            successful_pages += 1
                            logger.info(f"Page {page_num}: Found {len(page_listings)} listings")
                        else:
                            logger.warning(f"Page {page_num}: No listings found")
                        
                        # Respectful delay between pages
                        await asyncio.sleep(random.uniform(*REQUEST_DELAY_RANGE))
                        
                    except Exception as e:
                        logger.error(f"Error scraping page {page_num}: {e}")
                        continue
                        
            finally:
                await browser.close()
                
    except Exception as e:
        logger.error(f"Error in worker for postcode {postcode}: {e}")
        if proxy_used and proxy_rotator:
            proxy_rotator.mark_proxy_failed(proxy_used)
    
    # Add postcode info to each listing
    for listing in all_listings:
        listing["search_postcode"] = postcode
    
    logger.info(f"Completed {postcode}: {len(all_listings)} total listings from {successful_pages} pages")
    
    # Put results in queue
    await results_queue.put({
        "postcode": postcode,
        "listings": all_listings,
        "pages_scraped": successful_pages
    })


async def scrape_multiple_postcodes(postcodes: List[str], pages_per_postcode: int = 3, 
                                  proxy_list: List[str] = None, outfile: Path = None) -> pd.DataFrame:
    """Scrape multiple postcodes concurrently with rate limiting"""
    
    logger.info(f"Starting concurrent scraping of {len(postcodes)} postcodes")
    
    # Initialize proxy rotator
    proxy_rotator = ProxyRotator(proxy_list) if proxy_list else ProxyRotator()
    
    # Create semaphores for rate limiting
    browser_semaphore = asyncio.Semaphore(MAX_CONCURRENT_BROWSERS)
    page_semaphore = asyncio.Semaphore(MAX_CONCURRENT_PAGES)
    
    # Results queue
    results_queue = asyncio.Queue()
    
    # Create worker tasks
    tasks = []
    for postcode in postcodes:
        task = asyncio.create_task(
            scrape_postcode_worker(postcode, pages_per_postcode, page_semaphore, proxy_rotator, results_queue)
        )
        tasks.append(task)
    
    # Function to limit concurrent workers
    async def run_worker_with_limit(worker):
        async with browser_semaphore:
            return await worker
    
    # Run workers with browser concurrency limit
    limited_tasks = [run_worker_with_limit(task) for task in tasks]
    
    # Wait for all tasks to complete
    await asyncio.gather(*limited_tasks, return_exceptions=True)
    
    # Collect results
    all_listings = []
    postcode_manager = PostcodeManager()
    
    while not results_queue.empty():
        try:
            result = await results_queue.get()
            postcode = result["postcode"]
            listings = result["listings"]
            
            all_listings.extend(listings)
            
            # Record success rate
            postcode_manager.record_success_rate(postcode, len(listings))
            
            logger.info(f"Collected {len(listings)} listings from {postcode}")
            
        except Exception as e:
            logger.error(f"Error collecting results: {e}")
    
    logger.info(f"Total listings collected: {len(all_listings)}")
    
    # Convert to DataFrame
    if all_listings:
        df = pd.DataFrame(all_listings)
        
        # Clean up data
        df = df.drop_duplicates(subset=["title", "price", "location"], keep="first")
        
        # Save to file if specified
        if outfile:
            df.to_csv(outfile, index=False)
            logger.info(f"Results saved to {outfile}")
        
        return df
    else:
        logger.warning("No listings found")
        return pd.DataFrame()


def analyse(csv_path: Path, show_plots: bool = True) -> None:
    """Analyze scraped data"""
    
    if not csv_path.exists():
        logger.error(f"File not found: {csv_path}")
        return
    
    try:
        df = pd.read_csv(csv_path)
        logger.info(f"Loaded {len(df)} listings from {csv_path}")
        
        if df.empty:
            logger.warning("No data to analyze")
            return
        
        # Basic statistics
        print("\n" + "="*60)
        print("FACEBOOK MARKETPLACE FORD TRANSIT L2 H2 ANALYSIS")
        print("="*60)
        print(f"Total listings: {len(df):,}")
        print(f"Date range: {df['scraped_at'].min()} to {df['scraped_at'].max()}")
        
        # Price analysis
        if 'price_numeric' in df.columns:
            price_df = df[df['price_numeric'].notna() & (df['price_numeric'] > 0)]
            
            if not price_df.empty:
                print(f"\nPRICE ANALYSIS ({len(price_df)} listings with valid prices)")
                print("-" * 50)
                print(f"Average price: £{price_df['price_numeric'].mean():,.0f}")
                print(f"Median price: £{price_df['price_numeric'].median():,.0f}")
                print(f"Price range: £{price_df['price_numeric'].min():,.0f} - £{price_df['price_numeric'].max():,.0f}")
                
                # Price percentiles
                print(f"25th percentile: £{price_df['price_numeric'].quantile(0.25):,.0f}")
                print(f"75th percentile: £{price_df['price_numeric'].quantile(0.75):,.0f}")
                print(f"90th percentile: £{price_df['price_numeric'].quantile(0.90):,.0f}")
        
        # Mileage analysis
        if 'mileage_numeric' in df.columns:
            mileage_df = df[df['mileage_numeric'].notna() & (df['mileage_numeric'] > 0)]
            
            if not mileage_df.empty:
                print(f"\nMILEAGE ANALYSIS ({len(mileage_df)} listings with mileage)")
                print("-" * 50)
                print(f"Average mileage: {mileage_df['mileage_numeric'].mean():,.0f} miles")
                print(f"Median mileage: {mileage_df['mileage_numeric'].median():,.0f} miles")
                print(f"Mileage range: {mileage_df['mileage_numeric'].min():,.0f} - {mileage_df['mileage_numeric'].max():,.0f} miles")
        
        # Year analysis
        if 'year_numeric' in df.columns:
            year_df = df[df['year_numeric'].notna()]
            
            if not year_df.empty:
                print(f"\nYEAR ANALYSIS ({len(year_df)} listings with year)")
                print("-" * 50)
                print(f"Year range: {int(year_df['year_numeric'].min())} - {int(year_df['year_numeric'].max())}")
                print(f"Average year: {year_df['year_numeric'].mean():.0f}")
                print(f"Most common year: {year_df['year_numeric'].mode().iloc[0]:.0f}")
        
        # Location analysis
        if 'location' in df.columns:
            location_counts = df['location'].value_counts().head(10)
            print(f"\nTOP LOCATIONS")
            print("-" * 50)
            for location, count in location_counts.items():
                print(f"{location}: {count} listings")
        
        # Seller type analysis
        if 'seller_type' in df.columns:
            seller_counts = df['seller_type'].value_counts()
            print(f"\nSELLER TYPES")
            print("-" * 50)
            for seller_type, count in seller_counts.items():
                print(f"{seller_type}: {count} listings ({count/len(df)*100:.1f}%)")
        
        # Generate plots if requested and libraries available
        if show_plots and plt is not None and np is not None:
            try:
                _generate_analysis_plots(df, csv_path.stem)
            except Exception as e:
                logger.warning(f"Error generating plots: {e}")
        
    except Exception as e:
        logger.error(f"Error analyzing data: {e}")


def _generate_analysis_plots(df: pd.DataFrame, title_prefix: str):
    """Generate analysis plots for the Facebook Marketplace data"""
    
    plt.style.use('default')
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle(f'{title_prefix} - Facebook Marketplace Ford Transit L2 H2 Analysis', fontsize=16, fontweight='bold')
    
    # Price distribution
    if 'price_numeric' in df.columns:
        price_data = df[df['price_numeric'].notna() & (df['price_numeric'] > 0)]['price_numeric']
        if not price_data.empty:
            axes[0, 0].hist(price_data, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
            axes[0, 0].set_title('Price Distribution')
            axes[0, 0].set_xlabel('Price (£)')
            axes[0, 0].set_ylabel('Number of Listings')
            axes[0, 0].axvline(price_data.median(), color='red', linestyle='--', label=f'Median: £{price_data.median():,.0f}')
            axes[0, 0].legend()
    
    # Price vs Mileage scatter plot
    if 'price_numeric' in df.columns and 'mileage_numeric' in df.columns:
        plot_df = df[(df['price_numeric'].notna()) & (df['mileage_numeric'].notna()) & 
                     (df['price_numeric'] > 0) & (df['mileage_numeric'] > 0)]
        if not plot_df.empty:
            axes[0, 1].scatter(plot_df['mileage_numeric'], plot_df['price_numeric'], alpha=0.6)
            axes[0, 1].set_title('Price vs Mileage')
            axes[0, 1].set_xlabel('Mileage (miles)')
            axes[0, 1].set_ylabel('Price (£)')
            
            # Add trend line
            if len(plot_df) > 1:
                z = np.polyfit(plot_df['mileage_numeric'], plot_df['price_numeric'], 1)
                p = np.poly1d(z)
                axes[0, 1].plot(plot_df['mileage_numeric'], p(plot_df['mileage_numeric']), "r--", alpha=0.8)
    
    # Year distribution
    if 'year_numeric' in df.columns:
        year_data = df[df['year_numeric'].notna()]['year_numeric']
        if not year_data.empty:
            year_counts = year_data.value_counts().sort_index()
            axes[1, 0].bar(year_counts.index, year_counts.values, alpha=0.7, color='lightgreen', edgecolor='black')
            axes[1, 0].set_title('Distribution by Year')
            axes[1, 0].set_xlabel('Year')
            axes[1, 0].set_ylabel('Number of Listings')
            axes[1, 0].tick_params(axis='x', rotation=45)
    
    # Price by Year (box plot)
    if 'price_numeric' in df.columns and 'year_numeric' in df.columns:
        plot_df = df[(df['price_numeric'].notna()) & (df['year_numeric'].notna()) & (df['price_numeric'] > 0)]
        if not plot_df.empty and len(plot_df['year_numeric'].unique()) > 1:
            years_to_plot = sorted(plot_df['year_numeric'].unique())[-8:]  # Last 8 years
            plot_df_recent = plot_df[plot_df['year_numeric'].isin(years_to_plot)]
            
            if not plot_df_recent.empty:
                axes[1, 1].boxplot([plot_df_recent[plot_df_recent['year_numeric'] == year]['price_numeric'].values 
                                  for year in years_to_plot], labels=years_to_plot)
                axes[1, 1].set_title('Price Distribution by Year')
                axes[1, 1].set_xlabel('Year')
                axes[1, 1].set_ylabel('Price (£)')
                axes[1, 1].tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    
    # Save plot
    plot_filename = f"{title_prefix}_facebook_analysis.png"
    plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
    print(f"\nPlot saved as: {plot_filename}")
    
    # Show plot
    plt.show()


async def scrape_facebook_single_postcode(postcode: str, pages: int, outfile: Path) -> pd.DataFrame:
    """Scrape Facebook Marketplace for a single postcode (legacy function)"""
    
    logger.info(f"Starting Facebook Marketplace scrape for postcode: {postcode}")
    
    all_listings = []
    
    try:
        async with async_playwright() as playwright:
            browser, context, proxy_used = await create_browser_context(playwright)
            
            try:
                page = await context.new_page()
                await page.set_viewport_size({"width": 1920, "height": 1080})
                
                for page_num in range(1, pages + 1):
                    try:
                        # Use different search queries for variety
                        search_query = random.choice(FACEBOOK_SEARCH_QUERIES)
                        location_part = postcode.replace(" ", "%20")
                        
                        url = f"https://www.facebook.com/marketplace/{location_part}/search/?query={search_query}&sortBy=creation_time_descend&exact=false"
                        
                        logger.info(f"Scraping page {page_num}/{pages}: {url}")
                        
                        page_listings = await _scrape_page_core(page, url)
                        
                        if page_listings:
                            # Add metadata
                            for listing in page_listings:
                                listing["search_postcode"] = postcode
                                listing["page_number"] = page_num
                            
                            all_listings.extend(page_listings)
                            logger.info(f"Page {page_num}: Found {len(page_listings)} listings")
                        else:
                            logger.warning(f"Page {page_num}: No listings found")
                        
                        # Respectful delay between pages
                        await asyncio.sleep(random.uniform(*REQUEST_DELAY_RANGE))
                        
                    except Exception as e:
                        logger.error(f"Error on page {page_num}: {e}")
                        continue
                        
            finally:
                await browser.close()
                
    except Exception as e:
        logger.error(f"Error in single postcode scrape: {e}")
    
    # Convert to DataFrame and save
    if all_listings:
        df = pd.DataFrame(all_listings)
        df.to_csv(outfile, index=False)
        logger.info(f"Saved {len(df)} unique listings to {outfile}")
        
        return df
    else:
        logger.warning("No listings found")
        return pd.DataFrame()


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    
    parser = argparse.ArgumentParser(
        description="Scrape Ford Transit L2 H2 listings from Facebook Marketplace UK",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic scraping
  python get_vans_facebook.py scrape --postcode "M1 1AA" --pages 10

  # Multi-postcode with strategy
  python get_vans_facebook.py scrape-multi --strategy commercial_hubs --postcode-limit 20

  # UK-wide scraping
  python get_vans_facebook.py scrape-uk --outfile ford_transit_uk_facebook.csv

  # Analysis
  python get_vans_facebook.py analyse my_data.csv
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Scrape command (single postcode)
    scrape_parser = subparsers.add_parser("scrape", help="Scrape single postcode")
    scrape_parser.add_argument("--postcode", required=True, help="UK postcode to search")
    scrape_parser.add_argument("--pages", type=int, default=5, help="Number of pages to scrape")
    scrape_parser.add_argument("--outfile", type=Path, default="facebook_transit_listings.csv", help="Output CSV file")
    
    # Scrape-multi command
    multi_parser = subparsers.add_parser("scrape-multi", help="Scrape multiple postcodes")
    multi_parser.add_argument("--strategy", type=PostcodeStrategy, choices=list(PostcodeStrategy), 
                             default=PostcodeStrategy.MIXED_DENSITY, help="Postcode selection strategy")
    multi_parser.add_argument("--postcode-limit", type=int, default=30, help="Number of postcodes to scrape")
    multi_parser.add_argument("--pages-per-postcode", type=int, default=3, help="Pages per postcode")
    multi_parser.add_argument("--postcodes", nargs="*", help="Custom postcodes to use")
    multi_parser.add_argument("--center-postcode", help="Center postcode for geographic filtering")
    multi_parser.add_argument("--radius-km", type=float, help="Radius in km for geographic filtering")
    multi_parser.add_argument("--proxy-file", type=Path, help="File containing proxy list")
    multi_parser.add_argument("--outfile", type=Path, default="facebook_transit_multi.csv", help="Output CSV file")
    multi_parser.add_argument("--max-browsers", type=int, default=MAX_CONCURRENT_BROWSERS, help="Max concurrent browsers")
    multi_parser.add_argument("--max-pages", type=int, default=MAX_CONCURRENT_PAGES, help="Max concurrent pages")
    
    # Scrape-UK command
    uk_parser = subparsers.add_parser("scrape-uk", help="Scrape UK-wide with optimized settings")
    uk_parser.add_argument("--outfile", type=Path, default="ford_transit_uk_facebook.csv", help="Output CSV file")
    uk_parser.add_argument("--include-mixed", action="store_true", help="Include mixed density areas")
    uk_parser.add_argument("--postcode-limit", type=int, default=100, help="Number of postcodes")
    uk_parser.add_argument("--pages-per-postcode", type=int, default=5, help="Pages per postcode")
    uk_parser.add_argument("--proxy-file", type=Path, help="File containing proxy list")
    uk_parser.add_argument("--max-browsers", type=int, default=MAX_CONCURRENT_BROWSERS, help="Max concurrent browsers")
    uk_parser.add_argument("--max-pages", type=int, default=MAX_CONCURRENT_PAGES, help="Max concurrent pages")
    
    # Postcodes command
    postcodes_parser = subparsers.add_parser("postcodes", help="Analyze postcode strategies")
    postcodes_parser.add_argument("--strategy", type=PostcodeStrategy, choices=list(PostcodeStrategy),
                                 default=PostcodeStrategy.MIXED_DENSITY, help="Strategy to analyze")
    postcodes_parser.add_argument("--limit", type=int, default=20, help="Number of postcodes to show")
    postcodes_parser.add_argument("--center-postcode", help="Center postcode for geographic filtering")
    postcodes_parser.add_argument("--radius-km", type=float, help="Radius in km for geographic filtering")
    
    # Analyse command
    analyse_parser = subparsers.add_parser("analyse", help="Analyze scraped data")
    analyse_parser.add_argument("csv_file", type=Path, help="CSV file to analyze")
    analyse_parser.add_argument("--no-plots", action="store_true", help="Skip generating plots")
    
    return parser.parse_args()


def load_proxies_from_file(proxy_file: Path) -> List[str]:
    """Load proxy list from file"""
    try:
        with open(proxy_file, 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]
        logger.info(f"Loaded {len(proxies)} proxies from {proxy_file}")
        return proxies
    except Exception as e:
        logger.error(f"Error loading proxies from {proxy_file}: {e}")
        return []


def handle_postcode_command(args):
    """Handle the postcodes command"""
    manager = PostcodeManager()
    
    postcodes = manager.get_postcodes(
        strategy=args.strategy,
        limit=args.limit,
        geographic_radius_km=args.radius_km,
        center_postcode=args.center_postcode
    )
    
    print(f"\nPostcode Strategy: {args.strategy.value}")
    print(f"Generated {len(postcodes)} postcodes:")
    print("-" * 50)
    
    for i, postcode in enumerate(postcodes, 1):
        print(f"{i:2d}. {postcode}")
    
    # Show stats
    stats = manager.get_stats()
    if stats:
        print(f"\nDatabase Statistics:")
        print("-" * 50)
        print(f"Tracked postcodes: {stats['total_postcodes_tracked']}")
        print(f"Average success rate: {stats['average_success_rate']:.2%}")
        print(f"Total listings found: {stats['total_listings_found']}")


def main():
    """Main entry point"""
    args = parse_args()
    
    if not args.command:
        print("No command specified. Use --help for usage information.")
        return
    
    try:
        if args.command == "scrape":
            # Single postcode scraping
            result = asyncio.run(scrape_facebook_single_postcode(args.postcode, args.pages, args.outfile))
            print(f"Scraping completed. Found {len(result)} listings.")
            
        elif args.command == "scrape-multi":
            # Multi-postcode scraping
            global MAX_CONCURRENT_BROWSERS, MAX_CONCURRENT_PAGES
            MAX_CONCURRENT_BROWSERS = args.max_browsers
            MAX_CONCURRENT_PAGES = args.max_pages
            
            manager = PostcodeManager()
            
            # Get postcodes based on strategy
            if args.postcodes:
                postcodes = args.postcodes
            else:
                postcodes = manager.get_postcodes(
                    strategy=args.strategy,
                    limit=args.postcode_limit,
                    geographic_radius_km=args.radius_km,
                    center_postcode=args.center_postcode
                )
            
            logger.info(f"Using {len(postcodes)} postcodes with strategy: {args.strategy}")
            
            result = asyncio.run(scrape_multiple_postcodes(
                postcodes, args.pages_per_postcode, args.proxy_file, args.outfile
            ))
            
            print(f"Multi-postcode scraping completed. Found {len(result)} total listings.")
            
        elif args.command == "scrape-uk":
            # UK-wide scraping with optimized settings
            global MAX_CONCURRENT_BROWSERS, MAX_CONCURRENT_PAGES
            MAX_CONCURRENT_BROWSERS = args.max_browsers
            MAX_CONCURRENT_PAGES = args.max_pages
            
            manager = PostcodeManager()
            
            # Use commercial hubs strategy with optional mixed density
            strategy = PostcodeStrategy.COMMERCIAL_HUBS
            if args.include_mixed:
                strategy = PostcodeStrategy.MIXED_DENSITY
            
            postcodes = manager.get_postcodes(
                strategy=strategy,
                limit=args.postcode_limit
            )
            
            logger.info(f"Starting UK-wide Facebook Marketplace scraping with {len(postcodes)} postcodes")
            
            result = asyncio.run(scrape_multiple_postcodes(
                postcodes, args.pages_per_postcode, args.proxy_file, args.outfile
            ))
            
            print(f"UK-wide scraping completed. Found {len(result)} total listings.")
            
        elif args.command == "postcodes":
            # Postcode analysis
            handle_postcode_command(args)
            
        elif args.command == "analyse":
            # Data analysis
            analyse(args.csv_file, show_plots=not args.no_plots)
            
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise


if __name__ == "__main__":
    main() 
