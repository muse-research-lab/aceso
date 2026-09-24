#!/usr/bin/env python3
"""
ACESO Genetic Algorithm Optimizer for microservice placement using realistic simulation metrics
with region and microservice filtering
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

from microservice_optimizer.core.regions import ALL_REGIONS, get_region_carbon_intensity, get_instance_cost, REGION_INSTANCE_COSTS
from microservice_optimizer.core.graph import generate_realistic_microservice_graph, print_graph_summary
from microservice_optimizer.core.microservice import MicroserviceProfile
from microservice_optimizer.core.latency import get_inter_region_latency
from microservice_optimizer.evaluation.evaluator import evaluate_realistic_assignment_fast
from microservice_optimizer.utils.csv_logger import log_realistic_experiment_csv


class ACESOGAOptimizer:
    def __init__(self, ms_size, base_location, candidate_regions=None, fixed_percentage=0.2, 
                 latency_threshold=1000, load_level=5, random_seed=42, slo_requirement=None,
                 movable_percentage=1.0, original_regions_str=None):
        """
        Initialize ACESO GA Optimizer with filtering
        
        Args:
            ms_size: Number of microservices
            base_location: Base region for fixed nodes
            candidate_regions: List of candidate regions for placement
            fixed_percentage: Percentage of nodes to fix to base location
            latency_threshold: Maximum allowed latency (ms)
            load_level: Load multiplier for cost calculation
            random_seed: Random seed for reproducible graphs
            slo_requirement: SLO latency requirement in ms
            movable_percentage: Percentage of movable microservices (0.0 to 1.0)
            original_regions_str: Original candidate regions string as passed (for CSV logging)
        """
        self.ms_size = ms_size
        self.base_location = base_location
        self.candidate_regions = candidate_regions or list(ALL_REGIONS.keys())
        self.fixed_percentage = fixed_percentage
        self.latency_threshold = latency_threshold
        self.load_level = load_level
        self.random_seed = random_seed
        self.slo_requirement = slo_requirement
        self.movable_percentage = movable_percentage
        self.original_regions_str = original_regions_str or "|".join(self.candidate_regions)
        
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
        
        # Apply ACESO filtering
        self.filtered_region_names, self.filtered_region_indices = self._apply_region_filtering()
        self.movable_services = self._apply_microservice_filtering()
        
        # Set random seeds
        random.seed(self.random_seed)
        np.random.seed(self.random_seed)
        
        print(f"🔧 ACESO GA Optimizer Initialized:")
        print(f"   Microservices: {self.n_services}")
        print(f"   Candidate Regions: {len(self.region_names)} → {len(self.filtered_region_names)} after filtering")
        print(f"   Base Location: {base_location}")
        print(f"   Fixed Nodes: {len(self.fixed_nodes)}")
        print(f"   Movable Services: {len(self.movable_services)} ({movable_percentage*100}%)")
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
    
    def _get_region_cost_comparison(self, region_name):
        """Get cost for region comparison using medium instance size"""
        # Use medium instance cost for comparison (same logic as your simulation)
        return get_instance_cost(region_name, "medium")
    
    def _apply_region_filtering(self):
        """Apply ACESO region filtering logic"""
        base_carbon = get_region_carbon_intensity(self.base_location)
        base_cost = self._get_region_cost_comparison(self.base_location)
        
        print(f"🔍 Base region {self.base_location}: carbon={base_carbon}g, cost=${base_cost:.4f}")
        
        # Filter regions based on carbon/cost compared to base location
        worse_regions = []
        for region in self.region_names:
            region_carbon = get_region_carbon_intensity(region)
            region_cost = self._get_region_cost_comparison(region)
            
            # Check if region is strictly worse than base
            if region_carbon > base_carbon and region_cost > base_cost:
                worse_regions.append(region)
                print(f"   ❌ Excluding {region}: carbon={region_carbon}g, cost=${region_cost:.4f}")
        
        # Check if any region is strictly better than base
        better_exists = False
        for region in self.region_names:
            if region == self.base_location:
                continue
            region_carbon = get_region_carbon_intensity(region)
            region_cost = self._get_region_cost_comparison(region)
            if region_carbon < base_carbon and region_cost < base_cost:
                better_exists = True
                print(f"   ✅ Found better region: {region}: carbon={region_carbon}g, cost=${region_cost:.4f}")
                break
        
        if better_exists:
            # Keep only regions that are better or equal to base
            filtered_regions = [region for region in self.region_names 
                              if get_region_carbon_intensity(region) <= base_carbon 
                              and self._get_region_cost_comparison(region) <= base_cost]
            print(f"   🔧 Using strict filtering (better regions exist)")
        else:
            # Remove strictly worse regions
            filtered_regions = [region for region in self.region_names if region not in worse_regions]
            print(f"   🔧 Using relaxed filtering (no strictly better regions)")
        
        # Ensure base location is included
        if self.base_location not in filtered_regions:
            filtered_regions.insert(0, self.base_location)
            print(f"   🔧 Added base location {self.base_location} to filtered regions")
        
        # Create filtered region indices mapping
        filtered_indices = {name: idx for idx, name in enumerate(filtered_regions)}
        
        print(f"🔧 Region filtering: {len(self.region_names)} → {len(filtered_regions)} regions")
        return filtered_regions, filtered_indices
    
    def _compute_node_latency_impact(self):
        """Compute latency impact for each node (for microservice filtering)"""
        # Use simulation's latency calculation to estimate node impact
        # We'll use a simplified approach: nodes in critical paths have higher impact
        paths = self._find_all_paths(self.graph)
        
        # Count how many paths each node appears in
        path_count = {node: 0 for node in self.graph}
        for path in paths:
            for node in path:
                path_count[node] += 1
        
        return path_count
    
    def _apply_microservice_filtering(self):
        """Apply ACESO microservice filtering logic"""
        # Get all movable services (excluding fixed nodes)
        all_movable = [s for s in range(self.n_services) if s not in self.fixed_nodes]
        
        if self.movable_percentage >= 1.0:
            # No filtering, use all movable services
            print(f"🔧 Microservice filtering: Using all {len(all_movable)} movable services")
            return all_movable
        
        # Compute latency impact for each node
        latency_impact = self._compute_node_latency_impact()
        
        # Sort movable services by latency impact (descending)
        sorted_movable = sorted(all_movable, key=lambda n: latency_impact[n], reverse=True)
        
        # Select top k% based on movable_percentage
        k = max(1, int(len(sorted_movable) * self.movable_percentage))
        selected_movable = sorted_movable[:k]
        
        print(f"🔧 Microservice filtering: {len(all_movable)} movable → {len(selected_movable)} selected (top {self.movable_percentage*100}%)")
        
        # Show which services were selected
        if len(selected_movable) > 0:
            print(f"   📊 Selected services by impact: {selected_movable}")
        
        return selected_movable
    
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
    
    def solve(self, population_size=200, generations=400, crossover_rate=0.8,
          mutation_rate=0.12, tournament_k=3):
        """Solve using ACESO Genetic Algorithm with filtering - ENFORCE FEASIBLE SOLUTIONS"""
        print(f"\n🎯 Starting ACESO GA Optimization...")
        print(f"   Population: {population_size}, Generations: {generations}")
        print(f"   Crossover: {crossover_rate}, Mutation: {mutation_rate}")
        
        # Compute baseline
        baseline_carbon, baseline_cost, baseline_latency = self._compute_baseline_simulation_style()
        
        # Use SLO requirement if specified, otherwise use latency threshold
        latency_constraint = self.slo_requirement if self.slo_requirement else self.latency_threshold
        
        # Get filtered region count and base index in filtered regions
        n_regions_filtered = len(self.filtered_region_names)
        base_idx_filtered = self.filtered_region_indices[self.base_location]
        
        # Create extended fixed nodes (original fixed nodes + non-selected movable services)
        all_movable = [s for s in range(self.n_services) if s not in self.fixed_nodes]
        non_selected_movable = [s for s in all_movable if s not in self.movable_services]
        fixed_nodes_extended = self.fixed_nodes + non_selected_movable
    
        print(f"🔧 Search space: {len(self.movable_services)} movable × {n_regions_filtered} regions = {len(self.movable_services) * n_regions_filtered} placements")
        
        # Individual representation: numpy array length n_services, each entry is filtered region index
        def random_individual():
            ind = np.empty(self.n_services, dtype=int)
            for s in range(self.n_services):
                if s in fixed_nodes_extended:
                    # Fixed nodes and non-selected movable services go to base
                    ind[s] = base_idx_filtered
                else:
                    # Selected movable services can be placed in any filtered region
                    ind[s] = np.random.randint(0, n_regions_filtered)
            return ind

        def fitness(ind):
            """
            Fitness function returns (objective_value, latency_violation_penalty, carbon, cost, latency)
            - STRONGER PENALTY like original ACESO
            """
            # Convert filtered region indices back to original for evaluation
            assignment_original = np.empty(self.n_services, dtype=int)
            for s in range(self.n_services):
                region_name = self.filtered_region_names[ind[s]]
                assignment_original[s] = self.region_indices[region_name]
        
            # Evaluate using simulation's exact evaluation
            carbon_val, cost_val, latency_val = self._evaluate_assignment_simulation_style(assignment_original)
            
            # Combined objective (carbon + cost) - SAME AS ORIGINAL ACESO
            obj = carbon_val + cost_val
            #obj = cost_val #ONLY optimize cost
            
            # STRONG penalty when latency > constraint - LIKE ORIGINAL ACESO
            if latency_val > latency_constraint:
                # Use much stronger penalty like original ACESO
                penalty = 1e9 + (latency_val - latency_constraint) * 1e6  # Increased penalty
            else:
                penalty = 0.0
            
            return obj + penalty, latency_val, carbon_val, cost_val

        # Population initialization
        population = [random_individual() for _ in range(population_size)]
        pop_fitness = [fitness(ind) for ind in population]

        # Helper selection: tournament
        def tournament_select(pop, fits):
            best = None
            best_fit = None
            for _ in range(tournament_k):
                i = random.randrange(len(pop))
                if best is None or fits[i][0] < best_fit[0]:
                    best = pop[i]
                    best_fit = fits[i]
            return best.copy()

        # Crossover: uniform crossover but preserve fixed nodes
        def crossover(a, b):
            child1 = a.copy()
            child2 = b.copy()
            if random.random() < crossover_rate:
                for s in range(len(a)):
                    if s in fixed_nodes_extended:
                        continue
                    if random.random() < 0.5:
                        child1[s], child2[s] = child2[s], child1[s]
            return child1, child2

        # Mutation: random reset of a gene (service region) for selected movable services only
        def mutate(ind):
            for s in range(len(ind)):
                if s in fixed_nodes_extended:
                    continue
                if random.random() < mutation_rate:
                    ind[s] = random.randint(0, n_regions_filtered - 1)
            return ind

        # GA loop - ENFORCE FEASIBLE SOLUTIONS
        start_time = time.time()
        best_feasible = None
        best_feasible_fit = (float('inf'), float('inf'), None, None)
        best_overall = None
        best_overall_fit = (float('inf'), float('inf'), None, None)
        stagnation = 0
        feasible_found = False
    
        print(f"   Evolving {generations} generations...")
        
        for gen in range(generations):
            if gen % 50 == 0 and gen > 0:
                best_fit = min(pop_fitness, key=lambda x: x[0])
                feasible_count = sum(1 for fit in pop_fitness if fit[1] <= latency_constraint)
                print(f"   ... generation {gen}/{generations}, feasible: {feasible_count}/{population_size}, best fitness: {best_fit[0]:.2f}")
            
            new_pop = []
            
            # Elitism: keep top 2 individuals, PREFER FEASIBLE ONES
            sorted_pop = sorted(zip(population, pop_fitness), key=lambda x: (x[1][1] > latency_constraint, x[1][0]))
            elites = [sorted_pop[0][0].copy(), sorted_pop[1][0].copy()]
            new_pop.extend(elites)

            # Generate new population through selection, crossover, and mutation
            while len(new_pop) < population_size:
                parent1 = tournament_select(population, pop_fitness)
                parent2 = tournament_select(population, pop_fitness)
                child1, child2 = crossover(parent1, parent2)
                child1 = mutate(child1)
                child2 = mutate(child2)
                new_pop.append(child1)
                if len(new_pop) < population_size:
                    new_pop.append(child2)

            population = new_pop
            pop_fitness = [fitness(ind) for ind in population]

            # Track best FEASIBLE solution
            feasible_solutions = [(ind, fit) for ind, fit in zip(population, pop_fitness) if fit[1] <= latency_constraint]
            
            if feasible_solutions:
                feasible_solutions.sort(key=lambda x: x[1][0])
                best_feasible_current = feasible_solutions[0]
                
                if best_feasible_current[1][0] < best_feasible_fit[0]:
                    best_feasible = best_feasible_current[0].copy()
                    best_feasible_fit = best_feasible_current[1]
                    stagnation = 0
                    feasible_found = True
                    print(f"   ✅ Found feasible solution at generation {gen}")
                else:
                    stagnation += 1
            else:
                # If no feasible solutions, track best overall
                gen_best_idx = min(range(len(population)), key=lambda i: pop_fitness[i][0])
                if pop_fitness[gen_best_idx][0] < best_overall_fit[0]:
                    best_overall = population[gen_best_idx].copy()
                    best_overall_fit = pop_fitness[gen_best_idx]
                stagnation += 1

            # Adaptive termination - stop if we have a good feasible solution and no improvement
            if feasible_found and stagnation >= 50:
                print(f"   ⏹️  Early termination at generation {gen} (feasible solution found and stagnated)")
                break

        solve_time = time.time() - start_time

        # ALWAYS RETURN FEASIBLE SOLUTION IF FOUND, OTHERWISE USE BASELINE
        if feasible_found:
            print(f"   ✅ Using best feasible solution found")
            best_assignment_filtered = best_feasible
            final_obj, final_latency, final_carbon, final_cost = best_feasible_fit
        else:
            print(f"   ⚠️  No feasible solution found, using baseline (all in base location)")
            # Return baseline assignment (all in base)
            best_assignment_filtered = np.array([base_idx_filtered] * self.n_services)
            final_carbon, final_cost, final_latency = self._compute_baseline_simulation_style()
            final_obj = final_carbon + final_cost

        # Convert best solution back to original region indices
        best_assignment_original = np.empty(self.n_services, dtype=int)
        for s in range(self.n_services):
            region_name = self.filtered_region_names[best_assignment_filtered[s]]
            best_assignment_original[s] = self.region_indices[region_name]

        # Convert to dictionary format
        assignment_dict = {s: int(best_assignment_original[s]) for s in range(self.n_services)}
    
        # Calculate improvements
        carbon_improvement = baseline_carbon - final_carbon
        cost_improvement = baseline_cost - final_cost
        latency_improvement = baseline_latency - final_latency
        
        carbon_improvement_pct = (carbon_improvement / baseline_carbon * 100) if baseline_carbon > 0 else 0
        cost_improvement_pct = (cost_improvement / baseline_cost * 100) if baseline_cost > 0 else 0
        latency_improvement_pct = (latency_improvement / baseline_latency * 100) if baseline_latency > 0 else 0
        
        # Check SLO requirement
        slo_ok = final_latency <= latency_constraint
        
        # Print results
        self._print_results(
            assignment_dict, final_carbon, final_cost, final_latency, slo_ok,
            baseline_carbon, baseline_cost, baseline_latency,
            carbon_improvement, cost_improvement, latency_improvement,
            carbon_improvement_pct, cost_improvement_pct, latency_improvement_pct,
            solve_time, population_size, generations
        )
    
        # Log to CSV
        self._log_results(
            assignment_dict, final_carbon, final_cost, final_latency,
            carbon_improvement, cost_improvement, latency_improvement,
            carbon_improvement_pct, cost_improvement_pct, latency_improvement_pct,
            solve_time, baseline_carbon, baseline_cost
        )
        
        return {
            'assignment': assignment_dict,
            'carbon': final_carbon,
            'cost': final_cost,
            'latency': final_latency,
            'slo_ok': slo_ok,
            'feasible_found': feasible_found,
            'improvements': {
                'carbon': carbon_improvement,
                'cost': cost_improvement, 
                'latency': latency_improvement,
                'carbon_pct': carbon_improvement_pct,
                'cost_pct': cost_improvement_pct,
                'latency_pct': latency_improvement_pct
            }
        }
    
    def _print_results(self, assignment, carbon, cost, latency, slo_ok,
                      baseline_carbon, baseline_cost, baseline_latency,
                      carbon_imp, cost_imp, latency_imp,
                      carbon_imp_pct, cost_imp_pct, latency_imp_pct, 
                      solve_time, population_size, generations):
        """Print optimization results"""
        latency_status = "✅ WITHIN LIMIT" if latency <= self.latency_threshold else "❌ EXCEEDS LIMIT"
        slo_status = "✅ WITHIN SLO" if (not self.slo_requirement or slo_ok) else "❌ EXCEEDS SLO"
        
        print(f"\n{'='*80}")
        print("🎯 ACESO GA OPTIMIZATION RESULTS")
        print(f"{'='*80}")
        
        print(f"\n📊 Performance Metrics:")
        print(f"   Solve Time: {solve_time:.2f} seconds")
        print(f"   Population: {population_size}, Generations: {generations}")
        print(f"   Services: {self.n_services}, Regions: {len(self.region_names)} → {len(self.filtered_region_names)}")
        print(f"   Fixed Nodes: {len(self.fixed_nodes)}")
        print(f"   Movable Services: {len(self.movable_services)} ({self.movable_percentage*100}%)")
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
        """
        log_realistic_experiment_csv(
            filename="results/baseline_results.csv",
            title=f"aceso-{self.ms_size}ms-{self.base_location}-load{self.load_level}-slo{self.slo_requirement if self.slo_requirement else 'none'}",
            base_location=self.base_location,
            n_services=self.n_services,
            n_movable=len(self.movable_services),
            load_multiplier=self.load_level,
            solve_time=solve_time,
            assignment=assignment_dict,
            carbon=carbon_pct,
            cost=cost_pct,
            latency=latency
        )
        """
        # Log to scalability_results.csv
        self._log_scalability_results(solve_time)

    def _log_scalability_results(self, solve_time):
        """Log scalability results to CSV with only MS count, solve time, SLO, and candidate regions"""
        import csv
        import os
        
        filename = "results/scalability_results.csv"
        file_exists = os.path.isfile(filename)
        
        with open(filename, 'a', newline='') as csvfile:
            fieldnames = ['num_ms', 'solve_time', 'slo', 'candidate_regions']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow({
                'num_ms': self.ms_size,
                'solve_time': round(solve_time, 2),
                'slo': self.slo_requirement if self.slo_requirement else 'none',
                'candidate_regions': self.original_regions_str
            })


def main():
    """Main function for ACESO GA optimizer"""
    if len(sys.argv) < 3:
        print("Usage: python ga_aceso.py <ms_size> <base_location> [candidate_regions] [slo_requirement] [movable_percentage] [pop_size] [generations]")
        print("Example: python ga_aceso.py 25 Spain Spain|Stockholm|Milan|Tokyo 500 0.5 200 400")
        print("Example: python ga_aceso.py 30 Stockholm ALL 300 0.7 300 600")
        print("Example: python ga_aceso.py 30 Stockholm Spain|Stockholm|Milan")  # No SLO requirement, default movable=1.0")
        return
    
    try:
        ms_size = int(sys.argv[1])
        base_location = sys.argv[2]
        
        # Parse candidate regions
        original_regions_str = None
        if len(sys.argv) > 3:
            if sys.argv[3].upper() == "ALL":
                candidate_regions = list(ALL_REGIONS.keys())
                original_regions_str = "ALL"
            else:
                original_regions_str = sys.argv[3]
                candidate_regions = [r.strip() for r in sys.argv[3].split("|")]
        else:
            # Default: use all regions
            candidate_regions = list(ALL_REGIONS.keys())
            original_regions_str = "ALL"
        
        # Parse SLO requirement (optional)
        slo_requirement = None
        movable_percentage = 1.0  # Default: no microservice filtering
        pop_size = 200  # Default
        
        generations = 400  # Default
        
        if len(sys.argv) > 4:
            try:
                slo_requirement = int(sys.argv[4])
                print(f"🔧 SLO requirement set to: {slo_requirement}ms")
            except ValueError:
                print(f"⚠️  Invalid SLO requirement: {sys.argv[4]}, ignoring SLO")
        
        # Parse movable percentage (optional)
        if len(sys.argv) > 5:
            try:
                movable_percentage = float(sys.argv[5])
                if not 0.0 <= movable_percentage <= 1.0:
                    raise ValueError("Movable percentage must be between 0.0 and 1.0")
                print(f"🔧 Movable percentage: {movable_percentage*100}%")
            except ValueError:
                print(f"⚠️  Invalid movable percentage: {sys.argv[5]}, using default: 100%")
        
        # Parse population size (optional)
        if len(sys.argv) > 6:
            try:
                pop_size = int(sys.argv[6])
                print(f"🔧 Population size: {pop_size}")
            except ValueError:
                print(f"⚠️  Invalid population size: {sys.argv[6]}, using default: {pop_size}")
        
        # Parse generations (optional)
        if len(sys.argv) > 7:
            try:
                generations = int(sys.argv[7])
                print(f"🔧 Generations: {generations}")
            except ValueError:
                print(f"⚠️  Invalid generations: {sys.argv[7]}, using default: {generations}")
        
        # Validate base location
        if base_location not in candidate_regions:
            print(f"⚠️  Base location {base_location} not in candidate regions, adding it")
            candidate_regions.append(base_location)
        
        print(f"\n{'='*70}")
        print(f"🎯 ACESO GA Optimization - Microservice Size: {ms_size}")
        print(f"🌍 Base Location: {base_location}")
        print(f"📍 Candidate Regions: {', '.join(candidate_regions)}")
        if slo_requirement:
            print(f"⏱️  SLO Requirement: {slo_requirement}ms")
        print(f"🔢 Movable Services: {movable_percentage*100}%")
        print(f"🧬 Population: {pop_size}, Generations: {generations}")
        print(f"{'='*70}")

        load_levels = [1, 2, 3, 4]
        
        for load_level in load_levels:
            print(f"\n{'='*70}")
            print(f"🎯 ACESO GA Optimization - Load Level: {load_level}x")
            print(f"🌍 Base Location: {base_location}")
            print(f"📍 Candidate Regions: {', '.join(candidate_regions)}")
            if slo_requirement:
                print(f"⏱️  SLO Requirement: {slo_requirement}ms")
            print(f"🔢 Movable Services: {movable_percentage*100}%")
            print(f"🧬 Population: {pop_size}, Generations: {generations}")
            print(f"{'='*70}")
            
            # Create and run optimizer for this load level
            optimizer = ACESOGAOptimizer(
                ms_size=ms_size,
                base_location=base_location,
                candidate_regions=candidate_regions,
                fixed_percentage=0.2,  # 20% of nodes fixed to base
                latency_threshold=800,  # 800ms latency threshold
                load_level=load_level,  # Current load level
                random_seed=42,
                slo_requirement=slo_requirement,
                movable_percentage=movable_percentage,
                original_regions_str=original_regions_str
            )
            
            # Print graph summary (only once to avoid repetition)
            if load_level == load_levels[0]:
                print_graph_summary(optimizer.graph, optimizer.service_profiles, optimizer.fixed_nodes)
            
            # Solve
            results = optimizer.solve(
                population_size=pop_size,
                generations=generations,
                crossover_rate=0.8,
                mutation_rate=0.12,
                tournament_k=3
            )
            
            if results:
                if not slo_requirement or results.get('slo_ok', True):
                    print(f"\n✅ ACESO GA optimization for load {load_level}x completed successfully!")
                else:
                    print(f"\n⚠️  Solution found but exceeds SLO requirement for load {load_level}x")
            else:
                print(f"\n❌ ACESO GA optimization for load {load_level}x failed!")
        
        print(f"\n🎉 All load levels completed! Results saved to: results/scalability_results.csv")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()