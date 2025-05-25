# Ford Transit UK-Wide Scraping Guide

## Overview

The enhanced `get_vans.py` script now includes powerful UK-wide scraping capabilities with intelligent postcode selection, focusing on commercial and industrial areas where Ford Transits are most commonly found.

## Key Features

### 🎯 **Smart Postcode Selection**
- **Commercial Hubs Strategy**: Automatically targets areas with high commercial vehicle activity
- **Industrial Areas Focus**: Prioritizes business districts, transport hubs, and commercial zones
- **Geographic Distribution**: Ensures coverage across all UK regions

### 📋 **Enhanced Data Collection**
- **Van Descriptions**: Detailed vehicle specifications and features
- **Image URLs**: Direct links to vehicle photos
- **Complete Listings**: Title, year, mileage, price, postcode, and more
- **Commercial Focus**: Optimized for areas with highest van density

### ⚡ **High-Performance Scraping**
- **Concurrent Processing**: Multiple browsers and pages simultaneously
- **Proxy Support**: Built-in proxy rotation for large-scale scraping
- **Intelligent Throttling**: Human-like delays to avoid detection
- **Error Recovery**: Automatic retry with different proxies

## Quick Start

### Basic UK-Wide Scraping
```bash
python get_vans.py scrape-uk
```

This will:
- Use 100 commercial hub postcodes across the UK
- Scrape 5 pages per postcode
- Save results to `ford_transit_uk_complete.csv`
- Include descriptions and image URLs

### Enhanced Coverage
```bash
python get_vans.py scrape-uk --include-mixed --postcode-limit 150 --pages-per-postcode 8
```

### High-Performance with Proxies
```bash
python get_vans.py scrape-uk --proxy-file proxies.txt --max-browsers 10 --max-pages 40
```

## Command Options

| Option | Default | Description |
|--------|---------|-------------|
| `--outfile` | `ford_transit_uk_complete.csv` | Output CSV filename |
| `--pages-per-postcode` | `5` | Pages to scrape per postcode |
| `--postcode-limit` | `100` | Number of postcodes to use |
| `--include-mixed` | `False` | Include mixed density areas |
| `--proxy-file` | `None` | File containing proxy URLs |
| `--max-browsers` | `8` | Max concurrent browsers |
| `--max-pages` | `30` | Max concurrent pages |

## Output CSV Structure

The resulting CSV file includes these columns:

| Column | Description | Example |
|--------|-------------|---------|
| `title` | Vehicle title/model | "Ford Transit 350 L2 H2 Panel Van" |
| `year` | Manufacturing year | `2019` |
| `mileage` | Vehicle mileage | `45000` |
| `price` | Listed price (GBP) | `18995` |
| `description` | Detailed specs and features | "2.0 EcoBlue 170 BHP \| Manual \| Diesel" |
| `image_url` | URL to vehicle image | `https://cdn.autotrader.co.uk/...` |
| `url` | Link to original listing | `https://www.autotrader.co.uk/...` |
| `postcode` | Search postcode used | `M1 1AA` |
| `age` | Calculated vehicle age | `5` |

## Commercial Hub Postcodes

The script automatically targets these types of areas:

### Major Commercial Centers
- **London**: Westminster, West End, Southwark, City areas
- **Manchester**: Central business districts and industrial zones
- **Birmingham**: Commercial quarters and transport hubs
- **Leeds**: Business parks and commercial areas

### Industrial Areas
- **Sheffield**: Manufacturing and steel industry zones
- **Bristol**: Port and industrial areas
- **Newcastle**: Industrial estates and business parks
- **Cardiff**: Commercial and port areas

### Regional Commercial Hubs
- **Glasgow/Edinburgh**: Scottish commercial centers
- **Nottingham**: East Midlands commercial zones
- **Coventry**: West Midlands industrial areas
- **Reading**: Thames Valley business areas

## Best Practices

### For Maximum Coverage
```bash
# Comprehensive UK scraping with mixed areas
python get_vans.py scrape-uk \
    --include-mixed \
    --postcode-limit 200 \
    --pages-per-postcode 10 \
    --outfile comprehensive_uk_transits.csv
```

### For High-Speed Scraping
```bash
# Fast scraping with proxies
python get_vans.py scrape-uk \
    --proxy-file proxies.txt \
    --max-browsers 12 \
    --max-pages 50 \
    --pages-per-postcode 6
```

### For Testing/Development
```bash
# Quick test run
python uk_scrape_demo.py --quick
```

## Proxy Configuration

Create a `proxies.txt` file with one proxy per line:
```
http://username:password@proxy1.example.com:8080
http://username:password@proxy2.example.com:8080
socks5://username:password@proxy3.example.com:1080
```

## Performance Expectations

### Typical Results
- **Postcodes Covered**: 100-200 across UK
- **Listings per Postcode**: 20-50 on average
- **Total Listings**: 2,000-10,000 Ford Transits
- **Scraping Time**: 30-90 minutes
- **CSV File Size**: 1-10 MB

### Success Rates
- **Commercial Hubs**: 85-95% successful postcodes
- **Mixed Areas**: 70-85% successful postcodes
- **Image URLs**: 90%+ of listings
- **Descriptions**: 95%+ of listings

## Monitoring and Logs

The script provides detailed logging:
```
2024-01-15 10:30:15 - INFO - Starting UK-wide Ford Transit scraping:
2024-01-15 10:30:15 - INFO -   Strategy: Commercial Hubs
2024-01-15 10:30:15 - INFO -   Postcodes: 100
2024-01-15 10:30:15 - INFO -   Pages per postcode: 5
2024-01-15 10:30:15 - INFO -   Expected fields: title, year, mileage, price, description, image_url, url, postcode
```

## Troubleshooting

### Common Issues

**No results found**
- Check internet connection
- Verify AutoTrader site is accessible
- Try reducing concurrency settings

**Cloudflare protection**
- Use proxy rotation with `--proxy-file`
- Reduce `--max-browsers` and `--max-pages`
- Add longer delays between requests

**Memory issues**
- Reduce `--max-browsers` (try 3-5)
- Reduce `--max-pages` (try 10-20)
- Process in smaller batches

### Getting Help

For issues or questions:
1. Check the log file `scraping.log`
2. Try the demo script with `--quick` flag
3. Reduce concurrency settings
4. Verify proxy configuration if using proxies

## Advanced Usage

### Custom Postcode Analysis
```bash
# Analyze postcode strategies
python get_vans.py postcodes list --strategy commercial_hubs --limit 50
python get_vans.py postcodes stats
```

### Geographic Filtering
```bash
# Focus on specific regions (e.g., 50km around Manchester)
python get_vans.py scrape-multi \
    --strategy commercial_hubs \
    --center-postcode "M1 1AA" \
    --radius-km 50 \
    --postcode-limit 30
```

### Data Analysis
```bash
# Quick analysis of results
python get_vans.py analyse ford_transit_uk_complete.csv

# Regression analysis
python get_vans.py regress ford_transit_uk_complete.csv --predictors mileage age
```

---

**Happy scraping! 🚐📊** 
