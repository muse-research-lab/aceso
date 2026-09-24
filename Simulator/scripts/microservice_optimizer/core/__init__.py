"""
Core module for microservice optimization system.
"""

# Empty __init__.py - imports will be handled by the modules themselves
__all__ = [
    'ALL_REGIONS',
    'REGION_INSTANCE_COSTS', 
    'REGION_TO_AWS',
    'get_region_carbon_intensity',
    'get_instance_cost',
    'get_aws_region_code',
    'MicroserviceProfile',
    'generate_realistic_microservice_graph',
    'get_graph_statistics',
    'print_graph_summary', 
    'validate_assignment',
    'get_service_dependencies',
    'export_graph_to_dict',
    'import_graph_from_dict',
    'load_aws_latency_data',
    'get_intra_region_latency',
    'get_inter_region_latency'
]