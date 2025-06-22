# 🇬🇧 Ford Transit UK-Wide Scraping Guide

## Overview

This guide covers the advanced UK-wide Ford Transit scraping capabilities across multiple platforms. The system intelligently targets commercial and industrial areas where Ford Transits are most commonly found, using sophisticated postcode intelligence and concurrent processing.

## 🎯 Multi-Source UK Scraping

### Available Sources

| Source | Speciality | Key Benefits |
|--------|------------|-------------|
| **AutoTrader** | Premium dealer network | Most comprehensive specs, dealer ratings |
| **CarGurus** | Current asking prices | Real-time market pricing from all sellers |
| **eBay** | Auctions & Buy-It-Now | Auction insights, immediate sale prices |
| **Gumtree** | Private & trade sellers | Local market, private seller focus |
| **Facebook Marketplace** | Community sales | Local deals, social verification |

### Unified Multi-Source Command
```bash
# Scrape ALL sources simultaneously (recommended)
python uk_scrape.py

# Quick test across all sources
python uk_scrape.py --quick

# High-performance mode for powerful machines
python uk_scrape.py --turbo --max-parallel 5
```

## 🧠 Intelligent Postcode Strategies

### Strategy Selection

#### **Commercial Hubs** (Recommended for Transit vans)
```bash
python get_vans.py scrape-uk --strategy commercial_hubs
```
- **Target**: Business districts, industrial estates, transport hubs
- **Best for**: Maximum Ford Transit activity
- **Areas**: Manufacturing zones, logistics centers, commercial parks
- **Expected yield**: 20-50 listings per postcode

#### **Major Cities** (High volume)
```bash
python get_vans.py scrape-uk --strategy major_cities
```
- **Target**: High-density urban centers
- **Best for**: Quick high-volume results  
- **Areas**: London, Manchester, Birmingham, Glasgow, Leeds
- **Expected yield**: 15-40 listings per postcode

#### **Geographic Spread** (National coverage)
```bash
python get_vans.py scrape-uk --strategy geographic_spread
```
- **Target**: Even distribution across all UK regions
- **Best for**: Comprehensive national dataset
- **Areas**: All regions balanced representation
- **Expected yield**: 10-30 listings per postcode

#### **Mixed Density** (Balanced approach)
```bash
python get_vans.py scrape-uk --strategy mixed_density
```
- **Target**: Urban + suburban + rural balance
- **Best for**: Well-rounded market view
- **Areas**: Balanced mix across density levels
- **Expected yield**: 12-35 listings per postcode

### Geographic Targeting
```bash
# Focus on 50km radius around Manchester
python get_vans.py scrape-multi --strategy commercial_hubs \
    --center-postcode "M1 1AA" --radius-km 50 --postcode-limit 25

# London area comprehensive scraping
python get_vans.py scrape-multi --strategy mixed_density \
    --center-postcode "SW1 1AA" --radius-km 75 --postcode-limit 40
```

## ⚡ Performance Optimization

### Single Source Scraping

#### AutoTrader (Premium dealer focus)
```bash
# Standard UK-wide AutoTrader scraping
python get_vans.py scrape-uk --outfile autotrader_results.csv

# Enhanced coverage with mixed areas
python get_vans.py scrape-uk --include-mixed --pages-per-postcode 8 \
    --postcode-limit 150 --outfile autotrader_enhanced.csv

# High-performance with proxies
python get_vans.py scrape-uk --proxy-file proxies.txt \
    --max-browsers 10 --max-pages 40 --outfile autotrader_turbo.csv
```

#### CarGurus (Current asking prices)
```bash
# Current market prices from CarGurus
python get_vans_cargurus.py scrape-uk --outfile cargurus_prices.csv

# Commercial focus for business pricing
python get_vans_cargurus.py scrape-multi --strategy commercial_hubs \
    --postcode-limit 100 --outfile cargurus_commercial.csv
```

#### eBay (Auction insights)
```bash
# eBay current listings
python get_vans_ebay.py scrape-uk --outfile ebay_current.csv

# eBay completed/sold listings for market analysis
python get_vans_ebay_completed.py scrape-uk --outfile ebay_sold.csv
```

### Performance Modes

#### Quick Test Mode
```bash
# Fast test run (10-15 minutes)
python uk_scrape.py --quick
```
- 20 postcodes, 3 pages each
- 3 parallel browsers
- ~500-1,500 listings total

#### Standard Mode (Auto-scaled)
```bash
# Default balanced performance
python uk_scrape.py
```
- Auto-scaled based on system resources
- 60-100 postcodes, 4-6 pages each
- 4-6 parallel browsers
- ~5,000-15,000 listings total

#### Turbo Mode
```bash
# High-performance for powerful machines
python uk_scrape.py --turbo
```
- 300 postcodes, 12 pages each
- 10 parallel browsers
- ~15,000-25,000 listings total

