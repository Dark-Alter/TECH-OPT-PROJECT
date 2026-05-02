import numpy as np
import itertools

class CongestionGame:
    def __init__(self, players_count, paths, link_costs):
        """
        link_costs: dict mapping link (e.g., 'SA') to (a, b) for cost = a*k + b
        paths: list of paths, where each path is a list of links
        """
        self.n = players_count
        self.paths = paths
        self.link_costs = link_costs
        # Initialize players with a random path strategy
        self.strategies = [0] * self.n 
        
    def get_link_loads(self, current_strategies):
        loads = {link: 0 for link in self.link_costs.keys()}
        for strat_idx in current_strategies:
            path = self.paths[strat_idx]
            for link in path:
                loads[link] += 1
        return loads

    def calculate_player_cost(self, path_idx, loads):
        path = self.paths[path_idx]
        total_cost = 0
        for link in path:
            a, b = self.link_costs[link]
            k = loads[link]
            total_cost += (a * k + b) # c(k) = ak + b
        return total_cost

    def get_potential(self, current_strategies):
        """Rosenthal Potential Function"""
        loads = self.get_link_loads(current_strategies)
        potential = 0
        for link, (a, b) in self.link_costs.items():
            for k in range(1, loads[link] + 1):
                potential += (a * k + b)
        return potential

    def best_response_step(self):
        """One iteration of Best-Response Dynamics"""
        changed = False
        for i in range(self.n):
            current_loads = self.get_link_loads(self.strategies)
            current_cost = self.calculate_player_cost(self.strategies[i], current_loads)
            
            best_strat = self.strategies[i]
            min_cost = current_cost
            
            for p_idx in range(len(self.paths)):
                if p_idx == self.strategies[i]: continue
                
                # Simulate move: decrease load on old path, increase on new
                temp_strategies = list(self.strategies)
                temp_strategies[i] = p_idx
                temp_loads = self.get_link_loads(temp_strategies)
                new_cost = self.calculate_player_cost(p_idx, temp_loads)
                
                if new_cost < min_cost:
                    min_cost = new_cost
                    best_strat = p_idx
            
            if best_strat != self.strategies[i]:
                self.strategies[i] = best_strat
                changed = True
        return changed

    def get_social_cost(self, strats=None):
        """Sum of all individual costs"""
        if strats is None: strats = self.strategies
        loads = self.get_link_loads(strats)
        return sum(self.calculate_player_cost(s, loads) for s in strats)

    def find_social_optimum(self):
        """Centralized optimization via exhaustive search[cite: 1]"""
        all_combinations = list(itertools.product(range(len(self.paths)), repeat=self.n))
        min_cost = float('inf')
        best_combo = None
        for combo in all_combinations:
            sc = self.get_social_cost(combo)
            if sc < min_cost:
                min_cost = sc
                best_combo = combo
        return min_cost, best_combo