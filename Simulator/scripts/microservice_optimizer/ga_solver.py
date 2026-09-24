#!/usr/bin/env python3
"""
Genetic Algorithm Optimizer for microservice placement using realistic simulation metrics
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


class GAOptimizer:
    def __init__(self, ms_size, base_location, candidate_regions=None, fixed_percentage=0.2, 
                 latency_threshold=1000, load_level=5, random_seed=42, slo_requirement=None):
        """
        Initialize GA Optimizer
        
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
        
        # Set random seeds
        random.seed(self.random_seed)
        np.random.seed(self.random_seed)
        
        print(f"🔧 GA Optimizer Initialized:")
        print(f"   Microservices: {self.n_services}")
        print(f"   Candidate Regions: {len(self.region_names)}")
        print(f"   Base Location: {base_location} (index {self.base_idx})")
        print(f"   Fixed Nodes: {len(self.fixed_nodes)}")
        print(f"   Latency Threshold: {latency_threshold}ms")
        print(f"   Load Level: {load_level}x")
        if self.slo_requirement:
            print(f"   SLO Requirement: {self.slo_requirement}ms")

    def _generate_graph(self):
        """Generate microservice graph with fixed random seed using simulation's generator"""
        import random
        random.seed(self.random_seed)
        return generate_realistic_microservice_graph(self.ms_size, self.fixed_percentage)
    
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
        """Solve using Genetic Algorithm - ENFORCE FEASIBLE SOLUTIONS"""
        print(f"\n🎯 Starting GA Optimization...")
        print(f"   Population: {population_size}, Generations: {generations}")
        print(f"   Crossover: {crossover_rate}, Mutation: {mutation_rate}")
        
        movable_services = [s for s in range(self.n_services) if s not in self.fixed_nodes]
        
        # Compute baseline
        baseline_carbon, baseline_cost, baseline_latency = self._compute_baseline_simulation_style()
        
        # Use SLO requirement if specified, otherwise use latency threshold
        latency_constraint = self.slo_requirement if self.slo_requirement else self.latency_threshold
        
        # Individual representation: numpy array length n_services, each entry is region index
        def random_individual():
            ind = np.empty(self.n_services, dtype=int)
            for s in range(self.n_services):
                if s in self.fixed_nodes:
                    ind[s] = self.base_idx
                else:
                    ind[s] = np.random.randint(0, self.n_regions)
            return ind

        def fitness(ind):
            """
            Fitness function returns (objective_value, latency_violation_penalty, carbon, cost, latency)
            - STRONGER PENALTY to enforce feasible solutions
            """
            # Evaluate using simulation's exact evaluation
            carbon_val, cost_val, latency_val = self._evaluate_assignment_simulation_style(ind)
            
            # Combined objective (carbon + normalized cost) - same as LP
            obj = carbon_val + cost_val * 100.0
            
            # STRONG penalty when latency > constraint
            if latency_val > latency_constraint:
                penalty = 1e9 + (latency_val - latency_constraint) * 1e6  # Much stronger penalty
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
                    if s in self.fixed_nodes:
                        continue
                    if random.random() < 0.5:
                        child1[s], child2[s] = child2[s], child1[s]
            return child1, child2

        # Mutation: random reset of a gene (service region) for movable services
        def mutate(ind):
            for s in range(len(ind)):
                if s in self.fixed_nodes:
                    continue
                if random.random() < mutation_rate:
                    ind[s] = random.randint(0, self.n_regions - 1)
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
                    if gen % 50 == 0:  # Only print every 50 generations to avoid spam
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
            best_assignment = best_feasible
            final_obj, final_latency, final_carbon, final_cost = best_feasible_fit
        else:
            print(f"   ⚠️  No feasible solution found, using baseline (all in base location)")
            # Return baseline assignment (all in base)
            best_assignment = np.array([self.base_idx] * self.n_services)
            final_carbon, final_cost, final_latency = self._compute_baseline_simulation_style()
            final_obj = final_carbon + final_cost * 100.0

        # Convert to dictionary format
        assignment_dict = {s: int(best_assignment[s]) for s in range(self.n_services)}
        
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
        print("🎯 GA OPTIMIZATION RESULTS")
        print(f"{'='*80}")
        
        print(f"\n📊 Performance Metrics:")
        print(f"   Solve Time: {solve_time:.2f} seconds")
        print(f"   Population: {population_size}, Generations: {generations}")
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
            title=f"ga-{self.ms_size}ms-{self.base_location}-load{self.load_level}",
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
    """Main function for GA optimizer"""
    if len(sys.argv) < 3:
        print("Usage: python ga.py <ms_size> <base_location> [candidate_regions] [slo_requirement] [pop_size] [generations]")
        print("Example: python ga.py 25 Spain Spain,Stockholm,Milan,Tokyo 500 200 400")
        print("Example: python ga.py 30 Stockholm ALL 300 300 600")
        print("Example: python ga.py 30 Stockholm Spain,Stockholm,Milan")  # No SLO requirement
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
        pop_size = 1000  # Default
        generations = 10000  # Default
        
        if len(sys.argv) > 4:
            try:
                slo_requirement = int(sys.argv[4])
                print(f"🔧 SLO requirement set to: {slo_requirement}ms")
            except ValueError:
                print(f"⚠️  Invalid SLO requirement: {sys.argv[4]}, ignoring SLO")
        
        # Parse population size (optional)
        if len(sys.argv) > 5:
            try:
                pop_size = int(sys.argv[5])
                print(f"🔧 Population size: {pop_size}")
            except ValueError:
                print(f"⚠️  Invalid population size: {sys.argv[5]}, using default: {pop_size}")
        
        # Parse generations (optional)
        if len(sys.argv) > 6:
            try:
                generations = int(sys.argv[6])
                print(f"🔧 Generations: {generations}")
            except ValueError:
                print(f"⚠️  Invalid generations: {sys.argv[6]}, using default: {generations}")
        
        # Validate base location
        if base_location not in candidate_regions:
            print(f"⚠️  Base location {base_location} not in candidate regions, adding it")
            candidate_regions.append(base_location)

        load_levels = [1, 2, 3, 4]

        for load_level in load_levels:
        
            print(f"\n{'='*70}")
            print(f"🎯 GA Optimization - Microservice Size: {ms_size}")
            print(f"🌍 Base Location: {base_location}")
            print(f"📍 Candidate Regions: {', '.join(candidate_regions)}")
            if slo_requirement:
                print(f"⏱️  SLO Requirement: {slo_requirement}ms")
            print(f"🔢 Population: {pop_size}, Generations: {generations}")
            print(f"{'='*70}")
            
            # Create and run optimizer
            optimizer = GAOptimizer(
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
            results = optimizer.solve(
                population_size=pop_size,
                generations=generations,
                crossover_rate=0.8,
                mutation_rate=0.12,
                tournament_k=3
            )
        
            if results:
                if not slo_requirement or results.get('slo_ok', True):
                    print(f"\n✅ GA optimization completed successfully!")
                    print(f"   Results saved to: results/baseline_results.csv")
                else:
                    print(f"\n⚠️  Solution found but exceeds SLO requirement")
                    print(f"   Consider relaxing SLO or using different regions")
            else:
                print(f"\n❌ GA optimization failed!")
        print(f"\n🎉 All load levels completed! Results saved to: results/baseline_results.csv")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()