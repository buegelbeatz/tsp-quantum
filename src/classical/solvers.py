"""Classical TSP solver implementations."""
import itertools
import numpy as np
from typing import List, Tuple


def calculate_tour_length(cities: np.ndarray, tour: List[int]) -> float:
    """Calculate total length of a tour."""
    total_length = 0.0
    for i in range(len(tour)):
        current_city = cities[tour[i]]
        next_city = cities[tour[(i + 1) % len(tour)]]
        total_length += float(np.linalg.norm(current_city - next_city))
    return total_length


def get_distance_matrix(cities: np.ndarray) -> np.ndarray:
    """Compute pairwise distance matrix for all cities."""
    num_cities = len(cities)
    distance_matrix = np.zeros((num_cities, num_cities))
    
    for i in range(num_cities):
        for j in range(num_cities):
            if i != j:
                distance_matrix[i, j] = float(np.linalg.norm(cities[i] - cities[j]))
    
    return distance_matrix


class ClassicalTSPSolver:
    """Base class for classical TSP algorithms."""
    
    def __init__(self, cities: np.ndarray):
        """
        Initialize solver with city coordinates.
        
        Args:
            cities: Array of shape (num_cities, 2) with (x, y) coordinates
        """
        self.cities = cities
        self.num_cities = len(cities)
        self.distance_matrix = get_distance_matrix(cities)
    
    def solve(self) -> Tuple[List[int], float]:
        """
        Solve TSP and return best tour and its length.
        
        Returns:
            Tuple of (tour as list of city indices, tour length)
        """
        raise NotImplementedError


class NearestNeighborSolver(ClassicalTSPSolver):
    """Nearest neighbor heuristic for TSP."""
    
    def solve(self, start_city: int = 0) -> Tuple[List[int], float]:
        """
        Solve TSP using nearest neighbor heuristic.
        
        Args:
            start_city: Starting city index
            
        Returns:
            Tuple of (tour as list of city indices, tour length)
        """
        unvisited = set(range(self.num_cities))
        current = start_city
        tour = [current]
        unvisited.remove(current)
        
        while unvisited:
            nearest = min(
                unvisited,
                key=lambda city: self.distance_matrix[current, city]
            )
            tour.append(nearest)
            unvisited.remove(nearest)
            current = nearest
        
        tour_length = calculate_tour_length(self.cities, tour)
        return tour, tour_length
    
    def solve_best_start(self) -> Tuple[List[int], float]:
        """
        Solve by trying all starting cities and returning best result.
        
        Returns:
            Tuple of (best tour, best tour length)
        """
        best_tour = None
        best_length = float('inf')
        
        for start_city in range(self.num_cities):
            tour, length = self.solve(start_city)
            if length < best_length:
                best_length = length
                best_tour = tour
        
        return best_tour, best_length


class BruteForceSolver(ClassicalTSPSolver):
    """Brute force solver for small TSP instances (N <= 10)."""
    
    def solve(self) -> Tuple[List[int], float]:
        """
        Solve TSP by checking all possible tours.
        
        Note: This has O(N!) complexity and is only practical for N <= 10.
        
        Returns:
            Tuple of (optimal tour, optimal tour length)
        """
        if self.num_cities > 12:
            raise ValueError(
                "Brute force solver is impractical for N > 12. "
                f"Got N = {self.num_cities}"
            )
        
        # Fix first city and permute the rest
        first_city = 0
        remaining_cities = list(range(1, self.num_cities))
        
        best_tour = None
        best_length = float('inf')
        
        for perm in itertools.permutations(remaining_cities):
            tour = [first_city] + list(perm)
            length = calculate_tour_length(self.cities, tour)
            
            if length < best_length:
                best_length = length
                best_tour = tour
        
        return best_tour, best_length


class TwoOptSolver(ClassicalTSPSolver):
    """2-opt local search heuristic for TSP."""
    
    def solve(self, initial_tour: List[int] | None = None) -> Tuple[List[int], float]:
        """
        Solve TSP using 2-opt local search.
        
        Args:
            initial_tour: Initial tour to improve. If None, uses nearest neighbor.
            
        Returns:
            Tuple of (improved tour, tour length)
        """
        if initial_tour is None:
            solver = NearestNeighborSolver(self.cities)
            tour, _ = solver.solve_best_start()
        else:
            tour = initial_tour.copy()
        
        improved = True
        while improved:
            improved = False
            for i in range(1, self.num_cities - 1):
                for j in range(i + 1, self.num_cities):
                    if self._should_swap(tour, i, j):
                        tour[i:j] = reversed(tour[i:j])
                        improved = True
                        break
                if improved:
                    break
        
        tour_length = calculate_tour_length(self.cities, tour)
        return tour, tour_length
    
    def _should_swap(self, tour: List[int], i: int, j: int) -> bool:
        """Check if swapping edges at positions i and j improves tour."""
        city_a = tour[i - 1]
        city_b = tour[i]
        city_c = tour[j]
        city_d = tour[(j + 1) % self.num_cities]
        
        # Current distance
        current = (
            self.distance_matrix[city_a, city_b] +
            self.distance_matrix[city_c, city_d]
        )
        
        # New distance after swap
        new = (
            self.distance_matrix[city_a, city_c] +
            self.distance_matrix[city_b, city_d]
        )
        
        return new < current
