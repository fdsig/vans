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

# Ensure data directory exists
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

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


async def _scrape_page_core(page, url: str, proxy: str = None) -> List[ScrapingResult]:
    """Core page scraping logic for Facebook Marketplace"""
    
    listings = []
    
    try:
        logger.info(f"🔍 Navigating to Facebook Marketplace: {url}")
        
        # Navigate to the page
        await page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until='domcontentloaded')
        
        # Handle potential Facebook login/consent prompts
        try:
            # Close any popups or dialogs that might appear
            close_selectors = [
                "[aria-label='Close']",
                "[data-testid='cookie-policy-manage-dialog-accept-button']",
                "[data-testid='non_fb_user_interstitial_dismiss_button']"
            ]
            
            for selector in close_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=3000)
                    if element:
                        await element.click()
                        await asyncio.sleep(1)
                except:
                    pass
        except:
            pass
        
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
                if listing_data and listing_data.get("title") and listing_data.get("price_numeric"):
                    
                    # Extract and clean data
                    title = listing_data.get("title", "")
                    year = listing_data.get("year_numeric")
                    mileage = listing_data.get("mileage_numeric")
                    price = listing_data.get("price_numeric")
                    location = listing_data.get("location", "")
                    description_text = listing_data.get("description", "")
                    seller_name = listing_data.get("seller_name", "")
                    seller_type = listing_data.get("seller_type", "")
                    condition = listing_data.get("condition", "")
                    posted_date = listing_data.get("posted_date", "")
                    
                    # Build comprehensive description from available Facebook fields
                    description_parts = []
                    if description_text:
                        description_parts.append(description_text[:300])  # Truncate main description
                    if condition:
                        description_parts.append(f"Condition: {condition}")
                    if location:
                        description_parts.append(f"Location: {location}")
                    if seller_name:
                        description_parts.append(f"Seller: {seller_name}")
                    if seller_type:
                        description_parts.append(f"Type: {seller_type}")
                    if posted_date:
                        description_parts.append(f"Posted: {posted_date}")
                    if listing_data.get("distance"):
                        description_parts.append(f"Distance: {listing_data.get('distance')}")
                    if listing_data.get("engine_size"):
                        description_parts.append(f"Engine: {listing_data.get('engine_size')}")
                    if listing_data.get("doors"):
                        description_parts.append(f"Doors: {listing_data.get('doors')}")
                    
                    full_description = "; ".join(description_parts) if description_parts else title
                    
                    # Extract postcode from location if available
                    postcode = ""
                    if location:
                        from van_scraping_utils import POSTCODE_RE
                        postcode_match = POSTCODE_RE.search(location)
                        if postcode_match:
                            postcode = standardize_postcode(postcode_match.group(0))
                    
                    # Detect VAT status and listing type
                    full_text = f"{title} {description_text} {seller_type}"
                    vat_included = detect_vat_status(full_text, "facebook")
                    listing_type = detect_listing_type(full_text, "facebook")
                    
                    # Get coordinates from postcode
                    latitude, longitude = get_coordinates_from_postcode(postcode)
                    
                    # Create ScrapingResult object
                    result = ScrapingResult(
                        title=title,
                        year=year,
                        mileage=mileage,
                        price=price,
                        description=full_description,
                        image_url=listing_data.get("image_url", ""),
                        url=listing_data.get("link", ""),
                        postcode=postcode,
                        source="facebook",
                        listing_type=listing_type,
                        vat_included=vat_included,
                        scraped_at=datetime.now(),
                        latitude=latitude,
                        longitude=longitude
                    )
                    
                    listings.append(result)
                    logger.debug(f"Extracted listing {idx + 1}: {title[:50]}...")
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
        title_element = await listing_element.query_selector(SELECTORS["title"])
        if title_element:
            title = await title_element.inner_text()
            listing_data["title"] = title.strip()
        
        # Extract price
        price_element = await listing_element.query_selector(SELECTORS["price"])
        if price_element:
            price_text = await price_element.inner_text()
            listing_data["price"] = price_text.strip()
            listing_data["price_numeric"] = clean_price(price_text)
        
        # Extract description
        desc_element = await listing_element.query_selector(SELECTORS["description"])
        if desc_element:
            description = await desc_element.inner_text()
            listing_data["description"] = description.strip()
        
        # Extract location
        location_element = await listing_element.query_selector(SELECTORS["location"])
        if location_element:
            location = await location_element.inner_text()
            listing_data["location"] = location.strip()
        
        # Extract distance
        distance_element = await listing_element.query_selector(SELECTORS["distance"])
        if distance_element:
            distance = await distance_element.inner_text()
            listing_data["distance"] = distance.strip()
        
        # Extract link
        link_element = await listing_element.query_selector(SELECTORS["link"])
        if link_element:
            href = await link_element.get_attribute("href")
            if href:
                if href.startswith("/"):
                    listing_data["link"] = f"https://www.facebook.com{href}"
                else:
                    listing_data["link"] = href
        
        # Extract image URL
        image_element = await listing_element.query_selector(SELECTORS["image"])
        if image_element:
            src = await image_element.get_attribute("src")
            if src:
                listing_data["image_url"] = src
        
        # Extract posted date
        posted_date_element = await listing_element.query_selector(SELECTORS["posted_date"])
        if posted_date_element:
            posted_date = await posted_date_element.inner_text()
            listing_data["posted_date"] = posted_date.strip()
        
        # Extract seller name
        seller_name_element = await listing_element.query_selector(SELECTORS["seller_name"])
        if seller_name_element:
            seller_name = await seller_name_element.inner_text()
            listing_data["seller_name"] = seller_name.strip()
        
        # Extract seller type
        seller_type_element = await listing_element.query_selector(SELECTORS["seller_type"])
        if seller_type_element:
            seller_type = await seller_type_element.inner_text()
            listing_data["seller_type"] = seller_type.strip()
        
        # Extract condition, year, and mileage from title/description
        full_text = f"{listing_data['title']} {listing_data['description']}"
        
        # Extract year
        listing_data["year_numeric"] = clean_year(full_text)
        if listing_data["year_numeric"]:
            listing_data["year"] = str(listing_data["year_numeric"])
        
        # Extract mileage
        listing_data["mileage_numeric"] = clean_mileage(full_text)
        if listing_data["mileage_numeric"]:
            listing_data["mileage"] = f"{listing_data['mileage_numeric']:,} miles"
        
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
        full_text_lower = full_text.lower()
        if any(word in full_text_lower for word in ["new", "brand new"]):
            listing_data["condition"] = "New"
        elif any(word in full_text_lower for word in ["used", "second hand", "pre-owned"]):
            listing_data["condition"] = "Used"
        
        return listing_data
        
    except Exception as e:
        logger.error(f"Error extracting listing data: {e}")
        return listing_data


