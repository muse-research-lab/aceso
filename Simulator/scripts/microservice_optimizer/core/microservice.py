"""Microservice profile definitions"""
import random

# Import at the top level, not inside methods
from microservice_optimizer.core.regions import get_instance_cost

class MicroserviceProfile:
    def __init__(self, service_id, service_type="compute"):
        self.service_id = service_id
        self.service_type = service_type
        
        # REALISTIC Processing characteristics
        self.base_processing_time = self._get_base_processing_time(service_type)
        self.processing_variance = self._get_processing_variance(service_type)
        self.base_power_watts = self._get_base_power(service_type)
        self.scaling_thresholds = self._get_scaling_thresholds(service_type)
        self.accesses_database = random.random() < 0.3
        
        # Execution constraints
        self.depends_on_services = []
        self.can_run_in_parallel_with = []
        self.load_multiplier = 1.0
        
    def _get_base_processing_time(self, service_type):
        """Get base processing time based on service type"""
        processing_times = {
            "api": (0.1, 0.3),
            "database": (0.5, 2.0),
            "cache": (0.05, 0.2),
            "compute": (0.2, 0.8)
        }
        low, high = processing_times.get(service_type, (0.2, 0.8))
        return random.uniform(low, high)
    
    def _get_processing_variance(self, service_type):
        """Get processing variance based on service type"""
        variances = {
            "api": (0.05, 0.1),
            "database": (0.1, 0.3),
            "cache": (0.02, 0.08),
            "compute": (0.08, 0.15)
        }
        low, high = variances.get(service_type, (0.08, 0.15))
        return random.uniform(low, high)
    
    def _get_base_power(self, service_type):
        """Get base power consumption based on service type"""
        power_ranges = {
            "database": (8, 15),
            "api": (3, 6),
            "cache": (2, 5),
            "compute": (4, 10)
        }
        low, high = power_ranges.get(service_type, (4, 10))
        return random.uniform(low, high)
    
    def _get_scaling_thresholds(self, service_type):
        """Get scaling thresholds based on service type"""
        thresholds = {
            "database": {"small": 2.0, "medium": 4.0, "large": 7.0, "xlarge": 10.0},
            "api": {"small": 3.0, "medium": 6.0, "large": 9.0, "xlarge": 10.0},
            "cache": {"small": 4.0, "medium": 8.0, "large": 10.0, "xlarge": 10.0},
            "compute": {"small": 3.0, "medium": 6.0, "large": 8.0, "xlarge": 10.0}
        }
        return thresholds.get(service_type, thresholds["compute"])
    
    def get_required_instance_size(self, load):
        """Determine which instance size is needed for current load"""
        if load <= self.scaling_thresholds["small"]:
            return "small"
        elif load <= self.scaling_thresholds["medium"]:
            return "medium"
        elif load <= self.scaling_thresholds["large"]:
            return "large"
        else:
            return "xlarge"
        
    def get_processing_time(self):
        """Get current processing time with load scaling and variance"""
        base_time = self.base_processing_time * self.load_multiplier
        variance = random.uniform(-self.processing_variance, self.processing_variance)
        return max(0.01, base_time + variance)
    
    def get_power_consumption(self):
        """Get current power consumption with load scaling"""
        return self.base_power_watts * self.load_multiplier
    
    def get_hourly_cost(self, region_name, current_load):
        """Get hourly cost based on required instance size for current load"""
        # Determine which instance size we need for this load
        required_size = self.get_required_instance_size(current_load)
        
        # Get the base cost for that instance size in the region
        base_cost = get_instance_cost(region_name, required_size)
        
        # Adjust cost based on service type complexity
        if self.service_type == "database":
            base_cost *= 1.3  # Databases are more expensive
        elif self.service_type == "api":
            base_cost *= 1.1  # API gateways slightly more expensive
        
        return base_cost
    
    def set_load_multiplier(self, multiplier):
        """Set load multiplier with bounds"""
        self.load_multiplier = max(1.0, min(10.0, multiplier))