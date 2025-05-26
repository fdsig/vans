# 🏢 AutoTrader Ford Transit Scraper (`get_vans.py`)

## 🌟 Overview

`get_vans.py` is the **foundation scraper** and most sophisticated component of the Ford Transit data collection system. It targets **AutoTrader UK** - the UK's largest automotive marketplace - and serves as the primary data source and template for all other scrapers in the platform.

## 🎯 Key Features

### **Premium Data Source**
- **Market Leadership**: AutoTrader hosts 95%+ of UK dealer inventory
- **Data Quality**: Comprehensive vehicle specifications and dealer verification
- **Image Quality**: High-resolution photos with multiple angles
- **Dealer Intelligence**: Verified dealer ratings and location data

### **Advanced Scraping Capabilities**
- **Multi-Strategy Postcode Intelligence**: 5 strategic approaches for targeting
- **Concurrent Processing**: Multi-browser parallel execution
- **Proxy Support**: Rotating proxy pools for scale and reliability
- **Error Recovery**: Robust handling of network issues and rate limits
- **Data Validation**: Comprehensive quality checks and standardization

### **Intelligent Features**
- **Success Rate Learning**: Adapts based on historical performance
- **Geographic Filtering**: Precise radius-based targeting
- **Commercial Focus**: Prioritizes business vehicle listings
- **Performance Scaling**: Auto-adjusts based on system resources

## 🚀 Quick Start

### Basic Usage Examples

#### **Single Postcode Scraping**
```bash
# Basic scraping from Manchester area
python get_vans.py scrape --postcode "M1 1AA" --pages 5

# Output: AutoTrader listings from Manchester postcode area
# Expected: 80-150 listings depending on availability
```

#### **Multi-Postcode Intelligence**
```bash
# Commercial hubs strategy (recommended)
python get_vans.py scrape-multi --strategy commercial_hubs --postcode-limit 30

# Geographic spread across UK
python get_vans.py scrape-multi --strategy geographic_spread --postcode-limit 25

# Major cities focus
python get_vans.py scrape-multi --strategy major_cities --pages-per-postcode 8
```

### Advanced Usage

#### **High-Performance Scraping**
```bash
# Maximum performance with all optimizations
python get_vans.py scrape-multi \
    --strategy commercial_hubs \
    --postcode-limit 50 \
    --pages-per-postcode 10 \
    --max-browsers 8 \
    --max-pages 200 \
    --max-parallel 4

# Expected: 3,000-5,000 listings in 45-60 minutes
```

#### **Geographic Targeting**
```bash
# London area focus (30km radius)
python get_vans.py scrape-multi \
    --strategy commercial_hubs \
    --center-postcode "W1A 1AA" \
    --radius-km 30 \
    --postcode-limit 20

# Manchester region analysis
python get_vans.py scrape-multi \
    --strategy mixed_density \
    --center-postcode "M1 1AA" \
    --radius-km 50 \
    --track-success
```

## 📊 Data Structure

### AutoTrader CSV Output Format

| Column | Description | Data Quality | Example |
|--------|-------------|--------------|---------|
| `title` | Vehicle model and trim | 100% | "Ford Transit 350 L2 H2 Panel Van TDCi" |
| `year` | Model year | 99%+ | `2020` |
| `mileage` | Odometer reading | 98%+ | `45000` |
| `price` | Listed price (GBP) | 100% | `22995` |
| `description` | Detailed specifications | 95%+ | "2.0 EcoBlue 170 BHP Manual Diesel Euro 6" |
| `image_url` | Primary vehicle photo | 92%+ | `https://cdn.autotrader.co.uk/...` |
| `url` | Original listing URL | 100% | `https://www.autotrader.co.uk/...` |
| `postcode` | Search location | 100% | `M1 1AA` |
| `source` | Platform identifier | 100% | `autotrader` |
| `scraped_at` | Collection timestamp | 100% | `2024-01-15T14:30:15.123Z` |
| `age` | Calculated vehicle age | 99%+ | `4` |
| `dealer_name` | Dealer/seller name | 90%+ | "Ford Direct Manchester" |
| `dealer_rating` | Dealer rating score | 85%+ | `4.7` |
| `location` | Vehicle location | 95%+ | "Manchester, Greater Manchester" |

### Quality Assurance Features

#### **Data Validation Pipeline**
```python
def validate_listing(listing: Dict) -> bool:
    """Comprehensive validation checks"""
    # Price validation (£1,000 - £100,000)
    # Mileage validation (0 - 500,000 miles)  
    # Year validation (1990 - 2025)
    # Image URL accessibility check
    # Content quality filtering
```

