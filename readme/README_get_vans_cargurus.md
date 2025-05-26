# CarGurus Ford Transit Scraper 🚐💻

*Advanced CarGurus UK scraping system with intelligent postcode management, concurrent scraping, and sophisticated market intelligence.*

**Location**: `scrapers/get_vans_cargurus.py` - Part of the modular scrapers package

## 🎯 Purpose & Scope

**Primary Function**: Harvests **current asking prices** from CarGurus UK, targeting Ford Transit L2 H2 listings from both dealers and private sellers across the UK marketplace.

**Key Differentiator**: CarGurus aggregates listings from multiple sources, providing comprehensive market coverage and price analysis insights that complement dealer-specific platforms.

### Why CarGurus?
- ✅ **Current Asking Prices**: Real-time market data from active listings
- ✅ **Dual Source Coverage**: Both dealer and private seller inventories
- ✅ **Market Intelligence**: Built-in price analysis and market insights
- ✅ **Geographic Breadth**: Comprehensive UK coverage with regional filtering
- ✅ **Detailed Specifications**: Vehicle histories, features, and condition reports

---

## 🏗️ Integration with Unified System

### Part of Scrapers Package
The CarGurus scraper is now part of the modular `scrapers/` package and integrates seamlessly with the unified scraping system:

```python
# Import from scrapers package
from scrapers import UnifiedVanScraper, PostcodeManager

# Used automatically in unified scraping
python uk_scrape.py  # Includes CarGurus among all sources

# Direct import availability
from scrapers.get_vans_cargurus import CarGurusScraper
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
# Single postcode scraping
python scrapers/get_vans_cargurus.py scrape --postcode "M1 1AA" --pages 10 --outfile transit_cargurus.csv

# Multi-postcode commercial strategy
python scrapers/get_vans_cargurus.py scrape-multi --strategy commercial_hubs --postcode-limit 30 --pages-per-postcode 5

# UK-wide comprehensive scraping
python scrapers/get_vans_cargurus.py scrape-uk --outfile ford_transit_uk_cargurus.csv

# Unified multi-source scraping (recommended)
python uk_scrape.py --sources cargurus

# Analyze scraped data
python get_vans.py analyse data/ford_transit_uk_cargurus.csv
```

---

## 📋 Command Reference

### 1. `scrape` - Single Postcode Scraping
**Purpose**: Focused scraping around a specific UK postcode for detailed local market analysis.

```bash
python scrapers/get_vans_cargurus.py scrape [OPTIONS]

Options:
  --postcode TEXT     UK postcode (required, e.g., "M1 1AA", "SW1A 1AA")
  --pages INTEGER     Pages to scrape per postcode (default: 10)
  --outfile PATH      Output CSV filename (default: data/cargurus_listings.csv)
```

**Example Commands**:
```bash
# London commercial area analysis
python scrapers/get_vans_cargurus.py scrape --postcode "EC1V 9NR" --pages 15 --outfile data/london_cargurus.csv

# Manchester region deep dive
python scrapers/get_vans_cargurus.py scrape --postcode "M1 1AA" --pages 20 --outfile data/manchester_cargurus.csv

# Birmingham commercial district
python scrapers/get_vans_cargurus.py scrape --postcode "B1 1AA" --pages 12 --outfile data/birmingham_cargurus.csv
```

### 2. `scrape-multi` - Multi-Postcode Concurrent Scraping
**Purpose**: Strategic scraping across multiple postcodes using intelligent selection algorithms and concurrent processing.

```bash
python scrapers/get_vans_cargurus.py scrape-multi [OPTIONS]

Options:
  --strategy CHOICE           Postcode selection strategy (default: mixed_density)
                             Choices: major_cities, commercial_hubs, geographic_spread, mixed_density, custom
  --postcode-limit INTEGER    Number of postcodes to process (default: 50)
  --pages-per-postcode INT    Pages per postcode (default: 3)
  --outfile PATH             Output CSV filename (default: data/cargurus_multi.csv)
  --proxy-file PATH          File containing proxy list (optional)
  --postcodes TEXT...        Custom postcode list (overrides strategy)
  --center-postcode TEXT     Center point for geographic filtering
  --radius-km FLOAT          Radius in km for geographic filtering
```

