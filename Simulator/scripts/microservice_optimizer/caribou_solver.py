#!/usr/bin/env python3
"""
HBSS Optimizer for microservice placement using realistic simulation metrics
"""

import sys
import os
import time
import numpy as np
import random
from collections import deque

# Add current directory to path for package imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from microservice_optimizer.core.regions import ALL_REGIONS, get_region_carbon_intensity, get_instance_cost
from microservice_optimizer.core.graph import generate_realistic_microservice_graph, print_graph_summary
from microservice_optimizer.core.microservice import MicroserviceProfile
from microservice_optimizer.core.latency import get_inter_region_latency
from microservice_optimizer.evaluation.evaluator import evaluate_realistic_assignment_fast
from microservice_optimizer.utils.csv_logger import log_realistic_experiment_csv


class HBSSOptimizer:
    def __init__(self, ms_size, base_location, candidate_regions=None, fixed_percentage=0.2, 
                 latency_threshold=1000, load_level=5, random_seed=42, slo_requirement=None):
        """
        Initialize HBSS Optimizer
        
        Args:
            ms_size: Number of microservices
            base_location: Base region for fixed nodes
            candidate_regions: List of candidate regions for placement
            fixed_percentage: Percentage of nodes to fix to base location
            latency_threshold: Maximum allowed latency (ms)
            load_level: Load multiplier for cost calculation
            random_seed: Random seed for reproducible graphs
            slo_requirement: SLO latency requirement in ms
        """
        self.ms_size = ms_size
        self.base_location = base_location
        self.candidate_regions = candidate_regions or list(ALL_REGIONS.keys())
        self.fixed_percentage = fixed_percentage
        self.latency_threshold = latency_threshold
        self.load_level = load_level
        self.random_seed = random_seed
        self.slo_requirement = slo_requirement
        
        # Generate microservice graph using simulation's generator
        self.graph, self.fixed_nodes, self.service_profiles = self._generate_graph()
        
        # Region indices mapping
        self.region_names = self.candidate_regions
        self.region_indices = {name: idx for idx, name in enumerate(self.region_names)}
        self.n_regions = len(self.region_names)
        self.n_services = len(self.graph)
        
        # Get base region index
        self.base_idx = self.region_indices.get(base_location, 0)
        
        # Pre-calculate latency matrix
        self.latency_matrix = self._get_inter_region_latency_matrix()
        
        # Set random seeds
        random.seed(self.random_seed)
        np.random.seed(self.random_seed)
        
        print(f"🔧 HBSS Optimizer Initialized:")
        print(f"   Microservices: {self.n_services}")
        print(f"   Candidate Regions: {len(self.region_names)}")
        print(f"   Base Location: {base_location} (index {self.base_idx})")
        print(f"   Fixed Nodes: {len(self.fixed_nodes)}")
        print(f"   Latency Threshold: {latency_threshold}ms")
        print(f"   Load Level: {load_level}x")
        if self.slo_requirement:
            print(f"   SLO Requirement: {self.slo_requirement}ms")

    def _get_inter_region_latency_matrix(self):
        """Create latency matrix between all candidate regions using simulation's function"""
        latency_matrix = np.zeros((self.n_regions, self.n_regions))
        
        for i, region1 in enumerate(self.region_names):
            for j, region2 in enumerate(self.region_names):
                latency_matrix[i, j] = get_inter_region_latency(region1, region2)
        
        return latency_matrix

    def _generate_graph(self):
        """Generate microservice graph with fixed random seed using simulation's generator"""
        import random
        random.seed(self.random_seed)
        return generate_realistic_microservice_graph(self.ms_size, self.fixed_percentage)
    
    def _get_service_carbon_cost(self, service_id, region_idx):
        """Get carbon emissions for a service in a specific region"""
        profile = self.service_profiles[service_id]
        region_name = self.region_names[region_idx]
        
        # Carbon calculation (same as in evaluator)
        carbon_intensity = get_region_carbon_intensity(region_name)
        power_kw = profile.get_power_consumption() / 1000.0
        energy_kwh = power_kw * 1.0  # 1 hour execution
        return energy_kwh * carbon_intensity
    
    def _get_service_monetary_cost(self, service_id, region_idx):
        """Get monetary cost for a service in a specific region"""
        profile = self.service_profiles[service_id]
        region_name = self.region_names[region_idx]
        
        # Cost calculation (same as in evaluator)
        return profile.get_hourly_cost(region_name, self.load_level)
    
    def _find_all_paths(self, graph, start_node=0):
        """Find all root-to-leaf paths in the graph"""
        paths = []
        def dfs(node, path):
            path.append(node)
            if not graph[node]:  # Leaf node
                paths.append(list(path))
            else:
                for child in graph[node]:
                    dfs(child, path)
            path.pop()
        dfs(start_node, [])
        return paths
    
    def _evaluate_assignment_simulation_style(self, assignment_array):
        """
        Evaluate assignment using simulation's exact evaluation
        assignment_array: numpy array of region indices for each service
        """
        # Convert to region names for evaluation
        assignment_dict = {s: self.region_names[r] for s, r in enumerate(assignment_array)}
        
        # Set load level for all services
        for profile in self.service_profiles.values():
            profile.set_load_multiplier(self.load_level)
        
        # Evaluate using simulation's exact evaluator
        regions_dict = {name: ALL_REGIONS[name] for name in self.region_names}
        
        carbon, cost, latency, instances = evaluate_realistic_assignment_fast(
            assignment_dict, self.graph, self.service_profiles, 
            regions_dict, self.base_location, self.load_level
        )
        
        return carbon, cost, latency
    
    def _compute_baseline_simulation_style(self):
        """Compute baseline with all services in base location"""
        baseline_assignment = {s: self.base_location for s in range(self.n_services)}
        
        # Set load level for all services
        for profile in self.service_profiles.values():
            profile.set_load_multiplier(self.load_level)
        
        regions_dict = {name: ALL_REGIONS[name] for name in self.region_names}
        
        carbon, cost, latency, _ = evaluate_realistic_assignment_fast(
            baseline_assignment, self.graph, self.service_profiles,
            regions_dict, self.base_location, self.load_level
        )
        
        return carbon, cost, latency
    
    def _construct_heuristic_probabilities(self):
        """Construct heuristic preference weights per region (low carbon, low cost)"""
        # Calculate average carbon and cost per region across all service types
        avg_carbons = []
        avg_costs = []
        
        for region_idx in range(self.n_regions):
            region_carbons = []
            region_costs = []
            
            for service_id in range(self.n_services):
                carbon = self._get_service_carbon_cost(service_id, region_idx)
                cost = self._get_service_monetary_cost(service_id, region_idx)
                region_carbons.append(carbon)
                region_costs.append(cost)
            
            avg_carbons.append(np.mean(region_carbons))
            avg_costs.append(np.mean(region_costs))
        
        # Normalize and combine heuristics
        carbons = np.array(avg_carbons)
        costs = np.array(avg_costs)
        
        # Convert to minimization problem (lower is better)
        norm_carbons = carbons / (carbons.max() + 1e-9)
        norm_costs = costs / (costs.max() + 1e-9)
        
        # Combined heuristic (lower carbon + lower cost = higher preference)
        heuristics = 1.0 / (0.5 * norm_carbons + 0.5 * norm_costs + 1e-9)
        
        return heuristics
    
    def solve(self, n_samples=50000, bias_strength=4.0):
        """Solve using Heuristic-Biased Stochastic Sampling"""
        print(f"\n🎯 Starting HBSS Optimization with {n_samples} samples...")
        
        movable_services = [s for s in range(self.n_services) if s not in self.fixed_nodes]
        
        # Compute baseline
        baseline_carbon, baseline_cost, baseline_latency = self._compute_baseline_simulation_style()
        
        # Construct heuristic probabilities
        heuristics = self._construct_heuristic_probabilities()
        probs = heuristics ** bias_strength
        probs /= probs.sum()
        
        print(f"🔧 Heuristic probabilities: {dict(zip(self.region_names, probs))}")
        
        start_time = time.time()
        best_assignment = None
        best_score = float("inf")
        best_carbon = None
        best_cost = None
        best_latency = None
        feasible_solutions_found = 0
        
        # Use SLO requirement if specified, otherwise use latency threshold
        latency_constraint = self.slo_requirement if self.slo_requirement else self.latency_threshold
        
        for sample in range(n_samples):
            if sample % 10000 == 0 and sample > 0:
                print(f"   ... processed {sample}/{n_samples} samples, found {feasible_solutions_found} feasible")
            
            # Generate random assignment based on heuristic probabilities
            assignment = np.empty(self.n_services, dtype=int)
            for s in range(self.n_services):
                if s in self.fixed_nodes:
                    assignment[s] = self.base_idx
                else:
                    assignment[s] = np.random.choice(self.n_regions, p=probs)
            
            # Evaluate using simulation's exact evaluation
            carbon, cost, latency = self._evaluate_assignment_simulation_style(assignment)
            
            # Check latency constraint
            if latency <= latency_constraint:
                feasible_solutions_found += 1
                # Combined score (carbon + normalized cost)
                score = carbon + cost   # Normalize cost to similar scale as carbon
                
                if score < best_score:
                    best_score = score
                    best_assignment = assignment.copy()
                    best_carbon = carbon
                    best_cost = cost
                    best_latency = latency
        
        solve_time = time.time() - start_time
        
        # If no feasible solution found, use baseline
        if best_assignment is None:
            print("⚠️  No feasible solution found, using baseline")
            best_assignment = np.array([self.base_idx] * self.n_services)
            best_carbon, best_cost, best_latency = self._compute_baseline_simulation_style()
            feasible_solutions_found = 0
        
        # Convert to dictionary format
        assignment_dict = {s: int(best_assignment[s]) for s in range(self.n_services)}
        
        # Calculate improvements
        carbon_improvement = baseline_carbon - best_carbon
        cost_improvement = baseline_cost - best_cost
        latency_improvement = baseline_latency - best_latency
        
        carbon_improvement_pct = (carbon_improvement / baseline_carbon * 100) if baseline_carbon > 0 else 0
        cost_improvement_pct = (cost_improvement / baseline_cost * 100) if baseline_cost > 0 else 0
        latency_improvement_pct = (latency_improvement / baseline_latency * 100) if baseline_latency > 0 else 0
        
        # Check SLO requirement
        slo_ok = True
        if self.slo_requirement:
            slo_ok = best_latency <= self.slo_requirement
        
        # Print results
        self._print_results(
            assignment_dict, best_carbon, best_cost, best_latency, 
            feasible_solutions_found, slo_ok,
            baseline_carbon, baseline_cost, baseline_latency,
            carbon_improvement, cost_improvement, latency_improvement,
            carbon_improvement_pct, cost_improvement_pct, latency_improvement_pct,
            solve_time, n_samples
        )
        
        # Log to CSV
        self._log_results(
            assignment_dict, best_carbon, best_cost, best_latency,
            carbon_improvement, cost_improvement, latency_improvement,
            carbon_improvement_pct, cost_improvement_pct, latency_improvement_pct,
            solve_time, baseline_carbon, baseline_cost
        )
        
        return {
            'assignment': assignment_dict,
            'carbon': best_carbon,
            'cost': best_cost,
            'latency': best_latency,
            'slo_ok': slo_ok,
            'feasible_solutions': feasible_solutions_found,
            'improvements': {
                'carbon': carbon_improvement,
                'cost': cost_improvement, 
                'latency': latency_improvement,
                'carbon_pct': carbon_improvement_pct,
                'cost_pct': cost_improvement_pct,
                'latency_pct': latency_improvement_pct
            }
        }
    
    def _print_results(self, assignment, carbon, cost, latency, feasible_solutions, slo_ok,
                      baseline_carbon, baseline_cost, baseline_latency,
                      carbon_imp, cost_imp, latency_imp,
                      carbon_imp_pct, cost_imp_pct, latency_imp_pct, solve_time, n_samples):
        """Print optimization results"""
        latency_status = "✅ WITHIN LIMIT" if latency <= self.latency_threshold else "❌ EXCEEDS LIMIT"
        slo_status = "✅ WITHIN SLO" if (not self.slo_requirement or slo_ok) else "❌ EXCEEDS SLO"
        
        print(f"\n{'='*80}")
        print("🎯 HBSS OPTIMIZATION RESULTS")
        print(f"{'='*80}")
        
        print(f"\n📊 Performance Metrics:")
        print(f"   Solve Time: {solve_time:.2f} seconds")
        print(f"   Samples: {n_samples}, Feasible Solutions Found: {feasible_solutions}")
        print(f"   Services: {self.n_services}, Regions: {self.n_regions}")
        print(f"   Fixed Nodes: {len(self.fixed_nodes)}")
        print(f"   Latency: {latency:.2f}ms vs Threshold: {self.latency_threshold}ms {latency_status}")
        if self.slo_requirement:
            print(f"   SLO Requirement: {latency:.2f}ms vs {self.slo_requirement}ms {slo_status}")
        
        print(f"\n📈 Optimization Results vs Baseline:")
        print(f"   Carbon: {carbon:6.2f}g vs {baseline_carbon:6.2f}g "
              f"(Δ {carbon_imp:+.2f}g, {carbon_imp_pct:+.1f}%)")
        print(f"   Cost:   ${cost:6.4f} vs ${baseline_cost:6.4f} "
              f"(Δ ${cost_imp:+.4f}, {cost_imp_pct:+.1f}%)")
        print(f"   Latency: {latency:6.2f}ms vs {baseline_latency:6.2f}ms "
              f"(Δ {latency_imp:+.2f}ms, {latency_imp_pct:+.1f}%)")
        
        print(f"\n🌍 Service Placement:")
        region_counts = {}
        for service_id, region_idx in assignment.items():
            region_name = self.region_names[region_idx]
            region_counts[region_name] = region_counts.get(region_name, 0) + 1
        
        for region, count in sorted(region_counts.items()):
            print(f"   {region}: {count} services")
    
    def _log_results(self, assignment, carbon, cost, latency,
                    carbon_imp, cost_imp, latency_imp,
                    carbon_imp_pct, cost_imp_pct, latency_imp_pct, solve_time, baseline_carbon, baseline_cost):
        """Log results to CSV"""
        # Convert assignment to the format expected by our logger (region names)
        assignment_dict = {s: self.region_names[r] for s, r in assignment.items()}
        carbon_pct = (carbon / baseline_carbon * 100) if baseline_carbon > 0 else 0
        cost_pct = (cost / baseline_cost * 100) if baseline_cost > 0 else 0
        log_realistic_experiment_csv(
            filename="results/baseline_results.csv",
            title=f"caribou-{self.ms_size}ms-load{self.load_level}",
            base_location=self.base_location,
            n_services=self.n_services,
            n_movable=self.n_services - len(self.fixed_nodes),
            load_multiplier=self.load_level,
            solve_time=solve_time,
            assignment=assignment_dict,
            carbon=carbon_pct,
            cost=cost_pct,
            latency=latency
        )


