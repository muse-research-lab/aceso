# Analysis Module

This module provides analysis tools for evaluating microservice deployments across different regions, loads, and configurations.

## Files

### 1. `baseline.py`
**Purpose**: Single-region baseline analysis and regional comparisons.

**Key Functions**:
- `run_optimized_baseline_analysis_with_graph()`: Analyze single region with pre-generated graph
- `compare_baseline_regions()`: Compare multiple regions using same graph

**Features**:
- Single-region deployment analysis
- Load scaling from 1x to 10x
- Instance size distribution tracking
- CSV logging for results

### 2. `multi_region.py` 
**Purpose**: Multi-region comparison with consistent graphs for fair evaluation.

**Key Functions**:
- `run_multiple_regions_analysis()`: Test multiple regions with same graph
- `run_single_region_analysis_with_graph()`: Single region analysis with shared graph
- `analyze_region_tradeoffs()`: Carbon-cost-latency tradeoff analysis

**Features**:
- Fixed random seed for reproducible graphs
- Same graph used across all regions
- Comparative summary reporting
- Tradeoff scoring system

## Usage Examples

```python
from analysis import run_multiple_regions_analysis, compare_baseline_regions

# Compare multiple regions with same graph
results = run_multiple_regions_analysis(
    ms_size=20,
    regions_to_test=["Spain", "Stockholm", "Milan", "Tokyo"],
    load_scenarios=[1, 5, 10]
)

# Single region baseline analysis
from analysis import run_optimized_baseline_analysis_with_graph
results = run_optimized_baseline_analysis_with_graph(
    ms_size=50,
    base_location="Stockholm",
    load_scenarios=[1, 3, 5, 7, 10]
)

# Region tradeoff analysis
tradeoffs = analyze_region_tradeoffs(
    ms_size=30,
    regions_to_test=["Spain", "Stockholm", "Tokyo", "Cape Town"],
    load_level=5
)