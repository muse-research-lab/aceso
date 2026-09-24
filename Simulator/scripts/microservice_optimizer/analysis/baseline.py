"""Baseline analysis for single-region microservice deployment"""
import time
from microservice_optimizer.core.regions import ALL_REGIONS
from microservice_optimizer.evaluation.evaluator import evaluate_realistic_assignment_fast
from microservice_optimizer.utils.csv_logger import log_realistic_experiment_csv


def run_optimized_baseline_analysis_with_graph(ms_size=100, base_location="Spain", load_scenarios=None, 
                                             graph=None, fixed_nodes=None, service_profiles=None):
    """
    Optimized baseline analysis using pre-generated graph
    
    Args:
        ms_size: Number of microservices
        base_location: Target region for deployment
        load_scenarios: List of load multipliers to test
        graph: Pre-generated microservice graph
        fixed_nodes: Pre-identified fixed nodes
        service_profiles: Pre-generated service profiles
    
    Returns:
        List of results for each load scenario
    """
    if load_scenarios is None:
        load_scenarios = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    
    print("🚀 Starting OPTIMIZED Baseline Analysis")
    print(f"   Microservices: {ms_size}, Base: {base_location}")
    print(f"   Load scenarios: {load_scenarios}")
    print("=" * 60)
    
    # Use pre-generated graph or generate new one
    if graph is None or service_profiles is None:
        print("📊 Generating new microservice graph and profiles...")
        from ..core.graph import generate_realistic_microservice_graph
        start_setup = time.time()
        graph, fixed_nodes, service_profiles = generate_realistic_microservice_graph(ms_size)
        setup_time = time.time() - start_setup
        print(f"✅ New graph generated in {setup_time:.2f} seconds")
    else:
        print("✅ Using pre-generated microservice graph")
        setup_time = 0
    
    print(f"   Generated: {ms_size} services, {len(fixed_nodes)} fixed nodes")
    
    # Single region setup
    regions = {base_location: ALL_REGIONS[base_location]}
    region_names = list(regions.keys())
    base_idx = 0  # Only one region
    
    # Show service type distribution
    from ..core.graph import print_graph_summary
    print_graph_summary(graph, service_profiles, fixed_nodes)
    
    # Create baseline assignment (all in base region)
    assignment = {service: base_idx for service in range(ms_size)}
    
    # Test all load scenarios efficiently
    print("\n📈 Testing load scenarios...")
    total_start_time = time.time()
    
    results = []
    
    for load in load_scenarios:
        scenario_start = time.time()
        
        # Update load multiplier for all services
        for profile in service_profiles.values():
            profile.set_load_multiplier(load)
        
        # Fast evaluation with DISCRETE scaling
        carbon, cost, latency, instance_dist = evaluate_realistic_assignment_fast(
            assignment, graph, service_profiles, regions, base_location, load
        )
        
        scenario_time = time.time() - scenario_start
        results.append((load, carbon, cost, latency, scenario_time, instance_dist))
        
        # Log to CSV
        experiment_title = f"optimized-baseline-{ms_size}ms-{base_location}-load{load}"
        log_realistic_experiment_csv(
            filename="optimized_baseline_results.csv",
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
    
    total_time = time.time() - total_start_time
    
    # Print summary
    print(f"\n📊 Scaling Summary for {base_location}:")
    print(f"{'Load':>4} {'Carbon':>8} {'Cost':>8} {'Latency':>8}")
    print(f"{'----':>4} {'------':>8} {'----':>8} {'-------':>8}")
    for load, carbon, cost, latency, _, _ in results:
        print(f"{load:4.0f}x {carbon:8.2f} ${cost:7.4f} {latency:8.2f}ms")
    
    print(f"\n✅ {base_location} scenarios completed in {total_time:.2f} seconds")
    
    return results


def compare_baseline_regions(ms_size=20, regions_to_compare=None, load_scenarios=None):
    """
    Compare baseline performance across multiple regions using same graph
    
    Args:
        ms_size: Number of microservices
        regions_to_compare: List of regions to compare
        load_scenarios: Load levels to test
    
    Returns:
        Dictionary of results by region
    """
    if regions_to_compare is None:
        regions_to_compare = ["Spain", "Stockholm", "Milan"]
    
    if load_scenarios is None:
        load_scenarios = [1, 5, 10]
    
    print("🔬 Comparing Baseline Performance Across Regions")
    print(f"   Microservices: {ms_size}")
    print(f"   Regions: {regions_to_compare}")
    print(f"   Load levels: {load_scenarios}")
    
    # Generate graph once
    from ..core.graph import generate_realistic_microservice_graph
    graph, fixed_nodes, service_profiles = generate_realistic_microservice_graph(ms_size)
    
    all_results = {}
    
    for region in regions_to_compare:
        print(f"\n🌍 Testing {region}...")
        results = run_optimized_baseline_analysis_with_graph(
            ms_size=ms_size,
            base_location=region,
            load_scenarios=load_scenarios,
            graph=graph,
            fixed_nodes=fixed_nodes,
            service_profiles=service_profiles
        )
        all_results[region] = results
    
    # Print comparison table
    print(f"\n{'='*80}")
    print("📊 REGION COMPARISON SUMMARY")
    print(f"{'='*80}")
    print(f"{'Region':<15} {'Load':>4} {'Carbon':>8} {'Cost':>8} {'Latency':>8}")
    print(f"{'-'*15} {'----':>4} {'------':>8} {'----':>8} {'-------':>8}")
    
    for region in regions_to_compare:
        results = all_results[region]
        for load, carbon, cost, latency, _, _ in results:
            print(f"{region:<15} {load:4.0f}x {carbon:8.2f} ${cost:7.4f} {latency:8.2f}ms")
    
    return all_results