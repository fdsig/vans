#!/usr/bin/env python3
"""
Ford Transit UK-Wide Multi-Source Scraping System (OOP Version)
===============================================================

This script demonstrates the enhanced unified scraping system that combines
ALL available sources to create a comprehensive Ford Transit dataset using
an object-oriented approach with scrapers imported as submodules.

🔗 **SOURCES COMBINED:**
- AutoTrader (get_vans.py) - Premium dealer listings
- CarGurus (scrapers/get_vans_cargurus.py) - Current asking prices  
- eBay (scrapers/get_vans_ebay.py) - Auction and Buy-It-Now listings
- Gumtree (scrapers/get_vans_gumtree.py) - Private seller and trade listings

🎯 **KEY FEATURES:**
- Object-oriented design with scrapers as submodules
- Single unified `data/ford_transit_uk_complete.csv` output file
- Intelligent deduplication across all sources
- Iterative appending of new results (no data loss)
- Shared postcode intelligence and optimization
- **MAXIMUM PARALLEL EXECUTION** optimized for high-RAM machines
- Auto-scaling based on system resources

The system uses the commercial_hubs strategy by default, focusing on areas
with high commercial vehicle activity like:
- Industrial areas
- Commercial zones  
- Business districts
- Transport hubs

**DEDUPLICATION STRATEGY:**
- Primary: URL-based deduplication (most reliable)
- Secondary: Content hash from title + price + mileage + year
- Prevents duplicate listings across all sources

**PERFORMANCE MODES:**
- **TURBO**: Maximum parallelism for 16GB+ RAM, 8+ CPU cores
- **INTENSIVE**: High performance for 8GB+ RAM, 4+ CPU cores  
- **STANDARD**: Optimized defaults with auto-scaling
- **QUICK**: Fast testing mode

Usage Examples:
--------------

1. **Turbo mode (maximum parallelism for high-end machines):**
   python uk_scrape.py --turbo

2. **Standard auto-scaled run (no arguments needed):**
   python uk_scrape.py

3. **Intensive mode:**
   python uk_scrape.py --intensive

4. **Quick test mode:**
   python uk_scrape.py --quick

The resulting CSV will include these columns:
- title: Vehicle title/name
- year: Manufacturing year
- mileage: Vehicle mileage
- price: Listed price in GBP
- description: Detailed vehicle description and specs
- image_url: URL to vehicle image
- url: Link to original listing
- postcode: Search postcode used
- source: Source website (autotrader, cargurus, ebay, gumtree)
- scraped_at: Timestamp when scraped
- age: Calculated vehicle age
- unique_id: Unique identifier for deduplication
"""

import asyncio
import sys
from pathlib import Path
import argparse
import logging
import psutil
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import concurrent.futures
import time

# Import scrapers as submodules
try:
    from scrapers import (
        PostcodeStrategy, 
        PostcodeManager, 
        CSVManager, 
        ScrapingResult,
        UnifiedVanScraper,
        UNIFIED_SCRAPER_AVAILABLE
    )
    
    if not UNIFIED_SCRAPER_AVAILABLE:
        print("⚠️  UnifiedVanScraper not fully available - some dependencies may be missing")
        print("This may affect advanced scraping functionality")
        
except ImportError as e:
    print(f"❌ Failed to import scrapers package: {e}")
    print("Make sure all required files are in the scrapers/ directory")
    print("Try installing requirements: pip install -r requirements.txt")
    sys.exit(1)

