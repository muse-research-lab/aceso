"""AWS latency data loading and management"""
import csv
import random
from microservice_optimizer.core.regions import REGION_TO_AWS

# Global cache for latency data
_LATENCY_CACHE = None
_AWS_REGIONS_LIST = []

def load_aws_latency_data():
    """Load AWS latency data from CSV with inter-region latencies"""
    global _LATENCY_CACHE, _AWS_REGIONS_LIST
    
    if _LATENCY_CACHE is not None:
        return _LATENCY_CACHE, _AWS_REGIONS_LIST
    
    latency_data = {}
    
    try:
        # FIX: Use the correct path when running as a package
        import os
        # Get the directory where THIS file (aws_data.py) is located
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(current_file_dir, "aws_latency_data.csv")
        
        print(f"🔍 Loading CSV from: {csv_path}")
        print(f"🔍 CSV exists: {os.path.exists(csv_path)}")

        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)
            print(f"🔍 CSV headers: {headers}")
            aws_regions = [region.strip() for region in headers[1:]]
            _AWS_REGIONS_LIST = aws_regions
            print(f"🔍 Found {len(aws_regions)} AWS regions in CSV")
            
            for row in reader:
                if not row:
                    continue
                source_aws = row[0].strip()
                latencies = row[1:]
                
                for i, latency_str in enumerate(latencies):
                    if i >= len(aws_regions):
                        break
                    target_aws = aws_regions[i].strip()
                    if latency_str and latency_str.replace('.', '').replace('ms', '').isdigit():
                        try:
                            latency_value = float(latency_str.replace('ms', '').strip())
                            latency_data[(source_aws, target_aws)] = latency_value
                        except ValueError:
                            continue
        
        print(f"✅ Loaded AWS latency data for {len(aws_regions)} regions")
        _LATENCY_CACHE = latency_data
        return latency_data, aws_regions
        
    except FileNotFoundError:
        print("❌ AWS latency CSV not found")
        # No fallback needed - get_inter_region_latency will handle missing data
        _LATENCY_CACHE = {}
        _AWS_REGIONS_LIST = []
        return {}, []

def get_aws_regions_list():
    """Get list of all AWS regions in the latency data"""
    latency_data, aws_regions = load_aws_latency_data()
    return aws_regions

def get_latency_matrix():
    """
    Get complete latency matrix as a 2D array
    
    Returns:
        tuple: (regions_list, latency_matrix)
    """
    latency_data, aws_regions = load_aws_latency_data()
    
    # Create matrix
    matrix = []
    for i, source in enumerate(aws_regions):
        row = []
        for j, target in enumerate(aws_regions):
            latency_key = (source, target)
            if latency_key in latency_data:
                row.append(latency_data[latency_key])
            else:
                # Fallback: intra-region if same, else estimate
                if source == target:
                    row.append(0.3)  # Default intra-region
                else:
                    row.append(50.0)  # Default inter-region
        matrix.append(row)
    
    return aws_regions, matrix

def export_latency_summary():
    """
    Export latency statistics summary
    
    Returns:
        Dictionary with latency statistics
    """
    latency_data, aws_regions = load_aws_latency_data()
    
    if not latency_data:
        return {"error": "No latency data available"}
    
    # Calculate statistics
    intra_region_latencies = []
    inter_region_latencies = []
    
    for (source, target), latency in latency_data.items():
        if source == target:
            intra_region_latencies.append(latency)
        else:
            inter_region_latencies.append(latency)
    
    stats = {
        "total_regions": len(aws_regions),
        "total_latency_entries": len(latency_data),
        "intra_region_latencies": {
            "count": len(intra_region_latencies),
            "min": min(intra_region_latencies) if intra_region_latencies else 0,
            "max": max(intra_region_latencies) if intra_region_latencies else 0,
            "avg": sum(intra_region_latencies) / len(intra_region_latencies) if intra_region_latencies else 0
        },
        "inter_region_latencies": {
            "count": len(inter_region_latencies),
            "min": min(inter_region_latencies) if inter_region_latencies else 0,
            "max": max(inter_region_latencies) if inter_region_latencies else 0,
            "avg": sum(inter_region_latencies) / len(inter_region_latencies) if inter_region_latencies else 0
        }
    }
    
    return stats

def validate_latency_data():
    """
    Validate the loaded latency data for completeness
    
    Returns:
        Dictionary with validation results
    """
    latency_data, aws_regions = load_aws_latency_data()
    
    validation = {
        "has_data": bool(latency_data),
        "region_count": len(aws_regions),
        "missing_intra_region": [],
        "missing_inter_region": 0,
        "completeness_score": 0.0
    }
    
    if not latency_data or not aws_regions:
        return validation
    
    # Check intra-region latencies
    for region in aws_regions:
        if (region, region) not in latency_data:
            validation["missing_intra_region"].append(region)
    
    # Check inter-region latencies completeness
    total_possible_pairs = len(aws_regions) * len(aws_regions)
    actual_pairs = len(latency_data)
    validation["completeness_score"] = actual_pairs / total_possible_pairs if total_possible_pairs > 0 else 0
    
    # Count missing inter-region pairs (approximate)
    validation["missing_inter_region"] = total_possible_pairs - actual_pairs
    
    return validation

def get_region_latency_stats(region_name):
    """
    Get latency statistics for a specific region
    
    Args:
        region_name: AWS region name
    
    Returns:
        Dictionary with latency statistics for the region
    """
    from ..core.regions import REGION_TO_AWS
    
    aws_region = REGION_TO_AWS.get(region_name)
    if not aws_region:
        return {"error": f"Unknown region: {region_name}"}
    
    latency_data, aws_regions = load_aws_latency_data()
    
    if aws_region not in aws_regions:
        return {"error": f"AWS region not in latency data: {aws_region}"}
    
    # Collect all latencies from this region
    outbound_latencies = []
    inbound_latencies = []
    
    for (source, target), latency in latency_data.items():
        if source == aws_region:
            outbound_latencies.append({
                "target": target,
                "latency": latency
            })
        if target == aws_region:
            inbound_latencies.append({
                "source": source, 
                "latency": latency
            })
    
    # Calculate statistics
    outbound_values = [item["latency"] for item in outbound_latencies]
    inbound_values = [item["latency"] for item in inbound_latencies]
    
    stats = {
        "region": region_name,
        "aws_region": aws_region,
        "outbound_connections": len(outbound_latencies),
        "inbound_connections": len(inbound_latencies),
        "outbound_latency": {
            "min": min(outbound_values) if outbound_values else 0,
            "max": max(outbound_values) if outbound_values else 0,
            "avg": sum(outbound_values) / len(outbound_values) if outbound_values else 0
        },
        "inbound_latency": {
            "min": min(inbound_values) if inbound_values else 0,
            "max": max(inbound_values) if inbound_values else 0, 
            "avg": sum(inbound_values) / len(inbound_values) if inbound_values else 0
        },
        "closest_regions": sorted(outbound_latencies, key=lambda x: x["latency"])[:5],
        "furthest_regions": sorted(outbound_latencies, key=lambda x: x["latency"], reverse=True)[:5]
    }
    
    return stats