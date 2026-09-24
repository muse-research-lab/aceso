"""Multi-region analysis with consistent graph for fair comparison"""
import random
import time
from microservice_optimizer.core.regions import ALL_REGIONS
from microservice_optimizer.core.graph import generate_realistic_microservice_graph, print_graph_summary
from microservice_optimizer.evaluation.evaluator import evaluate_realistic_assignment_fast
from microservice_optimizer.utils.csv_logger import log_realistic_experiment_csv

def run_multiple_regions_analysis(ms_size=20, regions_to_test=None, load_scenarios=None, random_seed=42):
    """
    Run analysis for multiple regions using the SAME microservice graph
    
    Args:
        ms_size: Number of microservices
        regions_to_test: List of regions to analyze
        load_scenarios: Load multipliers to test
        random_seed: Fixed seed for reproducible graphs
    
    Returns:
        Dictionary of results by region
    """
    if regions_to_test is None:
        regions_to_test = ["Spain", "Stockholm", "Milan"]
    
    if load_scenarios is None:
        load_scenarios = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    
    # SET FIXED RANDOM SEED for reproducible graphs
    random.seed(random_seed)
    
    print("🔄 Generating microservice graph ONCE for all regions...")
    graph, fixed_nodes, service_profiles = generate_realistic_microservice_graph(ms_size)
    
    # Print graph summary (so you can see it's the same)
    print_graph_summary(graph, service_profiles, fixed_nodes)
    
    all_results = {}
    
    for region in regions_to_test:
        print(f"\n{'='*70}")
        print(f"🌍 Testing Region: {region}")
        print(f"{'='*70}")
        
        # Use the EXACT SAME graph and service_profiles for all regions
        results = run_single_region_analysis_with_graph(
            ms_size=ms_size,
            base_location=region,
            load_scenarios=load_scenarios,
            graph=graph,
            fixed_nodes=fixed_nodes, 
            service_profiles=service_profiles
        )
        all_results[region] = results
    
    # Print comparative summary
    _print_multi_region_summary(all_results, regions_to_test, load_scenarios)
    
    return all_results


def run_single_region_analysis_with_graph(ms_size, base_location, load_scenarios, graph, fixed_nodes, service_profiles):
    """
    Run analysis for a single region using pre-generated graph
    
    Args:
        ms_size: Number of microservices
        base_location: Target region for deployment  
        load_scenarios: Load multipliers to test
        graph: Pre-generated microservice graph
        fixed_nodes: Pre-identified fixed nodes
        service_profiles: Pre-generated service profiles
    
    Returns:
        List of results for each load scenario
    """
    print(f"🚀 Starting Analysis for {base_location}")
    print(f"   Using pre-generated graph with {ms_size} services")
    print(f"   Load scenarios: {load_scenarios}")
    
    # Single region setup
    regions = {base_location: ALL_REGIONS[base_location]}
    
    # Create baseline assignment (all in base region)
    assignment = {service: 0 for service in range(ms_size)}  # All services in region 0
    
    # Test all load scenarios
    results = []
    
    for load in load_scenarios:
        scenario_start = time.time()
        
        # Update load multiplier for all services
        for profile in service_profiles.values():
            profile.set_load_multiplier(load)
        
        # Evaluate with the same graph and profiles
        carbon, cost, latency, instance_dist = evaluate_realistic_assignment_fast(
            assignment, graph, service_profiles, regions, base_location, load
        )
        
        scenario_time = time.time() - scenario_start
        results.append((load, carbon, cost, latency, scenario_time, instance_dist))
        
        # Log to CSV
        experiment_title = f"multi-region-{ms_size}ms-{base_location}-load{load}"
        log_realistic_experiment_csv(
            filename="multi_region_results.csv",
            title=experiment_title,
            base_location=base_location,
            n_services=ms_size,
            n_movable=0,
            load_multiplier=load,
            solve_time=scenario_time,
            assignment=assignment,
            carbon=carbon,
            cost=cost,
            latency=latency
        )
        
        print(f"   Load {load:2.0f}x: Carbon={carbon:6.2f}g, Cost=${cost:.4f}, "
              f"Latency={latency:6.2f}ms")
        print(f"        Instances: {instance_dist}")
    
    return results


