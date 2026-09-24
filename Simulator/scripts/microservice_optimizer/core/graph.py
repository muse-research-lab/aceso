"""Graph generation utilities"""
import random
from collections import deque
from .microservice import MicroserviceProfile

def generate_realistic_microservice_graph(n_services, fixed_percentage=0.1):
    """Generate graph and profiles once - most expensive operation"""
    graph = {i: [] for i in range(n_services)}
    service_profiles = {}
    
    # Create service profiles with realistic distributions
    _create_service_profiles(service_profiles, n_services)
    
    # Build graph structure
    _build_graph_structure(graph, service_profiles, n_services)
    
    # Identify fixed nodes
    fixed_nodes = _identify_fixed_nodes(n_services, service_profiles, fixed_percentage, graph)
    
    return graph, fixed_nodes, service_profiles

def _create_service_profiles(service_profiles, n_services):
    """Create service profiles with realistic type distributions"""
    for i in range(n_services):
        if i == 0:
            service_type = "api"  # First service is always API gateway
        elif random.random() < 0.1:  # 10% are databases
            service_type = "database" 
        elif random.random() < 0.3:  # 30% are cache/services
            service_type = "cache"
        else:  # 60% are compute services
            service_type = "compute"
        service_profiles[i] = MicroserviceProfile(i, service_type)

def _build_graph_structure(graph, service_profiles, n_services):
    """Build the microservice dependency graph structure"""
    available_nodes = deque([0])
    used_nodes = {0}
    
    for i in range(1, n_services):
        if not available_nodes:
            break
        parent = random.choice(list(available_nodes))
        graph[parent].append(i)
        service_profiles[i].depends_on_services.append(parent)
        
        # ALWAYS add the new node to available nodes (removed the cap for path length)
        available_nodes.append(i)
        used_nodes.add(i)
    
    return graph

def _identify_fixed_nodes(n_services, service_profiles, fixed_percentage, graph):
    """Identify which nodes should be fixed in place - prioritize critical path nodes"""
    fixed_nodes = []
    fixed_critical_nodes = []
    if fixed_percentage > 0:
        num_fixed = max(1, int(n_services * fixed_percentage))
        
        # Calculate critical path contributions
        critical_paths = _calculate_critical_path_order(graph, service_profiles)
        
        # Sort nodes by critical path length (highest first)
        nodes_by_criticality = sorted(critical_paths.keys(), 
                                    key=lambda x: critical_paths[x], reverse=True)
        
        # Always fix the root (API gateway) - it's critical
        fixed_nodes.append(0)
        
        # Fix the top k most critical nodes (excluding root)
        critical_nodes = [node for node in nodes_by_criticality if node != 0]
        num_additional_fixed = num_fixed - 1  # minus the root
        
        if num_additional_fixed > 0:
            # Take the most critical nodes
            fixed_critical_nodes = critical_nodes[:num_additional_fixed]
            fixed_nodes.extend(fixed_critical_nodes)
        
        print(f"   Fixed {len(fixed_nodes)} nodes:")
        print(f"     - Root (API): 0")
        for node in fixed_critical_nodes:
            print(f"     - Service {node}: critical_path={critical_paths[node]:.2f}ms")
    
    return fixed_nodes

def _calculate_execution_order(graph):
    """Calculate when each node executes in the request flow (higher = later)"""
    if not graph:
        return {}
    
    # Use BFS level to approximate execution order
    # Nodes at deeper levels typically execute later
    execution_levels = {}
    visited = set()
    queue = deque([(0, 0)])  # (node, level)
    
    while queue:
        node, level = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        execution_levels[node] = level
        
        for child in graph.get(node, []):
            if child not in visited:
                queue.append((child, level + 1))
    
    return execution_levels

# Alternative: More sophisticated execution order based on critical path
def _calculate_critical_path_order(graph, service_profiles):
    """Calculate execution order based on critical path analysis"""
    if not graph:
        return {}
    
    # First, calculate the critical path length for each node
    critical_path_lengths = {}
    
    def calculate_critical_path(node):
        if node in critical_path_lengths:
            return critical_path_lengths[node]
        
        children = graph.get(node, [])
        if not children:
            # Leaf node - just its own processing time
            profile = service_profiles[node]
            critical_path_lengths[node] = profile.base_processing_time
        else:
            # Node + max of children's critical paths
            child_paths = [calculate_critical_path(child) for child in children]
            profile = service_profiles[node]
            critical_path_lengths[node] = profile.base_processing_time + max(child_paths)
        
        return critical_path_lengths[node]
    
    # Calculate for all nodes
    for node in graph:
        calculate_critical_path(node)
    
    return critical_path_lengths

def get_graph_statistics(graph, service_profiles):
    """Get statistics about the generated graph"""
    stats = {
        "total_services": len(graph),
        "total_edges": sum(len(children) for children in graph.values()),
        "service_types": {},
        "max_children": 0,
        "avg_children": 0,
        "database_services": 0,
        "graph_depth": _calculate_graph_depth(graph),
        "connected_components": _count_connected_components(graph)
    }
    
    # Count service types
    for profile in service_profiles.values():
        service_type = profile.service_type
        stats["service_types"][service_type] = stats["service_types"].get(service_type, 0) + 1
        if profile.accesses_database:
            stats["database_services"] += 1
    
    # Calculate children statistics
    children_counts = [len(children) for children in graph.values()]
    if children_counts:
        stats["max_children"] = max(children_counts)
        stats["avg_children"] = sum(children_counts) / len(children_counts)
    
    return stats