#### Custom Performance Tuning
```bash
# Fine-tuned performance settings
python uk_scrape.py --postcode-limit 150 --pages-per-postcode 6 \
    --max-browsers 8 --max-pages 35 --max-parallel 4
```

## 📊 Output Data Structure

### Standardized CSV Columns

All scrapers produce consistent output with these fields:

| Column | Description | Example Value |
|--------|-------------|---------------|
| `title` | Vehicle description | "Ford Transit 350 L2 H2 Panel Van TDCi" |
| `year` | Manufacturing year | `2020` |
| `mileage` | Odometer reading | `45000` |
| `price` | Listed price in GBP | `22995` |
| `description` | Detailed specifications | "2.0 EcoBlue 170 BHP Manual Diesel Euro 6" |
| `image_url` | Photo URL | `https://cdn.autotrader.co.uk/...` |
| `url` | Original listing link | `https://www.autotrader.co.uk/...` |
| `postcode` | Search postcode | `M1 1AA` |
| `source` | Platform scraped | `autotrader`, `cargurus`, `ebay`, etc. |
| `scraped_at` | Timestamp | `2024-01-15T14:30:15` |
| `age` | Calculated age | `4` |
| `listing_type` | Type of listing | `buy_it_now`, `auction` |
| `vat_included` | VAT status | `true`/`false` |

### Data Quality Features
- **✅ Intelligent filtering**: Excludes navigation elements and non-vehicle content
- **✅ Price validation**: Validates realistic price ranges (£1,000-£100,000)
- **✅ Mileage verification**: Checks realistic mileage ranges (0-500,000)
- **✅ Year validation**: Ensures valid model years (1990-2025)
- **✅ Image quality**: Filters out placeholder and navigation images
- **✅ Deduplication**: Removes duplicate listings across postcodes/sources

## 🗺️ UK Coverage Areas

### Commercial Hub Postcodes (Highest Transit Activity)
```
London Commercial: SW1A, IG1, DA1, RM1, UB1, CR0
Manchester Area: M1, WD1, SL1  
Birmingham: B1, CV1
Industrial Centers: MK1, NN1, DE1, NG1, PE1
```

### Major City Coverage
```
Scotland: G1 (Glasgow), EH1 (Edinburgh), AB1 (Aberdeen)
Wales: CF1 (Cardiff), SA1 (Swansea), NP1 (Newport)  
Northern England: LS1 (Leeds), L1 (Liverpool), S1 (Sheffield), NE1 (Newcastle)
Southern England: BS1 (Bristol), PO1 (Portsmouth), SO1 (Southampton)
```

### Geographic Distribution
```
Regions Covered: 11 major UK regions
Total Postcode Areas: 48+ with GPS coordinates
Commercial Activity Zones: 28 high-activity areas
Population Centers: 20+ major cities
```

## 📈 Expected Performance Results

### Typical Results by Mode

#### Quick Mode
- **Time**: 10-20 minutes
- **Postcodes**: 15-25
- **Listings**: 500-1,500
- **File Size**: 0.5-2 MB
- **Use Case**: Testing, development

#### Standard Mode  
- **Time**: 30-75 minutes
- **Postcodes**: 60-100
- **Listings**: 5,000-15,000  
- **File Size**: 3-15 MB
- **Use Case**: Regular market analysis

#### Turbo Mode
- **Time**: 60-120 minutes
- **Postcodes**: 200-300
- **Listings**: 15,000-25,000
- **File Size**: 10-30 MB
- **Use Case**: Comprehensive market research

### Success Rates by Source
- **AutoTrader**: 90-95% postcodes yield results
- **CarGurus**: 85-92% postcodes yield results
- **eBay**: 75-85% postcodes yield results (variable auction timing)
- **Gumtree**: 80-90% postcodes yield results
- **Facebook**: 70-85% postcodes yield results (geographic variation)

## 🔧 Advanced Configuration

### Proxy Configuration for Large-Scale Scraping
```bash
# Create proxies.txt file
echo "http://username:password@proxy1.example.com:8080" > proxies.txt
echo "http://username:password@proxy2.example.com:8080" >> proxies.txt
echo "socks5://username:password@proxy3.example.com:1080" >> proxies.txt

# Use with scraping
python uk_scrape.py --turbo --proxy-file proxies.txt
```

### Custom Postcode Lists
```bash
# Use specific postcodes only
python get_vans.py scrape-multi --postcodes "M1 1AA" "B1 1AA" "SW1A 1AA" \
    --pages-per-postcode 8 --outfile custom_areas.csv

# Import postcodes from file
python get_vans.py scrape-multi --postcode-file my_postcodes.txt \
    --pages-per-postcode 5
```

