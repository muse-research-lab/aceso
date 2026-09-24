"""Enhanced latency calculation with inter-region support"""
import csv
import random

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
        import os
        
        # FIX: Look for CSV in the package directory, not current working directory
        package_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(package_dir, "..", "utils", "aws_latency_data.csv")
        csv_path = os.path.normpath(csv_path)  # Clean up the path
        
        
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)
            aws_regions = [region.strip() for region in headers[1:]]
            _AWS_REGIONS_LIST = aws_regions
            
            row_count = 0
            for row in reader:
                if not row:
                    continue
                row_count += 1
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
            
        _LATENCY_CACHE = latency_data
        return latency_data, aws_regions
        
    except FileNotFoundError:
        _LATENCY_CACHE = {}
        _AWS_REGIONS_LIST = []
        return {}, []

def get_intra_region_latency(region_name):
    """Get accurate intra-region latency - ORIGINAL LOGIC"""
    return random.uniform(0.1, 0.3) 

def get_inter_region_latency(source_region_name, target_region_name):
    """Get inter-region latency from CSV data"""
    from .regions import REGION_TO_AWS
    
    # If same region, use intra-region latency 
    if source_region_name == target_region_name:
        return get_intra_region_latency(source_region_name)
    
    # Get AWS region codes
    source_aws = REGION_TO_AWS.get(source_region_name, "eu-south-2")
    target_aws = REGION_TO_AWS.get(target_region_name, "eu-south-2")
    
    # Load latency data
    latency_data, _ = load_aws_latency_data()
    
    # Look up latency in CSV data
    latency_key = (source_aws, target_aws)
    
    if latency_key in latency_data:
        return latency_data[latency_key]
    else:
        # Fallback for missing inter-region data
        print(f"⚠️  No latency data for {source_region_name} -> {target_region_name}, using fallback")
        return random.uniform(20.0, 80.0)  # Reasonable inter-region fallback