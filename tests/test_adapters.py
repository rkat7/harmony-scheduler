import pytest
import json
from pathlib import Path
from src.adapters.factory import AdapterFactory
from src.adapters.client_a import ClientAAdapter
from src.adapters.client_b import ClientBAdapter
from src.solver.engine import solve_schedule


def test_client_a_adapter():
    """Test that Client A adapter works with original format."""
    sample_path = Path(__file__).parent.parent / "examples" / "sample_input.json"
    with open(sample_path) as f:
        data = json.load(f)

    adapter = ClientAAdapter()
    request = adapter.to_cdm(data)

    assert request.horizon.start.year == 2025
    assert len(request.resources) == 4
    assert len(request.products) == 4


def test_client_b_adapter():
    """Test that Client B adapter transforms legacy format correctly."""
    sample_path = Path(__file__).parent.parent / "examples" / "client_b_input.json"
    with open(sample_path) as f:
        data = json.load(f)

    adapter = ClientBAdapter()
    request = adapter.to_cdm(data)

    # Verify horizon
    assert request.horizon.start.year == 2025
    assert request.horizon.start.month == 11
    assert request.horizon.start.day == 3
    assert request.horizon.start.hour == 8
    assert request.horizon.end.hour == 16

    # Verify resources
    assert len(request.resources) == 4
    fill_1 = next(r for r in request.resources if r.id == "Fill-1")
    assert "fill" in fill_1.capabilities

    # Fill-1 has a break, should have 2 calendar windows
    assert len(fill_1.calendar) == 2

    # Fill-2 has no breaks, should have 1 full shift window
    fill_2 = next(r for r in request.resources if r.id == "Fill-2")
    assert len(fill_2.calendar) == 1

    # Verify products
    assert len(request.products) == 2
    ord_100 = next(p for p in request.products if p.id == "ORD-100")
    assert ord_100.family == "standard"
    assert ord_100.due.hour == 12
    assert ord_100.due.minute == 30
    assert len(ord_100.route) == 3

    # Verify changeover matrix
    assert request.changeover_matrix_minutes.values["standard->premium"] == 20


def test_adapter_factory_explicit():
    """Test factory with explicit client_id."""
    factory = AdapterFactory()

    # Client A
    client_a_data = {"client_id": "client_a", "horizon": {}, "products": [], "resources": []}
    adapter = factory.get_adapter(client_a_data)
    assert isinstance(adapter, ClientAAdapter)

    # Client B
    client_b_data = {"client_id": "client_b", "shift_window": "", "orders": [], "machines": []}
    adapter = factory.get_adapter(client_b_data)
    assert isinstance(adapter, ClientBAdapter)


def test_adapter_factory_auto_detect():
    """Test factory with automatic schema detection."""
    factory = AdapterFactory()

    # Should detect Client A
    client_a_data = {"horizon": {"start": "", "end": ""}, "products": [], "resources": []}
    adapter = factory.get_adapter(client_a_data)
    assert isinstance(adapter, ClientAAdapter)

    # Should detect Client B
    client_b_data = {"shift_window": "", "orders": [], "machines": []}
    adapter = factory.get_adapter(client_b_data)
    assert isinstance(adapter, ClientBAdapter)


def test_client_b_end_to_end():
    """Test that Client B input can be solved successfully."""
    sample_path = Path(__file__).parent.parent / "examples" / "client_b_input.json"
    with open(sample_path) as f:
        data = json.load(f)

    factory = AdapterFactory()
    adapter = factory.get_adapter(data)
    request = adapter.to_cdm(data)

    result = solve_schedule(request)

    # Should produce valid schedule
    from src.models.cdm import ScheduleResponse
    assert isinstance(result, ScheduleResponse)
    assert len(result.assignments) > 0
    assert result.kpis.tardiness_minutes >= 0


def test_unknown_client():
    """Test that unknown client format raises error."""
    factory = AdapterFactory()

    with pytest.raises(ValueError, match="Unable to detect"):
        factory.get_adapter({"unknown": "format"})
