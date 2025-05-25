#!/usr/bin/env python3
"""
Ford Transit UK-Wide Multi-Source Scraping Demo
===============================================

This script demonstrates the enhanced unified scraping system that combines
ALL available sources to create a comprehensive Ford Transit dataset:

🔗 **SOURCES COMBINED:**
- AutoTrader (get_vans.py) - Premium dealer listings
- CarGurus (get_vans_cargurus.py) - Current asking prices  
- eBay (get_vans_ebay.py) - Auction and Buy-It-Now listings
- Gumtree (get_vans_gumtree.py) - Private seller and trade listings
- Facebook Marketplace (get_vans_facebook.py) - Social marketplace listings

🎯 **KEY FEATURES:**
- Single unified `ford_transit_uk_complete.csv` output file
- Intelligent deduplication across all sources
- Iterative appending of new results (no data loss)
- Shared postcode intelligence and optimization
- Parallel execution for maximum efficiency

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

Usage Examples:
--------------

1. **Full UK-wide multi-source scraping:**
   python uk_scrape_demo.py

2. **Enhanced coverage with mixed areas:**
   python uk_scrape_demo.py --include-mixed --postcode-limit 150

3. **High-performance scraping with proxies:**
   python uk_scrape_demo.py --proxy-file proxies.txt --max-parallel 5

4. **Specific sources only:**
   python uk_scrape_demo.py --sources autotrader cargurus ebay

5. **Quick test with all sources:**
   python uk_scrape_demo.py --quick

The resulting CSV will include these columns:
- title: Vehicle title/name
- year: Manufacturing year
- mileage: Vehicle mileage
- price: Listed price in GBP
- description: Detailed vehicle description and specs
- image_url: URL to vehicle image
- url: Link to original listing
- postcode: Search postcode used
- source: Source website (autotrader, cargurus, ebay, gumtree, facebook)
- scraped_at: Timestamp when scraped
- age: Calculated vehicle age
- unique_id: Unique identifier for deduplication
"""

import subprocess
import sys
from pathlib import Path
import argparse
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_unified_scrape(custom_args=None):
    """Run the unified multi-source scraping"""
    
    # Base command for unified scraper
    base_command = [
        sys.executable, "unified_van_scraper.py",
        "--postcode-limit", "100",
        "--pages-per-postcode", "5", 
        "--max-browsers", "5",
        "--max-pages", "50",
        "--max-parallel", "3",
        "--outfile", "ford_transit_uk_complete.csv"
    ]
    
    if custom_args:
        base_command.extend(custom_args)
    
    print("🚐 Starting UK-wide MULTI-SOURCE Ford Transit scraping...")
    print("🔗 Sources: AutoTrader + CarGurus + eBay + Gumtree + Facebook")
    print(f"📋 Command: {' '.join(base_command)}")
    print("⏱️  This may take 60-120 minutes depending on your settings")
    print("📊 Expected output: ford_transit_uk_complete.csv with ALL sources combined")
    print("🔄 Results are appended iteratively with intelligent deduplication")
    print("-" * 80)
    
    try:
        result = subprocess.run(base_command, check=True, capture_output=False)
        print("\n✅ Multi-source scraping completed successfully!")
        
        # Check if output file exists and show stats
        output_file = Path("ford_transit_uk_complete.csv")
        if output_file.exists():
            print(f"📁 Output saved to: {output_file}")
            print(f"📊 File size: {output_file.stat().st_size / (1024*1024):.1f} MB")
            
            # Try to show quick stats
            try:
                import pandas as pd
                df = pd.read_csv(output_file)
                print(f"📈 Total records: {len(df):,}")
                
                if 'source' in df.columns:
                    print("📊 Records by source:")
                    source_counts = df['source'].value_counts()
                    for source, count in source_counts.items():
                        print(f"   • {source}: {count:,} records")
                
                if 'price' in df.columns:
                    print(f"💰 Price range: £{df['price'].min():,.0f} - £{df['price'].max():,.0f}")
                    print(f"💰 Median price: £{df['price'].median():,.0f}")
                    
            except ImportError:
                logger.info("Install pandas for detailed statistics")
            except Exception as e:
                logger.warning(f"Could not generate statistics: {e}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Multi-source scraping failed with exit code: {e.returncode}")
        return False
    except KeyboardInterrupt:
        print(f"\n⏹️  Scraping interrupted by user")
        return False
    except FileNotFoundError:
        print(f"\n❌ unified_van_scraper.py not found! Please ensure it exists in the current directory.")
        return False