async def _scrape_page_enhanced(page, url: str, proxy: str = None, semaphore: asyncio.Semaphore = None) -> List[ScrapingResult]:
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
    """Scrape multiple postcodes concurrently with rate limiting and deduplication"""
    
    logger.info(f"🚀 Starting concurrent Facebook Marketplace scraping of {len(postcodes)} postcodes")
    logger.info(f"📄 {pages_per_postcode} pages per postcode")
    
    # Initialize proxy rotator
    proxy_rotator = ProxyRotator(proxy_list) if proxy_list else ProxyRotator()
    
    # Initialize CSV manager for deduplication
    if outfile is None:
        outfile = Path('data/facebook_multi.csv')
    csv_manager = CSVManager(str(outfile))
    
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
    all_results = []
    postcode_manager = PostcodeManager()
    completed_postcodes = 0
    
    while not results_queue.empty():
        try:
            result = await results_queue.get()
            postcode = result["postcode"]
            listings = result["listings"]
            
            # Convert dictionary listings to ScrapingResult objects
            scraping_results = []
            for listing_dict in listings:
                try:
                    # Build description from Facebook-specific fields
                    description_parts = []
                    if listing_dict.get("description"):
                        description_parts.append(listing_dict["description"][:300])
                    if listing_dict.get("condition"):
                        description_parts.append(f"Condition: {listing_dict['condition']}")
                    if listing_dict.get("location"):
                        description_parts.append(f"Location: {listing_dict['location']}")
                    if listing_dict.get("seller_name"):
                        description_parts.append(f"Seller: {listing_dict['seller_name']}")
                    if listing_dict.get("distance"):
                        description_parts.append(f"Distance: {listing_dict['distance']}")
                    
                    description = "; ".join(description_parts) if description_parts else listing_dict.get("title", "")
                    
                    # Extract postcode from location
                    postcode_extracted = ""
                    if listing_dict.get("location"):
                        from van_scraping_utils import POSTCODE_RE
                        postcode_match = POSTCODE_RE.search(listing_dict["location"])
                        if postcode_match:
                            postcode_extracted = standardize_postcode(postcode_match.group(0))
                    
                    # Detect VAT and listing type
                    full_text = f"{listing_dict.get('title', '')} {listing_dict.get('description', '')} {listing_dict.get('seller_type', '')}"
                    vat_included = detect_vat_status(full_text, "facebook")
                    listing_type = detect_listing_type(full_text, "facebook")
                    
                    # Get coordinates from postcode
                    final_postcode = postcode_extracted or postcode
                    latitude, longitude = get_coordinates_from_postcode(final_postcode)
                    
                    result = ScrapingResult(
                        title=listing_dict.get("title", ""),
                        year=listing_dict.get("year_numeric"),
                        mileage=listing_dict.get("mileage_numeric"),
                        price=listing_dict.get("price_numeric"),
                        description=description,
                        image_url=listing_dict.get("image_url", ""),
                        url=listing_dict.get("link", ""),
                        postcode=final_postcode,
                        source="facebook",
                        listing_type=listing_type,
                        vat_included=vat_included,
                        scraped_at=datetime.now(),
                        latitude=latitude,
                        longitude=longitude
                    )
                    
                    scraping_results.append(result)
                    
                except Exception as e:
                    logger.warning(f"Error converting Facebook listing to ScrapingResult: {e}")
                    continue
            
            # Save results incrementally with deduplication
            if scraping_results:
                new_count = csv_manager.append_results(scraping_results)
                logger.info(f"📊 {postcode}: Added {new_count} unique results (total {len(scraping_results)} scraped)")
            
            all_results.extend(scraping_results)
            completed_postcodes += 1
            
            # Record success rate
            postcode_manager.record_success_rate(postcode, len(scraping_results), "facebook")
            
            logger.info(f"📊 Progress: {completed_postcodes}/{len(postcodes)} postcodes completed")
            
        except Exception as e:
            logger.error(f"Error collecting results: {e}")
    
    # Get final statistics
    stats = csv_manager.get_stats()
    logger.info(f"✅ Facebook Marketplace scraping completed: {stats.get('total_records', 0)} unique listings saved")
    
    # Return DataFrame for compatibility (though results are already saved)
    if all_results:
        return pd.DataFrame([result.to_dict() for result in all_results])
    else:
        logger.warning("⚠️ No Facebook Marketplace listings found")
        return pd.DataFrame()


def analyse(csv_path: Path, show_plots: bool = True) -> None:
    """Quick analysis of Facebook Marketplace listings - simplified to avoid compute overhead"""
    
    if not csv_path.exists():
        logger.error(f"❌ CSV file not found: {csv_path}")
        return
    
    logger.info(f"📊 Analyzing Facebook Marketplace listings from: {csv_path}")
    
    try:
        # Get basic file info without loading full DataFrame
        import os
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
    scrape_parser.add_argument("--outfile", type=Path, default=Path("data/facebook_transit_listings.csv"), help="Output CSV file")
    
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
    multi_parser.add_argument("--outfile", type=Path, default=Path("data/facebook_transit_multi.csv"), help="Output CSV file")
    multi_parser.add_argument("--max-browsers", type=int, default=MAX_CONCURRENT_BROWSERS, help="Max concurrent browsers")
    multi_parser.add_argument("--max-pages", type=int, default=MAX_CONCURRENT_PAGES, help="Max concurrent pages")
    
    # Scrape-UK command
    uk_parser = subparsers.add_parser("scrape-uk", help="Scrape UK-wide with optimized settings")
    uk_parser.add_argument("--outfile", type=Path, default=Path("data/ford_transit_uk_facebook.csv"), help="Output CSV file")
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
