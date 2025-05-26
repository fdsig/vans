#!/usr/bin/env python3
"""
Unified Ford Transit Multi-Source Scraper
=========================================

This script orchestrates scraping from all available sources:
- AutoTrader (get_vans.py)
- CarGurus (get_vans_cargurus.py)  
- eBay (get_vans_ebay.py)
- Gumtree (get_vans_gumtree.py)
- Facebook Marketplace (get_vans_facebook.py)

Results are appended to a single ford_transit_uk_complete.csv file
with deduplication to ensure no repeated listings.
"""

import asyncio
import subprocess
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
import concurrent.futures
import time

from .van_scraping_utils import (
    PostcodeStrategy, PostcodeManager, ProxyRotator, CSVManager,
    ScrapingResult, clean_price, clean_mileage, clean_year, 
    standardize_postcode
)

# Setup logging
# Ensure logs directory exists
logs_dir = Path("../logs")
logs_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(logs_dir / 'unified_scraping.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class UnifiedVanScraper:
    """Unified scraper that coordinates multiple sources"""
    
    def __init__(self, output_file: str = "data/ford_transit_uk_complete.csv"):
        self.output_file = output_file
        self.csv_manager = CSVManager(output_file)
        self.postcode_manager = PostcodeManager()
        
        # Available scrapers with their command configurations
        self.scrapers = {
            'autotrader': {
                'script': 'get_vans.py',
                'command': 'scrape-uk',
                'source_name': 'autotrader'
            },
            'cargurus': {
                'script': 'scrapers/get_vans_cargurus.py', 
                'command': 'scrape-uk',
                'source_name': 'cargurus'
            },
            'ebay': {
                'script': 'scrapers/get_vans_ebay.py',
                'command': 'scrape-uk', 
                'source_name': 'ebay'
            },
            'gumtree': {
                'script': 'scrapers/get_vans_gumtree.py',
                'command': 'scrape-uk',
                'source_name': 'gumtree'
            },
            'facebook': {
                'script': 'scrapers/get_vans_facebook.py',
                'command': 'scrape-uk',
                'source_name': 'facebook'
            }
        }

    def build_scraper_command(self, scraper_config: Dict[str, str], args: argparse.Namespace) -> List[str]:
        """Build command for individual scraper"""
        base_cmd = [sys.executable, scraper_config['script'], scraper_config['command']]
        
        # Save to temporary file first
        temp_output = f"data/temp_{scraper_config['source_name']}_results.csv"
        base_cmd.extend(['--outfile', temp_output])
        
        # Add common arguments
        if args.postcode_limit:
            base_cmd.extend(['--postcode-limit', str(args.postcode_limit)])
        if args.pages_per_postcode:
            base_cmd.extend(['--pages-per-postcode', str(args.pages_per_postcode)])
        if args.max_browsers:
            base_cmd.extend(['--max-browsers', str(args.max_browsers)])
        if args.max_pages:
            base_cmd.extend(['--max-pages', str(args.max_pages)])
        if args.include_mixed:
            base_cmd.append('--include-mixed')
        if args.proxy_file and Path(args.proxy_file).exists():
            base_cmd.extend(['--proxy-file', args.proxy_file])
            
        return base_cmd

    def run_scraper(self, scraper_name: str, command: List[str], timeout: int = 3600) -> Dict[str, Any]:
        """Run a single scraper and return results"""
        logger.info(f"🚀 Starting {scraper_name} scraper...")
        start_time = time.time()
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            elapsed = time.time() - start_time
            
            if result.returncode == 0:
                logger.info(f"✅ {scraper_name} completed successfully in {elapsed:.1f}s")
                return {
                    'scraper': scraper_name,
                    'success': True,
                    'elapsed': elapsed,
                    'output': result.stdout,
                    'error': None
                }
            else:
                logger.error(f"❌ {scraper_name} failed: {result.stderr}")
                return {
                    'scraper': scraper_name,
                    'success': False,
                    'elapsed': elapsed,
                    'output': result.stdout,
                    'error': result.stderr
                }
                
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ {scraper_name} timed out after {timeout}s")
            return {
                'scraper': scraper_name,
                'success': False,
                'elapsed': timeout,
                'output': None,
                'error': 'Timeout'
            }
        except Exception as e:
            logger.error(f"💥 {scraper_name} crashed: {str(e)}")
            return {
                'scraper': scraper_name,
                'success': False,
                'elapsed': time.time() - start_time,
                'output': None,
                'error': str(e)
            }

    def process_scraper_results(self, scraper_name: str, temp_file: str) -> int:
        """Process results from a scraper and append to unified CSV"""
        temp_path = Path(temp_file)
        
        if not temp_path.exists():
            logger.warning(f"No results file found for {scraper_name}: {temp_file}")
            return 0
            
        try:
            # Read the scraper's output
            df = pd.read_csv(temp_path)
            logger.info(f"📊 {scraper_name} produced {len(df)} raw results")
            
            if df.empty:
                logger.info(f"No results from {scraper_name}")
                return 0
            
            # Convert to standardized format
            scraping_results = []
            for _, row in df.iterrows():
                try:
                    # Build description from available fields
                    description_parts = []
                    if pd.notna(row.get('description', '')) and str(row.get('description', '')).strip():
                        description_parts.append(str(row.get('description', '')).strip())
                    
                    # Add condition if available
                    if pd.notna(row.get('condition', '')) and str(row.get('condition', '')).strip():
                        description_parts.append(f"Condition: {str(row.get('condition', '')).strip()}")
                    
                    # Add location if available  
                    if pd.notna(row.get('location', '')) and str(row.get('location', '')).strip():
                        description_parts.append(f"Location: {str(row.get('location', '')).strip()}")
                    
                    description = "; ".join(description_parts) if description_parts else str(row.get('title', ''))
                    
                    # Detect listing type and VAT status from description and other fields
                    full_text = f"{description} {str(row.get('title', ''))}"
                    listing_type = row.get('listing_type', 'buy_it_now')
                    if listing_type not in ['auction', 'buy_it_now']:
                        from .van_scraping_utils import detect_listing_type
                        listing_type = detect_listing_type(full_text, scraper_name)
                    
                    vat_included = row.get('vat_included')
                    if pd.isna(vat_included):
                        from .van_scraping_utils import detect_vat_status
                        vat_included = detect_vat_status(full_text, scraper_name)
                    
                    # Get coordinates from postcode
                    postcode = standardize_postcode(str(row.get('postcode', '')))
                    from .van_scraping_utils import get_coordinates_from_postcode
                    latitude, longitude = get_coordinates_from_postcode(postcode, self.postcode_manager)
                    
                    result = ScrapingResult(
                        title=str(row.get('title', '')),
                        year=clean_year(str(row.get('year', ''))),
                        mileage=clean_mileage(str(row.get('mileage', ''))),
                        price=clean_price(str(row.get('price', ''))),
                        description=description,
                        image_url=str(row.get('image_url', '')),
                        url=str(row.get('url', '')),
                        postcode=postcode,
                        source=scraper_name,
                        listing_type=listing_type,
                        vat_included=vat_included,
                        scraped_at=datetime.now(),
                        latitude=latitude,
                        longitude=longitude
                    )
                    scraping_results.append(result)
                    
                except Exception as e:
                    logger.warning(f"Error processing row from {scraper_name}: {e}")
                    continue
            
            # Append to unified CSV with deduplication
            new_count = self.csv_manager.append_results(scraping_results)
            logger.info(f"✅ {scraper_name}: Added {new_count} unique results to unified CSV")
            
            # Record success rate for postcode intelligence
            for postcode in df['postcode'].dropna().unique():
                postcode_count = len(df[df['postcode'] == postcode])
                self.postcode_manager.record_success_rate(
                    standardize_postcode(str(postcode)),
                    postcode_count,
                    scraper_name
                )
            
            # Keep the temp file as a subset but rename it for clarity
            subset_file = f"data/{scraper_name}_subset_results.csv"
            if temp_path.exists():
                import shutil
                shutil.copy2(temp_path, subset_file)
                logger.info(f"📁 Preserved {scraper_name} subset results: {subset_file}")
                
                # Clean up the temp file only after copying
                temp_path.unlink()
            
            return new_count
            
        except Exception as e:
            logger.error(f"Error processing results from {scraper_name}: {e}")
            return 0

    async def run_parallel_scraping(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Run multiple scrapers in parallel"""
        
        # Determine which scrapers to use
        scrapers_to_run = args.sources if args.sources else list(self.scrapers.keys())
        
        # Set default timeout if not provided
        timeout = getattr(args, 'timeout', 3600)  # Default 1 hour timeout
        
        logger.info(f"🎯 Starting unified scraping with sources: {', '.join(scrapers_to_run)}")
        logger.info(f"📁 Output file: {self.output_file}")
        logger.info(f"⚡ Max parallel scrapers: {args.max_parallel}")
        
        results = {}
        
        # Build commands for all scrapers
        scraper_commands = {}
        for scraper_name in scrapers_to_run:
            if scraper_name in self.scrapers:
                scraper_config = self.scrapers[scraper_name]
                if not Path(scraper_config['script']).exists():
                    logger.warning(f"⚠️  Scraper script not found: {scraper_config['script']}")
                    continue
                    
                command = self.build_scraper_command(scraper_config, args)
                scraper_commands[scraper_name] = {
                    'command': command,
                    'config': scraper_config
                }
        
        if not scraper_commands:
            logger.error("❌ No valid scrapers found!")
            return {'success': False, 'results': {}}
        
        # Run scrapers in parallel with limited concurrency
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_parallel) as executor:
            # Submit all scraper tasks
            future_to_scraper = {}
            for scraper_name, scraper_info in scraper_commands.items():
                future = executor.submit(
                    self.run_scraper,
                    scraper_name,
                    scraper_info['command'],
                    timeout
                )
                future_to_scraper[future] = scraper_name
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_scraper):
                scraper_name = future_to_scraper[future]
                try:
                    result = future.result()
                    results[scraper_name] = result
                    
                    # Process results immediately if successful
                    if result['success']:
                        temp_file = f"data/temp_{scraper_name}_results.csv"
                        new_results = self.process_scraper_results(scraper_name, temp_file)
                        result['new_results'] = new_results
                    
                    logger.info(f"🏁 {scraper_name} finished - Success: {result['success']}")
                    
                except Exception as e:
                    logger.error(f"💥 {scraper_name} task failed: {str(e)}")
                    results[scraper_name] = {
                        'scraper': scraper_name,
                        'success': False,
                        'error': str(e)
                    }
        
        return {'success': True, 'results': results}

    def generate_summary_report(self, results: Dict[str, Any]) -> None:
        """Generate a summary report of the scraping session"""
        print("\n" + "="*60)
        print("🎉 UNIFIED SCRAPING COMPLETE!")
        print("="*60)
        
        # Overall statistics
        stats = self.csv_manager.get_stats()
        print(f"📁 Output file: {self.output_file}")
        print(f"📊 Total unique records: {stats.get('total_records', 0):,}")
        
        if stats.get('price_range'):
            price_range = stats['price_range']
            print(f"💰 Price range: £{price_range['min']:,.0f} - £{price_range['max']:,.0f}")
            print(f"💰 Median price: £{price_range['median']:,.0f}")
        
        if stats.get('year_range'):
            year_range = stats['year_range']
            print(f"🚗 Year range: {year_range['min']} - {year_range['max']}")
        
        # Source breakdown
        if stats.get('source_breakdown'):
            print(f"\n📈 Results by source:")
            for source, count in stats['source_breakdown'].items():
                print(f"  • {source}: {count:,} records")
        
        # Scraper performance
        print(f"\n⚡ Scraper performance:")
        for scraper_name, result in results.get('results', {}).items():
            status = "✅" if result.get('success') else "❌"
            elapsed = result.get('elapsed', 0)
            new_results = result.get('new_results', 0)
            print(f"  {status} {scraper_name}: {elapsed:.1f}s, {new_results} new results")
        
        # Check for subset files
        print(f"\n📂 Individual subset files:")
        data_dir = Path("data")
        subset_files = list(data_dir.glob("*_subset_results.csv"))
        if subset_files:
            for subset_file in sorted(subset_files):
                try:
                    import pandas as pd
                    subset_df = pd.read_csv(subset_file)
                    source_name = subset_file.stem.replace('_subset_results', '')
                    print(f"  📄 {subset_file.name}: {len(subset_df):,} records from {source_name}")
                except Exception:
                    print(f"  📄 {subset_file.name}: Available for analysis")
        else:
            print("  ⚠️  No subset files found")
        
        print(f"\n💡 Usage tips:")
        print(f"  • Main unified CSV: {self.output_file}")
        print(f"  • Individual source analysis: data/*_subset_results.csv")
        print(f"  • Results are automatically deduplicated and appended")
        print(f"  • Re-run the same command to continue scraping more data")
        
        print("\n" + "="*60)

def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Unified Ford Transit Multi-Source Scraper")
    
    # Output configuration
    parser.add_argument("--outfile", default="ford_transit_uk_complete.csv",
                       help="Output CSV filename")
    
    # Source selection
    parser.add_argument("--sources", nargs='+', 
                       choices=['autotrader', 'cargurus', 'ebay', 'gumtree', 'facebook'],
                       help="Specific sources to scrape (default: all)")
    
    # Scraping parameters
    parser.add_argument("--postcode-limit", type=int, default=100,
                       help="Number of postcodes per source")
    parser.add_argument("--pages-per-postcode", type=int, default=5,
                       help="Pages to scrape per postcode")
    parser.add_argument("--max-browsers", type=int, default=5,
                       help="Maximum concurrent browsers per source")
    parser.add_argument("--max-pages", type=int, default=50,
                       help="Maximum total pages per source")
    parser.add_argument("--include-mixed", action="store_true",
                       help="Include mixed density areas for broader coverage")
    
    # Parallel execution
    parser.add_argument("--max-parallel", type=int, default=3,
                       help="Maximum scrapers to run in parallel")
    parser.add_argument("--timeout", type=int, default=3600,
                       help="Timeout per scraper in seconds")
    
    # Proxy support
    parser.add_argument("--proxy-file", help="Path to proxy file")
    
    # Quick test mode
    parser.add_argument("--quick", action="store_true",
                       help="Quick test with reduced settings")
    
    return parser.parse_args()

async def main():
    """Main execution function"""
    args = parse_args()
    
    # Quick test mode adjustments
    if args.quick:
        args.postcode_limit = 10
        args.pages_per_postcode = 2
        args.max_pages = 10
        args.max_browsers = 2
        args.timeout = 600  # 10 minutes
        logger.info("🚀 Running in quick test mode")
    
    # Initialize unified scraper
    scraper = UnifiedVanScraper(args.outfile)
    
    # Check initial state
    initial_stats = scraper.csv_manager.get_stats()
    logger.info(f"📊 Starting with {initial_stats.get('total_records', 0)} existing records")
    
    # Run parallel scraping
    try:
        results = await scraper.run_parallel_scraping(args)
        
        if results['success']:
            scraper.generate_summary_report(results)
        else:
            logger.error("❌ Unified scraping failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("⏹️ Scraping interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 
