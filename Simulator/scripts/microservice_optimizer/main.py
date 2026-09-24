#!/usr/bin/env python3
"""
Main entry point for microservice optimization analysis.
Run comprehensive analyses using the modular architecture.
"""

import sys
import os

# Add the current directory to Python path so modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analysis.multi_region import run_multiple_regions_analysis, analyze_region_tradeoffs
from analysis.baseline import compare_baseline_regions
from core.graph import generate_realistic_microservice_graph, print_graph_summary
from evaluation.evaluator import evaluate_realistic_assignment_fast
from utils.csv_logger import analyze_experiment_results


def run_comprehensive_analysis():
    """Run comprehensive multi-region analysis"""
    print("🚀 Starting Comprehensive Microservice Analysis")
    print("=" * 70)
    
    # Test configurations
    test_sizes = [20, 50]  # Small and medium microservice architectures
    regions_to_test = ["Spain", "Stockholm", "Milan", "Tokyo", "Cape Town"]
    
    for size in test_sizes:
        print(f"\n{'='*70}")
        print(f"🧪 Testing Microservice Size: {size}")
        print(f"{'='*70}")
        
        # Run multi-region analysis
        results = run_multiple_regions_analysis(
            ms_size=size,
            regions_to_test=regions_to_test,
            load_scenarios=[1, 3, 5, 7, 10],  # Light to heavy load
            random_seed=42
        )
    
    return results


def run_quick_demo():
    """Run a quick demo with fewer regions and loads"""
    print("🎯 Running Quick Demo")
    print("=" * 50)
    
    results = run_multiple_regions_analysis(
        ms_size=20,
        regions_to_test=["Spain", "Stockholm", "Milan"],
        load_scenarios=[1, 5, 10],  # Just min, medium, max load
        random_seed=42
    )
    
    return results


def run_tradeoff_analysis():
    """Run carbon-cost-latency tradeoff analysis"""
    print("🔄 Running Carbon-Cost-Latency Tradeoff Analysis")
    print("=" * 60)
    
    tradeoffs = analyze_region_tradeoffs(
        ms_size=30,
        regions_to_test=["Spain", "Stockholm", "Milan", "Tokyo", "Cape Town", "Northern Virginia"],
        load_level=5
    )
    
    return tradeoffs


def run_single_region_deep_dive():
    """Deep dive into a single region with detailed analysis"""
    print("🔍 Single Region Deep Dive: Stockholm")
    print("=" * 50)
    
    from analysis.baseline import run_optimized_baseline_analysis_with_graph
    
    # Generate graph once
    from core.graph import generate_realistic_microservice_graph
    graph, fixed_nodes, service_profiles = generate_realistic_microservice_graph(30, fixed_percentage=0.2)
    
    print_graph_summary(graph, service_profiles, fixed_nodes)
    
    # Run detailed analysis
    results = run_optimized_baseline_analysis_with_graph(
        ms_size=30,
        base_location="Stockholm", 
        load_scenarios=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        graph=graph,
        fixed_nodes=fixed_nodes,
        service_profiles=service_profiles
    )
    
    return results


def analyze_existing_results():
    """Analyze results from previous runs"""
    print("📊 Analyzing Existing Experiment Results")
    print("=" * 50)
    
    csv_files = [
        "multi_region_results.csv",
        "optimized_baseline_results.csv"
    ]
    
    for csv_file in csv_files:
        if os.path.exists(csv_file):
            print(f"\nAnalyzing {csv_file}:")
            analysis = analyze_experiment_results(csv_file)
            print(f"  Total experiments: {analysis.get('total_experiments', 0)}")
            print(f"  Unique configurations: {analysis.get('unique_configurations', 0)}")
            print(f"  Regions tested: {list(analysis.get('experiments_by_region', {}).keys())}")
        else:
            print(f"  {csv_file} not found - run analyses first")