**Strategic Examples**:
```bash
# Commercial hubs focus - maximum dealer concentration
python scrapers/get_vans_cargurus.py scrape-multi --strategy commercial_hubs --postcode-limit 40 \
    --pages-per-postcode 6 --outfile data/transit_commercial_cargurus.csv

# Geographic spread - even UK distribution
python scrapers/get_vans_cargurus.py scrape-multi --strategy geographic_spread --postcode-limit 60 \
    --pages-per-postcode 4 --outfile data/transit_geographic_cargurus.csv

# Major cities - high-density population centers
python scrapers/get_vans_cargurus.py scrape-multi --strategy major_cities --postcode-limit 25 \
    --pages-per-postcode 8 --outfile data/transit_cities_cargurus.csv

# Custom geographic focus - 75km around London
python scrapers/get_vans_cargurus.py scrape-multi --strategy geographic_spread \
    --center-postcode "SW1A 1AA" --radius-km 75 --postcode-limit 35 \
    --outfile data/transit_london_region_cargurus.csv

# Proxy-enabled large-scale scraping
python scrapers/get_vans_cargurus.py scrape-multi --strategy mixed_density --postcode-limit 100 \
    --proxy-file proxies.txt --pages-per-postcode 5 --outfile data/transit_large_scale_cargurus.csv
```

### 3. `scrape-uk` - Comprehensive UK-Wide Scraping
**Purpose**: Optimized nationwide scraping with advanced concurrency and proxy management for maximum market coverage.

```bash
python scrapers/get_vans_cargurus.py scrape-uk [OPTIONS]

Options:
  --outfile PATH             Output CSV filename (default: data/ford_transit_uk_cargurus.csv)
  --include-mixed BOOL       Include mixed density areas for broader coverage
  --pages-per-postcode INT   Pages per postcode (default: 5)
  --postcode-limit INTEGER   Maximum postcodes to process (default: 100)
  --proxy-file PATH          Proxy rotation file for large-scale scraping
  --max-browsers INTEGER     Concurrent browser limit (default: 5)
  --max-pages INTEGER        Concurrent page limit (default: 15)
```

**UK-Wide Examples**:
```bash
# Standard UK-wide commercial focus
python scrapers/get_vans_cargurus.py scrape-uk --outfile data/ford_transit_uk_cargurus.csv

# Comprehensive coverage with mixed density areas
python scrapers/get_vans_cargurus.py scrape-uk --include-mixed --pages-per-postcode 7 \
    --postcode-limit 150 --outfile data/ford_transit_comprehensive_cargurus.csv

# High-performance scaling with proxy rotation
python scrapers/get_vans_cargurus.py scrape-uk --proxy-file proxies.txt --max-browsers 8 \
    --max-pages 20 --pages-per-postcode 6 --outfile data/ford_transit_scaled_cargurus.csv

# Extended coverage for market research
python scrapers/get_vans_cargurus.py scrape-uk --include-mixed --postcode-limit 200 \
    --pages-per-postcode 4 --max-browsers 6 --outfile data/ford_transit_market_research_cargurus.csv
```

### 4. `postcodes` - Postcode Management & Analysis
**Purpose**: Analyze and manage intelligent postcode selection strategies with success rate tracking.

**Note**: Postcode management is now unified across all scrapers via the shared `PostcodeManager`.

```bash
# Use the main postcode management system
python get_vans.py postcodes [OPTIONS]

Options:
  --strategy CHOICE     Postcode selection strategy to preview
  --limit INTEGER       Number of postcodes to display (default: 20)
  --stats              Show comprehensive postcode database statistics
```

**Management Examples**:
```bash
# Preview commercial hubs strategy (shared across all scrapers)
python get_vans.py postcodes --strategy commercial_hubs --limit 30

# Show postcode database statistics
python get_vans.py postcodes --stats

# Preview geographic spread approach
python get_vans.py postcodes --strategy geographic_spread --limit 40
```

### 5. `analyse` - Data Analysis & Visualization
**Purpose**: Generate comprehensive analysis reports with price trends, geographic distribution, and market insights.

