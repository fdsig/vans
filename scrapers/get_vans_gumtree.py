#!/usr/bin/env python3
"""
Scrape and Analyse Ford Transit L2 H2 Listings from Gumtree UK
==============================================================

*Enhanced Gumtree scraping system with intelligent postcode management, 
concurrent scraping with proxy support, and advanced geographic intelligence.*

**🎯 KEY FEATURE: Scrapes CURRENT listings to get ASKING PRICES and market availability**

This script supports these sub‑commands:

* `scrape`    – harvest current listings → CSV (single postcode, legacy)
* `scrape-multi` – concurrent scraping across multiple postcodes with smart strategies
* `scrape-uk` – optimized UK-wide scraping focusing on commercial/industrial areas with descriptions and images
* `postcodes` – analyze and manage postcode selection strategies  
* `analyse`  – quick medians & scatter plots

----
Why Gumtree?
------------
Gumtree is one of the UK's largest classified ad platforms, showing what Ford Transits are currently available for.

- ✅ Current asking prices (market availability)
- ✅ Wide geographic coverage across UK
- ✅ Both private and trade sellers
- ✅ Detailed descriptions and specifications

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

**1) Basic Gumtree scraping (single postcode)**
```bash
python get_vans_gumtree.py scrape --postcode G23NX --pages 15 --outfile transit_gumtree.csv
```

**2) Smart multi-postcode Gumtree scraping**
```bash
# Use commercial hubs strategy across 30 postcodes
python get_vans_gumtree.py scrape-multi --strategy commercial_hubs --postcode-limit 30 \
    --pages-per-postcode 5 --outfile transit_commercial_gumtree.csv

# Geographic focus: 50km radius around Manchester
python get_vans_gumtree.py scrape-multi --strategy geographic_spread --center-postcode "M1 1AA" \
    --radius-km 50 --postcode-limit 20 --outfile transit_manchester_gumtree.csv

# Use custom postcodes with proxy rotation
python get_vans_gumtree.py scrape-multi --postcodes "SW1A 1AA" "M1 1AA" "B1 1AA" \
    --proxy-file proxies.txt --pages-per-postcode 10
```

**3) UK-wide Gumtree scraping (optimized command)**
```bash
# Scrape the whole UK focusing on commercial/industrial areas
python get_vans_gumtree.py scrape-uk --outfile ford_transit_uk_gumtree.csv

# Include mixed density areas for broader coverage
python get_vans_gumtree.py scrape-uk --include-mixed --pages-per-postcode 8 --postcode-limit 150

# Use proxies for large-scale scraping
python get_vans_gumtree.py scrape-uk --proxy-file proxies.txt --max-browsers 10 --max-pages 40
```

**4) Analysis of asking prices**
```bash
# Quick scatter plots and medians from current listings
python get_vans_gumtree.py analyse transit_commercial_gumtree.csv
```

----
Advanced Features
-----------------

**Gumtree Intelligence:**
- Extracts current asking prices and availability
- Handles both private and trade seller listings
- Captures detailed descriptions and specifications
- Monitors listing age and posting dates

**Concurrent Scraping:**
- Configurable browser and page concurrency limits
- Intelligent proxy rotation with failure handling
- Human-like delays and behavior simulation

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
import os

import pandas as pd
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# Import shared utilities and ScrapingResult
from van_scraping_utils import (
    ScrapingResult, PostcodeStrategy, PostcodeArea, PostcodeManager, 
    ProxyRotator, CSVManager, clean_price, clean_mileage, clean_year,
    detect_vat_status, detect_listing_type, standardize_postcode,
    human_delay, async_human_delay, get_coordinates_from_postcode
)

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
        logging.FileHandler('logs/gumtree_scraping.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Ensure data directory exists
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Configuration for Gumtree UK
# ---------------------------------------------------------------------------

REQUEST_DELAY_RANGE = (2.0, 4.0)  # Human-like delays for Gumtree
MAX_CONCURRENT_BROWSERS = 5
MAX_CONCURRENT_PAGES = 15

# Gumtree UK search URL template
GUMTREE_URL_TEMPLATE = (
    "https://www.gumtree.com/search?"
    "search_category=motors-cars-vans&"
    "q=ford+transit+l2+h2&"
    "search_location={postcode}&"
    "distance={distance}&"
    "page={page}"
)

HEADLESS = True
PAGE_TIMEOUT_MS = 60_000
THROTTLE_MS = 2_000

# Gumtree-specific CSS selectors
SELECTORS = {
    "listing": ".listing-maxi, .listing-summary, .listing-mini",
    "title": ".listing-title, h2 a, .listing-link",
    "price": ".listing-price, .ad-price, .price",
    "description": ".listing-description, .ad-description",
    "location": ".listing-location, .ad-location",
    "link": ".listing-title a, .listing-link",
    "image": ".listing-thumbnail img, .ad-image img",
    "posted_date": ".listing-posted-date, .ad-posted-date, .posted-date",
    "seller_type": ".listing-seller-type, .seller-type",
    "featured": ".listing-featured, .featured-ad",
    "seller_name": ".seller-name, .listing-seller",
    "phone": ".phone-number, .contact-phone",
}

# Gumtree-specific regex patterns
PRICE_RE = re.compile(r"£([\d,]+(?:\.\d{2})?)", re.I)
YEAR_RE = re.compile(r'\b(19|20)\d{2}\b')
MILEAGE_RE = re.compile(r'(\d{1,3}(?:,\d{3})*)\s*(?:miles?|mi)', re.I)
POSTCODE_RE = re.compile(r'\b[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}\b', re.I)

# ---------------------------------------------------------------------------
# Browser Context and Core Scraping Functions  
# ---------------------------------------------------------------------------

async def create_browser_context(playwright_instance, proxy_rotator: ProxyRotator = None):
    """Create a browser context with optional proxy"""
    proxy = None
    if proxy_rotator:
        proxy_url = proxy_rotator.get_next_proxy()
        if proxy_url:
            try:
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

async def _scrape_page_core(page, url: str, proxy: str = None) -> List[ScrapingResult]:
    """Core scraping logic for a single page of Gumtree listings"""
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
                
                # Skip featured/promoted listings that don't contain transit
                if "transit" not in title.lower():
                    continue
                
                # Extract price
                price_text = "N/A"
                price_value = None
                
                price_elem = await listing.query_selector(SELECTORS["price"])
                if price_elem:
                    price_text = await price_elem.inner_text()
                    price_text = price_text.strip()
                    price_value = clean_price(price_text)
                
                # Extract link
                link_elem = await listing.query_selector(SELECTORS["link"])
                link = await link_elem.get_attribute('href') if link_elem else "N/A"
                if link and link.startswith('/'):
                    link = f"https://www.gumtree.com{link}"
                
                # Extract image URL
                img_elem = await listing.query_selector(SELECTORS["image"])
                img_url = await img_elem.get_attribute('src') if img_elem else "N/A"
                
                # Extract description
                desc_elem = await listing.query_selector(SELECTORS["description"])
                description_text = await desc_elem.inner_text() if desc_elem else ""
                description_text = description_text.strip()
                
                # Extract location
                location_elem = await listing.query_selector(SELECTORS["location"])
                location = await location_elem.inner_text() if location_elem else ""
                location = location.strip()
                
                # Extract posted date
                posted_elem = await listing.query_selector(SELECTORS["posted_date"])
                posted_date = await posted_elem.inner_text() if posted_elem else ""
                posted_date = posted_date.strip()
                
                # Extract seller type
                seller_type_elem = await listing.query_selector(SELECTORS["seller_type"])
                seller_type = await seller_type_elem.inner_text() if seller_type_elem else "Private"
                seller_type = seller_type.strip()
                
                # Extract seller name
                seller_elem = await listing.query_selector(SELECTORS["seller_name"])
                seller_name = await seller_elem.inner_text() if seller_elem else ""
                seller_name = seller_name.strip()
                
                # Check if featured listing
                featured_elem = await listing.query_selector(SELECTORS["featured"])
                is_featured = featured_elem is not None
                
                # Build comprehensive description from available fields
                description_parts = []
                if description_text:
                    description_parts.append(description_text[:300])  # Truncate main description
                if location:
                    description_parts.append(f"Location: {location}")
                if seller_type and seller_type != "Private":
                    description_parts.append(f"Seller: {seller_type}")
                if seller_name:
                    description_parts.append(f"Contact: {seller_name}")
                if posted_date:
                    description_parts.append(f"Posted: {posted_date}")
                if is_featured:
                    description_parts.append("Featured listing")
                
                full_description = "; ".join(description_parts) if description_parts else title
                
                # Extract year from title or description
                year = clean_year(f"{title} {description_text}")
                
                # Extract mileage from title or description  
                mileage = clean_mileage(f"{title} {description_text}")
                
                # Extract postcode from location
                postcode_match = POSTCODE_RE.search(location)
                extracted_postcode = standardize_postcode(postcode_match.group(0)) if postcode_match else ""
                
                # Detect VAT status and listing type
                full_text = f"{title} {description_text} {seller_type}"
                vat_included = detect_vat_status(full_text, "gumtree")
                listing_type = detect_listing_type(full_text, "gumtree")
                
                # Get coordinates from postcode
                latitude, longitude = get_coordinates_from_postcode(extracted_postcode)
                
                # Create ScrapingResult object
                result = ScrapingResult(
                    title=title,
                    year=year,
                    mileage=mileage,
                    price=price_value,
                    description=full_description,
                    image_url=img_url if img_url != "N/A" else "",
                    url=link if link != "N/A" else "",
                    postcode=extracted_postcode,
                    source="gumtree",
                    listing_type=listing_type,
                    vat_included=vat_included,
                    scraped_at=datetime.now(),
                    latitude=latitude,
                    longitude=longitude
                )
                
                results.append(result)
                
                if len(results) % 10 == 0:
                    logger.info(f"✅ Processed {len(results)} Gumtree listings...")
                
            except Exception as e:
                logger.warning(f"⚠️ Error processing listing {i+1}: {e}")
                continue
        
        logger.info(f"✅ Successfully scraped {len(results)} Gumtree listings from page")
        return results
        
    except Exception as e:
        logger.error(f"❌ Error scraping page {url}: {e}")
        return []

async def _scrape_page_enhanced(page, url: str, proxy: str = None, semaphore: asyncio.Semaphore = None) -> List[ScrapingResult]:
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
                    url = GUMTREE_URL_TEMPLATE.format(
                        postcode=quote_plus(postcode),
                        page=page_num,
                        distance=25  # 25 mile radius
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
            manager.record_success_rate(postcode, len(postcode_results), "gumtree")
            
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
    """Scrape multiple postcodes concurrently for Gumtree listings with deduplication"""
    
    proxy_rotator = ProxyRotator(proxy_list) if proxy_list else None
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_PAGES)
    results_queue = asyncio.Queue()
    
    # Initialize CSV manager for deduplication
    if outfile is None:
        outfile = Path('data/gumtree_multi.csv')
    csv_manager = CSVManager(str(outfile))
    
    logger.info(f"🚀 Starting concurrent Gumtree scraping of {len(postcodes)} postcodes")
    logger.info(f"📄 {pages_per_postcode} pages per postcode")
    logger.info(f"🔗 {'With' if proxy_rotator else 'Without'} proxy rotation")
    logger.info(f"📁 Output file: {outfile}")
    
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
            
            # Save results incrementally with deduplication
            if results:
                new_count = csv_manager.append_results(results)
                logger.info(f"📊 {postcode}: Added {new_count} unique results (total {len(results)} scraped)")
            
            logger.info(f"📊 Progress: {completed_postcodes}/{len(postcodes)} postcodes completed")
    
    except Exception as e:
        logger.error(f"Error collecting results: {e}")
    
    # Wait for all workers to complete
    try:
        await asyncio.gather(*worker_tasks, return_exceptions=True)
    except Exception as e:
        logger.error(f"Error waiting for workers: {e}")
    
    # Get final statistics
    stats = csv_manager.get_stats()
    logger.info(f"✅ Gumtree scraping completed: {stats.get('total_records', 0)} unique listings saved")
    
    # Return DataFrame for compatibility (though results are already saved)
    if all_results:
        return pd.DataFrame([result.to_dict() for result in all_results])
    else:
        logger.warning("⚠️ No Gumtree listings found")
        return pd.DataFrame()

def analyse(csv_path: Path, show_plots: bool = True) -> None:
    """Quick analysis of Gumtree listings - simplified to avoid compute overhead"""
    
    if not csv_path.exists():
        logger.error(f"❌ CSV file not found: {csv_path}")
        return
    
    logger.info(f"📊 Analyzing Gumtree listings from: {csv_path}")
    
    try:
        # Get basic file info without loading full DataFrame
        file_size = os.path.getsize(csv_path)
        
        # Count lines for record count
        with open(csv_path, 'r') as f:
            line_count = sum(1 for _ in f) - 1  # Subtract header
            
        logger.info(f"📋 Total records: {line_count}")
        logger.info(f"📁 File size: {file_size / 1024 / 1024:.1f} MB")
        
        # Simple statistics without heavy computation
        logger.info("✅ Basic analysis completed - full EDA removed to conserve compute resources")
        
        if line_count > 0:
            logger.info("💡 For detailed analysis, use specialized tools or smaller datasets")
        
    except Exception as e:
        logger.error(f"❌ Error analyzing data: {e}")

async def scrape_gumtree_single_postcode(postcode: str, pages: int, outfile: Path) -> pd.DataFrame:
    """Scrape Gumtree listings for a single postcode"""
    
    logger.info(f"🎯 Scraping Gumtree listings for postcode: {postcode}")
    logger.info(f"📄 Pages to scrape: {pages}")
    
    all_results = []
    
    async with async_playwright() as p:
        browser, context = await create_browser_context(p)
        page = await context.new_page()
        
        try:
            for page_num in range(1, pages + 1):
                url = GUMTREE_URL_TEMPLATE.format(
                    postcode=quote_plus(postcode),
                    page=page_num,
                    distance=25
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
        df = pd.DataFrame([asdict(result) for result in all_results])
        df.to_csv(outfile, index=False)
        logger.info(f"✅ Saved {len(df)} Gumtree listings to {outfile}")
        
        # Record success for postcode intelligence
        manager = PostcodeManager()
        manager.record_success_rate(postcode, len(all_results), "gumtree")
        
        return df
    else:
        logger.warning("⚠️ No Gumtree listings found")
        return pd.DataFrame()

def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Scrape Ford Transit L2 H2 listings from Gumtree UK",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic Gumtree scraping
  python get_vans_gumtree.py scrape --postcode "M1 1AA" --pages 10 --outfile transit_gumtree.csv
  
  # Multi-postcode with commercial strategy
  python get_vans_gumtree.py scrape-multi --strategy commercial_hubs --postcode-limit 20 --pages-per-postcode 5
  
  # UK-wide Gumtree scraping
  python get_vans_gumtree.py scrape-uk --outfile ford_transit_uk_gumtree.csv
  
  # Analyze Gumtree listings
  python get_vans_gumtree.py analyse transit_gumtree.csv
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scrape command (single postcode)
    scrape_parser = subparsers.add_parser('scrape', help='Scrape single postcode')
    scrape_parser.add_argument('--postcode', required=True, help='UK postcode to search')
    scrape_parser.add_argument('--pages', type=int, default=5, help='Number of pages to scrape')
    scrape_parser.add_argument('--outfile', type=Path, default=Path('data/gumtree_listings.csv'), help='Output CSV file')
    
    # Scrape-multi command
    multi_parser = subparsers.add_parser('scrape-multi', help='Scrape multiple postcodes')
    multi_parser.add_argument('--strategy', type=PostcodeStrategy, choices=list(PostcodeStrategy), 
                             default=PostcodeStrategy.MIXED_DENSITY, help='Postcode selection strategy')
    multi_parser.add_argument('--postcode-limit', type=int, default=30, help='Number of postcodes to scrape')
    multi_parser.add_argument('--pages-per-postcode', type=int, default=3, help='Pages per postcode')
    multi_parser.add_argument('--postcodes', nargs='*', help='Custom postcodes to use')
    multi_parser.add_argument('--center-postcode', help='Center postcode for geographic filtering')
    multi_parser.add_argument('--radius-km', type=float, help='Radius in km for geographic filtering')
    multi_parser.add_argument('--outfile', type=Path, default=Path('data/gumtree_multi.csv'), help='Output CSV file')
    
    # Scrape-UK command
    uk_parser = subparsers.add_parser('scrape-uk', help='Scrape UK-wide with optimized settings')
    uk_parser.add_argument('--outfile', type=Path, default=Path('data/ford_transit_uk_gumtree.csv'), help='Output CSV file')
    uk_parser.add_argument('--include-mixed', action='store_true', help='Include mixed density areas')
    uk_parser.add_argument('--postcode-limit', type=int, default=100, help='Number of postcodes')
    uk_parser.add_argument('--pages-per-postcode', type=int, default=5, help='Pages per postcode')
    uk_parser.add_argument('--proxy-file', type=Path, help='File containing proxy list')
    uk_parser.add_argument('--max-browsers', type=int, default=5, help='Max concurrent browsers')
    uk_parser.add_argument('--max-pages', type=int, default=50, help='Max concurrent pages')
    
    # Postcodes command
    postcodes_parser = subparsers.add_parser('postcodes', help='Manage and analyze postcodes')
    postcodes_parser.add_argument('--strategy', choices=[s.value for s in PostcodeStrategy], 
                                 default='mixed_density', help='Postcode selection strategy')
    postcodes_parser.add_argument('--limit', type=int, default=20, help='Number of postcodes to show')
    postcodes_parser.add_argument('--stats', action='store_true', help='Show postcode statistics')
    
    # Analyse command
    analyse_parser = subparsers.add_parser('analyse', help='Analyze Gumtree listings CSV')
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
            asyncio.run(scrape_gumtree_single_postcode(
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
            logger.info(f"🇬🇧 UK-wide Gumtree scraping with {len(postcodes)} postcodes")
            
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
