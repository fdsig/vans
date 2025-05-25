#!/usr/bin/env python3
"""
Quick 10x Dataset Expansion
===========================

This script quickly expands your existing 1,441 records to 10,000+ records
by running targeted scraping with different strategies.
"""

import subprocess
import pandas as pd
from pathlib import Path
import time

def run_quick_scrape(strategy_name, args, expected_records):
    """Run a quick scraping session"""
    print(f"\n🚀 Running: {strategy_name}")
    print(f"🎯 Target: ~{expected_records} new records")
    
    start_time = time.time()
    
    try:
        cmd = ["python", "get_vans.py"] + args
        print(f"📋 Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)  # 30 min timeout
        
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ {strategy_name} completed in {elapsed/60:.1f} minutes")
            return True
        else:
            print(f"❌ {strategy_name} failed: {result.stderr[:200]}...")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {strategy_name} timed out after 30 minutes")
        return False
    except Exception as e:
        print(f"💥 {strategy_name} error: {str(e)}")
        return False

def main():
    print("🚀 QUICK 10X DATASET EXPANSION")
    print("=" * 50)
    print("Current dataset: ~1,441 records")
    print("Target: 10,000+ records")
    print("Strategy: Multiple targeted scraping sessions")
    print("⏱️  Estimated time: 90-120 minutes")
    print()
    
    # Define quick expansion strategies
    strategies = [
        {
            "name": "Deep_Commercial_Hubs",
            "args": [
                "scrape-uk", 
                "--postcode-limit", "150",
                "--pages-per-postcode", "15",
                "--max-browsers", "8",
                "--max-pages", "40",
                "--outfile", "ford_transit_deep_commercial.csv"
            ],
            "expected": 2000
        },
        
        {
            "name": "Wide_Mixed_Areas", 
            "args": [
                "scrape-uk",
                "--include-mixed",
                "--postcode-limit", "300",
                "--pages-per-postcode", "10",
                "--max-browsers", "10", 
                "--max-pages", "50",
                "--outfile", "ford_transit_wide_mixed.csv"
            ],
            "expected": 2500
        },
        
        {
            "name": "Major_Cities_Deep",
            "args": [
                "scrape-multi",
                "--strategy", "major_cities", 
                "--postcode-limit", "80",
                "--pages-per-postcode", "20",
                "--max-browsers", "6",
                "--max-pages", "30",
                "--outfile", "ford_transit_cities_deep.csv"
            ],
            "expected": 1800
        },
        
        {
            "name": "Geographic_Spread_Thorough",
            "args": [
                "scrape-multi",
                "--strategy", "geographic_spread",
                "--postcode-limit", "200", 
                "--pages-per-postcode", "12",
                "--max-browsers", "8",
                "--max-pages", "35",
                "--outfile", "ford_transit_geographic_thorough.csv"
            ],
            "expected": 2000
        }
    ]
    
    successful_strategies = []
    total_start_time = time.time()
    
    # Run each strategy
    for i, strategy in enumerate(strategies, 1):
        print(f"\n{'='*60}")
        print(f"STRATEGY {i}/{len(strategies)}: {strategy['name']}")
        print(f"{'='*60}")
        
        success = run_quick_scrape(
            strategy['name'], 
            strategy['args'], 
            strategy['expected']
        )
        
        if success:
            successful_strategies.append(strategy)
        
        # Brief pause between strategies
        if i < len(strategies):
            print("⏸️  Brief pause before next strategy...")
            time.sleep(5)
    
    # Combine all datasets
    print(f"\n{'='*60}")
    print("COMBINING ALL DATASETS")
    print(f"{'='*60}")
    
    all_files = [
        "ford_transit_uk_complete.csv",  # Original
        "ford_transit_deep_commercial.csv",
        "ford_transit_wide_mixed.csv", 
        "ford_transit_cities_deep.csv",
        "ford_transit_geographic_thorough.csv"
    ]
    
    combined_df = pd.DataFrame()
    file_stats = []
    
    for file in all_files:
        if Path(file).exists():
            df = pd.read_csv(file)
            file_stats.append(f"{file}: {len(df)} records")
            combined_df = pd.concat([combined_df, df], ignore_index=True)
        else:
            file_stats.append(f"{file}: NOT FOUND")
    
    print("\n📊 INDIVIDUAL FILE STATISTICS:")
    for stat in file_stats:
        print(f"  {stat}")
    
    print(f"\n📊 COMBINED STATISTICS:")
    print(f"  Total records before deduplication: {len(combined_df)}")
    
    # Deduplicate
    if 'url' in combined_df.columns:
        combined_df = combined_df.drop_duplicates(subset=['url'], keep='first')
        print(f"  After URL deduplication: {len(combined_df)}")
    
    # Final deduplication
    combined_df = combined_df.drop_duplicates(
        subset=['title', 'price', 'mileage'], 
        keep='first'
    )
    
    # Save mega dataset
    mega_file = "ford_transit_10X_MEGA_dataset.csv"
    combined_df.to_csv(mega_file, index=False)
    
    total_elapsed = time.time() - total_start_time
    
    print(f"\n🎉 10X DATASET EXPANSION COMPLETE!")
    print(f"{'='*60}")
    print(f"📁 Output file: {mega_file}")
    print(f"📊 Final record count: {len(combined_df):,}")
    print(f"📈 Expansion factor: {len(combined_df)/1441:.1f}x")
    print(f"⏱️  Total time: {total_elapsed/60:.1f} minutes")
    print(f"💰 Price range: £{combined_df['price'].min():,} - £{combined_df['price'].max():,}")
    print(f"🚗 Year range: {combined_df['year'].min()} - {combined_df['year'].max()}")
    print(f"🛣️  Mileage range: {combined_df['mileage'].min():,} - {combined_df['mileage'].max():,} miles")
    
    # Success summary
    print(f"\n✅ Successful strategies: {len(successful_strategies)}/{len(strategies)}")
    for strategy in successful_strategies:
        print(f"  • {strategy['name']}")

if __name__ == "__main__":
    main() 
