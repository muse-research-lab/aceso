# Utils Module

Utility functions for CSV logging, AWS data management, and experiment analysis.

## Files

### 1. `csv_logger.py`
**Purpose**: Comprehensive CSV logging and analysis of experiment results.

**Key Functions**:
- `log_realistic_experiment_csv()`: Log experiment results with full metadata
- `read_experiment_results()`: Read and parse experiment results
- `analyze_experiment_results()`: Statistical analysis of results
- `export_results_to_plot_data()`: Format results for visualization
- `cleanup_old_results()`: Remove old experiment data

**Features**:
- Automatic file creation with headers
- Comprehensive metadata including timestamps
- Assignment serialization/deserialization
- Statistical analysis and summarization
- Data cleanup and maintenance

### 2. `aws_data.py`
**Purpose**: AWS latency data loading, validation, and analysis.

**Key Functions**:
- `load_aws_latency_data()`: Load latency data from CSV with caching
- `get_latency_matrix()`: Get complete latency matrix
- `export_latency_summary()`: Statistical summary of latency data
- `validate_latency_data()`: Data completeness validation
- `get_region_latency_stats()`: Region-specific latency analysis

**Features**:
- Global caching for performance
- Data validation and completeness checking
- Statistical analysis of latency patterns
- Region-specific latency profiling

## Usage Examples

```python
from utils import log_realistic_experiment_csv, read_experiment_results
from utils import load_aws_latency_data, get_region_latency_stats

# Log experiment results
log_realistic_experiment_csv(
    filename="results.csv",
    title="experiment-1",
    base_location="Spain",
    n_services=20,
    n_movable=10,
    load_multiplier=5.0,
    solve_time=0.123,
    assignment={0:0, 1:0, 2:1},
    carbon=45.67,
    cost=0.8912,
    latency=23.45
)

# Analyze results
results = read_experiment_results("results.csv")
analysis = analyze_experiment_results("results.csv")

# Work with AWS latency data
latency_data, regions = load_aws_latency_data()
stats = get_region_latency_stats("Stockholm")