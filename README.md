# Harmony Production Scheduler

Constraint-based production scheduling system that minimizes tardiness while respecting resource capabilities, calendars, and precedence constraints.

## Features

- CP-SAT solver using Google OR-Tools
- Multi-resource support with capabilities and calendars
- Precedence constraints and operation ordering
- Calendar management (breaks, shifts, maintenance)
- Family changeover tracking
- KPI reporting (tardiness, changeovers, makespan, utilization)
- Multi-tenant adapters for different client formats
- Web UI with Gantt chart visualization

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

### Option 1: Full Stack with UI

```bash
./start_ui.sh
```

Opens browser at `http://localhost:3000` with Gantt chart visualization.

### Option 2: API Only

```bash
python3 run_server.py
```

Server runs on `http://localhost:8000`

### Option 3: API via cURL

```bash
curl -X POST http://localhost:8000/schedule \
  -H "Content-Type: application/json" \
  -d @examples/sample_input.json
```

API Documentation: `http://localhost:8000/docs`

## Input Format

```json
{
  "horizon": {
    "start": "2025-11-03T08:00:00",
    "end": "2025-11-03T16:00:00"
  },
  "resources": [
    {
      "id": "Fill-1",
      "capabilities": ["fill"],
      "calendar": [
        ["2025-11-03T08:00:00", "2025-11-03T12:00:00"],
        ["2025-11-03T12:30:00", "2025-11-03T16:00:00"]
      ]
    }
  ],
  "products": [
    {
      "id": "P-100",
      "family": "standard",
      "due": "2025-11-03T12:30:00",
      "route": [
        {"capability": "fill", "duration_minutes": 30},
        {"capability": "label", "duration_minutes": 20}
      ]
    }
  ],
  "changeover_matrix_minutes": {
    "values": {
      "standard->premium": 20,
      "premium->standard": 20
    }
  },
  "settings": {
    "time_limit_seconds": 30
  }
}
```

## Output Format

```json
{
  "assignments": [
    {
      "product": "P-100",
      "op": "fill",
      "resource": "Fill-1",
      "start": "2025-11-03T08:00:00",
      "end": "2025-11-03T08:30:00"
    }
  ],
  "kpis": {
    "tardiness_minutes": 0,
    "changeovers": 2,
    "makespan_minutes": 420,
    "utilization": {
      "Fill-1": 58,
      "Label-1": 49
    }
  }
}
```


## Architecture

```
src/
├── api/           # FastAPI endpoint
├── adapters/      # Multi-tenant format converters
├── models/        # Pydantic CDM schemas
├── solver/        # CP-SAT constraint engine
├── validation/    # Constraint checks & KPIs
└── utils/         # Time conversion utilities

frontend/
└── src/
    ├── components/  # React UI components
    └── App.jsx      # Main application
```

## Solver Approach

Uses constraint programming (CP-SAT) to minimize total tardiness while enforcing:
- No resource overlap
- Operation precedence
- Calendar compliance
- Capability matching

Time values converted to integer minutes for solver efficiency.

## Multi-Tenant Support

The system supports multiple client input formats through adapters:

- **Client A (Canonical)**: Direct CDM format (shown above)
- **Client B (Legacy ERP)**: Different date formats, flat structure (auto-detected)

See [docs/architecture.md](docs/architecture.md) for adapter design and offline-first patterns.

## Testing

```bash
# All tests
pytest tests/ -v

# Integration test with sample input
python3 validate_schedule.py examples/sample_input.json examples/sample_output.json
```

## What I'd Do Next

### Immediate (hours)
- **Explicit changeover intervals**: Model setup time as actual decision variables instead of post-hoc calculation
- **Unsat core analysis**: Use CP-SAT's conflict detection to pinpoint exact infeasibility reasons
- **Performance profiling**: Optimize for 100+ products using search hints and variable ordering

### Short-term (days)
- **Alternative objectives**: Add minimize-changeovers mode, weighted multi-objective optimization
- **Frozen zones**: Lock first N hours of schedule, only optimize remainder
- **Warm starts**: Cache and reuse good solutions for similar problem instances
- **Multi-attribute changeovers**: Support changeover matrices with color, size, etc.

### Long-term (weeks)
- **Rolling horizon**: Re-optimize as new orders arrive and disruptions occur
- **What-if analysis**: Compare multiple scenarios before committing
- **ML integration**: Learn actual durations, predict delays, suggest constraint relaxations
- **Cloud analytics**: Aggregate KPIs across sites, identify systemic bottlenecks
