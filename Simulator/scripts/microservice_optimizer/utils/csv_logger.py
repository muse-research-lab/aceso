"""CSV logging utilities for experiment results"""
import csv
import os
from datetime import datetime

def log_realistic_experiment_csv(filename, title, base_location, n_services, n_movable, 
                               load_multiplier, solve_time, assignment, carbon, cost, latency):
    """
    Log experiment results to CSV file with comprehensive metadata
    
    Args:
        filename: CSV file name
        title: Experiment title/identifier
        base_location: Base region name
        n_services: Number of microservices
        n_movable: Number of movable services
        load_multiplier: Current load level
        solve_time: Optimization/evaluation time
        assignment: Service to region assignment
        carbon: Carbon emissions (gCO2)
        cost: Total cost (USD)
        latency: Total latency (ms)
    """
    # Create file with headers if it doesn't exist
    file_exists = os.path.isfile(filename)
    
    with open(filename, 'a', newline='') as f:
        writer = csv.writer(f)
        
        # Write headers if new file
        if not file_exists:
            writer.writerow([
                'timestamp', 'experiment_id', 'base_location', 'n_services', 
                'n_movable', 'load_multiplier', 'solve_time_seconds',
                'assignment', 'carbon_emissions_g', 'total_cost_usd', 
                'total_latency_ms', 'carbon_per_service', 'cost_per_service',
                'latency_per_service'
            ])
        
        # Convert assignment to string format
        assignment_str = ";".join([f"s{service}:{region}" for service, region in assignment.items()])
        
        # Calculate per-service metrics
        carbon_per_service = carbon / n_services if n_services > 0 else 0
        cost_per_service = cost / n_services if n_services > 0 else 0
        latency_per_service = latency / n_services if n_services > 0 else 0
        
        # Write data row
        writer.writerow([
            datetime.now().isoformat(),
            title,
            base_location,
            n_services,
            n_movable,
            load_multiplier,
            round(solve_time, 6),
            assignment_str,
            round(carbon, 4),
            round(cost, 6),
            round(latency, 4),
            round(carbon_per_service, 4),
            round(cost_per_service, 6),
            round(latency_per_service, 4)
        ])

def read_experiment_results(filename):
    """
    Read experiment results from CSV file
    
    Args:
        filename: CSV file name
    
    Returns:
        List of dictionaries with experiment results
    """
    if not os.path.isfile(filename):
        return []
    
    results = []
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse assignment string back to dictionary
            assignment_str = row['assignment']
            assignment = {}
            if assignment_str:
                for pair in assignment_str.split(';'):
                    if ':' in pair:
                        service_str, region_str = pair.split(':', 1)
                        service_id = int(service_str[1:])  # Remove 's' prefix
                        region_idx = int(region_str)
                        assignment[service_id] = region_idx
            
            results.append({
                'timestamp': row['timestamp'],
                'experiment_id': row['experiment_id'],
                'base_location': row['base_location'],
                'n_services': int(row['n_services']),
                'n_movable': int(row['n_movable']),
                'load_multiplier': float(row['load_multiplier']),
                'solve_time': float(row['solve_time_seconds']),
                'assignment': assignment,
                'carbon': float(row['carbon_emissions_g']),
                'cost': float(row['total_cost_usd']),
                'latency': float(row['total_latency_ms']),
                'carbon_per_service': float(row['carbon_per_service']),
                'cost_per_service': float(row['cost_per_service']),
                'latency_per_service': float(row['latency_per_service'])
            })
    
    return results

