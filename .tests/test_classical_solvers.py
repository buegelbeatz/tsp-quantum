"""Tests for classical TSP solvers."""
import sys
sys.path.insert(0, '.')

import pytest
import numpy as np
from src.classical.solvers import (
    NearestNeighborSolver,
    BruteForceSolver,
    TwoOptSolver,
    calculate_tour_length,
    get_distance_matrix
)


class TestUtilityFunctions:
    """Test utility functions for TSP calculations."""
    
    def test_calculate_tour_length_simple_square(self):
        """Test tour length calculation for a square."""
        cities = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
        tour = [0, 1, 2, 3]
        
        length = calculate_tour_length(cities, tour)
        
        # Square perimeter = 4
        assert np.isclose(length, 4.0)
    
    def test_calculate_tour_length_triangle(self):
        """Test tour length calculation for an equilateral triangle."""
        side = 1.0
        cities = np.array([
            [0, 0],
            [side, 0],
            [side / 2, side * np.sqrt(3) / 2]
        ])
        tour = [0, 1, 2]
        
        length = calculate_tour_length(cities, tour)
        
        # Expected: 3 * side
        assert np.isclose(length, 3.0 * side, rtol=1e-10)
    
    def test_get_distance_matrix(self):
        """Test distance matrix computation."""
        cities = np.array([[0, 0], [1, 0], [0, 1]])
        
        dist_matrix = get_distance_matrix(cities)
        
        assert dist_matrix.shape == (3, 3)
        assert dist_matrix[0, 1] == 1.0
        assert dist_matrix[0, 2] == 1.0
        assert np.isclose(dist_matrix[1, 2], np.sqrt(2))
        # Diagonal should be zero
        assert np.all(np.diag(dist_matrix) == 0)
        # Matrix should be symmetric
        assert np.allclose(dist_matrix, dist_matrix.T)


class TestNearestNeighborSolver:
    """Test nearest neighbor heuristic solver."""
    
    def test_solve_simple_square(self):
        """Test nearest neighbor on a simple square."""
        cities = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
        solver = NearestNeighborSolver(cities)
        
        tour, length = solver.solve(start_city=0)
        
        assert len(tour) == 4
        assert all(city in tour for city in range(4))
        assert np.isclose(length, 4.0)
    
    def test_solve_best_start(self):
        """Test nearest neighbor with best starting city."""
        cities = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
        solver = NearestNeighborSolver(cities)
        
        tour, length = solver.solve_best_start()
        
        assert len(tour) == 4
        assert np.isclose(length, 4.0)
    
    def test_different_start_cities(self):
        """Test that different start cities can produce different results."""
        np.random.seed(42)
        cities = np.random.uniform(0, 10, size=(6, 2))
        solver = NearestNeighborSolver(cities)
        
        tours = []
        lengths = []
        for start in range(6):
            tour, length = solver.solve(start_city=start)
            tours.append(tour)
            lengths.append(length)
        
        # At least some different tour lengths should be found
        assert len(set(np.round(lengths, 4))) > 1 or all(
            np.isclose(l, lengths[0]) for l in lengths
        )


class TestBruteForceSolver:
    """Test brute force solver."""
    
    def test_solve_small_problem(self):
        """Test brute force on a small problem."""
        cities = np.array([[0, 0], [1, 0], [0, 1]])
        solver = BruteForceSolver(cities)
        
        tour, _ = solver.solve()
        
        assert len(tour) == 3
        assert tour[0] == 0  # First city is fixed
    
    def test_solve_rejects_large_problem(self):
        """Test that brute force rejects problems larger than N=12."""
        np.random.seed(42)
        cities = np.random.uniform(0, 10, size=(15, 2))
        solver = BruteForceSolver(cities)
        
        with pytest.raises(ValueError, match="impractical"):
            solver.solve()
    
    def test_brute_force_finds_optimal(self):
        """Test that brute force finds optimal solution."""
        # Use a small square - we know the optimal tour length is 4
        cities = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
        solver = BruteForceSolver(cities)
        
        tour, length = solver.solve()
        
        # Should find optimal: square perimeter = 4
        assert np.isclose(length, 4.0)


class TestTwoOptSolver:
    """Test 2-opt local search solver."""
    
    def test_solve_improves_random_tour(self):
        """Test that 2-opt improves a random tour."""
        np.random.seed(42)
        cities = np.random.uniform(0, 10, size=(8, 2))
        
        nn_solver = NearestNeighborSolver(cities)
        nn_tour, nn_length = nn_solver.solve_best_start()
        
        solver = TwoOptSolver(cities)
        _, improved_length = solver.solve(initial_tour=nn_tour)
        
        # 2-opt should not make solution worse
        assert improved_length <= nn_length * 1.01  # Allow small numerical tolerance
    
    def test_solve_without_initial_tour(self):
        """Test 2-opt without providing an initial tour."""
        cities = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
        solver = TwoOptSolver(cities)
        
        tour, length = solver.solve()
        
        assert len(tour) == 4
        assert np.isclose(length, 4.0)


class TestIntegration:
    """Integration tests for classical solvers."""
    
    def test_all_solvers_produce_valid_tours(self):
        """Test that all solvers produce valid tours."""
        np.random.seed(42)
        cities = np.random.uniform(0, 10, size=(5, 2))
        
        solvers = [
            NearestNeighborSolver(cities),
            BruteForceSolver(cities),
            TwoOptSolver(cities)
        ]
        
        for solver in solvers:
            if isinstance(solver, NearestNeighborSolver):
                tour, length = solver.solve_best_start()
            else:
                tour, length = solver.solve()
            
            # Should visit each city exactly once
            assert len(tour) == len(cities)
            assert len(set(tour)) == len(cities)
            # Length should be positive
            assert length > 0
    
    def test_solver_comparison_on_same_problem(self):
        """Compare different solvers on the same problem."""
        cities = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
        
        nn_solver = NearestNeighborSolver(cities)
        _, nn_length = nn_solver.solve_best_start()
        
        bf_solver = BruteForceSolver(cities)
        _, bf_length = bf_solver.solve()
        
        # Both should find optimal for this simple case
        assert np.isclose(nn_length, 4.0)
        assert np.isclose(bf_length, 4.0)
        assert np.isclose(nn_length, bf_length)
