#!/usr/bin/env python3
"""
Mega Ford Transit Data Collection Script
=======================================

This script runs multiple scraping strategies in parallel to maximize
data collection and reach 5000+ Ford Transit listings.
"""

import subprocess
import time
import pandas as pd
from pathlib import Path
import concurrent.futures

def run_scrape_strategy(strategy_name, command_args):
    """Run a specific scraping strategy"""
    print(f"🚀 Starting strategy: {strategy_name}")
    
    try:
        result = subprocess.run(
            ["python", "get_vans.py"] + command_args,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        if result.returncode == 0:
            print(f"✅ {strategy_name} completed successfully")
            return True, strategy_name
        else:
            print(f"❌ {strategy_name} failed: {result.stderr}")
            return False, strategy_name
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {strategy_name} timed out")
        return False, strategy_name
    except Exception as e:
        print(f"💥 {strategy_name} error: {str(e)}")
        return False, strategy_name

def main():
    """Run multiple scraping strategies to maximize data collection"""
    
    # Define multiple strategies
    strategies = [
        ("Commercial_Hubs_Deep", [
            "scrape-uk", 
            "--postcode-limit", "200",
            "--pages-per-postcode", "20", 
            "--max-browsers", "8",
            "--max-pages", "40",
            "--outfile", "ford_transit_commercial_deep.csv"
        ]),
        
        ("Mixed_Density_Wide", [
            "scrape-uk",
            "--include-mixed",
            "--postcode-limit", "400", 
            "--pages-per-postcode", "8",
            "--max-browsers", "10",
            "--max-pages", "50",
            "--outfile", "ford_transit_mixed_wide.csv"
        ]),
        
        ("Geographic_Spread", [
            "scrape-multi",
            "--strategy", "geographic_spread",
            "--postcode-limit", "150",
            "--pages-per-postcode", "12",
            "--max-browsers", "6",
            "--max-pages", "30",
            "--outfile", "ford_transit_geographic.csv"
        ]),
        
        ("Major_Cities_Focus", [
            "scrape-multi", 
            "--strategy", "major_cities",
            "--postcode-limit", "100",
            "--pages-per-postcode", "25",
            "--max-browsers", "8",
            "--max-pages", "40",
            "--outfile", "ford_transit_cities.csv"
        ])
    ]
    
    print("🎯 Starting MEGA Ford Transit data collection...")
    print(f"📊 Running {len(strategies)} parallel strategies")
    print("⏱️  Expected completion: 60-90 minutes")
    print("🎪 Target: 5000+ unique listings")
    print("-" * 60)
    
    # Run strategies in parallel (2 at a time to avoid overwhelming)
    max_workers = 2
    completed_strategies = []
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all strategies
        future_to_strategy = {
            executor.submit(run_scrape_strategy, name, args): name 
            for name, args in strategies
        }
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_strategy):
            strategy_name = future_to_strategy[future]
            try:
                success, name = future.result()
                completed_strategies.append((name, success))
                print(f"🏁 Strategy '{name}' finished - Success: {success}")
            except Exception as e:
                print(f"💥 Strategy '{strategy_name}' crashed: {str(e)}")
    
    # Combine all CSV files
    print("\n🔄 Combining all datasets...")
    combined_df = pd.DataFrame()
    output_files = [
        "ford_transit_commercial_deep.csv",
        "ford_transit_mixed_wide.csv", 
        "ford_transit_geographic.csv",
        "ford_transit_cities.csv",
        "ford_transit_uk_complete.csv"  # Include your existing data
    ]
    
    for file in output_files:
        if Path(file).exists():
            df = pd.read_csv(file)
            print(f"📁 {file}: {len(df)} records")
            combined_df = pd.concat([combined_df, df], ignore_index=True)
    
    # Remove duplicates (by URL or title+price combination)
    print(f"\n📊 Total records before deduplication: {len(combined_df)}")
    
    # Deduplicate by URL first (most reliable)
    if 'url' in combined_df.columns:
        combined_df = combined_df.drop_duplicates(subset=['url'], keep='first')
        print(f"📊 After URL deduplication: {len(combined_df)}")
    
    # Secondary deduplication by title + price + mileage
    combined_df = combined_df.drop_duplicates(
        subset=['title', 'price', 'mileage'], 
        keep='first'
    )
    print(f"📊 After full deduplication: {len(combined_df)}")
    
    # Save mega dataset
    mega_file = "ford_transit_MEGA_dataset.csv"
    combined_df.to_csv(mega_file, index=False)
    
    print(f"\n🎉 MEGA DATASET COMPLETE!")
    print(f"📁 Saved to: {mega_file}")
    print(f"📊 Total unique records: {len(combined_df)}")
    print(f"💰 Price range: £{combined_df['price'].min():,} - £{combined_df['price'].max():,}")
    print(f"🚗 Year range: {combined_df['year'].min()} - {combined_df['year'].max()}")
    print(f"🛣️  Mileage range: {combined_df['mileage'].min():,} - {combined_df['mileage'].max():,} miles")
    
    # Show statistics by strategy
    if 'postcode' in combined_df.columns:
        postcode_counts = combined_df['postcode'].value_counts()
        print(f"\n📍 Top postcodes by listings:")
        print(postcode_counts.head(10).to_string())

if __name__ == "__main__":
    main() 
