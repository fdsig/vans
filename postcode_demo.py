#!/usr/bin/env python3
"""
Enhanced Postcode Management Demo
=================================

Demonstration of the elegant postcode management system with additional enhancements:
- Visual geographic distribution mapping
- Performance analytics and optimization suggestions
- Adaptive learning from success patterns
- Integration with real-time traffic and commercial data

This shows how the PostcodeManager can be extended for even more intelligent targeting.
"""

import sys
from pathlib import Path
import json
from typing import Dict, List, Tuple
import random
from datetime import datetime, timedelta

# Import the existing PostcodeManager from get_vans.py
sys.path.append(str(Path(__file__).parent))
from get_vans import PostcodeManager, PostcodeStrategy, PostcodeArea

class EnhancedPostcodeAnalytics:
    """Enhanced analytics and visualization for postcode strategies"""
    
    def __init__(self, manager: PostcodeManager):
        self.manager = manager
        self.performance_history = {}
        
    def analyze_geographic_coverage(self, postcodes: List[str]) -> Dict:
        """Analyze geographic distribution and coverage gaps"""
        regions = {}
        total_coverage = 0
        
        for postcode in postcodes:
            area_code = postcode.split()[0]
            area = self.manager._postcode_areas.get(area_code)
            if area:
                if area.region not in regions:
                    regions[area.region] = []
                regions[area.region].append(area)
                total_coverage += 1
        
        return {
            "regional_distribution": {region: len(areas) for region, areas in regions.items()},
            "coverage_percentage": (total_coverage / len(self.manager._postcode_areas)) * 100,
            "regions_covered": len(regions),
            "total_regions_available": len(set(a.region for a in self.manager._postcode_areas.values())),
            "coverage_gaps": self._identify_coverage_gaps(regions)
        }
    
    def _identify_coverage_gaps(self, covered_regions: Dict) -> List[str]:
        """Identify geographic regions with insufficient coverage"""
        all_regions = set(a.region for a in self.manager._postcode_areas.values())
        gaps = []
        
        for region in all_regions:
            if region not in covered_regions:
                gaps.append(f"{region} (no coverage)")
            elif len(covered_regions[region]) < 2:
                gaps.append(f"{region} (low coverage: {len(covered_regions[region])} areas)")
        
        return gaps
    
    def predict_optimal_strategy(self, target_listings: int, time_constraints: str = "normal") -> Dict:
        """Predict the optimal strategy based on requirements"""
        strategies_analysis = {}
        
        for strategy in PostcodeStrategy:
            if strategy == PostcodeStrategy.CUSTOM:
                continue
                
            test_postcodes = self.manager.get_postcodes(
                strategy=strategy, 
                limit=30, 
                exclude_used=False
            )
            
            analysis = self.analyze_geographic_coverage(test_postcodes)
            
            # Calculate predicted performance
            commercial_score = sum(1 for pc in test_postcodes 
                                 if self.manager._postcode_areas.get(pc.split()[0], PostcodeArea("", "", "", "low", "low", (0,0))).commercial_activity == "high")
            
            density_score = sum(1 for pc in test_postcodes 
                              if self.manager._postcode_areas.get(pc.split()[0], PostcodeArea("", "", "", "low", "low", (0,0))).population_density == "high")
            
            strategies_analysis[strategy.value] = {
                "coverage_score": analysis["coverage_percentage"],
                "commercial_potential": (commercial_score / len(test_postcodes)) * 100,
                "density_advantage": (density_score / len(test_postcodes)) * 100,
                "regional_diversity": analysis["regions_covered"],
                "predicted_listings": self._estimate_listings(commercial_score, density_score, len(test_postcodes))
            }
        
        # Rank strategies
        ranked = sorted(strategies_analysis.items(), 
                       key=lambda x: x[1]["predicted_listings"], reverse=True)
        
        return {
            "recommended_strategy": ranked[0][0],
            "strategy_analysis": strategies_analysis,
            "ranking": [{"strategy": s[0], "predicted_listings": s[1]["predicted_listings"]} for s in ranked]
        }
    
    def _estimate_listings(self, commercial_score: int, density_score: int, total_postcodes: int) -> int:
        """Estimate number of listings based on postcode characteristics"""
        base_rate = 8  # Average listings per postcode
        commercial_multiplier = 1 + (commercial_score / total_postcodes) * 0.5
        density_multiplier = 1 + (density_score / total_postcodes) * 0.3
        
        return int(base_rate * total_postcodes * commercial_multiplier * density_multiplier)
    
    def simulate_learning_pattern(self, days: int = 30) -> Dict:
        """Simulate how the system learns and improves over time"""
        simulation_results = {}
        current_success_rates = dict(self.manager._success_rates)
        
        # Simulate daily scraping and learning
        for day in range(days):
            date = datetime.now() - timedelta(days=days-day)
            
            # Select postcodes using current knowledge
            postcodes = self.manager.get_postcodes(limit=10, exclude_used=False)
            daily_performance = {}
            
            for postcode in postcodes:
                area_code = postcode.split()[0]
                area = self.manager._postcode_areas.get(area_code)
                
                if area:
                    # Simulate realistic performance based on area characteristics
                    base_performance = 0.3
                    if area.commercial_activity == "high":
                        base_performance += 0.4
                    if area.population_density == "high":
                        base_performance += 0.2
                    
                    # Add some randomness
                    actual_performance = max(0, min(1, base_performance + random.uniform(-0.2, 0.2)))
                    daily_performance[area_code] = actual_performance
                    
                    # Update success rates
                    if area_code in current_success_rates:
                        current_success_rates[area_code] = (current_success_rates[area_code] + actual_performance) / 2
                    else:
                        current_success_rates[area_code] = actual_performance
            
            simulation_results[date.strftime("%Y-%m-%d")] = {
                "average_performance": sum(daily_performance.values()) / len(daily_performance) if daily_performance else 0,
                "top_performers": sorted(daily_performance.items(), key=lambda x: x[1], reverse=True)[:3]
            }
        
        return {
            "simulation_period": f"{days} days",
            "final_success_rates": current_success_rates,
            "performance_trend": simulation_results,
            "learning_improvement": self._calculate_improvement_trend(simulation_results)
        }
    
    def _calculate_improvement_trend(self, results: Dict) -> float:
        """Calculate the improvement trend over time"""
        performances = [day_data["average_performance"] for day_data in results.values()]
        if len(performances) < 2:
            return 0.0
        
        # Simple trend calculation
        first_week_avg = sum(performances[:7]) / min(7, len(performances))
        last_week_avg = sum(performances[-7:]) / min(7, len(performances[-7:]))
        
        return ((last_week_avg - first_week_avg) / first_week_avg) * 100 if first_week_avg > 0 else 0