### Timing and Rate Limiting
```bash
# Increased delays for stealth mode
python get_vans.py scrape-uk --human-delays --delay-range 3-6

# Conservative concurrent settings
python uk_scrape.py --max-browsers 3 --max-pages 12 --max-parallel 2
```

## 🔍 Monitoring and Logs

### Real-Time Progress Monitoring
```
🚐 Starting UK-wide Ford Transit scraping...
🔗 Sources: AutoTrader + CarGurus + eBay + Gumtree
📍 Strategy: Commercial Hubs  
⚡ Performance: STANDARD mode (auto-scaled)
📊 Settings: 80 postcodes, 5 pages each, 5 browsers
⏱️  Estimated time: 25-45 minutes
```

### Log Files Generated
- **`scraping.log`** - AutoTrader scraping activity
- **`cargurus_scraping.log`** - CarGurus scraping activity  
- **`ebay_scraping.log`** - eBay scraping activity
- **`gumtree_scraping.log`** - Gumtree scraping activity
- **`unified_scraping.log`** - Multi-source coordination logs

### Success Tracking Database
- **`postcode_intelligence.db`** - SQLite database storing:
  - Postcode success rates by source
  - Historical scraping performance
  - Geographic effectiveness patterns
  - Adaptive learning data

## 🛠️ Troubleshooting

### Common Issues and Solutions

#### **No Results Found**
```bash
# Check individual sources
python get_vans.py scrape --postcode "M1 1AA" --pages 2
python get_vans_cargurus.py scrape --postcode "M1 1AA" --pages 2

# Try different strategy
python get_vans.py scrape-uk --strategy major_cities --quick
```

#### **Cloudflare/Bot Detection**
```bash
# Use proxy rotation
python uk_scrape.py --proxy-file proxies.txt --max-browsers 3

# Reduce concurrency and add delays
python get_vans.py scrape-uk --max-browsers 3 --max-pages 10 --human-delays
```

#### **Memory/Performance Issues**
```bash
# Conservative settings for low-spec systems
python uk_scrape.py --postcode-limit 30 --max-browsers 2 --max-pages 8

# Process in smaller batches
python get_vans.py scrape-multi --strategy commercial_hubs --postcode-limit 20
```

#### **Incomplete Data**
```bash
# Include descriptions and images
python get_vans.py scrape-uk --include-descriptions --include-images

# Extended page coverage
python uk_scrape.py --pages-per-postcode 8 --include-mixed
```

### Performance Optimization Tips

1. **System Resource Matching**:
   - 4GB RAM: Use `--max-browsers 2-3`
   - 8GB RAM: Use `--max-browsers 4-6`  
   - 16GB+ RAM: Use `--max-browsers 8-12`

2. **Network Optimization**:
   - Stable connection: Use higher concurrency
   - Unstable/slow connection: Reduce `--max-pages`
   - Corporate network: Consider proxy rotation

3. **Target Optimization**:
   - Van dealers: Use `commercial_hubs` strategy
   - Price analysis: Include all sources with `uk_scrape.py`
   - Regional focus: Use geographic filtering

## 📋 Command Reference

### Quick Reference Commands

```bash
# Multi-source comprehensive scraping
python uk_scrape.py                              # Standard auto-scaled mode
python uk_scrape.py --quick                      # Fast test mode  
python uk_scrape.py --turbo                      # High-performance mode

# Single source scraping
python get_vans.py scrape-uk                     # AutoTrader UK-wide
python get_vans_cargurus.py scrape-uk            # CarGurus UK-wide
python get_vans_ebay.py scrape-uk                # eBay UK-wide

# Strategy-specific scraping
python get_vans.py scrape-multi --strategy commercial_hubs
python get_vans.py scrape-multi --strategy major_cities
python get_vans.py scrape-multi --strategy geographic_spread

# Analysis commands
python get_vans.py analyse results.csv           # Price trend analysis
python get_vans.py regress results.csv           # Regression modeling
python get_vans.py postcodes stats               # Postcode intelligence stats
```

### Full Parameter List

```bash
# Core settings
--outfile FILENAME              # Output CSV filename
--postcode-limit N              # Number of postcodes to use
--pages-per-postcode N          # Pages to scrape per postcode
--strategy STRATEGY             # Postcode selection strategy

# Performance settings  
--max-browsers N                # Concurrent browser instances
--max-pages N                   # Concurrent page requests
--max-parallel N                # Parallel scrapers (multi-source)

# Advanced options
--proxy-file FILE               # Proxy rotation file
--include-mixed                 # Include mixed density areas
--center-postcode CODE          # Geographic center for filtering
--radius-km N                   # Geographic radius in kilometers
--human-delays                  # Enable realistic human delays
```

---

**🎯 Ready to scrape the UK Ford Transit market? Start with `python uk_scrape.py --quick` to test, then scale up to `python uk_scrape.py --turbo` for comprehensive data collection!** 
