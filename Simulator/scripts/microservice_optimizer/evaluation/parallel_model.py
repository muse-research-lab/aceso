"""Parallel execution modeling for microservice latency calculation"""
from microservice_optimizer.core.latency import get_intra_region_latency, get_inter_region_latency

def calculate_hybrid_latency(service, graph, service_profiles, assignment, regions, visited=None, parent_region=None):
    """
    Calculate hybrid parallel/sequential execution latency for a service
    
    Args:
        service: Current service ID
        graph: Microservice dependency graph
        service_profiles: Dictionary of service profiles
        assignment: Service to region assignment
        regions: Available regions dictionary
        visited: Set of visited services (for cycle detection)
        parent_region: Region of parent service
    
    Returns:
        float: Total latency for this service and its dependencies
    """
    if visited is None:
        visited = set()
    if service in visited:
        return 0.0
    visited.add(service)
    
    from ..core.latency import get_intra_region_latency, get_inter_region_latency
    
    profile = service_profiles[service]
    processing_time = profile.get_processing_time()
    
    # Get current service's region
    current_region_idx = assignment[service]
    current_region_name = list(regions.keys())[current_region_idx]
    
    # Calculate latency from parent to current service
    network_latency = 0.0
    if parent_region is not None:
        if parent_region == current_region_name:
            network_latency = get_intra_region_latency(current_region_name)
        else:
            network_latency = get_inter_region_latency(parent_region, current_region_name)
    
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
        child_latency = calculate_hybrid_latency(
            seq_child, graph, service_profiles, assignment, regions, 
            visited.copy(), current_region_name
        )
        child_region_idx = assignment[seq_child]
        child_region_name = list(regions.keys())[child_region_idx]
        
        if current_region_name == child_region_name:
            child_network_latency = get_intra_region_latency(current_region_name)
        else:
            child_network_latency = get_inter_region_latency(current_region_name, child_region_name)
            
        sequential_latency += child_network_latency + child_latency
    
    # Calculate parallel groups latencies
    parallel_latency = 0.0
    for parallel_group in parallel_groups:
        group_latencies = []
        for parallel_child in parallel_group:
            child_latency = calculate_hybrid_latency(
                parallel_child, graph, service_profiles, assignment, regions,
                visited.copy(), current_region_name
            )
            child_region_idx = assignment[parallel_child]
            child_region_name = list(regions.keys())[child_region_idx]
            
            if current_region_name == child_region_name:
                child_network_latency = get_intra_region_latency(current_region_name)
            else:
                child_network_latency = get_inter_region_latency(current_region_name, child_region_name)
                
            total_child_latency = child_network_latency + child_latency
            group_latencies.append(total_child_latency)
        
        group_latency = max(group_latencies) if group_latencies else 0.0
        parallel_latency += group_latency
    
    # Database latency
    db_latency = get_intra_region_latency(current_region_name) if profile.accesses_database else 0.0
    
    return network_latency + processing_time + sequential_latency + parallel_latency + db_latency


def analyze_critical_path(graph, service_profiles, assignment, regions):
    """
    Analyze the critical path of microservice execution
    
    Args:
        graph: Microservice dependency graph
        service_profiles: Service profiles
        assignment: Service to region assignment
        regions: Available regions
    
    Returns:
        Dictionary with critical path analysis
    """
    critical_path = []
    critical_path_latency = 0.0
    
    def find_critical_path(node, current_path, current_latency, visited=None):
        nonlocal critical_path, critical_path_latency
        
        if visited is None:
            visited = set()
        if node in visited:
            return
        visited.add(node)
        
        from ..core.latency import get_intra_region_latency, get_inter_region_latency
        
        profile = service_profiles[node]
        processing_time = profile.get_processing_time()
        
        # Get network latency from parent
        network_latency = 0.0
        if current_path:  # Not the root
            parent = current_path[-1]
            parent_region_idx = assignment[parent]
            parent_region_name = list(regions.keys())[parent_region_idx]
            
            current_region_idx = assignment[node]
            current_region_name = list(regions.keys())[current_region_idx]
            
            if parent_region_name == current_region_name:
                network_latency = get_intra_region_latency(current_region_name)
            else:
                network_latency = get_inter_region_latency(parent_region_name, current_region_name)
        
        current_latency += network_latency + processing_time
        
        # Add database latency if applicable
        if profile.accesses_database:
            db_latency = get_intra_region_latency(list(regions.keys())[assignment[node]])
            current_latency += db_latency
        
        # Update critical path if this is the longest so far
        if current_latency > critical_path_latency:
            critical_path = current_path + [node]
            critical_path_latency = current_latency
        
        # Recursively check children
        for child in graph.get(node, []):
            find_critical_path(child, current_path + [node], current_latency, visited.copy())
    
    # Start from root (service 0)
    find_critical_path(0, [], 0.0)
    
    # Calculate breakdown for critical path
    path_breakdown = []
    total_latency = 0.0
    
    for i, node in enumerate(critical_path):
        profile = service_profiles[node]
        processing_time = profile.get_processing_time()
        
        # Network latency (except for first node)
        network_latency = 0.0
        if i > 0:
            prev_node = critical_path[i-1]
            prev_region = list(regions.keys())[assignment[prev_node]]
            curr_region = list(regions.keys())[assignment[node]]
            
            if prev_region == curr_region:
                network_latency = get_intra_region_latency(curr_region)
            else:
                network_latency = get_inter_region_latency(prev_region, curr_region)
        
        # Database latency
        db_latency = get_intra_region_latency(list(regions.keys())[assignment[node]]) if profile.accesses_database else 0.0
        
        node_latency = network_latency + processing_time + db_latency
        total_latency += node_latency
        
        path_breakdown.append({
            'service_id': node,
            'service_type': profile.service_type,
            'region': list(regions.keys())[assignment[node]],
            'processing_time': processing_time,
            'network_latency': network_latency,
            'db_latency': db_latency,
            'total_latency': node_latency
        })
    
    return {
        'critical_path': critical_path,
        'total_latency': total_latency,
        'breakdown': path_breakdown,
        'bottleneck_service': critical_path[-1] if critical_path else None
    }