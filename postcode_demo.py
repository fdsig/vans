#!/usr/bin/env python3
"""
PostcodeManager Demo Script
==========================

Demonstrates the enhanced postcode management features for van scraping.
"""

from get_vans import PostcodeManager, PostcodeStrategy

def main():
    print("🚐 Ford Transit Van Scraping - Enhanced Postcode Management Demo")
    print("=" * 65)
    
    # Initialize the manager
    manager = PostcodeManager()
    
    # Show basic stats
    stats = manager.get_stats()
    print(f"\n📊 Postcode Database Stats:")
    print(f"   • Total areas: {stats['total_areas']}")
    print(f"   • High commercial areas: {stats['high_commercial_areas']}")
    print(f"   • Regions: {', '.join(stats['regions'])}")
    
    print(f"\n🎯 Strategy Demonstrations:")
    print("-" * 40)
    
    # Demo 1: Major Cities Strategy
    print("\n1️⃣  MAJOR_CITIES Strategy (High population density)")
    postcodes = manager.get_postcodes(
        strategy=PostcodeStrategy.MAJOR_CITIES,
        limit=8,
        exclude_used=False
    )
    print(f"   Generated: {', '.join(postcodes[:5])}...")
    
    # Demo 2: Commercial Hubs Strategy  
    print("\n2️⃣  COMMERCIAL_HUBS Strategy (High business activity)")
    postcodes = manager.get_postcodes(
        strategy=PostcodeStrategy.COMMERCIAL_HUBS,
        limit=8,
        exclude_used=False
    )
    print(f"   Generated: {', '.join(postcodes[:5])}...")
    
    # Demo 3: Geographic Spread Strategy
    print("\n3️⃣  GEOGRAPHIC_SPREAD Strategy (Even distribution)")
    postcodes = manager.get_postcodes(
        strategy=PostcodeStrategy.GEOGRAPHIC_SPREAD,
        limit=10,
        exclude_used=False
    )
    print(f"   Generated: {', '.join(postcodes[:5])}...")
    
    # Demo 4: Geographic Filtering
    print("\n4️⃣  Geographic Filtering (50km around Manchester)")
    postcodes = manager.get_postcodes(
        strategy=PostcodeStrategy.MIXED_DENSITY,
        limit=12,
        exclude_used=False,
        center_postcode="M1",
        geographic_radius_km=50
    )
    print(f"   Generated: {', '.join(postcodes[:6])}...")
    
    # Demo 5: Success Rate Simulation
    print("\n5️⃣  Success Rate Learning Simulation")
    print("   Simulating successful scrapes...")
    
    # Simulate some successful scrapes
    test_postcodes = ["M1 1AA", "B1 2BB", "SW1 3CC", "LS1 4DD"]
    success_counts = [12, 8, 15, 5]  # Simulated listing counts
    
    for pc, count in zip(test_postcodes, success_counts):
        manager.record_success_rate(pc, count)
        area_code = pc.split()[0]
        rate = manager._success_rates.get(area_code, 0)
        print(f"   • {pc}: {count} listings found → success rate: {rate:.2f}")
    
    # Show how success rates affect selection
    print("\n6️⃣  Intelligent Selection (using learned success rates)")
    postcodes = manager.get_postcodes(
        strategy=PostcodeStrategy.MIXED_DENSITY,
        limit=8,
        exclude_used=False
    )
    print(f"   Top performers prioritized: {', '.join(postcodes[:5])}...")
    
    print(f"\n🚀 Example Usage Commands:")
    print("-" * 30)
    print("# Test different strategies:")
    print("python get_vans.py postcodes test --limit 10")
    print()
    print("# Smart commercial scraping:")
    print("python get_vans.py scrape-multi --strategy commercial_hubs \\")
    print("    --postcode-limit 25 --pages-per-postcode 5")
    print()
    print("# Geographic focus around London:")
    print("python get_vans.py scrape-multi --center-postcode 'SW1 1AA' \\")
    print("    --radius-km 30 --strategy mixed_density")
    
    print(f"\n✅ Demo complete! The PostcodeManager is ready for intelligent scraping.")

if __name__ == "__main__":
    main() 
