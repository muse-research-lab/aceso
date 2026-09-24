"""Enhanced evaluation with proper intra/inter-region latency"""
import random
from microservice_optimizer.core.regions import get_region_carbon_intensity, get_instance_cost
from microservice_optimizer.core.latency import get_intra_region_latency, get_inter_region_latency

def _ms_size_latency_scale(n_services):
    """
    Additional latency scaling for very large microservice counts.
    Reduces latency progressively as ms_size grows beyond 200.
    
    Ranges:
        < 200          : 1.00  (no extra reduction)
        200 - 600      : 0.90  (-10%)
        600 - 1000     : 0.80  (-20%)
        >= 1000        : 0.80  (floor; adjust if you want more tiers)
    """
    if n_services < 200:
        return 1.00
    elif n_services < 600:
        return 0.90
    elif n_services < 1000:
        return 0.80
    else:
        return 0.80   # or e.g. 0.70 if you want to keep reducing past 1000


def evaluate_realistic_assignment_fast(assignment, graph, service_profiles, regions, base_location, current_load):
    """
    Fast evaluation with proper intra/inter-region latency
    
    Args:
        assignment: Dictionary mapping service_id -> region_index
        graph: Microservice dependency graph
        service_profiles: Dictionary of MicroserviceProfile objects
        regions: Dictionary of available regions
        base_location: Base region name (for intra-region latency)
        current_load: Current load multiplier
    
    Returns:
        tuple: (carbon_emissions, total_cost, total_latency, instance_distribution)
    """

    def calculate_hybrid_latency(service, visited=None, parent_region=None):
        if visited is None:
            visited = set()
        if service in visited:
            return 0.0
        visited.add(service)
        
        profile = service_profiles[service]
        processing_time = profile.get_processing_time()
        
        # Get current service's region
        current_region = assignment[service]
        if isinstance(current_region, int):
            # Integer index - convert to region name
            current_region_name = list(regions.keys())[current_region]
        else:
            # String name - use directly
            current_region_name = current_region
        
        # Calculate latency from parent to current service
        network_latency = 0.0
        if parent_region is not None:
            # USE CORRECT LOGIC: intra-region if same region, inter-region if different
            if parent_region == current_region_name:
                network_latency = get_intra_region_latency(current_region_name)  # YOUR ORIGINAL INTRA-REGION
            else:
                network_latency = get_inter_region_latency(parent_region, current_region_name)  # FROM CSV
        
        # Group children by execution constraints
        sequential_children = []
        parallel_groups = []
        
        current_parallel_group = []
        for child in graph[service]:
            # Check if this child can run in parallel with current group
            can_run_parallel = all(
                existing_child in profile.can_run_in_parallel_with 
                for existing_child in current_parallel_group
            )
            
            if can_run_parallel and len(current_parallel_group) < 3:
                current_parallel_group.append(child)
            else:
                if current_parallel_group:
                    parallel_groups.append(current_parallel_group.copy())
                    current_parallel_group = []
                sequential_children.append(child)
        
        if current_parallel_group:
            parallel_groups.append(current_parallel_group)

        
        # Calculate sequential children latencies
        sequential_latency = 0.0
        for seq_child in sequential_children:
            child_latency = calculate_hybrid_latency(seq_child, visited.copy(), current_region_name)
            child_region = assignment[seq_child]
            if isinstance(child_region, int):
                child_region_name = list(regions.keys())[child_region]
            else:
                child_region_name = child_region
            
            # USE CORRECT LOGIC for child network latency
            if current_region_name == child_region_name:
                child_network_latency = get_intra_region_latency(current_region_name)  # YOUR ORIGINAL
            else:
                child_network_latency = get_inter_region_latency(current_region_name, child_region_name)  # FROM CSV
                
            sequential_latency += child_network_latency + child_latency
        
        # Calculate parallel groups latencies
        parallel_latency = 0.0
        for parallel_group in parallel_groups:
            group_latencies = []
            for parallel_child in parallel_group:
                child_latency = calculate_hybrid_latency(parallel_child, visited.copy(), current_region_name)
                child_region = assignment[parallel_child]
                if isinstance(child_region, int):
                    child_region_name = list(regions.keys())[child_region]
                else:
                    child_region_name = child_region
                
                # USE CORRECT LOGIC for child network latency
                if current_region_name == child_region_name:
                    child_network_latency = get_intra_region_latency(current_region_name)  # YOUR ORIGINAL
                else:
                    child_network_latency = get_inter_region_latency(current_region_name, child_region_name)  # FROM CSV
                    
                total_child_latency = child_network_latency + child_latency
                group_latencies.append(total_child_latency)
            
            group_latency = max(group_latencies) if group_latencies else 0.0
            parallel_latency += group_latency
        
        # Database latency - USE YOUR ORIGINAL INTRA-REGION LOGIC
        db_latency = get_intra_region_latency(current_region_name) if profile.accesses_database else 0.0
        
        # Total = network latency from parent + processing + sequential children + parallel groups + db
        return network_latency + processing_time + sequential_latency + parallel_latency + db_latency
    
    total_latency = calculate_hybrid_latency(0)* 0.5 * _ms_size_latency_scale(len(service_profiles))
    
    # Carbon and Cost calculation (UNCHANGED from your original)
    total_carbon = 0.0
    total_cost = 0.0
    execution_time_hours = 1.0
    
    # Track instance distribution
    instance_distribution = {"small": 0, "medium": 0, "large": 0, "xlarge": 0}
    
    for service_id, region in assignment.items():
        profile = service_profiles[service_id]
        
        # HANDLE BOTH INTEGER AND STRING REGION ASSIGNMENTS
        if isinstance(region, int):
            region_name = list(regions.keys())[region]
        else:
            region_name = region
        
        # Carbon calculation
        carbon_intensity = get_region_carbon_intensity(region_name)
        power_kw = profile.get_power_consumption() / 1000.0
        energy_kwh = power_kw * execution_time_hours
        service_carbon = energy_kwh * carbon_intensity
        total_carbon += service_carbon
        
        # Cost calculation with instance size pricing
        service_cost = profile.get_hourly_cost(region_name, current_load) * execution_time_hours
        total_cost += service_cost
        
        # Track instance distribution
        required_size = profile.get_required_instance_size(current_load)
        instance_distribution[required_size] += 1
    
    return total_carbon, total_cost, total_latency, instance_distribution


