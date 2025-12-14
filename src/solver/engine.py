from ortools.sat.python import cp_model
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import sys

from ..models.cdm import ScheduleRequest, Assignment, ScheduleResponse, KPIs, ScheduleError
from ..utils.time_utils import to_minutes, from_minutes


class ScheduleSolver:
    def __init__(self, request: ScheduleRequest):
        self.request = request
        self.model = cp_model.CpModel()
        self.reference_time = request.horizon.start

        # Convert time bounds to minutes
        self.horizon_start = 0
        self.horizon_end = to_minutes(request.horizon.end, self.reference_time)

        # Build resource capability map
        self.resource_map = self._build_resource_map()

        # Storage for decision variables
        self.operations = []
        self.intervals = {}
        self.starts = {}
        self.ends = {}
        self.resource_assignments = {}
        self.product_completion_times = {}

    def _build_resource_map(self) -> Dict[str, List[int]]:
        """Map capabilities to resource indices."""
        cap_map = {}
        for idx, resource in enumerate(self.request.resources):
            for cap in resource.capabilities:
                if cap not in cap_map:
                    cap_map[cap] = []
                cap_map[cap].append(idx)
        return cap_map

    def _convert_calendar_to_minutes(self, resource_idx: int) -> List[Tuple[int, int]]:
        """Convert resource calendar windows to minute offsets."""
        resource = self.request.resources[resource_idx]
        windows = []
        for start_dt, end_dt in resource.calendar:
            start_min = to_minutes(start_dt, self.reference_time)
            end_min = to_minutes(end_dt, self.reference_time)
            windows.append((start_min, end_min))
        return windows

    def build_model(self):
        """Construct the CP-SAT constraint model."""
        op_id = 0

        # Create variables for each operation
        for product in self.request.products:
            product_ops = []

            for op_idx, operation in enumerate(product.route):
                eligible_resources = self.resource_map.get(operation.capability, [])

                if not eligible_resources:
                    raise ValueError(
                        f"No resources available for capability '{operation.capability}' "
                        f"in product {product.id}"
                    )

                # Create start/end variables
                start_var = self.model.NewIntVar(
                    self.horizon_start,
                    self.horizon_end,
                    f"start_{product.id}_op{op_idx}"
                )
                end_var = self.model.NewIntVar(
                    self.horizon_start,
                    self.horizon_end,
                    f"end_{product.id}_op{op_idx}"
                )

                # Duration constraint
                self.model.Add(end_var == start_var + operation.duration_minutes)

                # Resource assignment
                resource_var = self.model.NewIntVarFromDomain(
                    cp_model.Domain.FromValues(eligible_resources),
                    f"resource_{product.id}_op{op_idx}"
                )

                # Create interval variables for each possible resource assignment
                intervals_for_op = []
                assignment_bools = []

                for res_idx in eligible_resources:
                    is_assigned = self.model.NewBoolVar(
                        f"assigned_{product.id}_op{op_idx}_res{res_idx}"
                    )
                    self.model.Add(resource_var == res_idx).OnlyEnforceIf(is_assigned)
                    self.model.Add(resource_var != res_idx).OnlyEnforceIf(is_assigned.Not())

                    assignment_bools.append(is_assigned)

                    interval = self.model.NewOptionalIntervalVar(
                        start_var,
                        operation.duration_minutes,
                        end_var,
                        is_assigned,
                        f"interval_{product.id}_op{op_idx}_res{res_idx}"
                    )
                    intervals_for_op.append((res_idx, interval, is_assigned))

                # Exactly one resource must be selected
                self.model.AddExactlyOne(assignment_bools)

                # Store operation info
                self.operations.append({
                    'id': op_id,
                    'product': product.id,
                    'product_idx': self.request.products.index(product),
                    'op_index': op_idx,
                    'capability': operation.capability,
                    'duration': operation.duration_minutes,
                    'family': product.family,
                    'start': start_var,
                    'end': end_var,
                    'resource': resource_var,
                    'intervals': intervals_for_op,
                })

                product_ops.append(op_id)
                op_id += 1

            # Precedence constraints within product
            for i in range(len(product_ops) - 1):
                curr_op = self.operations[product_ops[i]]
                next_op = self.operations[product_ops[i + 1]]
                self.model.Add(next_op['start'] >= curr_op['end'])

            # Track product completion time
            last_op = self.operations[product_ops[-1]]
            self.product_completion_times[product.id] = last_op['end']

        # No-overlap constraints per resource
        self._add_no_overlap_constraints()

        # Calendar constraints
        self._add_calendar_constraints()

        # Objective: minimize total tardiness
        self._set_objective()

    def _add_no_overlap_constraints(self):
        """Ensure no two operations overlap on the same resource."""
        for res_idx in range(len(self.request.resources)):
            intervals_on_resource = []

            for op in self.operations:
                for r_idx, interval, _ in op['intervals']:
                    if r_idx == res_idx:
                        intervals_on_resource.append(interval)

            if intervals_on_resource:
                self.model.AddNoOverlap(intervals_on_resource)

    def _add_calendar_constraints(self):
        """Ensure operations fit within resource working windows."""
        for op in self.operations:
            for res_idx, interval, is_assigned in op['intervals']:
                windows = self._convert_calendar_to_minutes(res_idx)

                # Operation must start and end within one of the windows
                window_literals = []
                for w_start, w_end in windows:
                    in_window = self.model.NewBoolVar(
                        f"in_window_{op['id']}_res{res_idx}_w{w_start}"
                    )

                    # If in this window, start >= w_start and end <= w_end
                    self.model.Add(op['start'] >= w_start).OnlyEnforceIf([is_assigned, in_window])
                    self.model.Add(op['end'] <= w_end).OnlyEnforceIf([is_assigned, in_window])

                    window_literals.append(in_window)

                # At least one window must be active if assigned
                if window_literals:
                    self.model.AddBoolOr(window_literals).OnlyEnforceIf(is_assigned)

    def _set_objective(self):
        """Minimize total tardiness."""
        tardiness_vars = []

        for product in self.request.products:
            completion_time = self.product_completion_times[product.id]
            due_time = to_minutes(product.due, self.reference_time)

            # Tardiness = max(0, completion - due)
            tardiness = self.model.NewIntVar(0, self.horizon_end, f"tardiness_{product.id}")
            self.model.AddMaxEquality(tardiness, [completion_time - due_time, 0])

            tardiness_vars.append(tardiness)

        self.model.Minimize(sum(tardiness_vars))

    def solve(self) -> ScheduleResponse | ScheduleError:
        """Solve the scheduling problem."""
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.request.settings.time_limit_seconds
        solver.parameters.log_search_progress = False

        status = solver.Solve(self.model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            return self._extract_solution(solver)
        else:
            return self._handle_infeasibility(solver, status)

    def _extract_solution(self, solver: cp_model.CpSolver) -> ScheduleResponse:
        """Extract solution from solver."""
        assignments = []

        for op in self.operations:
            start_min = solver.Value(op['start'])
            end_min = solver.Value(op['end'])
            resource_idx = solver.Value(op['resource'])

            assignment = Assignment(
                product=op['product'],
                op=op['capability'],
                resource=self.request.resources[resource_idx].id,
                start=from_minutes(start_min, self.reference_time),
                end=from_minutes(end_min, self.reference_time)
            )
            assignments.append(assignment)

        # Calculate KPIs
        from ..validation.kpis import calculate_kpis
        kpis = calculate_kpis(self.request, assignments)

        return ScheduleResponse(assignments=assignments, kpis=kpis)

    def _handle_infeasibility(self, solver: cp_model.CpSolver, status) -> ScheduleError:
        """Generate helpful error message for infeasible problems."""
        reasons = []

        if status == cp_model.INFEASIBLE:
            reasons.append("No feasible schedule exists given the constraints")

            # Check for obvious issues
            for product in self.request.products:
                total_duration = sum(op.duration_minutes for op in product.route)
                due_offset = to_minutes(product.due, self.reference_time)

                if total_duration > due_offset:
                    reasons.append(
                        f"Product {product.id}: minimum duration ({total_duration}min) "
                        f"exceeds time until due date ({due_offset}min)"
                    )

            # Check resource availability
            for cap in set(op.capability for p in self.request.products for op in p.route):
                if cap not in self.resource_map:
                    reasons.append(f"No resource available for capability: {cap}")

        elif status == cp_model.MODEL_INVALID:
            reasons.append("Invalid constraint model - please report this issue")
        else:
            reasons.append(f"Solver failed with status: {status}")

        return ScheduleError(
            error="Could not find feasible schedule",
            why=reasons if reasons else ["Unknown reason"]
        )


def solve_schedule(request: ScheduleRequest) -> ScheduleResponse | ScheduleError:
    """Main entry point for solving a schedule."""
    solver = ScheduleSolver(request)
    solver.build_model()
    return solver.solve()
