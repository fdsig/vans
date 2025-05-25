#!/usr/bin/env python3
"""
Ford Transit UK-Wide Scraping Demo
==================================

This script demonstrates how to use the enhanced get_vans.py script
to scrape Ford Transit listings across the entire UK with descriptions
and images included.

The new scrape-uk command uses the commercial_hubs strategy by default,
which focuses on areas with high commercial vehicle activity like:
- Industrial areas
- Commercial zones  
- Business districts
- Transport hubs

Usage Examples:
--------------

1. Basic UK-wide scraping:
   python get_vans.py scrape-uk

2. Enhanced coverage with mixed areas:
   python get_vans.py scrape-uk --include-mixed --postcode-limit 150

3. High-performance scraping with proxies:
   python get_vans.py scrape-uk --proxy-file proxies.txt --max-browsers 10

4. Custom output file and thorough scraping:
   python get_vans.py scrape-uk --outfile my_ford_transits.csv --pages-per-postcode 8

The resulting CSV will include these columns:
- title: Vehicle title/name
- year: Manufacturing year
- mileage: Vehicle mileage
- price: Listed price in GBP
- description: Detailed vehicle description and specs
- image_url: URL to vehicle image
- url: Link to original listing
- postcode: Search postcode used
- age: Calculated vehicle age
"""

import subprocess
import sys
from pathlib import Path
import argparse

def run_uk_scrape(custom_args=None):
    """Run the UK-wide scraping with optimal settings"""
    
    base_command = [
        sys.executable, "get_vans.py", "scrape-uk",
        "--pages-per-postcode", "10",
        "--postcode-limit", "200", 
        "--max-browsers", "10",
        "--max-pages", "100"
    ]
    
    if custom_args:
        base_command.extend(custom_args)
    
    print("🚐 Starting UK-wide Ford Transit scraping...")
    print(f"📋 Command: {' '.join(base_command)}")
    print("⏱️  This may take 30-60 minutes depending on your settings")
    print("📊 Expected output: ford_transit_uk_complete.csv with descriptions and images")
    print("-" * 60)
    
    try:
        result = subprocess.run(base_command, check=True, capture_output=False)
        print("\n✅ Scraping completed successfully!")
        
        # Check if output file exists
        output_file = Path("ford_transit_uk_complete.csv")
        if output_file.exists():
            print(f"📁 Output saved to: {output_file}")
            print(f"📊 File size: {output_file.stat().st_size / (1024*1024):.1f} MB")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Scraping failed with exit code: {e.returncode}")
        return False
    except KeyboardInterrupt:
        print(f"\n⏹️  Scraping interrupted by user")
        return False

def main():
    parser = argparse.ArgumentParser(description="Ford Transit UK Scraping Demo")
    parser.add_argument("--include-mixed", action="store_true",
                       help="Include mixed density areas for broader coverage")
    parser.add_argument("--proxy-file", help="Path to proxy file")
    parser.add_argument("--outfile", default="ford_transit_uk_complete.csv",
                       help="Output CSV filename")
    parser.add_argument("--pages-per-postcode", type=int, default=5,
                       help="Pages to scrape per postcode")
    parser.add_argument("--postcode-limit", type=int, default=100,
                       help="Number of postcodes to use")
    parser.add_argument("--quick", action="store_true",
                       help="Quick test with reduced settings")
    
    args = parser.parse_args()
    
    # Build custom arguments
    custom_args = ["--outfile", args.outfile]
    
    if args.include_mixed:
        custom_args.append("--include-mixed")
    
    if args.proxy_file:
        custom_args.extend(["--proxy-file", args.proxy_file])
    
    if args.quick:
        # Quick test settings
        custom_args.extend([
            "--postcode-limit", "20",
            "--pages-per-postcode", "2",
            "--max-browsers", "3"
        ])
    else:
        custom_args.extend([
            "--postcode-limit", str(args.postcode_limit),
            "--pages-per-postcode", str(args.pages_per_postcode)
        ])
    
    # Check if get_vans.py exists
    if not Path("get_vans.py").exists():
        print("❌ get_vans.py not found in current directory")
        sys.exit(1)
    
    success = run_uk_scrape(custom_args)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 
