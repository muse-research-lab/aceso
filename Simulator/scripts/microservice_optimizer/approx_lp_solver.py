#!/usr/bin/env python3
"""
LP Optimizer for microservice placement using realistic simulation metrics
"""

import sys
import os
import time
import numpy as np
import pyomo.environ as pyo
from pyomo.environ import (
    ConcreteModel, Var, Binary, Constraint, Objective, 
    SolverFactory, minimize, value
)

# Add current directory to path for package imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from microservice_optimizer.core.regions import ALL_REGIONS, REGION_INSTANCE_COSTS, get_region_carbon_intensity, get_instance_cost
from microservice_optimizer.core.graph import generate_realistic_microservice_graph, print_graph_summary
from microservice_optimizer.core.microservice import MicroserviceProfile
from microservice_optimizer.core.latency import get_inter_region_latency
from microservice_optimizer.evaluation.evaluator import evaluate_realistic_assignment_fast
from microservice_optimizer.utils.csv_logger import log_realistic_experiment_csv


class LPOptimizer:
    def __init__(self, ms_size, base_location, candidate_regions=None, fixed_percentage=0.2, 
                 latency_threshold=1000, load_level=5, random_seed=42, slo_requirement=None):
        """
        Initialize LP Optimizer
        
        Args:
            ms_size: Number of microservices
            base_location: Base region for fixed nodes
            candidate_regions: List of candidate regions for placement
            fixed_percentage: Percentage of nodes to fix to base location
            latency_threshold: Maximum allowed latency (ms)
            load_level: Load multiplier for cost calculation
            random_seed: Random seed for reproducible graphs
            slo_requirement: SLO latency requirement in ms (discards placements that exceed this)
        """
        self.ms_size = ms_size
        self.base_location = base_location
        self.candidate_regions = candidate_regions or list(ALL_REGIONS.keys())
        self.fixed_percentage = fixed_percentage
        self.latency_threshold = latency_threshold
        self.load_level = load_level
        self.random_seed = random_seed
        self.slo_requirement = slo_requirement  # New SLO requirement
        
        # Generate microservice graph
        self.graph, self.fixed_nodes, self.service_profiles = self._generate_graph()
        
        # Region indices mapping
        self.region_names = self.candidate_regions
        self.region_indices = {name: idx for idx, name in enumerate(self.region_names)}
        self.n_regions = len(self.region_names)
        self.n_services = len(self.graph)
        
        # Get base region index
        self.base_idx = self.region_indices.get(base_location, 0)
        
        # Pre-calculate latency matrix for SLO constraints
        self.latency_matrix = self._get_inter_region_latency_matrix()
        self.rtt_dict = self._create_rtt_dict()
        
        print(f"🔧 LP Optimizer Initialized:")
        print(f"   Microservices: {self.n_services}")
        print(f"   Candidate Regions: {len(self.region_names)}")
        print(f"   Base Location: {base_location} (index {self.base_idx})")
        print(f"   Fixed Nodes: {len(self.fixed_nodes)}")
        print(f"   Latency Threshold: {latency_threshold}ms")
        print(f"   Load Level: {load_level}x")
        if self.slo_requirement:
            print(f"   SLO Requirement: {self.slo_requirement}ms")

    def _get_inter_region_latency_matrix(self):
        """Create latency matrix between all candidate regions"""
        latency_matrix = np.zeros((self.n_regions, self.n_regions))
        
        for i, region1 in enumerate(self.region_names):
            for j, region2 in enumerate(self.region_names):
                latency_matrix[i, j] = get_inter_region_latency(region1, region2)
        
        return latency_matrix

    def _create_rtt_dict(self):
        """Create RTT dictionary for LP constraints"""
        rtt = {}
        for i in range(self.n_regions):
            for j in range(self.n_regions):
                rtt[(i, j)] = self.latency_matrix[i, j]
        return rtt

    def _generate_graph(self):
        """Generate microservice graph with fixed random seed"""
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
    
    def _extract_paths(self, graph):
        """Extract all root-to-leaf paths for latency calculation"""
        paths = []
        def dfs(node, path):
            path.append(node)
            if not graph[node]:  # Leaf node
                paths.append(list(path))
            else:
                for child in graph[node]:
                    dfs(child, path)
            path.pop()
        dfs(0, [])
        return paths
    
    def build_model(self):
        """Build Pyomo model with EXACT latency constraints from vanilla LP"""
        model = ConcreteModel()
        
        # Sets
        model.S = pyo.RangeSet(0, self.n_services - 1)  # Services
        model.R = pyo.RangeSet(0, self.n_regions - 1)   # Regions
        
        # Decision variables: x[s,r] = 1 if service s is placed in region r
        model.x = Var(model.S, model.R, domain=Binary)
        
        # z[s1,s2,r1,r2] = 1 if (s1 in r1) and (s2 in r2) for latency calculation
        model.z = Var(model.S, model.S, model.R, model.R, domain=Binary)
        
        # Constraint: Each service placed in exactly one region
        def one_region_rule(m, s):
            return sum(m.x[s, r] for r in m.R) == 1
        model.one_region = Constraint(model.S, rule=one_region_rule)
        
        # Fixed nodes constraint
        for node in self.fixed_nodes:
            for r in model.R:
                if r == self.base_idx:
                    model.x[node, r].fix(1)
                else:
                    model.x[node, r].fix(0)
        
        # Latency consistency constraints (from vanilla LP)
        def c1_rule(m, s1, s2, r1, r2):
            return m.z[s1, s2, r1, r2] <= m.x[s1, r1]
        def c2_rule(m, s1, s2, r1, r2):
            return m.z[s1, s2, r1, r2] <= m.x[s2, r2]
        def c3_rule(m, s1, s2, r1, r2):
            return m.z[s1, s2, r1, r2] >= m.x[s1, r1] + m.x[s2, r2] - 1

        model.c1 = Constraint(model.S, model.S, model.R, model.R, rule=c1_rule)
        model.c2 = Constraint(model.S, model.S, model.R, model.R, rule=c2_rule)
        model.c3 = Constraint(model.S, model.S, model.R, model.R, rule=c3_rule)
        
        # Latency accumulation (sequential traversal of each path) - FROM VANILLA LP
        latency_terms = []
        paths = self._extract_paths(self.graph)
        
        for path in paths:
            # Add latency for service-to-service communication
            for i in range(len(path) - 1):
                s1, s2 = path[i], path[i+1]
                for r1 in model.R:
                    for r2 in model.R:
                        latency_terms.append(model.z[s1, s2, r1, r2] * self.rtt_dict[(r1, r2)])
            
            # Add DB hop for leaf to base (from vanilla LP)
            leaf = path[-1]
            for r in model.R:
                latency_terms.append(model.x[leaf, r] * self.rtt_dict[(r, self.base_idx)])
        
        # Use SLO requirement if specified, otherwise use latency threshold
        latency_constraint_value = self.slo_requirement if self.slo_requirement else self.latency_threshold
        
        if latency_constraint_value:
            model.latency_con = Constraint(expr=sum(latency_terms) <= latency_constraint_value)
            print(f"🔧 Added latency constraint: {latency_constraint_value}ms")
        
        # Objective: Minimize combined carbon and cost (using simulation metrics)
        carbon_terms = []
        cost_terms = []
        
        for s in model.S:
            for r in model.R:
                carbon = self._get_service_carbon_cost(s, r)
                cost = self._get_service_monetary_cost(s, r)
                carbon_terms.append(model.x[s, r] * carbon)
                cost_terms.append(model.x[s, r] * cost)
        
        total_carbon = sum(carbon_terms)
        total_cost = sum(cost_terms)
        
        # Combined objective (carbon + normalized cost)
        carbon_weight = 1.0
        cost_weight = 100.0  # Adjust based on carbon vs cost priority
        
        model.objective = Objective(
            expr=carbon_weight * total_carbon + cost_weight * total_cost,
            sense=minimize
        )
        
        return model
    
    def solve(self, solver_name="glpk", solver_executable=None):
        """Solve the optimization problem"""
        print(f"\n🧮 Building optimization model...")
        model = self.build_model()
        
        print(f"🔍 Solving with {solver_name}...")
        start_time = time.time()
        
        try:
            solver = SolverFactory(solver_name, executable=solver_executable)
            results = solver.solve(model, tee=True)
            solve_time = time.time() - start_time
            
            if results.solver.termination_condition == pyo.TerminationCondition.optimal:
                print(f"✅ Solution found in {solve_time:.2f} seconds")
                return self._extract_solution(model, solve_time)
            elif results.solver.termination_condition == pyo.TerminationCondition.infeasible:
                print(f"❌ No solution found that satisfies constraints")
                if self.slo_requirement:
                    print(f"💡 Try relaxing SLO requirement from {self.slo_requirement}ms")
                return None
            else:
                print(f"❌ Solver failed: {results.solver.termination_condition}")
                return None
                
        except Exception as e:
            print(f"❌ Solver error: {e}")
            return None
    
    def _extract_solution(self, model, solve_time):
        """Extract solution and verify constraints"""
        # Extract assignment
        assignment = {}
        for s in model.S:
            for r in model.R:
                if pyo.value(model.x[s, r]) > 0.5:
                    assignment[s] = r
                    break
        
        # Convert to region names for evaluation
        region_assignment = {s: self.region_names[r] for s, r in assignment.items()}
        
        # Evaluate solution using our EXACT nautilus evaluator for final metrics
        regions_dict = {name: ALL_REGIONS[name] for name in self.region_names}

        # Set load level for all services
        for profile in self.service_profiles.values():
            profile.set_load_multiplier(self.load_level)
        
        carbon, cost, latency, instances = evaluate_realistic_assignment_fast(
            region_assignment, self.graph, self.service_profiles, 
            regions_dict, self.base_location, self.load_level
        )
        
        # Check latency constraint
        latency_ok = latency <= self.latency_threshold
        
        # Check SLO requirement
        slo_ok = True
        if self.slo_requirement:
            slo_ok = latency <= self.slo_requirement
        
        # Calculate baseline (all in base region)
        baseline_assignment = {s: self.base_location for s in range(self.n_services)}
        baseline_carbon, baseline_cost, baseline_latency, _ = evaluate_realistic_assignment_fast(
            baseline_assignment, self.graph, self.service_profiles,
            regions_dict, self.base_location, self.load_level
        )
        
        # Calculate improvements
        carbon_improvement = baseline_carbon - carbon
        cost_improvement = baseline_cost - cost
        latency_improvement = baseline_latency - latency
        
        carbon_improvement_pct = (carbon_improvement / baseline_carbon * 100) if baseline_carbon > 0 else 0
        cost_improvement_pct = (cost_improvement / baseline_cost * 100) if baseline_cost > 0 else 0
        latency_improvement_pct = (latency_improvement / baseline_latency * 100) if baseline_latency > 0 else 0
        
        # Print results
        self._print_results(
            assignment, carbon, cost, latency, instances, latency_ok, slo_ok,
            baseline_carbon, baseline_cost, baseline_latency,
            carbon_improvement, cost_improvement, latency_improvement,
            carbon_improvement_pct, cost_improvement_pct, latency_improvement_pct,
            solve_time
        )
        
        # Log to CSV
        self._log_results(
            assignment, carbon, cost, latency, latency_ok,
            carbon_improvement, cost_improvement, latency_improvement,
            carbon_improvement_pct, cost_improvement_pct, latency_improvement_pct,
            solve_time
        )
        
        return {
            'assignment': assignment,
            'carbon': carbon,
            'cost': cost,
            'latency': latency,
            'latency_ok': latency_ok,
            'slo_ok': slo_ok,
            'instances': instances,
            'improvements': {
                'carbon': carbon_improvement,
                'cost': cost_improvement, 
                'latency': latency_improvement,
                'carbon_pct': carbon_improvement_pct,
                'cost_pct': cost_improvement_pct,
                'latency_pct': latency_improvement_pct
            }
        }
    
    def _print_results(self, assignment, carbon, cost, latency, instances, latency_ok, slo_ok,
                      baseline_carbon, baseline_cost, baseline_latency,
                      carbon_imp, cost_imp, latency_imp,
                      carbon_imp_pct, cost_imp_pct, latency_imp_pct, solve_time):
        """Print optimization results"""
        latency_status = "✅ WITHIN LIMIT" if latency_ok else "❌ EXCEEDS LIMIT"
        slo_status = "✅ WITHIN SLO" if (not self.slo_requirement or slo_ok) else "❌ EXCEEDS SLO"
        
        print(f"\n{'='*80}")
        print("🎯 LP OPTIMIZATION RESULTS")
        print(f"{'='*80}")
        
        print(f"\n📊 Performance Metrics:")
        print(f"   Solve Time: {solve_time:.2f} seconds")
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
        
        print(f"\n🖥️  Instance Distribution:")
        print(f"   {instances}")
        
        print(f"\n🌍 Service Placement:")
        region_counts = {}
        for service_id, region_idx in assignment.items():
            region_name = self.region_names[region_idx]
            region_counts[region_name] = region_counts.get(region_name, 0) + 1
        
        for region, count in sorted(region_counts.items()):
            print(f"   {region}: {count} services")
    
    def _log_results(self, assignment, carbon, cost, latency, latency_ok,
                    carbon_imp, cost_imp, latency_imp,
                    carbon_imp_pct, cost_imp_pct, latency_imp_pct, solve_time):
        """Log results to CSV"""
        # Convert assignment to the format expected by our logger (region names)
        assignment_dict = {s: self.region_names[r] for s, r in assignment.items()}
        
        log_realistic_experiment_csv(
            filename="results/baseline_results.csv",
            title=f"lp-optimization-{self.ms_size}ms-{self.base_location}-load{self.load_level}",
            base_location=self.base_location,
            n_services=self.n_services,
            n_movable=self.n_services - len(self.fixed_nodes),
            load_multiplier=self.load_level,
            solve_time=solve_time,
            assignment=assignment_dict,
            carbon=100-carbon_imp_pct,
            cost=100-cost_imp_pct,
            latency=latency
        )


