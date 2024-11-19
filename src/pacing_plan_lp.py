import numpy as np
import cvxpy as cp
from abc import ABC, abstractmethod
from pacing_plan import PacingPlanStatic

class PacingPlanLP(PacingPlanStatic, ABC):
    def __init__(self, race_course, target_time, total_paces):
        super().__init__(race_course, target_time, total_paces)
        self.paces = None

    @abstractmethod
    def define_variables(self):
        """
        Defines the extra variables needed for the LP problem.
        """
        pass

    @abstractmethod
    def formulate_objective(self):
        """
        Defines the objective function for the LP problem.
        """
        pass

    @abstractmethod
    def formulate_constraints(self):
        """
        Defines the constraints for the LP problem.
        """
        pass

    def formulate_lp_problem(self, M=1):
        self.paces = cp.Variable(self.get_n_segments())
        self.define_variables()
        objective = self.formulate_objective()
        constraints = [
            self.paces @ self.get_segment_lengths() == self.target_time,
            self.paces >= 0,
        ]
        constraints += self.formulate_constraints()
        
        return cp.Problem(objective, constraints)

    def solve_lp_problem(self):
        problem = self.formulate_lp_problem()
        problem.solve(solver=cp.GUROBI)
        
        if problem.status == cp.OPTIMAL:
            self.true_paces_full = self.paces.value
        else:
            raise ValueError("LP problem is infeasible")

    def _calculate_recommendations(self, verbose):
        self.solve_lp_problem()
        return self.true_paces_full

class PacingPlanLPAbsolute(PacingPlanLP):
    def __init__(self, race_course, target_time, total_paces):
        super().__init__(race_course, target_time, total_paces)
        self.M = 1
    
    def define_variables(self):
        n_segments = self.get_n_segments()
        self.changes = cp.Variable(n_segments-1, integer=True)
        self.absolutes = cp.Variable(n_segments)

    def formulate_objective(self):
        return cp.Minimize(cp.sum(self.absolutes))

    def formulate_constraints(self):
        n_segments = self.get_n_segments()
        constraints = [
            self.changes >= 0,
            self.changes <= 1,
            cp.sum(self.changes) == self.total_paces - 1,
            self.absolutes >= self.paces - (self.optimal_paces),
            self.absolutes >= (self.optimal_paces) - self.paces
        ]
        constraints += [self.M*self.changes[i] >= self.paces[i+1] - self.paces[i] for i in range(n_segments-1)]
        constraints += [self.M*self.changes[i] >= self.paces[i] - self.paces[i+1] for i in range(n_segments-1)]
        return constraints

class PacingPlanLPSquare(PacingPlanLP):
    def __init__(self, race_course, target_time, total_paces):
        super().__init__(race_course, target_time, total_paces)
        self.M = 1
    
    def define_variables(self):
        n_segments = self.get_n_segments()
        self.changes = cp.Variable(n_segments-1, integer=True)

    def formulate_objective(self):
        return cp.Minimize(cp.sum_squares(self.paces - self.optimal_paces))

    def formulate_constraints(self):
        n_segments = self.get_n_segments()
        constraints = [
            self.changes >= 0,
            self.changes <= 1,
            cp.sum(self.changes) == self.total_paces - 1,
        ]
        constraints += [self.M*self.changes[i] >= self.paces[i+1] - self.paces[i] for i in range(n_segments-1)]
        constraints += [self.M*self.changes[i] >= self.paces[i] - self.paces[i+1] for i in range(n_segments-1)]
        return constraints