"""Complete worldwide region data with AWS pricing"""

# Carbon intensity data (gCO2/kWh)
ALL_REGIONS = {
    # Europe
    "Frankfurt": {"carbon": 86}, "Zurich": {"carbon": 31},
    "Stockholm": {"carbon": 12}, "Milan": {"carbon": 252},
    "Spain": {"carbon": 75}, "Ireland": {"carbon": 192},
    "London": {"carbon": 82}, "Paris": {"carbon": 15},
    
    # North America
    "Oregon": {"carbon": 206}, "Northern Virginia": {"carbon": 385},
    "Ohio": {"carbon": 385}, "Northern California": {"carbon": 366},
    "Montreal": {"carbon": 49}, "Calgary": {"carbon": 418},
    
    # South America
    "Sao Paolo": {"carbon": 90},
    
    # Africa
    "Cape Town": {"carbon": 653},
    
    # Middle East
    "Bahrain": {"carbon": 488}, "UAE (Dubai)": {"carbon": 326},
    "Israel (Tel Aviv)": {"carbon": 457},
    
    # Asia Pacific
    "Hong Kong": {"carbon": 589}, "Hyderabad": {"carbon": 619},
    "Jakarta": {"carbon": 665}, "Kuala Lumpur": {"carbon": 328},
    "Mumbai": {"carbon": 585}, "Melbourne": {"carbon": 466},
    "Auckland": {"carbon": 36}, "Osaka": {"carbon": 458},
    "Seoul": {"carbon": 382}, "Singapore": {"carbon": 600},
    "Sydney": {"carbon": 466}, "Taipei": {"carbon": 498},
    "Thailand": {"carbon": 478}, "Tokyo": {"carbon": 458},
    
    # Mexico
    "Mexico City": {"carbon": 392}
}

# AWS Region Mapping
REGION_TO_AWS = {
    # Europe
    "Frankfurt": "eu-central-1", "Ireland": "eu-west-1", 
    "London": "eu-west-2", "Milan": "eu-south-1", 
    "Paris": "eu-west-3", "Spain": "eu-south-2",
    "Zurich": "eu-central-2", "Stockholm": "eu-north-1",
    
    # Africa
    "Cape Town": "af-south-1",
    
    # South America
    "Sao Paolo": "sa-east-1",
    
    # North America
    "Northern Virginia": "us-east-1", "Ohio": "us-east-2",
    "Northern California": "us-west-1", "Oregon": "us-west-2",
    "Montreal": "ca-central-1", "Calgary": "ca-west-1",
    "Mexico City": "mx-central-1",
    
    # Middle East
    "Bahrain": "me-south-1", "UAE (Dubai)": "me-central-1",
    "Israel (Tel Aviv)": "il-central-1",
    
    # Asia Pacific
    "Hong Kong": "ap-east-1", "Hyderabad": "ap-south-2",
    "Jakarta": "ap-southeast-3", "Kuala Lumpur": "ap-southeast-5",
    "Melbourne": "ap-southeast-4", "Mumbai": "ap-south-1",
    "Auckland": "ap-southeast-6", "Osaka": "ap-northeast-3",
    "Seoul": "ap-northeast-2", "Singapore": "ap-southeast-1",
    "Sydney": "ap-southeast-2", "Taipei": "ap-east-2",
    "Thailand": "ap-southeast-7", "Tokyo": "ap-northeast-1"
}

