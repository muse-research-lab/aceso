# Core Module

The core module provides fundamental components for modeling microservice architectures, carbon-aware optimization, and realistic performance evaluation.

## Files

### 1. `regions.py`
**Purpose**: Worldwide region data with AWS pricing and carbon intensity.

**Key Components**:
- `ALL_REGIONS`: Carbon intensity data (gCO2/kWh) for 30+ worldwide regions
- `REGION_INSTANCE_COSTS`: Complete AWS pricing for small/medium/large/xlarge instances
- `REGION_TO_AWS`: Mapping from region names to AWS region codes
- `get_region_carbon_intensity(region_name)`: Get carbon intensity for a region
- `get_instance_cost(region_name, instance_size)`: Get instance cost
- `get_aws_region_code(region_name)`: Get AWS region code

**Regions Covered**: Europe, North America, South America, Africa, Middle East, Asia Pacific

### 2. `microservice.py`
**Purpose**: Realistic microservice profile modeling with type-specific characteristics.

**Key Components**:
- `MicroserviceProfile`: Models individual microservices with:
  - Service types: `api`, `database`, `cache`, `compute`
  - Realistic processing times and variances by type
  - Power consumption modeling
  - Instance size scaling thresholds
  - Database access patterns
  - Load-dependent performance and cost calculations

**Service Type Characteristics**:
- **API**: Fast processing (0.1-0.3ms), medium power, moderate scaling
- **Database**: Slow processing (0.5-2.0ms), high power, aggressive scaling  
- **Cache**: Very fast (0.05-0.2ms), low power, memory-bound scaling
- **Compute**: Medium processing (0.2-0.8ms), variable power, moderate scaling

### 3. `graph.py`
**Purpose**: Generate realistic microservice dependency graphs and analyze graph properties.

**Key Components**:
- `generate_realistic_microservice_graph(n_services, fixed_percentage=0.1)`: Generate graph with profiles
- Service distribution: 1 API, ~10% databases, ~30% cache, ~60% compute
- `_identify_fixed_nodes()`: Pin critical path nodes (root + highest critical path contributors)
- `get_graph_statistics()`: Comprehensive graph metrics
- `print_graph_summary()`: Formatted graph analysis
- `validate_assignment()`: Validate service-to-region assignments
- `export_graph_to_dict()` / `import_graph_from_dict()`: Graph serialization

**Graph Features**:
- Natural dependency structures with varied depths
- Critical path analysis for latency-sensitive node identification
- Realistic service fan-out without artificial limits

### 4. `latency.py`  
**Purpose**: Accurate intra-region and inter-region latency calculations.

**Key Components**:
- `load_aws_latency_data()`: Load real AWS latency data from CSV
- `get_intra_region_latency(region_name)`: Intra-region latency (0.1-0.3ms random)
- `get_inter_region_latency(source, target)`: Inter-region latency from CSV data

**Latency Model**:
- **Intra-region**: Fast (0.1-0.3ms) - uses original random uniform logic
- **Inter-region**: Real AWS latencies from CSV, fallback to 20-80ms random

## Usage Examples

```python
from core import generate_realistic_microservice_graph, print_graph_summary
from core import get_region_carbon_intensity, get_instance_cost

# Generate microservice architecture
graph, fixed_nodes, services = generate_realistic_microservice_graph(20)
print_graph_summary(graph, services, fixed_nodes)

# Access region data
carbon = get_region_carbon_intensity("Stockholm")  # 12 gCO2/kWh
cost = get_instance_cost("Tokyo", "large")         # $0.1088/hour

# Validate optimization assignments
validate_assignment(assignment, fixed_nodes, 20, ["Spain", "Stockholm"])