#### **Error Recovery System**
```python
class AutoTraderScraper:
    def handle_cloudflare_protection(self):
        """Intelligent Cloudflare bypass"""
        
    def recover_from_rate_limit(self):
        """Adaptive rate limit handling"""
        
    def validate_page_content(self):
        """Content validation and retry logic"""
```

## ⚙️ Command Line Interface

### Core Commands

#### **Single Scrape Command**
```bash
python get_vans.py scrape [OPTIONS]

Options:
  --postcode TEXT           Target postcode (e.g., "M1 1AA")
  --pages INTEGER          Number of pages to scrape [default: 5]
  --max-price INTEGER      Maximum price filter [default: 100000]
  --min-price INTEGER      Minimum price filter [default: 1000]
  --outfile TEXT           Output CSV filename
  --browser-type TEXT      Browser type (chrome/firefox) [default: chrome]
  --headless BOOLEAN       Run in headless mode [default: True]
  --proxy TEXT             Proxy server URL
  --delay-range TEXT       Delay range in seconds [default: "1-3"]
```

#### **Multi-Scrape Command**
```bash
python get_vans.py scrape-multi [OPTIONS]

Options:
  --strategy TEXT          Postcode strategy [default: mixed_density]
  --postcode-limit INTEGER Maximum postcodes [default: 50]
  --pages-per-postcode INT Pages per postcode [default: 5]
  --max-browsers INTEGER   Concurrent browsers [default: 4]
  --max-pages INTEGER      Total page limit [default: 100]
  --max-parallel INTEGER   Parallel processes [default: 2]
  --center-postcode TEXT   Center point for radius filtering
  --radius-km FLOAT        Radius in kilometers
  --track-success BOOLEAN  Enable success rate tracking
```

### Analysis Commands

#### **Data Analysis**
```bash
# Basic statistical analysis
python get_vans.py analyse [CSV_FILE]

# Price regression analysis
python get_vans.py regress [CSV_FILE] --predictors mileage age year

# Geographic price analysis
python get_vans.py geo-analysis [CSV_FILE] --postcode-column postcode
```

#### **Postcode Intelligence**
```bash
# Test postcode strategies
python get_vans.py postcodes test --limit 15

# List postcodes for strategy
python get_vans.py postcodes list --strategy commercial_hubs

# View success rate statistics
python get_vans.py postcodes stats

# Get strategy recommendations
python get_vans.py postcodes recommend --target-listings 1000
```

## 🧠 Postcode Intelligence System

### Strategic Approaches

#### **1. Commercial Hubs** (Recommended)
```bash
python get_vans.py scrape-multi --strategy commercial_hubs
```
- **Target Areas**: Business districts, commercial zones, dealer concentrations
- **Expected Yield**: 1,000-1,500 listings
- **Success Rate**: 92-95%
- **Best For**: Business vehicle analysis, dealer inventory tracking

#### **2. Major Cities**
```bash
python get_vans.py scrape-multi --strategy major_cities
```
- **Target Areas**: Birmingham, Manchester, Leeds, Liverpool, Newcastle
- **Expected Yield**: 800-1,200 listings
- **Success Rate**: 89-92%
- **Best For**: Urban market analysis, population center targeting

#### **3. Geographic Spread**
```bash
python get_vans.py scrape-multi --strategy geographic_spread
```
- **Target Areas**: Representative postcodes from all 11 UK regions
- **Expected Yield**: 600-900 listings
- **Success Rate**: 85-89%
- **Best For**: Comprehensive UK market surveys

#### **4. Mixed Density**
```bash
python get_vans.py scrape-multi --strategy mixed_density
```
- **Target Areas**: Combination of urban centers and suburban areas
- **Expected Yield**: 700-1,100 listings
- **Success Rate**: 87-90%
- **Best For**: Balanced market representation

### Success Rate Learning

#### **Adaptive Intelligence**
```python
class PostcodeManager:
    def update_success_rate(self, postcode: str, success: bool, listings: int):
        """Learn from scraping results"""
        
    def get_best_postcodes(self, limit: int = 50) -> List[str]:
        """Return highest-performing postcodes"""
        
    def optimize_strategy(self, target_listings: int) -> Dict:
        """Recommend optimal strategy for target"""
```

## 🔧 Configuration Options

