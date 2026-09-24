#!/usr/bin/env python3
"""
Nautilus analysis runner - PACKAGE VERSION
"""

import sys
import os

def main():
    if len(sys.argv) < 2:
        print("Usage: python nautilus.py <ms_size> <regions>")
        print("Example: python nautilus.py 25 Spain,Stockholm,Milan,Tokyo")
        return
    
    try:
        ms_size = int(sys.argv[1])
        regions = sys.argv[2].split(",") if len(sys.argv) > 2 else ["Spain", "Stockholm"]
        regions = [region.strip() for region in regions]
        
        # Import using the package
        from microservice_optimizer.analysis.multi_region import run_multiple_regions_analysis
        
        print(f"\n{'='*70}")
        print(f"🧪 Testing Microservice Size: {ms_size}")
        print(f"{'='*70}")
        
        run_multiple_regions_analysis(
            ms_size=ms_size,
            regions_to_test=regions
        )
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()