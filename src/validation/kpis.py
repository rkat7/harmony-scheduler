from typing import List, Dict
from datetime import datetime, timedelta
from collections import defaultdict

from ..models.cdm import ScheduleRequest, Assignment, KPIs
from ..utils.time_utils import to_minutes


def calculate_kpis(request: ScheduleRequest, assignments: List[Assignment]) -> KPIs:
    """Calculate all KPIs from the schedule."""

    # Organize assignments by product and resource
    product_assignments = defaultdict(list)
    resource_assignments = defaultdict(list)

    for a in assignments:
        product_assignments[a.product].append(a)
        resource_assignments[a.resource].append(a)

    # Calculate tardiness
    tardiness_minutes = _calculate_tardiness(request, product_assignments)

    # Count changeovers
    changeovers = _count_changeovers(request, resource_assignments)

    # Calculate makespan
    makespan_minutes = _calculate_makespan(request, assignments)

    # Calculate utilization per resource
    utilization = _calculate_utilization(request, resource_assignments)

    return KPIs(
        tardiness_minutes=tardiness_minutes,
        changeovers=changeovers,
        makespan_minutes=makespan_minutes,
        utilization=utilization
    )


def _calculate_tardiness(
    request: ScheduleRequest,
    product_assignments: Dict[str, List[Assignment]]
) -> int:
    """Calculate total tardiness across all products."""
    total_tardiness = 0

    for product in request.products:
        if product.id not in product_assignments:
            continue

        # Find completion time (end of last operation)
        ops = product_assignments[product.id]
        completion_time = max(a.end for a in ops)

        # Calculate tardiness
        if completion_time > product.due:
            delta = completion_time - product.due
            total_tardiness += int(delta.total_seconds() / 60)

    return total_tardiness


def _count_changeovers(
    request: ScheduleRequest,
    resource_assignments: Dict[str, List[Assignment]]
) -> int:
    """Count the number of family changeovers."""
    changeover_count = 0

    # Build product family lookup
    product_families = {p.id: p.family for p in request.products}

    for resource_id, ops in resource_assignments.items():
        # Sort by start time
        sorted_ops = sorted(ops, key=lambda x: x.start)

        # Count transitions between different families
        for i in range(len(sorted_ops) - 1):
            curr_family = product_families.get(sorted_ops[i].product)
            next_family = product_families.get(sorted_ops[i + 1].product)

            if curr_family and next_family and curr_family != next_family:
                changeover_count += 1

    return changeover_count


def _calculate_makespan(request: ScheduleRequest, assignments: List[Assignment]) -> int:
    """Calculate makespan (total schedule duration)."""
    if not assignments:
        return 0

    earliest_start = min(a.start for a in assignments)
    latest_end = max(a.end for a in assignments)

    delta = latest_end - earliest_start
    return int(delta.total_seconds() / 60)


def _calculate_utilization(
    request: ScheduleRequest,
    resource_assignments: Dict[str, List[Assignment]]
) -> Dict[str, int]:
    """Calculate utilization percentage for each resource."""
    utilization = {}

    # Calculate total available time per resource
    for resource in request.resources:
        total_available = 0
        for start_dt, end_dt in resource.calendar:
            delta = end_dt - start_dt
            total_available += delta.total_seconds() / 60

        # Calculate busy time
        busy_time = 0
        if resource.id in resource_assignments:
            for a in resource_assignments[resource.id]:
                delta = a.end - a.start
                busy_time += delta.total_seconds() / 60

        # Calculate percentage
        if total_available > 0:
            utilization[resource.id] = int((busy_time / total_available) * 100)
        else:
            utilization[resource.id] = 0

    return utilization