# Complete AWS instance pricing (USD per hour) for t3/t4g series
REGION_INSTANCE_COSTS = {
    # Europe
    "Spain": {"small": 0.0228, "medium": 0.0456, "large": 0.0912, "xlarge": 0.1824},
    "Milan": {"small": 0.024, "medium": 0.0479, "large": 0.0958, "xlarge": 0.1917},
    "Stockholm": {"small": 0.0216, "medium": 0.0432, "large": 0.0864, "xlarge": 0.1728},
    "Paris": {"small": 0.0236, "medium": 0.0472, "large": 0.0944, "xlarge": 0.1888},
    "Frankfurt": {"small": 0.024, "medium": 0.048, "large": 0.096, "xlarge": 0.192},
    "Ireland": {"small": 0.0228, "medium": 0.0456, "large": 0.0912, "xlarge": 0.1824},
    "London": {"small": 0.0236, "medium": 0.0472, "large": 0.0944, "xlarge": 0.1888},
    "Zurich": {"small": 0.0264, "medium": 0.0528, "large": 0.1056, "xlarge": 0.2112},
    
    # North America
    "Oregon": {"small": 0.0208, "medium": 0.0416, "large": 0.0832, "xlarge": 0.1664},
    "Northern Virginia": {"small": 0.0208, "medium": 0.0416, "large": 0.0832, "xlarge": 0.1664},
    "Ohio": {"small": 0.0208, "medium": 0.0416, "large": 0.0832, "xlarge": 0.1664},
    "Northern California": {"small": 0.0248, "medium": 0.0496, "large": 0.0992, "xlarge": 0.1984},
    "Montreal": {"small": 0.0232, "medium": 0.0464, "large": 0.0928, "xlarge": 0.1856},
    "Calgary": {"small": 0.0232, "medium": 0.0464, "large": 0.0928, "xlarge": 0.1856},
    "Mexico City": {"small": 0.02185, "medium": 0.0437, "large": 0.0874, "xlarge": 0.1748},
    
    # South America
    "Sao Paolo": {"small": 0.0336, "medium": 0.0672, "large": 0.1344, "xlarge": 0.2688},
    
    # Africa
    "Cape Town": {"small": 0.027125, "medium": 0.05425, "large": 0.1085, "xlarge": 0.217},
    
    # Middle East
    "Bahrain": {"small": 0.025075, "medium": 0.05015, "large": 0.1003, "xlarge": 0.2006},
    "UAE (Dubai)": {"small": 0.025075, "medium": 0.05015, "large": 0.1003, "xlarge": 0.2006},
    "Israel (Tel Aviv)": {"small": 0.02395, "medium": 0.0479, "large": 0.0958, "xlarge": 0.1916},
    
    # Asia Pacific
    "Hong Kong": {"small": 0.0292, "medium": 0.0584, "large": 0.1168, "xlarge": 0.2336},
    "Hyderabad": {"small": 0.0224, "medium": 0.0448, "large": 0.0896, "xlarge": 0.1792},
    "Jakarta": {"small": 0.0264, "medium": 0.0528, "large": 0.1056, "xlarge": 0.2112},
    "Kuala Lumpur": {"small": 0.02375, "medium": 0.0475, "large": 0.095, "xlarge": 0.19},
    "Melbourne": {"small": 0.0264, "medium": 0.0528, "large": 0.1056, "xlarge": 0.2112},
    "Mumbai": {"small": 0.0224, "medium": 0.0448, "large": 0.0896, "xlarge": 0.1792},
    "Auckland": {"small": 0.027725, "medium": 0.05545, "large": 0.1109, "xlarge": 0.2218},
    "Osaka": {"small": 0.0272, "medium": 0.0544, "large": 0.1088, "xlarge": 0.2176},
    "Seoul": {"small": 0.026, "medium": 0.052, "large": 0.104, "xlarge": 0.208},
    "Singapore": {"small": 0.0264, "medium": 0.0528, "large": 0.1056, "xlarge": 0.2112},
    "Sydney": {"small": 0.0264, "medium": 0.0528, "large": 0.1056, "xlarge": 0.2112},
    "Taipei": {"small": 0.024475, "medium": 0.04895, "large": 0.0979, "xlarge": 0.1958},
    "Thailand": {"small": 0.02375, "medium": 0.0475, "large": 0.095, "xlarge": 0.19},
    "Tokyo": {"small": 0.0272, "medium": 0.0544, "large": 0.1088, "xlarge": 0.2176}
}

def get_region_carbon_intensity(region_name):
    """Get carbon intensity for a region"""
    return ALL_REGIONS.get(region_name, {}).get("carbon", 100)  # Default 100 if not found

def get_instance_cost(region_name, instance_size):
    """Get instance cost for a region and size"""
    if region_name in REGION_INSTANCE_COSTS:
        return REGION_INSTANCE_COSTS[region_name].get(instance_size, 0.0456)
    return 0.0456  # Default medium instance cost

def get_aws_region_code(region_name):
    """Get AWS region code for a region name"""
    return REGION_TO_AWS.get(region_name, "eu-south-2")  # Default to Spain