def _calculate_graph_depth(graph):
    """Calculate the depth of the graph (longest path from root)"""
    if not graph:
        return 0
    
    depth = 0
    visited = set()
    
    def dfs(node, current_depth):
        nonlocal depth
        if node in visited:
            return
        visited.add(node)
        depth = max(depth, current_depth)
        for child in graph.get(node, []):
            dfs(child, current_depth + 1)
    
    # Start from root (node 0)
    dfs(0, 0)
    return depth

def _count_connected_components(graph):
    """Count number of connected components in the graph"""
    if not graph:
        return 0
    
    visited = set()
    components = 0
    
    def dfs(node):
        visited.add(node)
        for child in graph.get(node, []):
            if child not in visited:
                dfs(child)
    
    for node in graph:
        if node not in visited:
            components += 1
            dfs(node)
    
    return components

def print_graph_summary(graph, service_profiles, fixed_nodes=None):
    """Print a summary of the generated graph"""
    stats = get_graph_statistics(graph, service_profiles)
    
    print("\n📊 Graph Summary:")
    print(f"   Total services: {stats['total_services']}")
    print(f"   Total dependencies: {stats['total_edges']}")
    print(f"   Graph depth: {stats['graph_depth']}")
    print(f"   Connected components: {stats['connected_components']}")
    print(f"   Max children per service: {stats['max_children']}")
    print(f"   Avg children per service: {stats['avg_children']:.2f}")
    print(f"   Database-accessing services: {stats['database_services']}")
    
    print("   Service type distribution:")
    for service_type, count in sorted(stats["service_types"].items()):
        percentage = (count / stats["total_services"]) * 100
        print(f"     - {service_type:10}: {count:2} services ({percentage:5.1f}%)")
    
    if fixed_nodes:
        print(f"   Fixed nodes: {len(fixed_nodes)} services")
        fixed_types = {}
        for node in fixed_nodes:
            service_type = service_profiles[node].service_type
            fixed_types[service_type] = fixed_types.get(service_type, 0) + 1
        for service_type, count in sorted(fixed_types.items()):
            print(f"     - {service_type}: {count}")

def validate_assignment(assignment, fixed_nodes, n_services, available_regions):
    """Validate that an assignment meets constraints"""
    if len(assignment) != n_services:
        raise ValueError(f"Assignment has {len(assignment)} services, expected {n_services}")
    
    # Check fixed nodes are assigned to valid regions
    for service_id in fixed_nodes:
        if service_id not in assignment:
            raise ValueError(f"Fixed node {service_id} not in assignment")
        region_idx = assignment[service_id]
        if region_idx >= len(available_regions):
            raise ValueError(f"Fixed node {service_id} assigned to invalid region index {region_idx}")
    
    # Check all region indices are valid
    for service_id, region_idx in assignment.items():
        if region_idx >= len(available_regions):
            raise ValueError(f"Service {service_id} assigned to invalid region index {region_idx}")
    
    return True

def get_service_dependencies(graph, service_id):
    """Get all dependencies for a service (children and parents)"""
    children = graph.get(service_id, [])
    parents = []
    for parent, child_list in graph.items():
        if service_id in child_list:
            parents.append(parent)
    return {
        "children": children,
        "parents": parents,
        "is_root": service_id == 0,
        "is_leaf": len(children) == 0
    }

def export_graph_to_dict(graph, service_profiles):
    """Export graph and profiles to a serializable dictionary"""
    export_data = {
        "graph": graph,
        "service_profiles": {},
        "statistics": get_graph_statistics(graph, service_profiles)
    }
    
    # Convert service profiles to serializable format
    for service_id, profile in service_profiles.items():
        export_data["service_profiles"][service_id] = {
            "service_id": profile.service_id,
            "service_type": profile.service_type,
            "base_processing_time": profile.base_processing_time,
            "processing_variance": profile.processing_variance,
            "base_power_watts": profile.base_power_watts,
            "scaling_thresholds": profile.scaling_thresholds,
            "accesses_database": profile.accesses_database,
            "depends_on_services": profile.depends_on_services
        }
    
    return export_data

def import_graph_from_dict(graph_data):
    """Import graph and profiles from a dictionary"""
    graph = graph_data["graph"]
    service_profiles = {}
    
    for service_id, profile_data in graph_data["service_profiles"].items():
        profile = MicroserviceProfile(profile_data["service_id"], profile_data["service_type"])
        # Set all the attributes manually since we can't pickle the random state
        profile.base_processing_time = profile_data["base_processing_time"]
        profile.processing_variance = profile_data["processing_variance"]
        profile.base_power_watts = profile_data["base_power_watts"]
        profile.scaling_thresholds = profile_data["scaling_thresholds"]
        profile.accesses_database = profile_data["accesses_database"]
        profile.depends_on_services = profile_data["depends_on_services"]
        service_profiles[service_id] = profile
    
    return graph, service_profiles