# Setup logging
# Ensure logs directory exists
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(logs_dir / 'uk_scrape.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SystemResourcesManager:
    """Manages system resource detection and optimization"""
    
    def __init__(self):
        self.cpu_cores = os.cpu_count()
        self.ram_gb = psutil.virtual_memory().total / (1024**3)
        
    @property
    def system_info(self) -> Dict[str, Any]:
        """Get system resource information"""
        return {
            'cpu_cores': self.cpu_cores,
            'ram_gb': self.ram_gb,
            'is_high_end': self.cpu_cores >= 8 and self.ram_gb >= 16,
            'is_medium_end': self.cpu_cores >= 4 and self.ram_gb >= 8,
            'is_low_end': self.cpu_cores < 4 or self.ram_gb < 8
        }
    
    def calculate_optimal_settings(self, mode: Optional[str] = None) -> Dict[str, Any]:
        """Calculate optimal settings based on system resources and mode"""
        
        if mode == "beast":
            # ULTRA-HIGH performance for 48+ cores, 64GB+ RAM machines
            return {
                'postcode_limit': 200,  # Reduced from 500
                'pages_per_postcode': 8,  # Reduced from 15
                'max_browsers': 8,  # Reduced from 15
                'max_pages': 150,  # Reduced from 300
                'max_parallel': 4,  # Reduced from 10
                'description': 'BEAST mode - High parallelism for server-class machines'
            }
        elif mode == "turbo":
            # Maximum parallelism for high-end machines
            return {
                'postcode_limit': 150,  # Reduced from 300
                'pages_per_postcode': 6,  # Reduced from 12
                'max_browsers': 6,  # Reduced from 10
                'max_pages': 100,  # Reduced from 200
                'max_parallel': 3,  # Reduced from 6
                'description': 'TURBO mode - High parallelism for high-end machines'
            }
        elif mode == "intensive":
            # High performance mode
            return {
                'postcode_limit': 100,  # Reduced from 250
                'pages_per_postcode': 5,  # Reduced from 10
                'max_browsers': 4,  # Reduced from 8
                'max_pages': 80,  # Reduced from 175
                'max_parallel': 3,  # Reduced from 5
                'description': 'INTENSIVE mode - High performance scraping'
            }
        elif mode == "quick":
            # Fast testing
            return {
                'postcode_limit': 10,  # Reduced from 20
                'pages_per_postcode': 2,  # Reduced from 3
                'max_browsers': 2,  # Reduced from 4
                'max_pages': 15,  # Reduced from 30
                'max_parallel': 2,  # Reduced from 3
                'description': 'QUICK TEST mode'
            }
        else:
            # Auto-scaled standard mode based on system resources
            if self.cpu_cores >= 32 and self.ram_gb >= 64:
                # Server-class machine: 64GB+ RAM, 32+ cores
                return {
                    'postcode_limit': 120,  # Reduced from 400
                    'pages_per_postcode': 6,  # Reduced from 12
                    'max_browsers': 6,  # Reduced from 12
                    'max_pages': 100,  # Reduced from 250
                    'max_parallel': 4,  # Reduced from 8
                    'description': f'AUTO-SCALED STANDARD mode (Server-class: {self.cpu_cores} cores, {self.ram_gb:.1f}GB RAM)'
                }
            elif self.system_info['is_high_end']:
                # High-end machine: 16GB+ RAM, 8+ cores
                return {
                    'postcode_limit': 80,  # Reduced from 200
                    'pages_per_postcode': 4,  # Reduced from 8
                    'max_browsers': 4,  # Reduced from 8
                    'max_pages': 60,  # Reduced from 150
                    'max_parallel': 3,  # Reduced from 5
                    'description': f'AUTO-SCALED STANDARD mode (High-end: {self.cpu_cores} cores, {self.ram_gb:.1f}GB RAM)'
                }
            elif self.system_info['is_medium_end']:
                # Medium machine: 8GB+ RAM, 4+ cores
                return {
                    'postcode_limit': 60,  # Reduced from 150
                    'pages_per_postcode': 3,  # Reduced from 6
                    'max_browsers': 3,  # Reduced from 6
                    'max_pages': 50,  # Reduced from 120
                    'max_parallel': 2,  # Reduced from 4
                    'description': f'AUTO-SCALED STANDARD mode (Medium: {self.cpu_cores} cores, {self.ram_gb:.1f}GB RAM)'
                }
            else:
                # Conservative settings for lower-end machines
                return {
                    'postcode_limit': 40,  # Reduced from 100
                    'pages_per_postcode': 2,  # Reduced from 4
                    'max_browsers': 2,  # Reduced from 4
                    'max_pages': 30,  # Reduced from 80
                    'max_parallel': 2,  # Reduced from 3
                    'description': f'AUTO-SCALED STANDARD mode (Conservative: {self.cpu_cores} cores, {self.ram_gb:.1f}GB RAM)'
                }


class UKFordTransitScraper:
    """Main scraper class that orchestrates multi-source Ford Transit scraping"""
    
    def __init__(self, output_file: str = "data/ford_transit_uk_complete.csv"):
        self.output_file = output_file
        self.resource_manager = SystemResourcesManager()
        self.postcode_manager = PostcodeManager()
        self.csv_manager = CSVManager(output_file)
        
        # Ensure data directory exists
        Path("data").mkdir(exist_ok=True)
        
        # Initialize unified scraper
        self.unified_scraper = UnifiedVanScraper(output_file)
    
    def validate_system_requirements(self, mode: str) -> bool:
        """Validate system meets requirements for specified mode"""
        system_info = self.resource_manager.system_info
        
        if mode == "beast":
            if system_info['cpu_cores'] < 32 or system_info['ram_gb'] < 64:
                logger.warning(f"⚠️  WARNING: BEAST mode is optimized for server-class systems (64GB+ RAM, 32+ CPU cores)")
                logger.warning(f"   Your system: {system_info['cpu_cores']} cores, {system_info['ram_gb']:.1f}GB RAM")
                logger.warning("   Consider using --turbo or --intensive mode if performance issues occur")
                return False
            else:
                logger.info(f"🔥 PERFECT! Your {system_info['cpu_cores']}-core, {system_info['ram_gb']:.1f}GB system is ideal for BEAST mode!")
                return True
                
        elif mode == "turbo":
            if not system_info['is_high_end']:
                logger.warning("⚠️  WARNING: TURBO mode is optimized for high-end systems (16GB+ RAM, 8+ CPU cores)")
                logger.warning(f"   Your system: {system_info['cpu_cores']} cores, {system_info['ram_gb']:.1f}GB RAM")
                logger.warning("   Consider using --intensive or standard mode for better performance")
                return False
        
        return True
    
    def print_startup_info(self, mode: Optional[str], settings: Dict[str, Any]):
        """Print startup information and settings"""
        system_info = self.resource_manager.system_info
        
        print("🚐 Starting UK-wide MULTI-SOURCE Ford Transit scraping...")
        print("🔗 Sources: AutoTrader + CarGurus + eBay + Gumtree")
        print("📍 Strategy: Commercial Hubs + Mixed Density areas for maximum coverage")
        print(f"🖥️  System: {system_info['cpu_cores']} CPU cores, {system_info['ram_gb']:.1f}GB RAM")
        print(f"⚡ {settings['description']}")
        print(f"📊 Settings: {settings['postcode_limit']} postcodes, {settings['pages_per_postcode']} pages each, {settings['max_browsers']} browsers, {settings['max_parallel']} parallel")
        
        # Estimate time based on settings
        self._print_time_estimate(mode, system_info)
        
        print("📊 Expected output: data/ford_transit_uk_complete.csv with ALL sources combined")
        print("🔄 Results are appended iteratively with intelligent deduplication")
        print("-" * 80)
    
    def _print_time_estimate(self, mode: Optional[str], system_info: Dict[str, Any]):
        """Print time estimates based on mode and system specs"""
        if mode == "beast":
            print("⏱️  Estimated time: 120-240 minutes (MAXIMUM data collection with ultra-high parallelism)")
        elif mode == "turbo":
            print("⏱️  Estimated time: 90-180 minutes (maximum data collection)")
        elif mode == "intensive":
            print("⏱️  Estimated time: 75-150 minutes (high performance)")
        elif mode == "quick":
            print("⏱️  Estimated time: 10-20 minutes (quick test)")
        else:
            if system_info['cpu_cores'] >= 32 and system_info['ram_gb'] >= 64:
                print("⏱️  Estimated time: 90-150 minutes (auto-scaled for your server-class system)")
            elif system_info['is_high_end']:
                print("⏱️  Estimated time: 60-120 minutes (optimized for your high-end system)")
            else:
                print("⏱️  Estimated time: 45-90 minutes (auto-scaled for your system)")
    
    async def run_scraping(self, mode: Optional[str] = None, sources: List[str] = None) -> bool:
        """Run the unified multi-source scraping operation"""
        
        # Get optimal settings for the mode and system
        settings = self.resource_manager.calculate_optimal_settings(mode)
        
        # Validate system requirements
        if mode in ["beast", "turbo"]:
            self.validate_system_requirements(mode)
        
        # Print startup information
        self.print_startup_info(mode, settings)
        
        # Default sources if none specified
        if sources is None:
            sources = ["autotrader", "cargurus", "ebay", "gumtree"]
        
        try:
            # Create arguments namespace for unified scraper
            args = argparse.Namespace(
                sources=sources,
                postcode_limit=settings['postcode_limit'],
                pages_per_postcode=settings['pages_per_postcode'],
                max_browsers=settings['max_browsers'],
                max_pages=settings['max_pages'],
                max_parallel=settings['max_parallel'],
                include_mixed=True,  # Include mixed density areas for broader coverage
                proxy_file=None,
                quick=(mode == "quick")
            )
            
            # Run the unified scraping
            results = await self.unified_scraper.run_parallel_scraping(args)
            
            # Generate summary report
            self.unified_scraper.generate_summary_report(results)
            
            # Check results and show stats
            success = self._check_results_and_show_stats()
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Multi-source scraping failed: {str(e)}")
            return False
        except KeyboardInterrupt:
            logger.info("⏹️  Scraping interrupted by user")
            return False
    
    def _check_results_and_show_stats(self) -> bool:
        """Check if output file exists and show statistics"""
        output_file = Path(self.output_file)
        
        if output_file.exists():
            print(f"\n✅ Multi-source scraping completed successfully!")
            print(f"📁 Output saved to: {output_file}")
            print(f"📊 File size: {output_file.stat().st_size / (1024*1024):.1f} MB")
            
            # Show basic line count without pandas to avoid EDA overhead
            try:
                with open(output_file, 'r') as f:
                    line_count = sum(1 for _ in f) - 1  # Subtract header
                print(f"📈 Total records: {line_count:,}")
                return True
                    
            except Exception as e:
                logger.warning(f"Could not generate basic statistics: {e}")
                return True
        else:
            logger.error(f"❌ Output file not created: {output_file}")
            return False
    
    def print_success_summary(self, mode: Optional[str]):
        """Print final success summary"""
        print("\n" + "="*80)
        print("🎉 SUCCESS! Your comprehensive Ford Transit dataset is ready!")
        print(f"📁 Check {self.output_file} for all results")
        print("🔄 Run this script again to append more data")
        print("📊 The CSV automatically prevents duplicates across all sources")
        if mode == "turbo":
            print("⚡ TURBO mode completed - Maximum data collection achieved!")
        elif mode == "beast":
            print("🐉 BEAST mode completed - ULTRA-HIGH parallel data collection achieved!")
        print("="*80)
    
    def print_failure_summary(self):
        """Print failure summary with troubleshooting tips"""
        print("\n" + "="*80)
        print("❌ Multi-source scraping encountered issues")
        print("💡 Try running with --quick for a test or check the logs")
        print("="*80)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Ford Transit UK Multi-Source Scraping System (OOP Version) - Optimized for High-Performance Systems")
    
    # Performance modes
    parser.add_argument("--beast", action="store_true",
                       help="BEAST mode: ULTRA-HIGH parallelism for server-class machines (48+ cores, 64GB+ RAM) - 500 postcodes, 15 pages each, 10 parallel scrapers")
    parser.add_argument("--turbo", action="store_true",
                       help="TURBO mode: Maximum parallelism for 16GB+ RAM, 8+ CPU cores (300 postcodes, 12 pages each)")
    parser.add_argument("--intensive", action="store_true",
                       help="INTENSIVE mode: High performance for 8GB+ RAM, 4+ CPU cores (250 postcodes, 10 pages each)")
    parser.add_argument("--quick", action="store_true",
                       help="QUICK mode: Fast testing (20 postcodes, 3 pages each)")
    
    # Output options
    parser.add_argument("--outfile", default="data/ford_transit_uk_complete.csv",
                       help="Output CSV filename (default: data/ford_transit_uk_complete.csv)")
    
    # Source selection
    parser.add_argument("--sources", nargs="+", 
                       choices=["autotrader", "cargurus", "ebay", "gumtree", "facebook"],
                       default=["autotrader", "cargurus", "ebay", "gumtree"],
                       help="Sources to scrape (default: autotrader cargurus ebay gumtree)")
    
    return parser.parse_args()


async def main():
    """Main execution function"""
    args = parse_arguments()
    
    # Determine mode
    mode = None
    if args.beast:
        mode = "beast"
        print("🐉 Running in BEAST mode - ULTRA-HIGH parallelism for server-class machines")
    elif args.turbo:
        mode = "turbo"
        print("🚀 Running in TURBO mode - Maximum parallelism")
    elif args.intensive:
        mode = "intensive"
        print("🔥 Running in INTENSIVE mode - High performance")
    elif args.quick:
        mode = "quick"
        print("⚡ Running in QUICK mode - Fast testing")
    else:
        print("📊 Running in AUTO-SCALED STANDARD mode")
    
    # Ensure output file is in data directory
    outfile = args.outfile
    if not outfile.startswith("data/"):
        outfile = f"data/{outfile}"
    
    # Check if required files exist in the scrapers directory
    required_files = ["scrapers/unified_van_scraper.py", "scrapers/van_scraping_utils.py"]
    for file in required_files:
        if not Path(file).exists():
            print(f"❌ Required file not found: {file}")
            print("Please ensure all scraping files are in the scrapers/ directory")
            sys.exit(1)
    
    # Create and run scraper
    scraper = UKFordTransitScraper(outfile)
    success = await scraper.run_scraping(mode, args.sources)
    
    if success:
        scraper.print_success_summary(mode)
        sys.exit(0)
    else:
        scraper.print_failure_summary()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 
