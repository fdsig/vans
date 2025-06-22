# 📱 Gumtree UK Ford Transit Scraper

*Advanced Gumtree UK scraping system with intelligent postcode management, concurrent processing, and comprehensive classified marketplace analytics.*

**Location**: `scrapers/get_vans_gumtree.py` - Part of the modular scrapers package

## 🌟 Overview

**Primary Function**: Harvests **current asking prices** from Gumtree UK - the UK's largest classified advertising platform, targeting Ford Transit L2 H2 listings from both **private sellers and trade advertisements**.

### 🎯 Why Gumtree?

Gumtree offers a **unique marketplace perspective** that complements premium dealer platforms:

- **📱 Local Focus**: Community-based listings with regional pricing
- **🏠 Private Sellers**: Individual vehicle owners selling directly  
- **🔧 Trade Advertisements**: Small dealers and garage sales
- **💰 Asking Price Intelligence**: Current market availability and pricing
- **📍 Geographic Coverage**: Comprehensive UK regional representation
- **📄 Detailed Descriptions**: Often more personal, detailed vehicle descriptions

---

## 🏗️ Integration with Unified System

### Part of Scrapers Package
The Gumtree scraper is now part of the modular `scrapers/` package and integrates seamlessly with the unified scraping system:

```python
# Import from scrapers package
from scrapers import UnifiedVanScraper, PostcodeManager

# Used automatically in unified scraping
python uk_scrape.py  # Includes Gumtree among all sources

# Direct import availability  
from scrapers.get_vans_gumtree import GumtreeScraper
```

### Shared Utilities
- **PostcodeManager**: Shared intelligent postcode selection
- **CSVManager**: Unified output format and deduplication
- **ProxyRotator**: Common proxy management  
- **Data Classes**: Standardized `ScrapingResult` format

---

## 🚀 Quick Start

### Installation
```bash
pip install -r requirements.txt
playwright install --with-deps
```

### Basic Usage
```bash
# Single postcode Gumtree scraping
python scrapers/get_vans_gumtree.py scrape --postcode "M1 1AA" --pages 10 --outfile transit_gumtree.csv

# Multi-postcode commercial strategy
python scrapers/get_vans_gumtree.py scrape-multi --strategy commercial_hubs --postcode-limit 30 --pages-per-postcode 5

# UK-wide Gumtree scraping
python scrapers/get_vans_gumtree.py scrape-uk --outfile ford_transit_uk_gumtree.csv

# Unified multi-source scraping (recommended)
python uk_scrape.py --sources gumtree

# Analyze scraped data
python get_vans.py analyse data/ford_transit_uk_gumtree.csv
```

---

## 🎯 Command Reference

### **1. `scrape`** - Single Postcode Scraping

Scrapes Gumtree listings for a specific postcode area.

```bash
python scrapers/get_vans_gumtree.py scrape [OPTIONS]

Options:
  --postcode TEXT     UK postcode (required, e.g., "M1 1AA", "B1 1AA")
  --pages INTEGER     Number of pages to scrape (default: 10)
  --outfile PATH      Output CSV filename (default: data/gumtree_listings.csv)
```

#### Examples
```bash
# Manchester area scraping
python scrapers/get_vans_gumtree.py scrape --postcode "M1 1AA" --pages 15 --outfile data/manchester_gumtree.csv

# London commercial district
python scrapers/get_vans_gumtree.py scrape --postcode "EC1A 1AA" --pages 12 --outfile data/london_gumtree.csv

# Birmingham coverage
python scrapers/get_vans_gumtree.py scrape --postcode "B1 1AA" --pages 20 --outfile data/birmingham_gumtree.csv
```

### **2. `scrape-multi`** - Multi-Postcode Concurrent Scraping

Advanced concurrent scraping across multiple postcodes with intelligent strategies.

```bash
python scrapers/get_vans_gumtree.py scrape-multi [OPTIONS]

Options:
  --strategy CHOICE           Postcode selection strategy (default: mixed_density)
                             Choices: major_cities, commercial_hubs, geographic_spread, mixed_density, custom
  --postcode-limit INTEGER    Number of postcodes to scrape (default: 50)
  --pages-per-postcode INT    Pages to scrape per postcode (default: 3)
  --outfile PATH             Output CSV filename (default: data/gumtree_multi.csv)
  --proxy-file PATH          File containing proxy list for rotation
  --postcodes TEXT...        Custom list of specific postcodes
  --center-postcode TEXT     Center point for geographic filtering
  --radius-km FLOAT          Radius in kilometers for geographic filtering
```

#### Examples

##### **Commercial Hub Strategy**
```bash
# Target high-activity commercial areas
python scrapers/get_vans_gumtree.py scrape-multi --strategy commercial_hubs \
    --postcode-limit 25 --pages-per-postcode 6 --outfile data/gumtree_commercial.csv
```

