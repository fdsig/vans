# Unified Ford Transit UK Scraping System

## 🚐 Overview

This comprehensive scraping system combines **ALL available sources** to create a unified Ford Transit dataset. Instead of running multiple scrapers separately and manually combining results, this system orchestrates all sources automatically with intelligent deduplication and optimization.

## 🔗 Sources Integrated

| Source | Type | Key Features |
|--------|------|-------------|
| **AutoTrader** | Premium dealers | Most comprehensive dealer network |
| **CarGurus** | Mixed dealers/private | Current asking prices from all sellers |
| **eBay** | Auctions/Buy-It-Now | Auction prices and immediate sales |
| **Gumtree** | Private/trade | Private seller focus, trade ads |
| **Facebook Marketplace** | Social | Local community sales |

## 🎯 Key Features

- **Single Unified Output**: All sources → one `ford_transit_uk_complete.csv`
- **Intelligent Deduplication**: Prevents duplicates across all sources
- **Iterative Growth**: Multiple runs add new data without loss
- **Parallel Execution**: 3-5 scrapers run simultaneously 
- **Shared Intelligence**: Postcode success tracking across sources
- **Standardized Format**: Consistent columns across all sources

## 📊 Output Format

The unified CSV contains these standardized columns:

| Column | Description |
|--------|-------------|
| `title` | Vehicle title/name |
| `year` | Manufacturing year |
| `mileage` | Vehicle mileage |
| `price` | Listed price in GBP |
| `description` | Detailed specs and features |
| `image_url` | URL to vehicle image |
| `url` | Link to original listing |
| `postcode` | Search postcode used |
| `source` | Source website (autotrader, cargurus, ebay, gumtree, facebook) |
| `scraped_at` | Timestamp when scraped |
| `age` | Calculated vehicle age |
| `unique_id` | Unique identifier for deduplication |

## 🚀 Quick Start

### Basic Usage (All Sources)
```bash
python uk_scrape_demo.py
```
*Runs all 5 sources with default settings (~60-120 minutes)*

### Quick Test
```bash
python uk_scrape_demo.py --quick
```
*Reduced settings for testing (~10-20 minutes)*

### Intensive Scraping
```bash
python uk_scrape_demo.py --intensive
```
*Maximum data collection (~2-4 hours)*

### Specific Sources Only
```bash
python uk_scrape_demo.py --sources autotrader cargurus ebay
```
*Run only selected sources*

## ⚙️ Configuration Options

### Coverage Settings
- `--postcode-limit N` - Number of postcodes per source (default: 100)
- `--pages-per-postcode N` - Pages to scrape per postcode (default: 5)
- `--include-mixed` - Include mixed density areas for broader coverage

### Performance Settings
- `--max-parallel N` - Maximum scrapers running simultaneously (default: 3)
- `--max-browsers N` - Maximum browsers per source (default: 5)
- `--max-pages N` - Maximum pages per source (default: 50)

### Proxy Support
- `--proxy-file proxies.txt` - Use proxy rotation for large-scale scraping

### Output Control
- `--outfile filename.csv` - Custom output filename (default: ford_transit_uk_complete.csv)

## 🧠 Intelligent Features

### Deduplication Strategy
1. **Primary**: URL-based deduplication (most reliable)
2. **Secondary**: Content hash from title + price + mileage + year
3. **Persistence**: Remembers seen listings across runs

### Postcode Intelligence
- **Commercial Hubs**: Focuses on areas with high commercial vehicle activity
- **Success Tracking**: Learns which postcodes yield most listings
- **Geographic Distribution**: Ensures even UK coverage
- **SQLite Database**: Persistent storage of scraping patterns

### Error Handling
- **Graceful Failures**: If one source fails, others continue
- **Timeout Management**: Prevents hanging on unresponsive sites
- **Retry Logic**: Intelligent retry with exponential backoff

## 📈 Performance Monitoring