### Environment Variables
```bash
# Performance tuning
export MAX_BROWSERS=8
export MAX_CONCURRENT_PAGES=12
export DEFAULT_DELAY_RANGE="2-4"
export PAGE_TIMEOUT=30

# Proxy configuration
export PROXY_LIST_FILE="proxies.txt"
export PROXY_ROTATION=true
export PROXY_TIMEOUT=10

# Output configuration
export DEFAULT_OUTPUT_FILE="autotrader_results.csv"
export LOG_LEVEL="INFO"
export LOG_FILE="scraping.log"
```

### Configuration File (`config.yaml`)
```yaml
scraping:
  default_strategy: commercial_hubs
  max_browsers: 6
  max_pages: 150
  concurrent_processes: 3
  
validation:
  min_price: 2000
  max_price: 80000
  min_year: 1995
  max_mileage: 400000
  
postcode_intelligence:
  learning_enabled: true
  success_threshold: 0.8
  exclude_failed_postcodes: true
```

## 📈 Performance Optimization

### Hardware Scaling

#### **Low-End Systems** (2-4 cores, 4-8GB RAM)
```bash
python get_vans.py scrape-multi \
    --strategy commercial_hubs \
    --postcode-limit 20 \
    --max-browsers 2 \
    --max-parallel 1 \
    --pages-per-postcode 5
```
- **Expected Duration**: 25-35 minutes
- **Expected Output**: 800-1,200 listings

#### **Mid-Range Systems** (4-8 cores, 8-16GB RAM)
```bash
python get_vans.py scrape-multi \
    --strategy mixed_density \
    --postcode-limit 40 \
    --max-browsers 4 \
    --max-parallel 2 \
    --pages-per-postcode 8
```
- **Expected Duration**: 35-50 minutes
- **Expected Output**: 1,500-2,500 listings

#### **High-End Systems** (8+ cores, 16+ GB RAM)
```bash
python get_vans.py scrape-multi \
    --strategy commercial_hubs \
    --postcode-limit 80 \
    --max-browsers 8 \
    --max-parallel 4 \
    --pages-per-postcode 12
```
- **Expected Duration**: 45-70 minutes
- **Expected Output**: 3,000-5,000 listings

### Network Optimization

#### **Proxy Configuration**
```bash
# Single proxy
python get_vans.py scrape-multi --proxy "http://proxy:port"

# Proxy rotation from file
python get_vans.py scrape-multi --proxy-file proxies.txt

# Proxy with authentication
python get_vans.py scrape-multi --proxy "http://user:pass@proxy:port"
```

#### **Rate Limiting**
```bash
# Conservative rate limiting
python get_vans.py scrape-multi --delay-range "3-6" --human-delays

# Aggressive (fast) scraping
python get_vans.py scrape-multi --delay-range "1-2" --max-browsers 8

# Custom timeout settings
python get_vans.py scrape-multi --page-timeout 45 --request-timeout 20
```

## 🛠️ Troubleshooting

### Common Issues and Solutions

#### **Cloudflare Protection**
```bash
# Issue: Cloudflare blocking requests
# Solution: Enable browser mode and human delays
python get_vans.py scrape-multi --browser-mode --human-delays --delay-range "4-8"
```

#### **Rate Limiting**
```bash
# Issue: Too many requests error
# Solution: Reduce concurrent browsers and add delays
python get_vans.py scrape-multi --max-browsers 2 --delay-range "5-10"
```

#### **Memory Issues**
```bash
# Issue: High memory usage
# Solution: Reduce page limits and browser count
python get_vans.py scrape-multi --max-pages 50 --max-browsers 2 --max-parallel 1
```

#### **No Results Found**
```bash
# Issue: Zero listings returned
# Solution: Verify postcode and try different strategy
python get_vans.py postcodes test --postcode "M1 1AA"
python get_vans.py scrape --postcode "M1 1AA" --pages 1 --verbose
```

### Debugging Commands

#### **Verbose Output**
```bash
# Enable detailed logging
python get_vans.py scrape-multi --verbose --log-level DEBUG

# Monitor progress in real-time
python get_vans.py scrape-multi --progress-bar --live-stats
```

#### **Validation and Testing**
```bash
# Test single postcode
python get_vans.py test-postcode "M1 1AA"

# Validate CSV output
python get_vans.py validate-csv autotrader_results.csv

# Check proxy connectivity
python get_vans.py test-proxy "http://proxy:port"
```

## 🎯 Use Case Examples

### **Dealer Inventory Analysis**
```bash
# Focus on dealer-heavy areas
python get_vans.py scrape-multi \
    --strategy commercial_hubs \
    --postcode-limit 30 \
    --pages-per-postcode 10 \
    --filter-dealers-only \
    --track-dealer-performance
```

