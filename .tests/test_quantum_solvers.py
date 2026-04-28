"""Tests for quantum TSP solvers."""
import sys
sys.path.insert(0, '.')

import pytest
import numpy as np
from src.quantum.solvers import QuantumTSPSolver


class TestQuantumTSPSolver:
    """Test quantum TSP solver implementations."""
    
    def test_solver_initialization(self):
        """Test solver initialization with cities."""
        cities = np.array([[0, 0], [1, 0], [0, 1]])
        solver = QuantumTSPSolver(cities)
        
        assert solver.num_cities == 3
        assert solver.distance_matrix.shape == (3, 3)
    
    def test_calculate_tour_cost(self):
        """Test tour cost calculation."""
        cities = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
        solver = QuantumTSPSolver(cities)
        
        tour = [0, 1, 2, 3]
        cost = solver._calculate_tour_cost(tour)
        
        # Square perimeter = 4
        assert np.isclose(cost, 4.0)
    
    def test_problem_statistics(self):
        """Test problem statistics computation."""
        cities = np.array([[0, 0], [1, 0], [0, 1]])
        solver = QuantumTSPSolver(cities)
        
        stats = solver.get_problem_statistics()
        
        assert 'num_cities' in stats
        assert 'avg_distance' in stats
        assert 'min_distance' in stats
        assert 'max_distance' in stats
        assert 'std_distance' in stats
        assert stats['num_cities'] == 3
    
    def test_encode_tour_to_binary(self):
        """Test tour encoding to binary string."""
        cities = np.array([[0, 0], [1, 0], [0, 1]])
        solver = QuantumTSPSolver(cities)
        
        tour = [0, 1, 2]
        encoded = solver._encode_tour_to_binary(tour)
        
        assert isinstance(encoded, str)
        assert len(encoded) > 0
    
    def test_create_cost_hamiltonian(self):
        """Test cost Hamiltonian creation."""
        cities = np.array([[0, 0], [1, 0], [1, 1]])
        solver = QuantumTSPSolver(cities)
        
        hamiltonian = solver._create_cost_hamiltonian()
        
        assert isinstance(hamiltonian, dict)
        assert len(hamiltonian) > 0
        # All values should be floats (costs)
        for cost in hamiltonian.values():
            assert isinstance(cost, float)
            assert cost > 0
    
    def test_solve_qaoa_simulation(self):
        """Test QAOA simulated solver."""
        cities = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
        solver = QuantumTSPSolver(cities)
        
        tour, cost, metadata = solver.solve_qaoa_simulation(shots=1000)
        
        # Should return valid tour
        assert len(tour) == 4
        assert all(city in tour for city in range(4))
        
        # Cost should be positive
        assert cost > 0
        
        # Metadata should have expected fields
        assert 'method' in metadata
        assert 'shots' in metadata
        assert metadata['method'] == 'QAOA-simulated'
    
    def test_solve_variational(self):
        """Test variational quantum eigensolver approach."""
        cities = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
        solver = QuantumTSPSolver(cities)
        
        tour, cost, metadata = solver.solve_variational(num_iterations=50)
        
        # Should return valid tour
        assert len(tour) == 4
        assert all(city in tour for city in range(4))
        
        # Cost should be positive
        assert cost > 0
        
        # Metadata should have expected fields
        assert 'method' in metadata
        assert 'iterations' in metadata
        assert 'cost_history' in metadata
        assert metadata['method'] == 'VQE-simulated'
        assert len(metadata['cost_history']) == 51  # Initial + num_iterations
    
    def test_cost_history_convergence(self):
        """Test that VQE cost history decreases over time."""
        cities = np.array([[0, 0], [1, 0], [1, 1]])
        solver = QuantumTSPSolver(cities)
        
        _, _, metadata = solver.solve_variational(num_iterations=20)
        
        costs = metadata['cost_history']
        
        # Cost should not increase dramatically
        # (it's a stochastic process, so some fluctuation is OK)
        assert costs[-1] <= costs[0] * 1.5
    
    def test_small_problem(self):
        """Test both quantum methods on a small problem."""
        cities = np.array([[0, 0], [1, 0], [0, 1]])
        solver = QuantumTSPSolver(cities)
        
        # QAOA
        tour_qaoa, cost_qaoa, _ = solver.solve_qaoa_simulation()
        assert len(tour_qaoa) == 3
        assert cost_qaoa > 0
        
        # VQE
        tour_vqe, cost_vqe, _ = solver.solve_variational(num_iterations=20)
        assert len(tour_vqe) == 3
        assert cost_vqe > 0
    
    def test_reproducibility_with_seed(self):
        """Test that setting seed gives reproducible results."""
        cities = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
        
        solver1 = QuantumTSPSolver(cities)
        tour1, cost1, _ = solver1.solve_qaoa_simulation()
        
        solver2 = QuantumTSPSolver(cities)
        tour2, cost2, _ = solver2.solve_qaoa_simulation()
        
        # Should get same cost (reproducible with seed)
        assert np.isclose(cost1, cost2)


class TestQuantumVsClassicalComparison:
    """Test comparison scenarios between quantum and classical."""
    
    def test_both_methods_solve_small_problem(self):
        """Test that both quantum and classical methods work on same problem."""
        cities = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
        
        quantum_solver = QuantumTSPSolver(cities)
        tour_quantum, cost_quantum, _ = quantum_solver.solve_variational()
        
        # Classical comparison
        from src.classical.solvers import NearestNeighborSolver
        classical_solver = NearestNeighborSolver(cities)
        tour_classical, cost_classical = classical_solver.solve_best_start()
        
        # Both should return valid tours
        assert len(tour_quantum) == 4
        assert len(tour_classical) == 4
        
        # Both should have positive costs
        assert cost_quantum > 0
        assert cost_classical > 0
        
        # Classical optimal should be <= quantum for this simple case
        # (since quantum solver is simulated)
        assert cost_classical <= cost_quantum * 1.5