def _print_multi_region_summary(all_results, regions, load_scenarios):
    """Print comparative summary of multi-region analysis"""
    print(f"\n{'='*80}")
    print("📊 MULTI-REGION COMPARISON SUMMARY")
    print(f"{'='*80}")
    
    # Print header
    header = f"{'Region':<15} {'Load':>4} {'Carbon':>8} {'Cost':>8} {'Latency':>8}"
    print(header)
    print('-' * len(header))
    
    # Print results for each region and load
    for region in regions:
        if region in all_results:
            results = all_results[region]
            for load, carbon, cost, latency, _, _ in results:
                if load in load_scenarios:  # Only print specified loads
                    print(f"{region:<15} {load:4.0f}x {carbon:8.2f} ${cost:7.4f} {latency:8.2f}ms")
    
    # Print key insights
    print(f"\n💡 KEY INSIGHTS:")
    
    # Find best region for carbon at max load
    max_load = max(load_scenarios)
    best_carbon_region = None
    best_carbon_value = float('inf')
    
    for region in regions:
        if region in all_results:
            results = all_results[region]
            for load, carbon, cost, latency, _, _ in results:
                if load == max_load and carbon < best_carbon_value:
                    best_carbon_value = carbon
                    best_carbon_region = region
    
    if best_carbon_region:
        print(f"   🌱 Best carbon at load {max_load}x: {best_carbon_region} ({best_carbon_value:.1f}g)")
    
    # Find best region for cost at max load  
    best_cost_region = None
    best_cost_value = float('inf')
    
    for region in regions:
        if region in all_results:
            results = all_results[region]
            for load, carbon, cost, latency, _, _ in results:
                if load == max_load and cost < best_cost_value:
                    best_cost_value = cost
                    best_cost_region = region
    
    if best_cost_region:
        print(f"   💰 Best cost at load {max_load}x: {best_cost_region} (${best_cost_value:.4f})")


def analyze_region_tradeoffs(ms_size=20, regions_to_test=None, load_level=5):
    """
    Analyze tradeoffs between carbon, cost, and latency across regions
    
    Args:
        ms_size: Number of microservices
        regions_to_test: Regions to compare
        load_level: Fixed load level for comparison
    
    Returns:
        Dictionary with tradeoff analysis
    """
    if regions_to_test is None:
        regions_to_test = ["Spain", "Stockholm", "Milan", "Tokyo", "Cape Town"]
    
    print(f"🔬 Analyzing Region Tradeoffs at Load {load_level}x")
    print(f"   Regions: {regions_to_test}")
    
    # Run analysis for all regions
    results = run_multiple_regions_analysis(
        ms_size=ms_size,
        regions_to_test=regions_to_test,
        load_scenarios=[load_level],  # Only test one load level
        random_seed=42
    )
    
    # Extract data for the target load level
    tradeoff_data = {}
    for region in regions_to_test:
        if region in results:
            region_results = results[region]
            if region_results:
                # Get results for the target load level
                for load, carbon, cost, latency, _, instances in region_results:
                    if load == load_level:
                        tradeoff_data[region] = {
                            'carbon': carbon,
                            'cost': cost,
                            'latency': latency,
                            'instances': instances
                        }
                        break
    
    # Print tradeoff analysis
    print(f"\n{'='*80}")
    print("🔄 CARBON-COST-LATENCY TRADEOFFS")
    print(f"{'='*80}")
    print(f"{'Region':<15} {'Carbon':>8} {'Cost':>8} {'Latency':>8} {'Tradeoff Score':>12}")
    print(f"{'-'*15} {'------':>8} {'----':>8} {'-------':>8} {'------------':>12}")
    
    # Calculate normalized tradeoff scores (lower is better)
    max_carbon = max(data['carbon'] for data in tradeoff_data.values())
    max_cost = max(data['cost'] for data in tradeoff_data.values())
    max_latency = max(data['latency'] for data in tradeoff_data.values())
    
    for region, data in tradeoff_data.items():
        # Normalize metrics (0-1 scale, lower is better)
        norm_carbon = data['carbon'] / max_carbon
        norm_cost = data['cost'] / max_cost
        norm_latency = data['latency'] / max_latency
        
        # Combined score (equal weighting)
        tradeoff_score = (norm_carbon + norm_cost + norm_latency) / 3
        
        print(f"{region:<15} {data['carbon']:8.1f} ${data['cost']:7.4f} {data['latency']:8.2f}ms {tradeoff_score:12.3f}")
    
    return tradeoff_data