##### **Geographic Radius Targeting**
```bash
# Manchester area (50km radius)
python scrapers/get_vans_gumtree.py scrape-multi --strategy mixed_density \
    --center-postcode "M1 1AA" --radius-km 50 --postcode-limit 20

# London metropolitan (30km radius)
python scrapers/get_vans_gumtree.py scrape-multi --strategy commercial_hubs \
    --center-postcode "EC1A 1AA" --radius-km 30 --pages-per-postcode 8
```

##### **Custom Postcode Lists**
```bash
# Major cities focus
python scrapers/get_vans_gumtree.py scrape-multi \
    --postcodes "M1 1AA" "B1 1AA" "LS1 1AA" "S1 1AA" "L1 1AA" \
    --pages-per-postcode 10 --outfile data/major_cities_gumtree.csv
```

### **3. `scrape-uk`** - UK-Wide Comprehensive Scraping

Optimized UK-wide scraping focusing on commercial and industrial areas.

```bash
python scrapers/get_vans_gumtree.py scrape-uk [OPTIONS]

Options:
  --outfile PATH             Output CSV filename (default: data/ford_transit_uk_gumtree.csv)
  --include-mixed BOOL       Include mixed density areas for broader coverage
  --pages-per-postcode INT   Pages to scrape per postcode (default: 5)
  --postcode-limit INTEGER   Maximum postcodes to use (default: 100)
  --proxy-file PATH          File containing proxy list
  --max-browsers INTEGER     Maximum concurrent browsers (default: 5)
  --max-pages INTEGER        Maximum concurrent pages (default: 15)
```

#### Examples

##### **Standard UK-Wide Scraping**
```bash
# Comprehensive UK coverage with commercial focus
python scrapers/get_vans_gumtree.py scrape-uk --outfile data/ford_transit_uk_gumtree.csv
```

##### **Enhanced Coverage**
```bash
# Include mixed density areas for broader market view
python scrapers/get_vans_gumtree.py scrape-uk --include-mixed --pages-per-postcode 8 \
    --postcode-limit 150 --outfile data/gumtree_enhanced_uk.csv
```

##### **High-Performance Scraping**
```bash
# Use proxy rotation for large-scale scraping
python scrapers/get_vans_gumtree.py scrape-uk --proxy-file proxies.txt \
    --max-browsers 8 --max-pages 20 --pages-per-postcode 6
```

---

## 🔗 Integration Methods

### 1. **Via Unified System (Recommended)**
```bash
# Gumtree included automatically
python uk_scrape.py

# Gumtree only via unified system
python uk_scrape.py --sources gumtree

# Gumtree with other sources
python uk_scrape.py --sources autotrader gumtree cargurus

# Direct unified scraper access
python -m scrapers.unified_van_scraper --sources gumtree
```

### 2. **Direct Scraper Usage**
```bash
# Full UK coverage via direct access
python scrapers/get_vans_gumtree.py scrape-uk

# Custom configuration
python scrapers/get_vans_gumtree.py scrape-multi --strategy commercial_hubs --postcode-limit 50
```

### 3. **Programmatic Integration**
```python
# Import and use directly
from scrapers.get_vans_gumtree import GumtreeScraper
from scrapers import PostcodeManager, CSVManager

# Use shared utilities
postcode_manager = PostcodeManager()
csv_manager = CSVManager("data/my_gumtree_data.csv")

# Access via unified scraper
from scrapers import UnifiedVanScraper
scraper = UnifiedVanScraper()
```

---

## 📊 Output Format Integration

### Standardized CSV Structure
The Gumtree scraper produces output compatible with the unified system:

```csv
title,year,mileage,price,description,image_url,url,postcode,source,listing_type,vat_included,scraped_at,age,unique_id
"Ford Transit 350 L2 H2 Panel Van",2018,65000,16995,"2.0 TDCi 130ps Manual Diesel",https://i.ebayimg.com/...,https://www.gumtree.com/...,M1 1AA,gumtree,buy_it_now,false,2024-01-15T10:30:15,6,xyz789abc123
```

### Data Quality Features
- **VAT Detection**: Intelligent VAT status recognition from Gumtree listings
- **Listing Classification**: Private seller vs trade advertisement identification
- **Price Validation**: Realistic price range checking (£1k-£100k)
- **Mileage Validation**: Odometer verification (0-500k miles)
- **Year Validation**: Model year validation (1990-2025)

---

## 🧠 Intelligent Postcode Strategies

### Shared Intelligence System
The Gumtree scraper uses the unified `PostcodeManager` with these strategies:

| Strategy | Focus | Gumtree Benefit | Typical Results |
|----------|-------|------------------|-----------------|
| **commercial_hubs** | Business districts | High trade advertisement density | 20-40 listings/postcode |
| **major_cities** | Urban centers | Diverse seller mix | 15-30 listings/postcode |
| **geographic_spread** | Even distribution | Regional market coverage | 10-25 listings/postcode |
| **mixed_density** | Balanced coverage | Comprehensive classified data | 12-28 listings/postcode |

### Success Rate Learning
```python
# The PostcodeManager learns which postcodes work best for Gumtree
from scrapers import PostcodeManager

manager = PostcodeManager()
# Records success automatically during scraping
manager.record_success_rate("M1 1AA", listings_found=25, source="gumtree")

# View statistics
stats = manager.get_stats()
print(f"Best Gumtree postcodes: {stats['best_postcodes']}")
```

