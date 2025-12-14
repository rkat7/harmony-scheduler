from typing import Dict, Any, List, Tuple
from datetime import datetime
from .base import ScheduleAdapter
from ..models.cdm import (
    ScheduleRequest, Horizon, Resource, Product, Operation,
    ChangeoverMatrix, Settings
)


class ClientBAdapter(ScheduleAdapter):
    """
    Adapter for Client B (legacy ERP format).

    Handles differences:
    - "orders" vs "products"
    - "machines" vs "resources"
    - MM/DD/YYYY date format vs ISO
    - Flat operations list vs nested routes
    - Decimal hours vs ISO timestamps
    - Implicit calendars (full shift unless break specified)
    """

    @property
    def client_id(self) -> str:
        return "client_b"

    def to_cdm(self, raw_input: Dict[str, Any]) -> ScheduleRequest:
        """Transform Client B format to CDM."""

        # Parse horizon
        horizon = self._parse_horizon(raw_input["shift_window"])

        # Parse resources (machines)
        resources = self._parse_resources(
            raw_input["machines"],
            raw_input.get("machine_breaks", []),
            horizon
        )

        # Parse products (orders)
        products = self._parse_products(
            raw_input["orders"],
            horizon.start
        )

        # Parse changeover matrix
        changeover_matrix = self._parse_changeover_matrix(
            raw_input.get("setup_times", [])
        )

        # Settings
        settings = Settings(
            time_limit_seconds=raw_input.get("time_limit_seconds", 30)
        )

        return ScheduleRequest(
            horizon=horizon,
            resources=resources,
            products=products,
            changeover_matrix_minutes=changeover_matrix,
            settings=settings
        )

    def _parse_horizon(self, shift_window: str) -> Horizon:
        """
        Parse shift window like "11/03/2025 08:00 - 16:00"
        """
        parts = shift_window.split(" - ")
        if len(parts) != 2:
            raise ValueError(f"Invalid shift_window format: {shift_window}")

        start_str = parts[0].strip()
        end_time_str = parts[1].strip()

        # Parse start datetime
        start_dt = datetime.strptime(start_str, "%m/%d/%Y %H:%M")

        # End is just time, use same date as start
        end_hour, end_min = map(int, end_time_str.split(":"))
        end_dt = start_dt.replace(hour=end_hour, minute=end_min)

        return Horizon(start=start_dt, end=end_dt)

    def _parse_resources(
        self,
        machines: List[str],
        breaks: List[Dict[str, Any]],
        horizon: Horizon
    ) -> List[Resource]:
        """
        Convert machines list to resources.

        Machines have implicit capabilities based on name prefix.
        Full shift calendar unless break specified.
        """
        resources = []

        for machine_id in machines:
            # Infer capability from machine name prefix
            capability = self._infer_capability(machine_id)

            # Build calendar (default full shift)
            calendar = self._build_calendar(machine_id, breaks, horizon)

            resources.append(Resource(
                id=machine_id,
                capabilities=[capability],
                calendar=calendar
            ))

        return resources

    def _infer_capability(self, machine_id: str) -> str:
        """Extract capability from machine name like 'Fill-1' -> 'fill'."""
        prefix = machine_id.split("-")[0].lower()
        return prefix

    def _build_calendar(
        self,
        machine_id: str,
        breaks: List[Dict[str, Any]],
        horizon: Horizon
    ) -> List[Tuple[datetime, datetime]]:
        """
        Build calendar windows for a machine.

        If no breaks, return full shift.
        If breaks exist, split around them.
        """
        machine_breaks = [b for b in breaks if b["machine"] == machine_id]

        if not machine_breaks:
            # Full shift availability
            return [(horizon.start, horizon.end)]

        # Sort breaks by start time
        sorted_breaks = sorted(
            machine_breaks,
            key=lambda b: self._parse_time(b["start"], horizon.start)
        )

        # Build windows around breaks
        windows = []
        current_start = horizon.start

        for brk in sorted_breaks:
            break_start = self._parse_time(brk["start"], horizon.start)
            break_end = self._parse_time(brk["end"], horizon.start)

            # Add window before break
            if current_start < break_start:
                windows.append((current_start, break_start))

            current_start = break_end

        # Add final window after last break
        if current_start < horizon.end:
            windows.append((current_start, horizon.end))

        return windows

    def _parse_time(self, time_str: str, base_date: datetime) -> datetime:
        """Parse time like '12:00' using base date."""
        hour, minute = map(int, time_str.split(":"))
        return base_date.replace(hour=hour, minute=minute)

    def _parse_products(
        self,
        orders: List[Dict[str, Any]],
        base_date: datetime
    ) -> List[Product]:
        """Convert orders to products."""
        products = []

        for order in orders:
            # Parse due time (decimal hour like 15.0 = 3pm)
            due_hour = order["deadline_hour"]
            due_dt = base_date.replace(
                hour=int(due_hour),
                minute=int((due_hour % 1) * 60)
            )

            # Build route from operations
            route = []
            for op in sorted(order["operations"], key=lambda x: x["step"]):
                route.append(Operation(
                    capability=op["type"],
                    duration_minutes=op["minutes"]
                ))

            products.append(Product(
                id=order["order_id"],
                family=order["product_family"],
                due=due_dt,
                route=route
            ))

        return products

    def _parse_changeover_matrix(
        self,
        setup_times: List[Dict[str, Any]]
    ) -> ChangeoverMatrix:
        """Convert setup_times list to changeover matrix."""
        values = {}

        for setup in setup_times:
            from_family = setup["from_family"]
            to_family = setup["to_family"]
            minutes = setup["minutes"]

            key = f"{from_family}->{to_family}"
            values[key] = minutes

        return ChangeoverMatrix(values=values)
