#!/usr/bin/env python3
"""
Van Scraping Utilities
======================

Shared utilities for all Ford Transit scraping tools to avoid code duplication
and provide consistent functionality across AutoTrader, CarGurus, eBay, 
Gumtree, and Facebook Marketplace scrapers.
"""

import pandas as pd
import sqlite3
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import random
import asyncio
import re
from datetime import datetime

# Setup logging
logger = logging.getLogger(__name__)

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
    population_density: str  # "high", "medium", "low"
    commercial_activity: str  # "high", "medium", "low"
    coordinates: Tuple[float, float]  # (lat, lon)

@dataclass 
class ScrapingResult:
    """Standardized result from any scraping source"""
    title: str
    year: Optional[int]
    mileage: Optional[int] 
    price: Optional[float]
    description: str
    image_url: str
    url: str
    postcode: str
    source: str  # 'autotrader', 'cargurus', 'ebay', 'gumtree', 'facebook'
    scraped_at: datetime
    listing_type: str = "buy_it_now"  # "auction" or "buy_it_now"
    vat_included: Optional[bool] = None  # None if unknown, True if VAT included, False if not
    age: Optional[int] = None
    latitude: Optional[float] = None  # Added latitude field
    longitude: Optional[float] = None  # Added longitude field
    
    def __post_init__(self):
        """Calculate age if year is available"""
        if self.year:
            self.age = datetime.now().year - self.year

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV export"""
        return {
            'title': self.title,
            'year': self.year,
            'mileage': self.mileage,
            'price': self.price,
            'description': self.description,
            'image_url': self.image_url,
            'url': self.url,
            'postcode': self.postcode,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'source': self.source,
            'listing_type': self.listing_type,
            'vat_included': self.vat_included,
            'scraped_at': self.scraped_at.isoformat(),
            'age': self.age,
            'unique_id': self.get_unique_id()
        }

    def get_unique_id(self) -> str:
        """Generate a unique ID for deduplication"""
        # Use URL as primary identifier, fallback to content hash
        if self.url and self.url != "N/A":
            return hashlib.md5(self.url.encode()).hexdigest()
        
        # Create hash from key attributes for better deduplication
        content = f"{self.title}|{self.price}|{self.mileage}|{self.year}|{self.source}"
        return hashlib.md5(content.encode()).hexdigest()

class PostcodeManager:
    """Shared postcode management across all scrapers"""
    
    def __init__(self):
        self.db_path = "data/postcode_intelligence.db"
        self._init_database()
        
        # Comprehensive postcode database with metadata
        self.postcode_areas = [
            # Major Cities - High population density
            PostcodeArea("SW1A", "London", "London", "high", "high", (51.5074, -0.1278)),
            PostcodeArea("M1", "Manchester", "Greater Manchester", "high", "high", (53.4808, -2.2426)),
            PostcodeArea("B1", "Birmingham", "West Midlands", "high", "high", (52.4862, -1.8904)),
            PostcodeArea("G1", "Glasgow", "Scotland", "high", "high", (55.8642, -4.2518)),
            PostcodeArea("LS1", "Leeds", "West Yorkshire", "high", "high", (53.8008, -1.5491)),
            PostcodeArea("EH1", "Edinburgh", "Scotland", "high", "medium", (55.9533, -3.1883)),
            PostcodeArea("L1", "Liverpool", "Merseyside", "high", "high", (53.4084, -2.9916)),
            PostcodeArea("S1", "Sheffield", "South Yorkshire", "high", "high", (53.3811, -1.4701)),
            PostcodeArea("BS1", "Bristol", "Somerset", "high", "high", (51.4545, -2.5879)),
            PostcodeArea("NE1", "Newcastle", "Tyne and Wear", "high", "medium", (54.9783, -1.6178)),
            
            # Commercial/Industrial Hubs
            PostcodeArea("IG1", "Ilford", "Greater London", "high", "high", (51.5590, 0.0819)),
            PostcodeArea("DA1", "Dartford", "Kent", "medium", "high", (51.4461, 0.2056)),
            PostcodeArea("RM1", "Romford", "Greater London", "high", "high", (51.5754, 0.1827)),
            PostcodeArea("UB1", "Southall", "Greater London", "high", "high", (51.5106, -0.3756)),
            PostcodeArea("CR0", "Croydon", "Greater London", "high", "high", (51.3762, -0.0982)),
            PostcodeArea("WD1", "Watford", "Hertfordshire", "medium", "high", (51.6565, -0.3973)),
            PostcodeArea("SL1", "Slough", "Berkshire", "medium", "high", (51.5105, -0.5950)),
            PostcodeArea("MK1", "Milton Keynes", "Buckinghamshire", "medium", "high", (52.0406, -0.7594)),
            PostcodeArea("NN1", "Northampton", "Northamptonshire", "medium", "high", (52.2405, -0.9027)),
            PostcodeArea("CV1", "Coventry", "West Midlands", "medium", "high", (52.4068, -1.5197)),
            
            # Geographic Spread - Regional Centers
            PostcodeArea("TR1", "Truro", "Cornwall", "low", "low", (50.2632, -5.0510)),
            PostcodeArea("EX1", "Exeter", "Devon", "medium", "medium", (50.7184, -3.5339)),
            PostcodeArea("BA1", "Bath", "Somerset", "medium", "low", (51.3758, -2.3599)),
            PostcodeArea("GL1", "Gloucester", "Gloucestershire", "medium", "medium", (51.8642, -2.2382)),
            PostcodeArea("HR1", "Hereford", "Herefordshire", "low", "medium", (52.0567, -2.7150)),
            PostcodeArea("SY1", "Shrewsbury", "Shropshire", "low", "medium", (52.7077, -2.7531)),
            PostcodeArea("ST1", "Stoke-on-Trent", "Staffordshire", "medium", "medium", (53.0027, -2.1794)),
            PostcodeArea("DE1", "Derby", "Derbyshire", "medium", "high", (52.9225, -1.4746)),
            PostcodeArea("NG1", "Nottingham", "Nottinghamshire", "high", "high", (52.9548, -1.1581)),
            PostcodeArea("PE1", "Peterborough", "Cambridgeshire", "medium", "high", (52.5695, -0.2405)),
            
            # Scotland
            PostcodeArea("AB1", "Aberdeen", "Scotland", "medium", "high", (57.1497, -2.0943)),
            PostcodeArea("DD1", "Dundee", "Scotland", "medium", "medium", (56.4620, -2.9707)),
            PostcodeArea("FK1", "Falkirk", "Scotland", "medium", "high", (56.0018, -3.7839)),
            PostcodeArea("KY1", "Kirkcaldy", "Scotland", "medium", "medium", (56.1132, -3.1563)),
            
            # Wales
            PostcodeArea("CF1", "Cardiff", "Wales", "high", "medium", (51.4816, -3.1791)),
            PostcodeArea("SA1", "Swansea", "Wales", "medium", "medium", (51.6214, -3.9436)),
            PostcodeArea("NP1", "Newport", "Wales", "medium", "medium", (51.5842, -2.9977)),
            
            # Northern Ireland
            PostcodeArea("BT1", "Belfast", "Northern Ireland", "high", "medium", (54.5973, -5.9301)),
            
            # Mixed Density Areas
            PostcodeArea("OX1", "Oxford", "Oxfordshire", "medium", "low", (51.7520, -1.2577)),
            PostcodeArea("CB1", "Cambridge", "Cambridgeshire", "medium", "low", (52.2053, 0.1218)),
            PostcodeArea("RG1", "Reading", "Berkshire", "medium", "medium", (51.4543, -0.9781)),
            PostcodeArea("GU1", "Guildford", "Surrey", "medium", "medium", (51.2362, -0.5704)),
            PostcodeArea("ME1", "Rochester", "Kent", "medium", "medium", (51.3886, 0.5041)),
            PostcodeArea("CT1", "Canterbury", "Kent", "medium", "low", (51.2802, 1.0789)),
            PostcodeArea("TN1", "Tunbridge Wells", "Kent", "medium", "low", (51.1328, 0.2634)),
            PostcodeArea("BN1", "Brighton", "East Sussex", "medium", "low", (50.8225, -0.1372)),
            PostcodeArea("PO1", "Portsmouth", "Hampshire", "medium", "medium", (50.8198, -1.0880)),
            PostcodeArea("SO1", "Southampton", "Hampshire", "medium", "high", (50.9097, -1.4044)),
        ]

    def _init_database(self):
        """Initialize SQLite database for tracking scraping success"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS postcode_success (
                postcode TEXT PRIMARY KEY,
                total_listings INTEGER DEFAULT 0,
                total_scrapes INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0.0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scraping_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                postcode TEXT,
                source TEXT,
                listings_found INTEGER,
                pages_scraped INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()

    def get_postcodes(self, 
                     strategy: PostcodeStrategy = PostcodeStrategy.MIXED_DENSITY,
                     limit: int = 50,
                     custom_postcodes: List[str] = None,
                     exclude_used: bool = True,
                     geographic_radius_km: Optional[float] = None,
                     center_postcode: Optional[str] = None) -> List[str]:
        """Get postcodes based on strategy"""
        
        if strategy == PostcodeStrategy.CUSTOM and custom_postcodes:
            return custom_postcodes[:limit]
        
        # Filter by strategy
        areas = self._filter_by_strategy(strategy)
        
        # Geographic filtering if specified
        if center_postcode and geographic_radius_km:
            postcode_list = [area.code for area in areas]
            postcode_list = self._filter_by_geography(postcode_list, center_postcode, geographic_radius_km)
            areas = [area for area in areas if area.code in postcode_list]
        
        # Geographic distribution for better coverage
        if strategy == PostcodeStrategy.GEOGRAPHIC_SPREAD:
            areas = self._select_geographically_distributed(areas)
        
        # Sort by effectiveness
        area_codes = [area.code for area in areas]
        sorted_codes = self._sort_by_effectiveness(area_codes)
        
        # Generate full postcodes and format
        full_postcodes = self._generate_full_postcodes(sorted_codes, limit)
        return self._format_postcodes(full_postcodes)

    def _filter_by_strategy(self, strategy: PostcodeStrategy) -> List[PostcodeArea]:
        """Filter postcode areas by strategy"""
        if strategy == PostcodeStrategy.MAJOR_CITIES:
            return [area for area in self.postcode_areas if area.population_density == "high"]
        elif strategy == PostcodeStrategy.COMMERCIAL_HUBS:
            return [area for area in self.postcode_areas if area.commercial_activity == "high"]
        elif strategy == PostcodeStrategy.MIXED_DENSITY:
            return self.postcode_areas  # Use all areas
        elif strategy == PostcodeStrategy.GEOGRAPHIC_SPREAD:
            return self.postcode_areas  # Use all areas for maximum spread
        else:
            return self.postcode_areas

    def record_success_rate(self, postcode: str, listings_found: int = 0, source: str = "unknown"):
        """Record scraping success for a postcode"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Insert into history
        cursor.execute("""
            INSERT INTO scraping_history (postcode, source, listings_found, pages_scraped)
            VALUES (?, ?, ?, ?)
        """, (postcode, source, listings_found, 1))
        
        # Update aggregated success
        cursor.execute("""
            INSERT OR REPLACE INTO postcode_success 
            (postcode, total_listings, total_scrapes, success_rate, last_updated)
            VALUES (
                ?,
                COALESCE((SELECT total_listings FROM postcode_success WHERE postcode = ?), 0) + ?,
                COALESCE((SELECT total_scrapes FROM postcode_success WHERE postcode = ?), 0) + 1,
                CASE 
                    WHEN (COALESCE((SELECT total_scrapes FROM postcode_success WHERE postcode = ?), 0) + 1) > 0
                    THEN CAST((COALESCE((SELECT total_listings FROM postcode_success WHERE postcode = ?), 0) + ?) AS REAL) / 
                         CAST((COALESCE((SELECT total_scrapes FROM postcode_success WHERE postcode = ?), 0) + 1) AS REAL)
                    ELSE 0.0
                END,
                CURRENT_TIMESTAMP
            )
        """, (postcode, postcode, listings_found, postcode, postcode, postcode, listings_found, postcode))
        
        conn.commit()
        conn.close()

    def _sort_by_effectiveness(self, postcodes: List[str]) -> List[str]:
        """Sort postcodes by historical effectiveness"""
        def effectiveness_score(pc: str) -> float:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT success_rate FROM postcode_success WHERE postcode = ?
            """, (pc,))
            result = cursor.fetchone()
            conn.close()
            
            # Default score for new postcodes
            if not result:
                return 0.5
            return result[0] if result[0] is not None else 0.5
        
        return sorted(postcodes, key=effectiveness_score, reverse=True)

    def _generate_full_postcodes(self, area_codes: List[str], limit: int) -> List[str]:
        """Generate full postcodes from area codes"""
        postcodes = []
        for area_code in area_codes:
            if len(postcodes) >= limit:
                break
                
            # Generate 2-3 full postcodes per area
            variations = [
                f"{area_code} 1AA", f"{area_code} 2BB", f"{area_code} 3CC"
            ]
            for variation in variations:
                if len(postcodes) < limit:
                    postcodes.append(variation)
        
        return postcodes

    def _format_postcodes(self, postcodes: List[str]) -> List[str]:
        """Ensure consistent postcode formatting"""
        formatted = []
        for pc in postcodes:
            # Remove extra spaces and ensure proper format
            pc = re.sub(r'\s+', ' ', pc.strip().upper())
            if re.match(r'^[A-Z]{1,2}\d{1,2}[A-Z]?\s+\d[A-Z]{2}$', pc):
                formatted.append(pc)
        return formatted