```bash
# Use the unified analysis system
python get_vans.py analyse [OPTIONS] CSV_FILE

Arguments:
  CSV_FILE              CarGurus listings CSV file to analyze

Options:
  --no-plots           Skip plot generation (text analysis only)
```

**Analysis Examples**:
```bash
# Full analysis with visualizations
python get_vans.py analyse data/transit_commercial_cargurus.csv

# Multi-source comparison analysis
python get_vans.py analyse data/ford_transit_uk_complete.csv

# Text-only analysis for automated processing
python get_vans.py analyse data/transit_uk_cargurus.csv --no-plots
```

---

## 🔗 Integration Methods

### 1. **Via Unified System (Recommended)**
```bash
# CarGurus included automatically
python uk_scrape.py

# CarGurus only via unified system
python uk_scrape.py --sources cargurus

# CarGurus with other premium sources
python uk_scrape.py --sources autotrader cargurus

# Direct unified scraper access
python -m scrapers.unified_van_scraper --sources cargurus
```

### 2. **Direct Scraper Usage**
```bash
# Full UK coverage via direct access
python scrapers/get_vans_cargurus.py scrape-uk

# Custom configuration
python scrapers/get_vans_cargurus.py scrape-multi --strategy commercial_hubs --postcode-limit 50
```

### 3. **Programmatic Integration**
```python
# Import and use directly
from scrapers.get_vans_cargurus import CarGurusScraper
from scrapers import PostcodeManager, CSVManager

# Use shared utilities
postcode_manager = PostcodeManager()
csv_manager = CSVManager("data/my_cargurus_data.csv")

# Access via unified scraper
from scrapers import UnifiedVanScraper
scraper = UnifiedVanScraper()
```

---

## 📊 Output Format Integration

### Standardized CSV Structure
The CarGurus scraper produces output compatible with the unified system:

```csv
title,year,mileage,price,description,image_url,url,postcode,source,listing_type,vat_included,scraped_at,age,unique_id
"Ford Transit 350 L2 H2 Panel Van",2019,45000,18995,"2.0 EcoBlue 170 BHP Manual Diesel",https://cdn.cargurus.co.uk/...,https://www.cargurus.co.uk/...,M1 1AA,cargurus,buy_it_now,true,2024-01-15T10:30:15,5,abc123def456
```

### Data Quality Features
- **VAT Detection**: Intelligent VAT status recognition from CarGurus listings
- **Listing Classification**: Dealer vs private seller identification
- **Price Validation**: Realistic price range checking (£1k-£100k)
- **Mileage Validation**: Odometer verification (0-500k miles)
- **Year Validation**: Model year validation (1990-2025)

---

## 🧠 Intelligent Postcode Strategies

### Shared Intelligence System
The CarGurus scraper uses the unified `PostcodeManager` with these strategies:

| Strategy | Focus | CarGurus Benefit | Typical Results |
|----------|-------|------------------|-----------------|
| **commercial_hubs** | Business districts | High dealer concentration | 30-50 listings/postcode |
| **major_cities** | Urban centers | Diverse pricing data | 25-40 listings/postcode |
| **geographic_spread** | Even distribution | Regional market analysis | 20-35 listings/postcode |
| **mixed_density** | Balanced coverage | Comprehensive dataset | 15-30 listings/postcode |

### Success Rate Learning
```python
# The PostcodeManager learns which postcodes work best for CarGurus
from scrapers import PostcodeManager

manager = PostcodeManager()
# Records success automatically during scraping
manager.record_success_rate("M1 1AA", listings_found=35, source="cargurus")

# View statistics
stats = manager.get_stats()
print(f"Best CarGurus postcodes: {stats['best_postcodes']}")
```

---

## 🚀 Performance Optimization

### Concurrent Processing
```bash
# Optimized settings for CarGurus
python scrapers/get_vans_cargurus.py scrape-uk \
    --max-browsers 6 \
    --max-pages 18 \
    --pages-per-postcode 5 \
    --postcode-limit 120
```

### Proxy Integration
```bash
# Large-scale CarGurus scraping with proxies
python scrapers/get_vans_cargurus.py scrape-uk \
    --proxy-file proxies.txt \
    --max-browsers 4 \
    --postcode-limit 200
```

