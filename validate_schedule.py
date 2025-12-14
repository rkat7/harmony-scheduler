#!/usr/bin/env python3
"""
Acceptance validation script for production schedules.

Checks:
1. No overlap on resources
2. Precedence constraints respected
3. Calendar/horizon compliance
4. KPIs are reproducible
"""

import json
import sys
from src.models.cdm import ScheduleRequest, ScheduleResponse
from src.validation.checkers import validate_schedule
from src.validation.kpis import calculate_kpis


def validate_from_files(input_file: str, output_file: str) -> bool:
    """Validate a schedule against acceptance criteria."""

    # Load input and output
    with open(input_file) as f:
        input_data = json.load(f)

    with open(output_file) as f:
        output_data = json.load(f)

    request = ScheduleRequest(**input_data)
    response = ScheduleResponse(**output_data)

    print(f"Validating schedule with {len(response.assignments)} assignments...")
    print()

    # Check 1-3: Constraints
    is_valid, errors = validate_schedule(request, response.assignments)

    if not is_valid:
        print("❌ VALIDATION FAILED")
        print("\nConstraint violations:")
        for err in errors:
            print(f"  - {err}")
        return False

    print("✓ No overlap violations")
    print("✓ Precedence constraints satisfied")
    print("✓ Calendar/horizon compliance verified")

    # Check 4: KPI reproducibility
    recalculated_kpis = calculate_kpis(request, response.assignments)

    tardiness_match = abs(recalculated_kpis.tardiness_minutes - response.kpis.tardiness_minutes) <= 1
    changeover_match = recalculated_kpis.changeovers == response.kpis.changeovers
    makespan_match = abs(recalculated_kpis.makespan_minutes - response.kpis.makespan_minutes) <= 1

    if not (tardiness_match and changeover_match and makespan_match):
        print("\n❌ KPI MISMATCH")
        print(f"  Reported tardiness: {response.kpis.tardiness_minutes}")
        print(f"  Recalculated:       {recalculated_kpis.tardiness_minutes}")
        print(f"  Reported changeovers: {response.kpis.changeovers}")
        print(f"  Recalculated:         {recalculated_kpis.changeovers}")
        return False

    print("✓ KPIs are reproducible")

    print()
    print("✅ ALL VALIDATION CHECKS PASSED")
    print()
    print("KPIs:")
    print(f"  Tardiness:   {response.kpis.tardiness_minutes} minutes")
    print(f"  Changeovers: {response.kpis.changeovers}")
    print(f"  Makespan:    {response.kpis.makespan_minutes} minutes")
    print(f"  Utilization: {response.kpis.utilization}")

    return True


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python validate_schedule.py <input.json> <output.json>")
        sys.exit(1)

    success = validate_from_files(sys.argv[1], sys.argv[2])
    sys.exit(0 if success else 1)
