from typing import List, Tuple
from collections import defaultdict

from ..models.cdm import ScheduleRequest, Assignment
from ..utils.time_utils import to_minutes, intervals_overlap


def validate_schedule(request: ScheduleRequest, assignments: List[Assignment]) -> Tuple[bool, List[str]]:
    """Run all validation checks on a schedule."""
    errors = []

    errors.extend(check_no_overlap(request, assignments))
    errors.extend(check_precedence(request, assignments))
    errors.extend(check_calendar_compliance(request, assignments))
    errors.extend(check_horizon_bounds(request, assignments))

    return len(errors) == 0, errors


def check_no_overlap(request: ScheduleRequest, assignments: List[Assignment]) -> List[str]:
    """Verify no operations overlap on the same resource."""
    errors = []
    resource_ops = defaultdict(list)

    for a in assignments:
        resource_ops[a.resource].append(a)

    for resource_id, ops in resource_ops.items():
        # Check all pairs for overlap
        for i in range(len(ops)):
            for j in range(i + 1, len(ops)):
                a1, a2 = ops[i], ops[j]

                # Convert to comparable format
                a1_start = a1.start.timestamp()
                a1_end = a1.end.timestamp()
                a2_start = a2.start.timestamp()
                a2_end = a2.end.timestamp()

                if intervals_overlap(a1_start, a1_end, a2_start, a2_end):
                    errors.append(
                        f"Overlap on {resource_id}: {a1.product}/{a1.op} "
                        f"[{a1.start} - {a1.end}] overlaps with "
                        f"{a2.product}/{a2.op} [{a2.start} - {a2.end}]"
                    )

    return errors


def check_precedence(request: ScheduleRequest, assignments: List[Assignment]) -> List[str]:
    """Verify operations within a product follow route order."""
    errors = []

    # Group assignments by product
    product_ops = defaultdict(list)
    for a in assignments:
        product_ops[a.product].append(a)

    # Check each product's route
    for product in request.products:
        if product.id not in product_ops:
            continue

        ops = product_ops[product.id]

        # Build operation lookup by capability
        op_lookup = {a.op: a for a in ops}

        # Verify precedence according to route
        for i in range(len(product.route) - 1):
            curr_cap = product.route[i].capability
            next_cap = product.route[i + 1].capability

            if curr_cap not in op_lookup or next_cap not in op_lookup:
                continue

            curr_assignment = op_lookup[curr_cap]
            next_assignment = op_lookup[next_cap]

            if curr_assignment.end > next_assignment.start:
                errors.append(
                    f"Precedence violation in {product.id}: "
                    f"{curr_cap} ends at {curr_assignment.end} but "
                    f"{next_cap} starts at {next_assignment.start}"
                )

    return errors


def check_calendar_compliance(request: ScheduleRequest, assignments: List[Assignment]) -> List[str]:
    """Verify all operations fit within resource calendars."""
    errors = []

    # Build resource lookup
    resource_lookup = {r.id: r for r in request.resources}

    for a in assignments:
        resource = resource_lookup.get(a.resource)
        if not resource:
            errors.append(f"Assignment references unknown resource: {a.resource}")
            continue

        # Check if assignment fits in any calendar window
        fits_in_window = False
        for window_start, window_end in resource.calendar:
            if a.start >= window_start and a.end <= window_end:
                fits_in_window = True
                break

        if not fits_in_window:
            errors.append(
                f"Calendar violation: {a.product}/{a.op} on {a.resource} "
                f"[{a.start} - {a.end}] not within working windows"
            )

    return errors


def check_horizon_bounds(request: ScheduleRequest, assignments: List[Assignment]) -> List[str]:
    """Verify all times are within the horizon."""
    errors = []

    for a in assignments:
        if a.start < request.horizon.start or a.end > request.horizon.end:
            errors.append(
                f"Horizon violation: {a.product}/{a.op} "
                f"[{a.start} - {a.end}] outside horizon "
                f"[{request.horizon.start} - {request.horizon.end}]"
            )

    return errors