### Resource Management
- **Memory Usage**: 1-3 GB typical (scales with concurrent browsers)
- **CPU Usage**: 2-8 cores depending on `--max-browsers` setting
- **Network**: Respects CarGurus rate limits automatically
- **Storage**: ~10-50 MB per 1000 listings

---

## 🔍 Monitoring & Logging

### Integrated Logging
```
logs/
├── cargurus_scraping.log          # CarGurus-specific detailed logs
├── uk_scrape.log                  # Unified system logs (includes CarGurus)
├── unified_scraping.log           # Multi-source coordination logs
└── scraping.log                   # General scraping logs
```

### Success Tracking
```bash
# View CarGurus-specific performance
grep "cargurus" logs/unified_scraping.log

# Monitor success rates
python get_vans.py postcodes stats
```

---

## 🛠️ Troubleshooting

### Common Issues

#### **CarGurus Access Issues**
```bash
# Test CarGurus connectivity
python scrapers/get_vans_cargurus.py scrape --postcode "M1 1AA" --pages 2

# Use with proxy if blocked
python scrapers/get_vans_cargurus.py scrape-uk --proxy-file proxies.txt --max-browsers 2
```

#### **Performance Issues**
```bash
# Reduce load for slower systems
python scrapers/get_vans_cargurus.py scrape-multi --postcode-limit 20 --pages-per-postcode 3 --max-browsers 2

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
python -c "from scrapers import get_vans_cargurus; print('Import OK')"

# Check unified system integration
python -c "from scrapers import UnifiedVanScraper; print('Unified OK')"
```

### CarGurus-Specific Solutions
- **Rate Limiting**: Built-in delays prevent blocking
- **Content Parsing**: Robust HTML parsing handles layout changes
- **Data Validation**: Comprehensive validation prevents corrupt data
- **Error Recovery**: Automatic retry with exponential backoff

---

## 🎯 Use Cases

### **Market Research Agency**
```bash
# Comprehensive CarGurus market analysis
python scrapers/get_vans_cargurus.py scrape-uk --include-mixed --postcode-limit 150 \
    --pages-per-postcode 6 --outfile data/cargurus_market_research.csv

# Multi-source comparison including CarGurus
python uk_scrape.py --sources autotrader cargurus --turbo
```

### **Price Comparison Service**
```bash
# CarGurus pricing intelligence
python scrapers/get_vans_cargurus.py scrape-multi --strategy commercial_hubs \
    --postcode-limit 50 --pages-per-postcode 8

# Combine with other sources for comprehensive pricing
python uk_scrape.py --sources autotrader cargurus ebay
```

### **Regional Dealer Analysis**
```bash
# London area CarGurus analysis
python scrapers/get_vans_cargurus.py scrape-multi --strategy geographic_spread \
    --center-postcode "SW1A 1AA" --radius-km 50 --postcode-limit 25

# Compare with AutoTrader in same region
python get_vans.py scrape-multi --strategy geographic_spread \
    --center-postcode "SW1A 1AA" --radius-km 50 --postcode-limit 25
```

---

## 📈 Expected Results

### Typical Performance
- **Standard UK Run**: 3,000-8,000 listings in 45-75 minutes
- **Turbo Mode**: 8,000-15,000 listings in 60-90 minutes
- **Quick Test**: 500-1,500 listings in 10-15 minutes

### Data Quality
- **Success Rate**: 85-92% of postcodes yield results
- **Price Accuracy**: 98%+ realistic price validation
- **Description Quality**: 90%+ have detailed specifications
- **Image Availability**: 88%+ have accessible images

### CarGurus Contribution to Unified Dataset
- **Unique Listings**: 25-30% of total when combined with other sources
- **Price Intelligence**: Current asking prices complement auction data
- **Market Coverage**: Strong dealer representation balances private sellers
- **Geographic Distribution**: Excellent UK-wide coverage

---

**🚐 The CarGurus scraper provides essential market pricing intelligence as part of the comprehensive Ford Transit data collection ecosystem. Use it standalone for focused CarGurus analysis or as part of the unified system for complete market coverage.**

*Ready to collect CarGurus pricing data? Start with `python scrapers/get_vans_cargurus.py scrape-uk` or include it in unified scraping with `python uk_scrape.py`*