def test_evaluation_function():
    """Test the core evaluation function directly"""
    print("🧪 Testing Core Evaluation Function")
    print("=" * 50)
    
    from core.graph import generate_realistic_microservice_graph
    from core.regions import ALL_REGIONS
    
    # Generate a small test graph
    graph, fixed_nodes, service_profiles = generate_realistic_microservice_graph(10)
    print_graph_summary(graph, service_profiles, fixed_nodes)
    
    # Create a simple assignment (all in one region)
    assignment = {service: 0 for service in range(10)}
    regions = {"Spain": ALL_REGIONS["Spain"]}
    
    # Test evaluation at different loads
    for load in [1, 5, 10]:
        carbon, cost, latency, instances = evaluate_realistic_assignment_fast(
            assignment, graph, service_profiles, regions, "Spain", load
        )
        print(f"Load {load}x: Carbon={carbon:.2f}g, Cost=${cost:.4f}, Latency={latency:.2f}ms")
        print(f"  Instances: {instances}")

def run_nautilus_analysis(ms_size=20, regions_to_test=None):
    """
    Run Nautilus analysis - equivalent to your original test code
    """
    if regions_to_test is None:
        regions_to_test = ["Spain", "Stockholm"]
    
    print(f"\n{'='*70}")
    print(f"🧪 Testing Microservice Size: {ms_size}")
    print(f"{'='*70}")
    
    results = run_multiple_regions_analysis(
        ms_size=ms_size,
        regions_to_test=regions_to_test
    )
    
    return results
def main():
    """Main function with menu-driven interface"""
    print("🌍 Microservice Carbon-Cost-Latency Optimization System")
    print("=" * 70)
    
    while True:
        print("\n📋 Available Analyses:")
        print("1. Quick Demo (3 regions, 3 load levels)")
        print("2. Comprehensive Analysis (5 regions, 5 load levels)") 
        print("3. Tradeoff Analysis (carbon-cost-latency scoring)")
        print("4. Single Region Deep Dive")
        print("5. Test Core Evaluation")
        print("6. Analyze Existing Results")
        print("7. Nautilus Analysis (Original Test)")
        print("8. Exit")
        
        choice = input("\nEnter your choice (1-8): ").strip()
        
        try:
            if choice == '1':
                run_quick_demo()
            elif choice == '2':
                run_comprehensive_analysis()
            elif choice == '3':
                run_tradeoff_analysis()
            elif choice == '4':
                run_single_region_deep_dive()
            elif choice == '5':
                test_evaluation_function()
            elif choice == '6':
                analyze_existing_results()
            elif choice == '7':
                # Nautilus Analysis - get user input
                try:
                    ms_size = int(input("Enter microservice size (default 20): ") or "20")
                    regions_input = input("Enter regions (comma-separated, default 'Spain,Stockholm'): ") or "Spain,Stockholm"
                    regions_to_test = [region.strip() for region in regions_input.split(",")]
                    
                    run_nautilus_analysis(ms_size, regions_to_test)
                except ValueError:
                    print("❌ Invalid input. Using defaults.")
                    run_nautilus_analysis()
            elif choice == '8':
                print("👋 Exiting. Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please enter 1-8.")
        except KeyboardInterrupt:
            print("\n⏹️  Analysis interrupted by user")
            break
        except Exception as e:
            print(f"❌ Error during analysis: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    # If no arguments, run the interactive menu
    if len(sys.argv) == 1:
        main()
    else:
        # Command line interface
        if sys.argv[1] == "demo":
            run_quick_demo()
        elif sys.argv[1] == "comprehensive":
            run_comprehensive_analysis()
        elif sys.argv[1] == "tradeoffs":
            run_tradeoff_analysis()
        elif sys.argv[1] == "analyze":
            analyze_existing_results()
        elif sys.argv[1] == "nautilus":
            # Nautilus analysis from command line
            ms_size = 20
            regions = ["Spain", "Stockholm"]
            
            if len(sys.argv) > 2:
                try:
                    ms_size = int(sys.argv[2])
                except ValueError:
                    print(f"❌ Invalid microservice size: {sys.argv[2]}, using default 20")
            
            if len(sys.argv) > 3:
                regions = sys.argv[3].split(",")
            
            run_nautilus_analysis(ms_size, regions)
        else:
            print("Usage: python main.py [demo|comprehensive|tradeoffs|analyze|nautilus]")
            print("  nautilus options: python main.py nautilus [ms_size] [regions]")
            print("  Example: python main.py nautilus 30 Spain,Stockholm,Milan")
            print("  Or run without arguments for interactive menu")