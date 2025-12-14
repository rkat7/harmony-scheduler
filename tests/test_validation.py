import pytest
from datetime import datetime
from src.models.cdm import (
    ScheduleRequest, Horizon, Resource, Product, Operation,
    ChangeoverMatrix, Settings, Assignment
)
from src.validation.checkers import (
    check_no_overlap, check_precedence,
    check_calendar_compliance, check_horizon_bounds
)


def test_overlap_detection():
    """Test that overlapping operations on same resource are caught."""
    horizon = Horizon(
        start=datetime(2025, 11, 3, 8, 0),
        end=datetime(2025, 11, 3, 16, 0)
    )

    resources = [
        Resource(
            id="R1",
            capabilities=["fill"],
            calendar=[(datetime(2025, 11, 3, 8, 0), datetime(2025, 11, 3, 16, 0))]
        )
    ]

    products = [
        Product(
            id="P1",
            family="standard",
            due=datetime(2025, 11, 3, 12, 0),
            route=[Operation(capability="fill", duration_minutes=30)]
        )
    ]

    request = ScheduleRequest(
        horizon=horizon,
        resources=resources,
        products=products,
        changeover_matrix_minutes=ChangeoverMatrix(),
        settings=Settings()
    )

    # Create overlapping assignments
    assignments = [
        Assignment(
            product="P1",
            op="fill",
            resource="R1",
            start=datetime(2025, 11, 3, 8, 0),
            end=datetime(2025, 11, 3, 8, 30)
        ),
        Assignment(
            product="P2",
            op="fill",
            resource="R1",
            start=datetime(2025, 11, 3, 8, 15),  # Overlaps!
            end=datetime(2025, 11, 3, 8, 45)
        )
    ]

    errors = check_no_overlap(request, assignments)
    assert len(errors) > 0
    assert "Overlap" in errors[0]


def test_no_overlap_valid():
    """Test that non-overlapping operations pass validation."""
    horizon = Horizon(
        start=datetime(2025, 11, 3, 8, 0),
        end=datetime(2025, 11, 3, 16, 0)
    )

    resources = [
        Resource(
            id="R1",
            capabilities=["fill"],
            calendar=[(datetime(2025, 11, 3, 8, 0), datetime(2025, 11, 3, 16, 0))]
        )
    ]

    products = [
        Product(
            id="P1",
            family="standard",
            due=datetime(2025, 11, 3, 12, 0),
            route=[Operation(capability="fill", duration_minutes=30)]
        )
    ]

    request = ScheduleRequest(
        horizon=horizon,
        resources=resources,
        products=products,
        changeover_matrix_minutes=ChangeoverMatrix(),
        settings=Settings()
    )

    # Non-overlapping assignments
    assignments = [
        Assignment(
            product="P1",
            op="fill",
            resource="R1",
            start=datetime(2025, 11, 3, 8, 0),
            end=datetime(2025, 11, 3, 8, 30)
        ),
        Assignment(
            product="P2",
            op="fill",
            resource="R1",
            start=datetime(2025, 11, 3, 8, 30),  # Starts when P1 ends
            end=datetime(2025, 11, 3, 9, 0)
        )
    ]

    errors = check_no_overlap(request, assignments)
    assert len(errors) == 0