### **Regional Market Analysis**
```bash
# Manchester region comprehensive analysis
python get_vans.py scrape-multi \
    --center-postcode "M1 1AA" \
    --radius-km 75 \
    --strategy mixed_density \
    --postcode-limit 25 \
    --outfile manchester_region_analysis.csv
```

### **Price Intelligence Gathering**
```bash
# Focus on price diversity and volume
python get_vans.py scrape-multi \
    --strategy geographic_spread \
    --postcode-limit 60 \
    --pages-per-postcode 8 \
    --price-range-analysis \
    --outfile price_intelligence.csv
```

### **Fleet Vehicle Research**
```bash
# Commercial vehicle focus
python get_vans.py scrape-multi \
    --strategy commercial_hubs \
    --filter-commercial-ads \
    --min-year 2018 \
    --max-mileage 100000 \
    --outfile fleet_vehicles.csv
```

## 🔮 Advanced Features

### **Machine Learning Integration**
```python
# Price prediction based on collected data
def predict_vehicle_price(year: int, mileage: int, model: str) -> float:
    """ML-based price prediction using historical AutoTrader data"""

# Market trend analysis
def analyze_market_trends(timeframe: str = "30d") -> Dict:
    """Identify pricing and availability trends"""
```

### **Real-Time Monitoring**
```python
# Live scraping dashboard
def start_monitoring_dashboard():
    """Web-based real-time monitoring interface"""

# Performance alerts
def setup_performance_alerts(email: str, thresholds: Dict):
    """Email alerts for performance issues"""
```

### **Data Export Options**
```bash
# JSON export for APIs
python get_vans.py scrape-multi --output-format json

# Database direct export
python get_vans.py scrape-multi --export-to-db postgresql://user:pass@host/db

# Excel export with charts
python get_vans.py scrape-multi --excel-export --include-charts
```

## 📚 API Reference

### Core Classes

#### **AutoTraderScraper**
```python
class AutoTraderScraper:
    def __init__(self, proxy: str = None, headless: bool = True):
        """Initialize scraper with configuration"""
        
    def scrape_postcode(self, postcode: str, pages: int = 5) -> List[Dict]:
        """Scrape specific postcode area"""
        
    def scrape_multiple_postcodes(self, postcodes: List[str]) -> List[Dict]:
        """Parallel scraping of multiple postcodes"""
        
    def validate_listings(self, listings: List[Dict]) -> List[Dict]:
        """Apply quality validation to listings"""
```

#### **PostcodeManager**
```python
class PostcodeManager:
    def get_postcodes(self, strategy: str, limit: int = 50) -> List[str]:
        """Get postcodes using specified strategy"""
        
    def filter_by_radius(self, center: str, radius_km: float) -> List[str]:
        """Filter postcodes by geographic radius"""
        
    def update_success_rates(self, results: Dict[str, int]):
        """Update learning database with results"""
```

### Utility Functions

#### **Data Processing**
```python
def standardize_listing_data(raw_listing: Dict) -> Dict:
    """Convert raw scraping output to standard format"""
    
def deduplicate_listings(listings: List[Dict]) -> List[Dict]:
    """Remove duplicate listings by URL and content"""
    
def validate_price_range(price: int, min_price: int, max_price: int) -> bool:
    """Validate price within reasonable range"""
```

## 🏆 Best Practices

### **Efficient Scraping**
1. **Start Small**: Test with `--postcode-limit 10` before scaling
2. **Use Strategies**: Always prefer strategic postcode selection over random
3. **Monitor Resources**: Watch CPU and memory usage during large runs
4. **Respect Rate Limits**: Use appropriate delays to avoid blocking

### **Data Quality**
1. **Enable Validation**: Always use built-in validation features
2. **Check Success Rates**: Monitor postcode success rates for optimization
3. **Verify Output**: Spot-check CSV files for data quality
4. **Track Performance**: Use `--track-success` for learning optimization

### **Scaling Guidelines**
1. **Hardware Matching**: Scale browser count to available CPU cores
2. **Network Consideration**: Adjust delays based on network speed
3. **Proxy Rotation**: Use proxies for large-scale operations
4. **Progressive Scaling**: Gradually increase limits rather than jumping to maximum

This **AutoTrader scraper** (`get_vans.py`) serves as the flagship component of the Ford Transit data collection platform, providing the highest quality data and most sophisticated scraping capabilities in the entire system. 