def main():
    parser = argparse.ArgumentParser(description="Ford Transit UK Multi-Source Scraping Demo")
    
    # Source selection
    parser.add_argument("--sources", nargs='+', 
                       choices=['autotrader', 'cargurus', 'ebay', 'gumtree', 'facebook'],
                       help="Specific sources to scrape (default: all)")
    
    # Coverage options
    parser.add_argument("--include-mixed", action="store_true",
                       help="Include mixed density areas for broader coverage")
    parser.add_argument("--proxy-file", help="Path to proxy file")
    parser.add_argument("--outfile", default="ford_transit_uk_complete.csv",
                       help="Output CSV filename")
    
    # Scraping intensity
    parser.add_argument("--postcode-limit", type=int, default=100,
                       help="Number of postcodes per source")
    parser.add_argument("--pages-per-postcode", type=int, default=5,
                       help="Pages to scrape per postcode")
    parser.add_argument("--max-browsers", type=int, default=5,
                       help="Maximum concurrent browsers per source")
    parser.add_argument("--max-pages", type=int, default=50,
                       help="Maximum total pages per source")
    
    # Parallel execution
    parser.add_argument("--max-parallel", type=int, default=3,
                       help="Maximum scrapers to run simultaneously")
    
    # Test modes
    parser.add_argument("--quick", action="store_true",
                       help="Quick test with reduced settings")
    parser.add_argument("--intensive", action="store_true",
                       help="Intensive scraping with maximum settings")
    
    args = parser.parse_args()
    
    # Build custom arguments for unified scraper
    custom_args = ["--outfile", args.outfile]
    
    if args.sources:
        custom_args.extend(["--sources"] + args.sources)
    
    if args.include_mixed:
        custom_args.append("--include-mixed")
    
    if args.proxy_file:
        custom_args.extend(["--proxy-file", args.proxy_file])
    
    custom_args.extend(["--max-parallel", str(args.max_parallel)])
    
    if args.quick:
        # Quick test settings
        custom_args.extend([
            "--postcode-limit", "10",
            "--pages-per-postcode", "2",
            "--max-browsers", "2",
            "--max-pages", "10",
            "--quick"
        ])
        print("🚀 Running in QUICK TEST mode")
        
    elif args.intensive:
        # Intensive settings for maximum data collection
        custom_args.extend([
            "--postcode-limit", "200",
            "--pages-per-postcode", "10",
            "--max-browsers", "8",
            "--max-pages", "100",
            "--max-parallel", "5"
        ])
        print("🔥 Running in INTENSIVE mode - maximum data collection")
        
    else:
        # Standard settings
        custom_args.extend([
            "--postcode-limit", str(args.postcode_limit),
            "--pages-per-postcode", str(args.pages_per_postcode),
            "--max-browsers", str(args.max_browsers),
            "--max-pages", str(args.max_pages)
        ])
    
    # Check if required files exist
    required_files = ["unified_van_scraper.py", "van_scraping_utils.py"]
    for file in required_files:
        if not Path(file).exists():
            print(f"❌ Required file not found: {file}")
            print("Please ensure all scraping files are in the current directory")
            sys.exit(1)
    
    success = run_unified_scrape(custom_args)
    
    if success:
        print("\n" + "="*80)
        print("🎉 SUCCESS! Your comprehensive Ford Transit dataset is ready!")
        print("📁 Check ford_transit_uk_complete.csv for all results")
        print("🔄 Run this script again to append more data")
        print("📊 The CSV automatically prevents duplicates across all sources")
        print("="*80)
        sys.exit(0)
    else:
        print("\n" + "="*80)
        print("❌ Multi-source scraping encountered issues")
        print("💡 Try running with --quick for a test or check the logs")
        print("="*80)
        sys.exit(1)

if __name__ == "__main__":
    main() 