def analyze_experiment_results(filename):
    """
    Analyze and summarize experiment results from CSV
    
    Args:
        filename: CSV file name
    
    Returns:
        Dictionary with analysis results
    """
    results = read_experiment_results(filename)
    if not results:
        return {}
    
    # Group by experiment type and load
    experiments = {}
    for result in results:
        exp_id = result['experiment_id']
        load = result['load_multiplier']
        
        if exp_id not in experiments:
            experiments[exp_id] = {}
        
        if load not in experiments[exp_id]:
            experiments[exp_id][load] = []
        
        experiments[exp_id][load].append(result)
    
    # Calculate statistics
    analysis = {
        'total_experiments': len(results),
        'unique_configurations': len(experiments),
        'experiments_by_region': {},
        'best_per_region': {},
        'scaling_analysis': {}
    }
    
    # Analyze by region
    regions = set()
    for result in results:
        region = result['base_location']
        regions.add(region)
        
        if region not in analysis['experiments_by_region']:
            analysis['experiments_by_region'][region] = []
        analysis['experiments_by_region'][region].append(result)
    
    # Find best results per region at max load
    max_load = max(r['load_multiplier'] for r in results)
    for region in regions:
        region_results = [r for r in results if r['base_location'] == region and r['load_multiplier'] == max_load]
        if region_results:
            best_carbon = min(region_results, key=lambda x: x['carbon'])
            best_cost = min(region_results, key=lambda x: x['cost'])
            best_latency = min(region_results, key=lambda x: x['latency'])
            
            analysis['best_per_region'][region] = {
                'best_carbon': best_carbon,
                'best_cost': best_cost,
                'best_latency': best_latency
            }
    
    return analysis

def export_results_to_plot_data(filename, output_format='json'):
    """
    Export results in format suitable for plotting
    
    Args:
        filename: CSV file name
        output_format: 'json' or 'csv'
    
    Returns:
        Data in requested format
    """
    results = read_experiment_results(filename)
    if not results:
        return None
    
    # Group by experiment and load for plotting
    plot_data = {}
    
    for result in results:
        exp_id = result['experiment_id']
        load = result['load_multiplier']
        
        if exp_id not in plot_data:
            plot_data[exp_id] = {
                'loads': [],
                'carbon': [],
                'cost': [],
                'latency': []
            }
        
        # Only add if this load level not already recorded (avoid duplicates)
        if load not in plot_data[exp_id]['loads']:
            plot_data[exp_id]['loads'].append(load)
            plot_data[exp_id]['carbon'].append(result['carbon'])
            plot_data[exp_id]['cost'].append(result['cost'])
            plot_data[exp_id]['latency'].append(result['latency'])
    
    # Sort by load for clean plotting
    for exp_id in plot_data:
        sorted_indices = sorted(range(len(plot_data[exp_id]['loads'])), 
                              key=lambda i: plot_data[exp_id]['loads'][i])
        
        plot_data[exp_id]['loads'] = [plot_data[exp_id]['loads'][i] for i in sorted_indices]
        plot_data[exp_id]['carbon'] = [plot_data[exp_id]['carbon'][i] for i in sorted_indices]
        plot_data[exp_id]['cost'] = [plot_data[exp_id]['cost'][i] for i in sorted_indices]
        plot_data[exp_id]['latency'] = [plot_data[exp_id]['latency'][i] for i in sorted_indices]
    
    if output_format == 'json':
        return plot_data
    else:
        # Convert to CSV format
        csv_lines = ['experiment_id,load,carbon,cost,latency']
        for exp_id, data in plot_data.items():
            for i in range(len(data['loads'])):
                csv_lines.append(f"{exp_id},{data['loads'][i]},{data['carbon'][i]},{data['cost'][i]},{data['latency'][i]}")
        return '\n'.join(csv_lines)

def cleanup_old_results(filename, days_old=30):
    """
    Remove experiment results older than specified days
    
    Args:
        filename: CSV file name
        days_old: Remove results older than this many days
    """
    if not os.path.isfile(filename):
        return
    
    from datetime import datetime, timedelta
    cutoff_date = datetime.now() - timedelta(days=days_old)
    
    # Read all results
    results = read_experiment_results(filename)
    if not results:
        return
    
    # Filter recent results
    recent_results = []
    for result in results:
        result_date = datetime.fromisoformat(result['timestamp'])
        if result_date >= cutoff_date:
            recent_results.append(result)
    
    # Rewrite file with only recent results
    if recent_results:
        # Remove file and recreate with headers
        os.remove(filename)
        for result in recent_results:
            log_realistic_experiment_csv(
                filename=filename,
                title=result['experiment_id'],
                base_location=result['base_location'],
                n_services=result['n_services'],
                n_movable=result['n_movable'],
                load_multiplier=result['load_multiplier'],
                solve_time=result['solve_time'],
                assignment=result['assignment'],
                carbon=result['carbon'],
                cost=result['cost'],
                latency=result['latency']
            )
    else:
        # No recent results, remove file
        os.remove(filename)