"""
Scrapers Package
================

Ford Transit van scraping utilities and scrapers for multiple sources.

Main components:
- UnifiedVanScraper: Orchestrates scraping across all sources
- van_scraping_utils: Shared utilities and data classes
- Individual scrapers for AutoTrader, CarGurus, eBay, Gumtree, Facebook
"""

from .van_scraping_utils import (
    PostcodeStrategy, 
    PostcodeManager, 
    ProxyRotator, 
    CSVManager,
    ScrapingResult,
    PostcodeArea,
    clean_price,
    clean_mileage, 
    clean_year,
    standardize_postcode,
    human_delay,
    async_human_delay
)

# Import UnifiedVanScraper with better error handling
try:
    from .unified_van_scraper import UnifiedVanScraper
    UNIFIED_SCRAPER_AVAILABLE = True
except ImportError as import_error:
    # Create a dummy class for when dependencies aren't available
    import warnings
    warnings.warn(f"UnifiedVanScraper not available: {import_error}")
    
    class UnifiedVanScraper:
        def __init__(self, *args, **kwargs):
            raise ImportError(f"UnifiedVanScraper dependencies not available: {import_error}")
    
    UNIFIED_SCRAPER_AVAILABLE = False

__all__ = [
    'PostcodeStrategy',
    'PostcodeManager', 
    'ProxyRotator',
    'CSVManager',
    'ScrapingResult',
    'PostcodeArea',
    'UnifiedVanScraper',
    'clean_price',
    'clean_mileage',
    'clean_year', 
    'standardize_postcode',
    'human_delay',
    'async_human_delay',
    'UNIFIED_SCRAPER_AVAILABLE'
] 
