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
    age: Optional[int] = None
    
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
            'source': self.source,
            'scraped_at': self.scraped_at.isoformat(),
            'age': self.age
        }

    def get_unique_id(self) -> str:
        """Generate a unique ID for deduplication"""
        # Use URL as primary identifier, fallback to content hash
        if self.url:
            return hashlib.md5(self.url.encode()).hexdigest()
        
        # Create hash from key attributes
        content = f"{self.title}|{self.price}|{self.mileage}|{self.year}"
        return hashlib.md5(content.encode()).hexdigest()

class PostcodeManager:
    """Shared postcode management across all scrapers"""
    
    def __init__(self):
        self.db_path = "postcode_intelligence.db"
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

    def record_success_rate(self, postcode: str, source: str, listings_found: int, pages_scraped: int = 1):
        """Record scraping success for a postcode and source"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Insert into history
        cursor.execute("""
            INSERT INTO scraping_history (postcode, source, listings_found, pages_scraped)
            VALUES (?, ?, ?, ?)
        """, (postcode, source, listings_found, pages_scraped))
        
        # Update aggregated success
        cursor.execute("""
            INSERT OR REPLACE INTO postcode_success 
            (postcode, total_listings, total_scrapes, success_rate, last_updated)
            VALUES (
                ?,
                COALESCE((SELECT total_listings FROM postcode_success WHERE postcode = ?), 0) + ?,
                COALESCE((SELECT total_scrapes FROM postcode_success WHERE postcode = ?), 0) + ?,
                CAST(? AS REAL) / CAST(? AS REAL),
                CURRENT_TIMESTAMP
            )
        """, (postcode, postcode, listings_found, postcode, pages_scraped, 
              listings_found, pages_scraped))
        
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
            
        new_results = []
        for result in results:
            unique_id = result.get_unique_id()
            if unique_id not in self.existing_ids:
                new_results.append(result)
                self.existing_ids.add(unique_id)
        
        if not new_results:
            logger.info("No new unique results to append")
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
        else:
            combined_df = new_df
        
        # Save back to file
        combined_df.to_csv(self.csv_path, index=False)
        logger.info(f"Appended {len(new_results)} new results to {self.csv_path}")
        
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
