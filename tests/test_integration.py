import pytest
import json
from pathlib import Path
from src.models.cdm import ScheduleRequest, ScheduleResponse
from src.solver.engine import solve_schedule
from src.validation.checkers import validate_schedule


def test_sample_input_solves():
    """Test that the sample input produces a valid schedule."""
    # Load sample input
    sample_path = Path(__file__).parent.parent / "examples" / "sample_input.json"
    with open(sample_path) as f:
        data = json.load(f)

    request = ScheduleRequest(**data)
    result = solve_schedule(request)

    # Should return a valid schedule, not an error
    assert isinstance(result, ScheduleResponse)
    assert len(result.assignments) > 0
    assert result.kpis.tardiness_minutes >= 0

    # Validate the schedule
    is_valid, errors = validate_schedule(request, result.assignments)
    if not is_valid:
        print("Validation errors:")
        for err in errors:
            print(f"  - {err}")

    assert is_valid, f"Schedule failed validation: {errors}"


def test_infeasible_schedule():
    """Test that infeasible problems return error messages."""
    # Create impossible scenario: need 3 hours of work but only 1 hour window
    data = {
        "horizon": {
            "start": "2025-11-03T08:00:00",
            "end": "2025-11-03T16:00:00"
        },
        "resources": [
            {
                "id": "R1",
                "capabilities": ["fill"],
                "calendar": [["2025-11-03T08:00:00", "2025-11-03T09:00:00"]]
            }
        ],
        "changeover_matrix_minutes": {"values": {}},
        "products": [
            {
                "id": "P1",
                "family": "standard",
                "due": "2025-11-03T12:00:00",
                "route": [{"capability": "fill", "duration_minutes": 180}]
            }
        ],
        "settings": {"time_limit_seconds": 5}
    }

    request = ScheduleRequest(**data)
    result = solve_schedule(request)

    # Should return error, not schedule
    from src.models.cdm import ScheduleError
    assert isinstance(result, ScheduleError)
    assert result.error is not None
    assert len(result.why) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