def main():
    """Main function for HBSS optimizer"""
    if len(sys.argv) < 3:
        print("Usage: python hbss.py <ms_size> <base_location> [candidate_regions] [slo_requirement] [n_samples]")
        print("Example: python hbss.py 25 Spain Spain,Stockholm,Milan,Tokyo 500 50000")
        print("Example: python hbss.py 30 Stockholm ALL 300 100000")
        print("Example: python hbss.py 30 Stockholm Spain,Stockholm,Milan")  # No SLO requirement
        return
    
    try:
        ms_size = int(sys.argv[1])
        base_location = sys.argv[2]
        
        # Parse candidate regions
        if len(sys.argv) > 3:
            if sys.argv[3].upper() == "ALL":
                candidate_regions = list(ALL_REGIONS.keys())
            else:
                candidate_regions = [r.strip() for r in sys.argv[3].split("|")] #changed here
        else:
            # Default: use all regions
            candidate_regions = list(ALL_REGIONS.keys())
        
        # Parse SLO requirement (optional)
        slo_requirement = None
        n_samples = 1000000  # Default #changed to 200k from 5k
        
        if len(sys.argv) > 4:
            try:
                slo_requirement = int(sys.argv[4])
                print(f"🔧 SLO requirement set to: {slo_requirement}ms")
            except ValueError:
                print(f"⚠️  Invalid SLO requirement: {sys.argv[4]}, ignoring SLO")
        
        # Parse number of samples (optional)
        if len(sys.argv) > 5:
            try:
                n_samples = int(sys.argv[5])
                print(f"🔧 Number of samples: {n_samples}")
            except ValueError:
                print(f"⚠️  Invalid sample count: {sys.argv[5]}, using default: {n_samples}")
        
        # Validate base location
        if base_location not in candidate_regions:
            print(f"⚠️  Base location {base_location} not in candidate regions, adding it")
            candidate_regions.append(base_location)
        
        print(f"\n{'='*70}")
        print(f"🎯 HBSS Optimization - Microservice Size: {ms_size}")
        print(f"🌍 Base Location: {base_location}")
        print(f"📍 Candidate Regions: {', '.join(candidate_regions)}")
        if slo_requirement:
            print(f"⏱️  SLO Requirement: {slo_requirement}ms")
        print(f"🔢 Samples: {n_samples}")
        print(f"{'='*70}")

        load_levels = [1, 2, 3, 4]
        #load_levels = [1]

        for load_level in load_levels:
        
            # Create and run optimizer
            optimizer = HBSSOptimizer(
                ms_size=ms_size,
                base_location=base_location,
                candidate_regions=candidate_regions,
                fixed_percentage=0.2,  # 20% of nodes fixed to base
                latency_threshold=800,  # 800ms latency threshold
                load_level=load_level,           # Medium load
                random_seed=42,
                slo_requirement=slo_requirement
            )
        
            # Print graph summary
            print_graph_summary(optimizer.graph, optimizer.service_profiles, optimizer.fixed_nodes)
            
            # Solve
            results = optimizer.solve(n_samples=n_samples, bias_strength=4.0)
            
            if results:
                if not slo_requirement or results.get('slo_ok', True):
                    print(f"\n✅ Caribou optimization completed successfully!")
                    print(f"   Results saved to: results/baseline_results.csv")
                    print(f"   Feasible solutions found: {results.get('feasible_solutions', 0)}")
                else:
                    print(f"\n⚠️  Solution found but exceeds SLO requirement")
                    print(f"   Consider relaxing SLO or using different regions")
            else:
                print(f"\n❌ Caribou optimization failed!")
        print(f"\n🎉 All load levels completed! Results saved to: results/baseline_results.csv")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()