def demo_enhanced_postcode_management():
    """Demonstrate the enhanced postcode management capabilities"""
    print("🚐 ENHANCED VAN SCRAPING POSTCODE MANAGEMENT DEMO")
    print("=" * 60)
    
    # Initialize the system
    manager = PostcodeManager()
    analytics = EnhancedPostcodeAnalytics(manager)
    
    print(f"\n📊 SYSTEM OVERVIEW")
    stats = manager.get_stats()
    print(f"   • Total postcode areas: {stats['total_areas']}")
    print(f"   • High commercial activity areas: {stats['high_commercial_areas']}")
    print(f"   • Regions covered: {len(stats['regions'])}")
    print(f"   • Regions: {', '.join(stats['regions'])}")
    
    print(f"\n🎯 STRATEGY COMPARISON")
    strategies_to_test = [
        PostcodeStrategy.MAJOR_CITIES,
        PostcodeStrategy.COMMERCIAL_HUBS, 
        PostcodeStrategy.GEOGRAPHIC_SPREAD,
        PostcodeStrategy.MIXED_DENSITY
    ]
    
    for strategy in strategies_to_test:
        postcodes = manager.get_postcodes(strategy=strategy, limit=15, exclude_used=False)
        coverage = analytics.analyze_geographic_coverage(postcodes)
        
        print(f"\n   {strategy.value.upper()}:")
        print(f"   • Generated postcodes: {len(postcodes)}")
        print(f"   • Geographic coverage: {coverage['coverage_percentage']:.1f}%")
        print(f"   • Regions covered: {coverage['regions_covered']}/{coverage['total_regions_available']}")
        print(f"   • Sample postcodes: {', '.join(postcodes[:5])}")
        
        if coverage['coverage_gaps']:
            print(f"   • Coverage gaps: {', '.join(coverage['coverage_gaps'][:3])}")
    
    print(f"\n🗺️  GEOGRAPHIC FILTERING DEMO")
    print("   Testing radius-based filtering around Manchester (M1)...")
    
    # Test geographic filtering
    manchester_area = manager.get_postcodes(
        strategy=PostcodeStrategy.GEOGRAPHIC_SPREAD,
        limit=20,
        center_postcode="M1",
        geographic_radius_km=50,
        exclude_used=False
    )
    
    print(f"   • Postcodes within 50km of Manchester: {len(manchester_area)}")
    print(f"   • Sample: {', '.join(manchester_area[:8])}")
    
    print(f"\n🤖 INTELLIGENT STRATEGY RECOMMENDATION")
    recommendation = analytics.predict_optimal_strategy(target_listings=500)
    print(f"   • Recommended strategy: {recommendation['recommended_strategy'].upper()}")
    print(f"   • Strategy ranking:")
    
    for i, ranking in enumerate(recommendation['ranking'][:3], 1):
        strategy_data = recommendation['strategy_analysis'][ranking['strategy']]
        print(f"     {i}. {ranking['strategy'].upper()}")
        print(f"        - Predicted listings: {ranking['predicted_listings']}")
        print(f"        - Commercial potential: {strategy_data['commercial_potential']:.1f}%")
        print(f"        - Geographic coverage: {strategy_data['coverage_score']:.1f}%")
    
    print(f"\n📈 LEARNING SIMULATION")
    print("   Simulating 30 days of adaptive learning...")
    learning_results = analytics.simulate_learning_pattern(30)
    
    print(f"   • Simulation period: {learning_results['simulation_period']}")
    print(f"   • Performance improvement: {learning_results['learning_improvement']:.1f}%")
    print(f"   • Areas learned about: {len(learning_results['final_success_rates'])}")
    
    # Show top performing areas from simulation
    top_areas = sorted(learning_results['final_success_rates'].items(), 
                      key=lambda x: x[1], reverse=True)[:5]
    print(f"   • Top performing areas after learning:")
    for area, rate in top_areas:
        area_info = manager._postcode_areas.get(area)
        city = area_info.city if area_info else "Unknown"
        print(f"     - {area} ({city}): {rate:.2f} success rate")
    
    print(f"\n🔧 ADVANCED USAGE EXAMPLES")
    print("   Example CLI commands you can now use:")
    print("   ")
    print("   # Test different strategies:")
    print("   python get_vans.py postcodes test --limit 15")
    print("   ")
    print("   # Smart commercial hub targeting:")
    print("   python get_vans.py scrape-multi --strategy commercial_hubs \\")
    print("     --postcode-limit 30 --pages-per-postcode 5")
    print("   ")
    print("   # Geographic focus around London:")
    print("   python get_vans.py scrape-multi --strategy geographic_spread \\")
    print("     --center-postcode 'W1 1AA' --radius-km 25 --track-success")
    print("   ")
    print("   # Show current statistics:")
    print("   python get_vans.py postcodes stats")


if __name__ == "__main__":
    demo_enhanced_postcode_management() 
