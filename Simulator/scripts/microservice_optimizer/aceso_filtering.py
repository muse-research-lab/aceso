#!/usr/bin/env python3
"""
ACESO Region Filtering Analysis - Creates CSV with filtering results for all base regions
Run with: python -m microservice_optimizer.aceso_filtering
"""

import sys
import os
import csv
from datetime import datetime

# Add current directory to path for package imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(current_dir))  # Add parent directory to path

from microservice_optimizer.core.regions import ALL_REGIONS, get_region_carbon_intensity, get_instance_cost


def get_region_cost_comparison(region_name):
    """Get cost for region comparison using medium instance size"""
    return get_instance_cost(region_name, "medium")


def apply_region_filtering(base_location, all_regions):
    """
    Apply ACESO region filtering logic for a given base region
    
    Returns:
        dict with filtering results
    """
    base_carbon = get_region_carbon_intensity(base_location)
    base_cost = get_region_cost_comparison(base_location)
    
    # Calculate region metrics
    region_data = []
    
    for region in all_regions:
        region_carbon = get_region_carbon_intensity(region)
        region_cost = get_region_cost_comparison(region)
        
        # Check if region is strictly worse than base
        is_worse = region_carbon > base_carbon and region_cost > base_cost
        
        # Check if region is strictly better than base
        is_better = region_carbon < base_carbon and region_cost < base_cost
        
        # Check if region is better or equal in at least one dimension
        better_or_equal_carbon = region_carbon <= base_carbon
        better_or_equal_cost = region_cost <= base_cost
        
        region_data.append({
            'region': region,
            'carbon': region_carbon,
            'cost': region_cost,
            'is_worse': is_worse,
            'is_better': is_better,
            'better_or_equal_carbon': better_or_equal_carbon,
            'better_or_equal_cost': better_or_equal_cost
        })
    
    # Check if any region is strictly better than base
    better_exists = any(r['is_better'] for r in region_data if r['region'] != base_location)
    
    if better_exists:
        # Strict filtering: keep regions better or equal to base
        filtered_regions = [r['region'] for r in region_data 
                           if r['better_or_equal_carbon'] and r['better_or_equal_cost']]
        filtering_mode = "strict"
    else:
        # Relaxed filtering: remove strictly worse regions
        filtered_regions = [r['region'] for r in region_data if not r['is_worse']]
        filtering_mode = "relaxed"
    
    # Ensure base location is included
    if base_location not in filtered_regions:
        filtered_regions.insert(0, base_location)
    
    # Sort filtered regions alphabetically for consistency
    filtered_regions.sort()
    
    return {
        'base_region': base_location,
        'base_carbon': base_carbon,
        'base_cost': base_cost,
        'total_regions': len(all_regions),
        'filtered_regions_count': len(filtered_regions),
        'filtered_regions': ','.join(filtered_regions),
        'better_exists': better_exists,
        'filtering_mode': filtering_mode,
        'region_details': region_data
    }


def main():
    """Main function - analyze filtering for all base regions and create CSV"""
    
    # Get all available regions
    all_regions = list(ALL_REGIONS.keys())
    all_regions.sort()  # Sort alphabetically for consistency
    
    print(f"\n{'='*80}")
    print("🔍 ACESO REGION FILTERING ANALYSIS")
    print(f"{'='*80}")
    print(f"Total regions available: {len(all_regions)}")
    print(f"Regions: {', '.join(all_regions)}")
    print(f"{'='*80}\n")
    
    # Results storage
    results = []
    
    # Analyze each region as base
    for base_region in all_regions:
        print(f"📊 Analyzing base region: {base_region}...")
        
        result = apply_region_filtering(base_region, all_regions)
        results.append(result)
        
        # Print summary for this base region
        print(f"   Base: {base_region} (carbon={result['base_carbon']}g, cost=${result['base_cost']:.4f})")
        print(f"   Mode: {result['filtering_mode']}")
        print(f"   Filtered: {result['filtered_regions_count']}/{result['total_regions']} regions")
        if result['better_exists']:
            print(f"   ✅ Better regions exist")
        print(f"   Filtered regions: {result['filtered_regions']}")
        print()
    
    # Create CSV file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"results/region_filtering_results.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'base_region', 
            'base_carbon_g', 
            'base_cost_usd',
            'filtering_mode',
            'better_regions_exist',
            'total_regions',
            'filtered_regions_count',
            'filtered_regions',
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            writer.writerow({
                'base_region': result['base_region'],
                'base_carbon_g': f"{result['base_carbon']:.2f}",
                'base_cost_usd': f"{result['base_cost']:.4f}",
                'filtering_mode': result['filtering_mode'],
                'better_regions_exist': result['better_exists'],
                'total_regions': result['total_regions'],
                'filtered_regions_count': result['filtered_regions_count'],
                'filtered_regions': result['filtered_regions'],
            })
    
    print(f"\n{'='*80}")
    print(f"✅ Analysis complete!")
    print(f"📁 Results saved to: {filename}")
    print(f"{'='*80}")
    
    # Print summary table
    print("\n📊 SUMMARY TABLE:")
    print("-" * 90)
    print(f"{'Base Region':<15} {'Carbon':<10} {'Cost':<12} {'Mode':<10} {'Filtered':<8} {'Worse':<8} {'Better Exists':<12}")
    print("-" * 90)
    
    for result in results:
        print(f"{result['base_region']:<15} "
              f"{result['base_carbon']:<10.2f} "
              f"${result['base_cost']:<11.4f} "
              f"{result['filtering_mode']:<10} "
              f"{result['filtered_regions_count']:<8} "
              f"{'✅' if result['better_exists'] else '❌':<12}")
    
    print("-" * 90)
    
    # Additional statistics
    avg_filtered = sum(r['filtered_regions_count'] for r in results) / len(results)
    strict_count = sum(1 for r in results if r['filtering_mode'] == 'strict')
    
    print(f"\n📈 Statistics:")
    print(f"   Average filtered regions per base: {avg_filtered:.1f}")
    print(f"   Strict filtering cases (better region exists): {strict_count}/{len(results)}")
    
    return filename


if __name__ == "__main__":
    main()