class ProxyRotator:
    """Shared proxy rotation for all scrapers"""
    
    def __init__(self, proxy_list: List[str] = None):
        self.proxies = proxy_list or []
        self.failed_proxies = set()
        self.current_index = 0

    def get_next_proxy(self) -> Optional[str]:
        """Get the next working proxy"""
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

class CSVManager:
    """Manages CSV file operations with deduplication"""
    
    def __init__(self, csv_path: str):
        self.csv_path = Path(csv_path)
        self.existing_ids: Set[str] = set()
        self._load_existing_ids()

    def _load_existing_ids(self):
        """Load existing unique IDs from CSV"""
        if self.csv_path.exists():
            try:
                df = pd.read_csv(self.csv_path)
                if 'unique_id' in df.columns:
                    self.existing_ids = set(df['unique_id'].dropna())
                else:
                    # Generate IDs from existing data
                    for _, row in df.iterrows():
                        if 'url' in row and pd.notna(row['url']):
                            unique_id = hashlib.md5(row['url'].encode()).hexdigest()
                            self.existing_ids.add(unique_id)
                        elif all(col in row for col in ['title', 'price', 'mileage', 'year']):
                            content = f"{row['title']}|{row['price']}|{row['mileage']}|{row['year']}"
                            unique_id = hashlib.md5(content.encode()).hexdigest()
                            self.existing_ids.add(unique_id)
                            
                logger.info(f"Loaded {len(self.existing_ids)} existing unique IDs")
            except Exception as e:
                logger.warning(f"Could not load existing IDs: {e}")

    def append_results(self, results: List[ScrapingResult]) -> int:
        """Append new results to CSV, avoiding duplicates"""
        if not results:
            return 0
        
        initial_total = len(self.existing_ids)
            
        new_results = []
        for result in results:
            unique_id = result.get_unique_id()
            if unique_id not in self.existing_ids:
                new_results.append(result)
                self.existing_ids.add(unique_id)
        
        if not new_results:
            logger.info(f"No new unique results to append (checked {len(results)} results)")
            return 0
        
        # Convert to DataFrame
        new_rows = []
        for result in new_results:
            row = result.to_dict()
            row['unique_id'] = result.get_unique_id()
            new_rows.append(row)
        
        new_df = pd.DataFrame(new_rows)
        
        # Append to existing file or create new
        if self.csv_path.exists():
            # Read existing data and append
            existing_df = pd.read_csv(self.csv_path)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            logger.info(f"📈 Appended {len(new_results)} new results to existing CSV")
        else:
            combined_df = new_df
            logger.info(f"📄 Created new CSV with {len(new_results)} results")
        
        # Save back to file
        combined_df.to_csv(self.csv_path, index=False)
        
        # Log progress
        final_total = len(combined_df)
        new_unique = len(new_results)
        total_checked = len(results)
        duplicates_filtered = total_checked - new_unique
        
        logger.info(f"✅ CSV Update Summary:")
        logger.info(f"   • Processed: {total_checked} results")
        logger.info(f"   • New unique: {new_unique}")
        logger.info(f"   • Duplicates filtered: {duplicates_filtered}")
        logger.info(f"   • Total records now: {final_total:,}")
        logger.info(f"   • File: {self.csv_path}")
        
        return len(new_results)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the CSV file"""
        if not self.csv_path.exists():
            return {"total_records": 0}
            
        df = pd.read_csv(self.csv_path)
        stats = {
            "total_records": len(df),
            "unique_sources": df['source'].nunique() if 'source' in df.columns else 0,
            "price_range": {
                "min": df['price'].min() if 'price' in df.columns else None,
                "max": df['price'].max() if 'price' in df.columns else None,
                "median": df['price'].median() if 'price' in df.columns else None
            },
            "year_range": {
                "min": df['year'].min() if 'year' in df.columns else None,
                "max": df['year'].max() if 'year' in df.columns else None
            }
        }
        
        if 'source' in df.columns:
            stats['source_breakdown'] = df['source'].value_counts().to_dict()
            
        return stats

def human_delay(min_seconds: float = 1.0, max_seconds: float = 3.0):
    """Generate human-like random delay"""
    import time
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)

async def async_human_delay(min_seconds: float = 1.0, max_seconds: float = 3.0):
    """Generate human-like random delay (async version)"""
    delay = random.uniform(min_seconds, max_seconds)
    await asyncio.sleep(delay)

def clean_price(price_text: str) -> Optional[float]:
    """Extract and clean price from text"""
    if not price_text:
        return None
        
    # Remove common prefixes and suffixes
    price_text = re.sub(r'(from|starting|price|£|,|\+|\s)', '', price_text.lower())
    
    # Extract numeric value
    match = re.search(r'(\d+(?:\.\d{2})?)', price_text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    
    return None

def clean_mileage(mileage_text: str) -> Optional[int]:
    """Extract and clean mileage from text"""
    if not mileage_text:
        return None
        
    # Remove common suffixes and clean
    mileage_text = re.sub(r'(miles?|mileage|,|\s)', '', mileage_text.lower())
    
    # Extract numeric value
    match = re.search(r'(\d+)', mileage_text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    
    return None

def clean_year(year_text: str) -> Optional[int]:
    """Extract and clean year from text"""
    if not year_text:
        return None
        
    # Look for 4-digit year
    match = re.search(r'\b(19|20)\d{2}\b', str(year_text))
    if match:
        try:
            year = int(match.group(0))
            # Reasonable bounds for vehicle years
            if 1990 <= year <= datetime.now().year + 1:
                return year
        except ValueError:
            pass
    
    return None

def detect_vat_status(text: str, source: str) -> Optional[bool]:
    """Detect VAT inclusion status from listing text"""
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Explicit VAT exclusion indicators
    vat_excluded_patterns = [
        r'\bno\s*vat\b',
        r'\bex\s*vat\b', 
        r'\bexcluding\s*vat\b',
        r'\bplus\s*vat\b',
        r'\bvat\s*exempt\b',
        r'\bvat\s*not\s*included\b'
    ]
    
    # Explicit VAT inclusion indicators  
    vat_included_patterns = [
        r'\binc\s*vat\b',
        r'\bincluding\s*vat\b',
        r'\bvat\s*included\b',
        r'\bwith\s*vat\b'
    ]
    
    # Check for explicit exclusion first
    for pattern in vat_excluded_patterns:
        if re.search(pattern, text_lower):
            return False
    
    # Check for explicit inclusion
    for pattern in vat_included_patterns:
        if re.search(pattern, text_lower):
            return True
    
    # Source-specific defaults
    if source == "autotrader":
        # AutoTrader assumption: VAT not included unless explicitly stated
        return False
    elif source == "ebay":
        # eBay private sellers typically don't charge VAT
        if any(term in text_lower for term in ['private', 'collection only', 'no warranty']):
            return False
        # Dealers typically include VAT
        return None  # Unknown
    
    # Default: unknown
    return None

def detect_listing_type(text: str, source: str) -> str:
    """Detect if listing is auction or buy-it-now"""
    if not text:
        return "buy_it_now"
    
    text_lower = text.lower()
    
    # Auction indicators
    auction_indicators = [
        r'\bauction\b',
        r'\bbidding\b', 
        r'\bbids?\b',
        r'\btime\s*left\b',
        r'\bending\s*soon\b',
        r'\bhighest\s*bid\b'
    ]
    
    # Buy-it-now indicators
    buy_now_indicators = [
        r'\bbuy\s*it\s*now\b',
        r'\bfixed\s*price\b',
        r'\bbuy\s*now\b',
        r'\bimmediate\s*purchase\b'
    ]
    
    # Check for auction indicators
    for pattern in auction_indicators:
        if re.search(pattern, text_lower):
            return "auction"
    
    # Check for buy-it-now indicators  
    for pattern in buy_now_indicators:
        if re.search(pattern, text_lower):
            return "buy_it_now"
    
    # Source-specific defaults
    if source == "ebay":
        return "buy_it_now"  # Most eBay listings are buy-it-now these days
    
    # All other sources default to buy-it-now
    return "buy_it_now"

def standardize_postcode(postcode: str) -> str:
    """Standardize postcode format"""
    if not postcode:
        return ""
        
    # Remove extra spaces and ensure proper format
    postcode = re.sub(r'\s+', ' ', postcode.strip().upper())
    
    # Ensure space before last 3 characters if not present
    if re.match(r'^[A-Z]{1,2}\d{1,2}[A-Z]?\d[A-Z]{2}$', postcode):
        postcode = postcode[:-3] + ' ' + postcode[-3:]
    
    return postcode

def get_coordinates_from_postcode(postcode: str, postcode_manager: Optional['PostcodeManager'] = None) -> Tuple[Optional[float], Optional[float]]:
    """
    Get latitude and longitude coordinates from a postcode.
    
    Args:
        postcode: The postcode to geocode
        postcode_manager: Optional PostcodeManager instance for cached lookups
    
    Returns:
        Tuple of (latitude, longitude) or (None, None) if not found
    """
    if not postcode:
        return None, None
    
    # Standardize the postcode
    clean_postcode = standardize_postcode(postcode)
    
    # If we have a PostcodeManager, try to find exact or area match first
    if postcode_manager:
        # Extract postcode area (first part before space)
        postcode_area = clean_postcode.split()[0] if ' ' in clean_postcode else clean_postcode[:2]
        
        # Look for exact match in our postcode areas
        for area in postcode_manager.postcode_areas:
            if area.code == postcode_area:
                return area.coordinates
    
    # Fallback: Use a comprehensive UK postcode coordinate lookup
    # This is a simplified version - in production you might use a proper geocoding API
    postcode_coordinates = {
        # London areas
        'SW1': (51.4944, -0.1406), 'SW1A': (51.4944, -0.1406), 'SW1B': (51.4944, -0.1406),
        'SW1C': (51.4944, -0.1406), 'SW1D': (51.4944, -0.1406), 'SW1E': (51.4944, -0.1406),
        'W1': (51.5177, -0.1536), 'WC1': (51.5203, -0.1241), 'WC2': (51.5125, -0.1243),
        'EC1': (51.5188, -0.1003), 'EC2': (51.5155, -0.0922), 'EC3': (51.5118, -0.0823),
        'EC4': (51.5129, -0.1003), 'E1': (51.5149, -0.0718), 'E2': (51.5306, -0.0550),
        'N1': (51.5362, -0.1031), 'N2': (51.5794, -0.1615), 'SE1': (51.5045, -0.0865),
        'SE2': (51.4881, 0.1764), 'NW1': (51.5341, -0.1421), 'NW2': (51.5594, -0.2150),
        
        # Manchester
        'M1': (53.4808, -2.2426), 'M2': (53.4793, -2.2446), 'M3': (53.4859, -2.2549),
        'M4': (53.4730, -2.2284), 'M5': (53.4691, -2.2749), 'M6': (53.4969, -2.2930),
        
        # Birmingham
        'B1': (52.4862, -1.8904), 'B2': (52.4796, -1.9026), 'B3': (52.4886, -1.9026),
        'B4': (52.4796, -1.8904), 'B5': (52.4886, -1.9148), 'B6': (52.4976, -1.8904),
        
        # Glasgow
        'G1': (55.8642, -4.2518), 'G2': (55.8567, -4.2763), 'G3': (55.8687, -4.2923),
        'G4': (55.8737, -4.2518), 'G5': (55.8492, -4.2518),
        
        # Leeds
        'LS1': (53.8008, -1.5491), 'LS2': (53.8003, -1.5591), 'LS3': (53.8143, -1.5791),
        'LS4': (53.8243, -1.5591), 'LS5': (53.8343, -1.5791),
        
        # Edinburgh
        'EH1': (55.9533, -3.1883), 'EH2': (55.9533, -3.2083), 'EH3': (55.9433, -3.2183),
        'EH4': (55.9733, -3.2283), 'EH5': (55.9833, -3.1783),
        
        # Liverpool
        'L1': (53.4084, -2.9916), 'L2': (53.4084, -3.0016), 'L3': (53.4184, -2.9716),
        'L4': (53.4284, -2.9816), 'L5': (53.4384, -2.9916),
        
        # Sheffield
        'S1': (53.3811, -1.4701), 'S2': (53.3711, -1.4801), 'S3': (53.3911, -1.4901),
        'S4': (53.4011, -1.4601), 'S5': (53.4111, -1.4701),
        
        # Bristol
        'BS1': (51.4545, -2.5879), 'BS2': (51.4645, -2.5779), 'BS3': (51.4445, -2.6079),
        'BS4': (51.4345, -2.5779), 'BS5': (51.4745, -2.5679),
        
        # Newcastle
        'NE1': (54.9783, -1.6178), 'NE2': (54.9883, -1.6278), 'NE3': (54.9983, -1.6078),
        'NE4': (54.9683, -1.6378), 'NE5': (54.9583, -1.6178),
        
        # Cardiff
        'CF1': (51.4816, -3.1791), 'CF2': (51.4916, -3.1891), 'CF3': (51.4716, -3.1691),
        'CF4': (51.4616, -3.1891), 'CF5': (51.5016, -3.1691),
        
        # Belfast
        'BT1': (54.5973, -5.9301), 'BT2': (54.6073, -5.9201), 'BT3': (54.6173, -5.9101),
        'BT4': (54.5873, -5.9401), 'BT5': (54.5773, -5.9501),
        
        # Other major areas
        'OX1': (51.7520, -1.2577), 'CB1': (52.2053, 0.1218), 'RG1': (51.4543, -0.9781),
        'GU1': (51.2362, -0.5704), 'ME1': (51.3886, 0.5041), 'CT1': (51.2802, 1.0789),
        'TN1': (51.1328, 0.2634), 'BN1': (50.8225, -0.1372), 'PO1': (50.8198, -1.0880),
        'SO1': (50.9097, -1.4044), 'TR1': (50.2632, -5.0510), 'EX1': (50.7184, -3.5339),
        'BA1': (51.3758, -2.3599), 'GL1': (51.8642, -2.2382), 'HR1': (52.0567, -2.7150),
        'SY1': (52.7077, -2.7531), 'ST1': (53.0027, -2.1794), 'DE1': (52.9225, -1.4746),
        'NG1': (52.9548, -1.1581), 'PE1': (52.5695, -0.2405), 'AB1': (57.1497, -2.0943),
        'DD1': (56.4620, -2.9707), 'FK1': (56.0018, -3.7839), 'KY1': (56.1132, -3.1563),
        'SA1': (51.6214, -3.9436), 'NP1': (51.5842, -2.9977),
        
        # Commercial hubs
        'IG1': (51.5590, 0.0819), 'DA1': (51.4461, 0.2056), 'RM1': (51.5754, 0.1827),
        'UB1': (51.5106, -0.3756), 'CR0': (51.3762, -0.0982), 'WD1': (51.6565, -0.3973),
        'SL1': (51.5105, -0.5950), 'MK1': (52.0406, -0.7594), 'NN1': (52.2405, -0.9027),
        'CV1': (52.4068, -1.5197),
    }
    
    # Try to find exact area match
    area_code = clean_postcode.split()[0] if ' ' in clean_postcode else clean_postcode[:2]
    
    if area_code in postcode_coordinates:
        return postcode_coordinates[area_code]
    
    # Try broader area match (first 1-2 letters)
    broad_area = clean_postcode[:2] if len(clean_postcode) >= 2 else clean_postcode
    if broad_area in postcode_coordinates:
        return postcode_coordinates[broad_area]
    
    # Try single letter area
    if len(clean_postcode) >= 1:
        single_area = clean_postcode[0]
        single_letter_areas = {
            'B': (52.4862, -1.8904),  # Birmingham
            'M': (53.4808, -2.2426),  # Manchester
            'L': (53.4084, -2.9916),  # Liverpool
            'S': (53.3811, -1.4701),  # Sheffield
            'G': (55.8642, -4.2518),  # Glasgow
            'E': (51.5149, -0.0718),  # East London
            'N': (51.5362, -0.1031),  # North London
            'W': (51.5177, -0.1536),  # West London
        }
        if single_area in single_letter_areas:
            return single_letter_areas[single_area]
    
    logger.warning(f"Could not find coordinates for postcode: {postcode}")
    return None, None