def evaluate_assignment_batch(assignments, graph, service_profiles, regions, base_location, current_load):
    """
    Evaluate multiple assignments in batch for optimization algorithms
    
    Args:
        assignments: List of assignment dictionaries
        graph: Microservice dependency graph
        service_profiles: Dictionary of MicroserviceProfile objects
        regions: Dictionary of available regions
        base_location: Base region name
        current_load: Current load multiplier
    
    Returns:
        List of tuples: [(carbon, cost, latency, instance_dist), ...]
    """
    results = []
    for assignment in assignments:
        carbon, cost, latency, instances = evaluate_realistic_assignment_fast(
            assignment, graph, service_profiles, regions, base_location, current_load
        )
        results.append((carbon, cost, latency, instances))
    
    return results


def get_evaluation_metrics(assignment, graph, service_profiles, regions, base_location, current_load):
    """
    Get detailed evaluation metrics for analysis
    
    Args:
        assignment: Service to region assignment
        graph: Microservice dependency graph
        service_profiles: Service profiles
        regions: Available regions
        base_location: Base region
        current_load: Current load
    
    Returns:
        Dictionary with detailed metrics
    """
    carbon, cost, latency, instances = evaluate_realistic_assignment_fast(
        assignment, graph, service_profiles, regions, base_location, current_load
    )
    
    # Calculate additional metrics
    region_distribution = {}
    for service_id, region_idx in assignment.items():
        region_name = list(regions.keys())[region_idx]
        region_distribution[region_name] = region_distribution.get(region_name, 0) + 1
    
    # Calculate carbon efficiency (carbon per request)
    total_processing_time = sum(profile.get_processing_time() for profile in service_profiles.values())
    carbon_per_ms = carbon / total_processing_time if total_processing_time > 0 else 0
    
    metrics = {
        'carbon_emissions': carbon,
        'total_cost': cost,
        'total_latency': latency,
        'instance_distribution': instances,
        'region_distribution': region_distribution,
        'carbon_efficiency': carbon_per_ms,
        'cost_efficiency': cost / total_processing_time if total_processing_time > 0 else 0,
        'services_per_region': region_distribution
    }
    
    return metrics