def test_precedence_violation():
    """Test that precedence violations are detected."""
    horizon = Horizon(
        start=datetime(2025, 11, 3, 8, 0),
        end=datetime(2025, 11, 3, 16, 0)
    )

    resources = [
        Resource(
            id="Fill-1",
            capabilities=["fill"],
            calendar=[(datetime(2025, 11, 3, 8, 0), datetime(2025, 11, 3, 16, 0))]
        ),
        Resource(
            id="Label-1",
            capabilities=["label"],
            calendar=[(datetime(2025, 11, 3, 8, 0), datetime(2025, 11, 3, 16, 0))]
        )
    ]

    products = [
        Product(
            id="P1",
            family="standard",
            due=datetime(2025, 11, 3, 12, 0),
            route=[
                Operation(capability="fill", duration_minutes=30),
                Operation(capability="label", duration_minutes=20)
            ]
        )
    ]

    request = ScheduleRequest(
        horizon=horizon,
        resources=resources,
        products=products,
        changeover_matrix_minutes=ChangeoverMatrix(),
        settings=Settings()
    )

    # Labeling starts before filling ends - violation!
    assignments = [
        Assignment(
            product="P1",
            op="fill",
            resource="Fill-1",
            start=datetime(2025, 11, 3, 8, 0),
            end=datetime(2025, 11, 3, 8, 30)
        ),
        Assignment(
            product="P1",
            op="label",
            resource="Label-1",
            start=datetime(2025, 11, 3, 8, 15),  # Starts before fill ends!
            end=datetime(2025, 11, 3, 8, 35)
        )
    ]

    errors = check_precedence(request, assignments)
    assert len(errors) > 0
    assert "Precedence violation" in errors[0]


def test_precedence_valid():
    """Test that valid precedence passes validation."""
    horizon = Horizon(
        start=datetime(2025, 11, 3, 8, 0),
        end=datetime(2025, 11, 3, 16, 0)
    )

    resources = [
        Resource(
            id="Fill-1",
            capabilities=["fill"],
            calendar=[(datetime(2025, 11, 3, 8, 0), datetime(2025, 11, 3, 16, 0))]
        ),
        Resource(
            id="Label-1",
            capabilities=["label"],
            calendar=[(datetime(2025, 11, 3, 8, 0), datetime(2025, 11, 3, 16, 0))]
        )
    ]

    products = [
        Product(
            id="P1",
            family="standard",
            due=datetime(2025, 11, 3, 12, 0),
            route=[
                Operation(capability="fill", duration_minutes=30),
                Operation(capability="label", duration_minutes=20)
            ]
        )
    ]

    request = ScheduleRequest(
        horizon=horizon,
        resources=resources,
        products=products,
        changeover_matrix_minutes=ChangeoverMatrix(),
        settings=Settings()
    )

    # Valid precedence
    assignments = [
        Assignment(
            product="P1",
            op="fill",
            resource="Fill-1",
            start=datetime(2025, 11, 3, 8, 0),
            end=datetime(2025, 11, 3, 8, 30)
        ),
        Assignment(
            product="P1",
            op="label",
            resource="Label-1",
            start=datetime(2025, 11, 3, 8, 30),
            end=datetime(2025, 11, 3, 8, 50)
        )
    ]

    errors = check_precedence(request, assignments)
    assert len(errors) == 0


def test_calendar_violation():
    """Test that operations outside calendar windows are caught."""
    horizon = Horizon(
        start=datetime(2025, 11, 3, 8, 0),
        end=datetime(2025, 11, 3, 16, 0)
    )

    # Resource with break from 12:00-12:30
    resources = [
        Resource(
            id="Fill-1",
            capabilities=["fill"],
            calendar=[
                (datetime(2025, 11, 3, 8, 0), datetime(2025, 11, 3, 12, 0)),
                (datetime(2025, 11, 3, 12, 30), datetime(2025, 11, 3, 16, 0))
            ]
        )
    ]

    products = [
        Product(
            id="P1",
            family="standard",
            due=datetime(2025, 11, 3, 13, 0),
            route=[Operation(capability="fill", duration_minutes=30)]
        )
    ]

    request = ScheduleRequest(
        horizon=horizon,
        resources=resources,
        products=products,
        changeover_matrix_minutes=ChangeoverMatrix(),
        settings=Settings()
    )

    # Operation scheduled during break
    assignments = [
        Assignment(
            product="P1",
            op="fill",
            resource="Fill-1",
            start=datetime(2025, 11, 3, 12, 0),  # Starts at break
            end=datetime(2025, 11, 3, 12, 30)
        )
    ]

    errors = check_calendar_compliance(request, assignments)
    assert len(errors) > 0
    assert "Calendar violation" in errors[0]
