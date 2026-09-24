# Evaluation Module

This module provides comprehensive evaluation tools for assessing microservice deployment performance, including carbon emissions, cost, and latency calculations.

## Files

### 1. `evaluator.py`
**Purpose**: Main evaluation function for microservice deployments with hybrid parallel/sequential execution.

**Key Functions**:
- `evaluate_realistic_assignment_fast()`: Comprehensive evaluation of deployments
- `evaluate_assignment_batch()`: Batch evaluation for optimization algorithms
- `get_evaluation_metrics()`: Detailed metrics for analysis

**Evaluation Components**:
- **Carbon Emissions**: Based on region carbon intensity and service power consumption
- **Cost Calculation**: Instance size pricing with service type adjustments
- **Latency Modeling**: Hybrid parallel/sequential execution with network delays
- **Instance Distribution**: Track small/medium/large/xlarge instance requirements

### 2. `parallel_model.py`
**Purpose**: Advanced parallel execution modeling and critical path analysis.

**Key Functions**:
- `calculate_hybrid_latency()`: Recursive latency calculation with parallel groups
- `analyze_critical_path()`: Identify and analyze the longest execution path

**Execution Model**:
- **Sequential Children**: Execute one after another
- **Parallel Groups**: Up to 3 children execute concurrently (max determines group time)
- **Network Latency**: Intra-region (0.1-0.3ms) vs inter-region (CSV data)
- **Database Access**: Additional intra-region latency for database operations

## Usage Examples

```python
from evaluation import evaluate_realistic_assignment_fast, analyze_critical_path

# Basic evaluation
carbon, cost, latency, instances = evaluate_realistic_assignment_fast(
    assignment, graph, service_profiles, regions, "Spain", current_load=5
)

# Batch evaluation for optimization
results = evaluate_assignment_batch(
    [assignment1, assignment2, assignment3],
    graph, service_profiles, regions, "Spain", current_load=5
)

# Critical path analysis
critical_info = analyze_critical_path(
    graph, service_profiles, assignment, regions
)
print(f"Critical path: {critical_info['critical_path']}")
print(f"Total latency: {critical_info['total_latency']:.2f}ms")