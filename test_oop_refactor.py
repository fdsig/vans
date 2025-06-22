#!/usr/bin/env python3
"""
Test Script for OOP Refactor
============================

This script tests the refactored object-oriented uk_scrape.py to ensure
all imports work correctly and the main classes can be instantiated.
"""

import sys
from pathlib import Path

def test_scrapers_import():
    """Test importing scrapers as submodules"""
    print("🧪 Testing scrapers package import...")
    
    try:
        from scrapers import (
            PostcodeStrategy, 
            PostcodeManager, 
            CSVManager, 
            ScrapingResult,
            UnifiedVanScraper
        )
        print("✅ Successfully imported scrapers submodules")
        return True
    except ImportError as e:
        print(f"❌ Failed to import scrapers: {e}")
        return False

def test_system_resources_manager():
    """Test SystemResourcesManager class"""
    print("🧪 Testing SystemResourcesManager...")
    
    try:
        # Import the class from uk_scrape module
        sys.path.append('.')
        from uk_scrape import SystemResourcesManager
        
        # Test instantiation
        manager = SystemResourcesManager()
        system_info = manager.system_info
        
        print(f"✅ SystemResourcesManager working - detected {system_info['cpu_cores']} cores, {system_info['ram_gb']:.1f}GB RAM")
        
        # Test settings calculation
        settings = manager.calculate_optimal_settings("quick")
        print(f"✅ Settings calculation working - quick mode: {settings['postcode_limit']} postcodes")
        
        return True
    except Exception as e:
        print(f"❌ SystemResourcesManager test failed: {e}")
        return False

def test_uk_ford_transit_scraper():
    """Test UKFordTransitScraper class"""
    print("🧪 Testing UKFordTransitScraper...")
    
    try:
        from uk_scrape import UKFordTransitScraper
        from scrapers import UNIFIED_SCRAPER_AVAILABLE
        
        # Test instantiation
        scraper = UKFordTransitScraper("test_output.csv")
        print("✅ UKFordTransitScraper instantiated successfully")
        
        # Test system requirements validation
        valid = scraper.validate_system_requirements("quick")
        print(f"✅ System requirements validation working - quick mode valid: {valid}")
        
        if not UNIFIED_SCRAPER_AVAILABLE:
            print("⚠️  Note: UnifiedVanScraper not fully available - this is expected in some environments")
        
        return True
    except Exception as e:
        print(f"❌ UKFordTransitScraper test failed: {e}")
        return False

def test_postcode_manager():
    """Test PostcodeManager functionality"""
    print("🧪 Testing PostcodeManager...")
    
    try:
        from scrapers import PostcodeManager, PostcodeStrategy
        
        manager = PostcodeManager()
        postcodes = manager.get_postcodes(PostcodeStrategy.COMMERCIAL_HUBS, limit=5)
        
        print(f"✅ PostcodeManager working - got {len(postcodes)} postcodes: {postcodes}")
        return True
    except Exception as e:
        print(f"❌ PostcodeManager test failed: {e}")
        return False

def test_csv_manager():
    """Test CSVManager functionality"""
    print("🧪 Testing CSVManager...")
    
    try:
        from scrapers import CSVManager
        
        # Create test CSV in data directory
        Path("data").mkdir(exist_ok=True)
        csv_path = "data/test_csv_manager.csv"
        
        manager = CSVManager(csv_path)
        stats = manager.get_stats()
        
        print(f"✅ CSVManager working - stats: {stats}")
        
        # Clean up test file
        if Path(csv_path).exists():
            Path(csv_path).unlink()
        
        return True
    except Exception as e:
        print(f"❌ CSVManager test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting OOP Refactor Tests")
    print("=" * 50)
    
    tests = [
        test_scrapers_import,
        test_system_resources_manager,
        test_uk_ford_transit_scraper,
        test_postcode_manager,
        test_csv_manager
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            print()
    
    print("=" * 50)
    print(f"🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! OOP refactor is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