### Real-time Progress
```
🚐 Starting UK-wide MULTI-SOURCE Ford Transit scraping...
🔗 Sources: AutoTrader + CarGurus + eBay + Gumtree + Facebook
⏱️  This may take 60-120 minutes depending on your settings
📊 Expected output: ford_transit_uk_complete.csv with ALL sources combined
🔄 Results are appended iteratively with intelligent deduplication
```

### Final Statistics
```
✅ Multi-source scraping completed successfully!
📁 Output saved to: ford_transit_uk_complete.csv
📊 File size: 15.2 MB
📈 Total records: 12,847
📊 Records by source:
   • autotrader: 4,521 records
   • cargurus: 3,108 records
   • ebay: 2,789 records
   • gumtree: 1,643 records
   • facebook: 786 records
💰 Price range: £2,500 - £89,950
💰 Median price: £18,500
```

## 🏗️ System Architecture

### Component Overview
```
uk_scrape_demo.py           # User interface
       ↓
unified_van_scraper.py      # Orchestration layer
       ↓
van_scraping_utils.py       # Shared utilities
       ↓
Individual scrapers         # Source-specific tools
```

### Data Flow
```
Individual scrapers → Parallel execution → Result standardization → 
Deduplication → Unified CSV append → Progress reporting
```

## 🔧 Troubleshooting

### Common Issues

**"unified_van_scraper.py not found"**
- Ensure all files are in the same directory
- Check that van_scraping_utils.py exists

**"No results from [source]"**
- Source may be temporarily unavailable
- Check internet connection
- Try with proxy rotation

**"Permission denied writing CSV"**
- Check file permissions
- Close Excel/other apps that might lock the file
- Use a different output filename

### Performance Optimization

**Slow scraping?**
- Reduce `--postcode-limit` for testing
- Increase `--max-parallel` if you have good hardware
- Use `--proxy-file` for large-scale scraping

**Too many timeouts?**
- Reduce `--max-browsers` per source
- Add delays between requests
- Check your internet connection stability

## 📋 File Dependencies

Required files in the same directory:
- `uk_scrape_demo.py` - Main interface
- `unified_van_scraper.py` - Orchestrator
- `van_scraping_utils.py` - Shared utilities
- `get_vans.py` - AutoTrader scraper
- `get_vans_cargurus.py` - CarGurus scraper
- `get_vans_ebay.py` - eBay scraper
- `get_vans_gumtree.py` - Gumtree scraper
- `get_vans_facebook.py` - Facebook scraper

## 💡 Usage Examples

### Market Research
```bash
# Comprehensive UK-wide dataset
python uk_scrape_demo.py --intensive --include-mixed --outfile complete_market_analysis.csv
```

### Regional Focus
```bash
# Focus on specific regions with custom postcodes
python uk_scrape_demo.py --sources autotrader cargurus --postcode-limit 50
```

### Quick Price Check
```bash
# Fast scan of current market
python uk_scrape_demo.py --quick --sources cargurus ebay
```

### High-Volume Collection
```bash
# Maximum data collection with proxies
python uk_scrape_demo.py --intensive --proxy-file proxies.txt --max-parallel 5
```

## 🎉 Benefits Over Manual Scraping

| Manual Approach | Unified System |
|----------------|---------------|
| Multiple output files | Single unified CSV |
| Manual deduplication | Automatic deduplication |
| Inconsistent formats | Standardized format |
| Sequential execution | Parallel execution |
| No shared intelligence | Shared postcode learning |
| Manual result merging | Automatic appending |

## 🔄 Iterative Usage

The system is designed for iterative data collection:

1. **First run**: Collects initial dataset
2. **Subsequent runs**: Add new listings, skip existing ones
3. **No data loss**: Previous results are preserved
4. **Smart updates**: Only scrapes new or changed content

This allows for:
- Daily/weekly market monitoring
- Gradual database building
- Fresh data collection without starting over
- Historical price tracking

---

*For technical support or feature requests, check the individual scraper documentation or review the source code.*