---

## 🚀 Performance Optimization

### Concurrent Processing
```bash
# Optimized settings for Gumtree
python scrapers/get_vans_gumtree.py scrape-uk \
    --max-browsers 6 \
    --max-pages 18 \
    --pages-per-postcode 5 \
    --postcode-limit 120
```

### Proxy Integration
```bash
# Large-scale Gumtree scraping with proxies
python scrapers/get_vans_gumtree.py scrape-uk \
    --proxy-file proxies.txt \
    --max-browsers 4 \
    --postcode-limit 200
```

### Resource Management
- **Memory Usage**: 800MB-2GB typical (scales with concurrent browsers)
- **CPU Usage**: 2-6 cores depending on `--max-browsers` setting
- **Network**: Respects Gumtree rate limits automatically
- **Storage**: ~8-40 MB per 1000 listings

---

## 🔍 Monitoring & Logging

### Integrated Logging
```
logs/
├── gumtree_scraping.log           # Gumtree-specific detailed logs
├── uk_scrape.log                  # Unified system logs (includes Gumtree)
├── unified_scraping.log           # Multi-source coordination logs
└── scraping.log                   # General scraping logs
```

### Success Tracking
```bash
# View Gumtree-specific performance
grep "gumtree" logs/unified_scraping.log

# Monitor success rates
python get_vans.py postcodes stats
```

---

## 🛠️ Troubleshooting

### Common Issues

#### **Gumtree Access Issues**
```bash
# Test Gumtree connectivity
python scrapers/get_vans_gumtree.py scrape --postcode "M1 1AA" --pages 2

# Use with proxy if blocked
python scrapers/get_vans_gumtree.py scrape-uk --proxy-file proxies.txt --max-browsers 2
```

#### **Performance Issues**
```bash
# Reduce load for slower systems
python scrapers/get_vans_gumtree.py scrape-multi --postcode-limit 20 --pages-per-postcode 3 --max-browsers 2

# Check system resources
python -c "
import psutil
print(f'Available RAM: {psutil.virtual_memory().available / (1024**3):.1f} GB')
print(f'CPU cores: {psutil.cpu_count()}')
"
```

#### **Integration Issues**
```bash
# Verify scrapers package
python -c "from scrapers import get_vans_gumtree; print('Import OK')"

# Check unified system integration
python -c "from scrapers import UnifiedVanScraper; print('Unified OK')"
```

### Gumtree-Specific Solutions
- **Rate Limiting**: Built-in delays prevent blocking
- **Content Parsing**: Robust HTML parsing handles layout changes
- **Data Validation**: Comprehensive validation prevents corrupt data
- **Error Recovery**: Automatic retry with exponential backoff

---

## 🎯 Use Cases

### **Classified Market Research**
```bash
# Comprehensive Gumtree classified analysis
python scrapers/get_vans_gumtree.py scrape-uk --include-mixed --postcode-limit 150 \
    --pages-per-postcode 6 --outfile data/gumtree_classified_research.csv

# Multi-source comparison including Gumtree
python uk_scrape.py --sources autotrader gumtree cargurus --turbo
```

### **Private Seller Intelligence**
```bash
# Gumtree private seller pricing
python scrapers/get_vans_gumtree.py scrape-multi --strategy commercial_hubs \
    --postcode-limit 50 --pages-per-postcode 8

# Combine with dealer sources for price comparison
python uk_scrape.py --sources autotrader gumtree
```

### **Regional Market Analysis**
```bash
# London area Gumtree analysis
python scrapers/get_vans_gumtree.py scrape-multi --strategy geographic_spread \
    --center-postcode "SW1A 1AA" --radius-km 50 --postcode-limit 25
```

---

## 📈 Expected Results

### Typical Performance
- **Standard UK Run**: 2,000-4,000 listings in 45-75 minutes
- **Turbo Mode**: 4,000-7,000 listings in 60-90 minutes  
- **Quick Test**: 300-800 listings in 10-15 minutes

### Data Quality
- **Success Rate**: 75-85% of postcodes yield results
- **Price Accuracy**: 95%+ realistic price validation
- **Description Quality**: 85%+ have detailed specifications
- **Image Availability**: 70%+ have accessible images

### Gumtree Contribution to Unified Dataset
- **Unique Listings**: 20-25% of total when combined with other sources
- **Private Seller Focus**: Strong representation of individual sellers
- **Geographic Distribution**: Excellent coverage of smaller towns/cities
- **Price Range**: Good representation of budget to mid-range vehicles

---

**🚐 The Gumtree scraper provides essential classified marketplace intelligence as part of the comprehensive Ford Transit data collection ecosystem. Use it standalone for focused Gumtree analysis or as part of the unified system for complete market coverage.**

*Ready to collect Gumtree classified data? Start with `python scrapers/get_vans_gumtree.py scrape-uk` or include it in unified scraping with `python uk_scrape.py`*