def main():
    """Main function for LP optimizer"""
    if len(sys.argv) < 3:
        print("Usage: python lp_optimizer.py <ms_size> <base_location> [candidate_regions] [slo_requirement]")
        print("Example: python lp_optimizer.py 25 Spain Spain,Stockholm,Milan,Tokyo 500")
        print("Example: python lp_optimizer.py 30 Stockholm ALL 300")
        print("Example: python lp_optimizer.py 30 Stockholm Spain,Stockholm,Milan")  # No SLO requirement
        return
    
    try:
        ms_size = int(sys.argv[1])
        base_location = sys.argv[2]
        
        # Parse candidate regions
        if len(sys.argv) > 3:
            if sys.argv[3].upper() == "ALL":
                candidate_regions = list(ALL_REGIONS.keys())
            else:
                candidate_regions = [r.strip() for r in sys.argv[3].split("|")]
        else:
            # Default: use all regions
            candidate_regions = list(ALL_REGIONS.keys())
        
        # Parse SLO requirement (optional)
        slo_requirement = None
        if len(sys.argv) > 4:
            try:
                slo_requirement = int(sys.argv[4])
                print(f"🔧 SLO requirement set to: {slo_requirement}ms")
            except ValueError:
                print(f"⚠️  Invalid SLO requirement: {sys.argv[4]}, ignoring SLO")
        
        # Validate base location
        if base_location not in candidate_regions:
            print(f"⚠️  Base location {base_location} not in candidate regions, adding it")
            candidate_regions.append(base_location)


        load_levels = [1, 2, 3, 4]
                
        for load_level in load_levels:
            print(f"\n{'='*70}")
            print(f"🧮 LP Optimization - Microservice Size: {ms_size}")
            print(f"🌍 Base Location: {base_location}")
            print(f"📍 Candidate Regions: {', '.join(candidate_regions)}")
            if slo_requirement:
                print(f"⏱️  SLO Requirement: {slo_requirement}ms")
            print(f"{'='*70}")
            
            # Create and run optimizer
            optimizer = LPOptimizer(
                ms_size=ms_size,
                base_location=base_location,
                candidate_regions=candidate_regions,
                fixed_percentage=0.2,  # 20% of nodes fixed to base
                latency_threshold=800,  # 800ms latency threshold
                load_level=5,           # Medium load
                random_seed=42,
                slo_requirement=slo_requirement  # New SLO parameter
            )
            
            # Print graph summary
            print_graph_summary(optimizer.graph, optimizer.service_profiles, optimizer.fixed_nodes)
            
            # Solve
            results = optimizer.solve(solver_name="glpk")
            
            if results:
                if not slo_requirement or results.get('slo_ok', True):
                    print(f"\n✅ LP optimization completed successfully!")
                    print(f"   Results saved to: results/baseline_results.csv")
                else:
                    print(f"\n⚠️  Solution found but exceeds SLO requirement")
                    print(f"   Consider relaxing SLO or using different regions")
            else:
                print(f"\n❌ LP optimization failed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()