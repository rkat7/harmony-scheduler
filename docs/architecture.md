# Architecture Design Document

## Executive Summary

This document describes the multi-tenant architecture for Harmony's production scheduler, supporting diverse client input formats while maintaining a single core solver engine. The design emphasizes separation of concerns, extensibility, and offline-first operation for factory sites with unreliable connectivity.

---

## 1. Canonical Data Model (CDM)

### 1.1 Core Types

The CDM serves as the "gold standard" internal representation that all client formats are transformed into before reaching the solver.

#### Horizon
```python
class Horizon:
    start: datetime      # Scheduling window start (UTC)
    end: datetime        # Scheduling window end (UTC)
```

**Purpose**: Defines the time bounds for all scheduling operations.

#### Resource
```python
class Resource:
    id: str                                    # Unique identifier (e.g., "Fill-1")
    capabilities: List[str]                    # Operations this resource can perform
    calendar: List[Tuple[datetime, datetime]]  # Working windows (breaks handled here)
```

**Purpose**: Represents factory equipment with specific capabilities and availability patterns.

**Calendar Representation**: List of time windows when resource is available. Gaps represent breaks, maintenance, or shifts. This handles arbitrary patterns without complex rules.

Example:
```python
# Resource with lunch break
calendar = [
    (datetime(2025, 11, 3, 8, 0), datetime(2025, 11, 3, 12, 0)),   # Morning shift
    (datetime(2025, 11, 3, 12, 30), datetime(2025, 11, 3, 16, 0))  # Afternoon shift
]
```

#### Operation
```python
class Operation:
    capability: str        # Required capability (e.g., "fill", "label")
    duration_minutes: int  # How long this step takes
```

**Purpose**: Single step in a product's route.

#### Product
```python
class Product:
    id: str                  # Order identifier
    family: str              # Product family (for changeovers)
    due: datetime            # Target completion time
    route: List[Operation]   # Ordered sequence of operations
```

**Purpose**: Represents a customer order with its processing requirements.

**Route**: Strict sequence of operations. Precedence is implicit from list order.

#### ChangeoverMatrix
```python
class ChangeoverMatrix:
    values: Dict[str, int]  # "family1->family2" : minutes

    def get_changeover_time(from_family: str, to_family: str) -> int
```

**Purpose**: Lookup table for setup times between product families.

**Key Format**: `"standard->premium"` maps to minutes required.

**Defaults**: Missing entries default to 0 (no changeover needed).

#### Settings
```python
class Settings:
    time_limit_seconds: int = 30  # Solver timeout
```

**Purpose**: Configurable solver parameters.

#### ScheduleRequest
```python
class ScheduleRequest:
    horizon: Horizon
    resources: List[Resource]
    products: List[Product]
    changeover_matrix_minutes: ChangeoverMatrix
    settings: Settings
```

**Purpose**: Complete input to solver. All clients must produce this structure.

### 1.2 Required vs Optional Fields

| Field | Required | Default | Notes |
|-------|----------|---------|-------|
| `horizon.start` | Yes | - | Must be before `end` |
| `horizon.end` | Yes | - | - |
| `resource.id` | Yes | - | Must be unique |
| `resource.capabilities` | Yes | - | Must be non-empty |
| `resource.calendar` | Yes | - | Can be empty list (resource never available) |
| `product.route` | Yes | - | Must be non-empty |
| `changeover_matrix.values` | No | `{}` | Empty means no changeovers |
| `settings.time_limit_seconds` | No | `30` | - |

### 1.3 Design Rationale

**Why not use Client A's format as CDM?**
- Client A format happens to align well, but tying CDM to any specific client creates coupling
- Future clients may have features that require CDM evolution
- CDM should represent domain concepts, not client quirks

**Why datetime instead of timestamps?**
- Type safety: Pydantic validates ISO strings automatically
- Timezone handling: Explicit UTC storage
- Human readable: Easier debugging

**Why separate Operation from route?**
- Enables operation reuse across products
- Clear schema validation
- Simpler serialization

---

## 2. Multi-Tenant Ingestion Strategy

### 2.1 Adapter Pattern Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                     │
│                    POST /schedule endpoint                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
                  ┌────────────────────┐
                  │  Adapter Factory   │
                  │  - Auto-detection  │
                  │  - Explicit routing│
                  └──────┬─────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
  ┌────────────┐  ┌────────────┐  ┌────────────┐
  │  Client A  │  │  Client B  │  │  Client C  │
  │  Adapter   │  │  Adapter   │  │  Adapter   │
  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
        │               │               │
        └───────────────┼───────────────┘
                        │
                        ▼
               ┌─────────────────┐
               │       CDM       │
               │ ScheduleRequest │
               └────────┬────────┘
                        │
                        ▼
               ┌─────────────────┐
               │  Core Solver    │
               │  (OR-Tools)     │
               └────────┬────────┘
                        │
                        ▼
               ┌─────────────────┐
               │ ScheduleResponse│
               └─────────────────┘
```

### 2.2 Base Adapter Interface

```python
class ScheduleAdapter(ABC):
    @abstractmethod
    def to_cdm(self, raw_input: Dict[str, Any]) -> ScheduleRequest:
        """Transform client format to CDM."""
        pass

    @property
    @abstractmethod
    def client_id(self) -> str:
        """Unique identifier for this client."""
        pass
```

**Key Benefits**:
- Each client's transformation logic is isolated
- Core solver never sees client-specific formats
- New clients don't require solver changes

### 2.3 Client A Adapter

Client A's format already closely matches CDM:

```python
class ClientAAdapter(ScheduleAdapter):
    def to_cdm(self, raw_input: Dict[str, Any]) -> ScheduleRequest:
        return ScheduleRequest(**raw_input)  # Direct passthrough
```

Minimal transformation needed. Main value is explicit interface compliance.

### 2.4 Client B Adapter

Client B has legacy ERP format requiring significant transformation:

**Input Differences**:
| Client B | CDM | Transformation |
|----------|-----|----------------|
| `shift_window: "11/03/2025 08:00 - 16:00"` | `horizon: {start, end}` | Parse MM/DD/YYYY, split range |
| `orders` | `products` | Rename + restructure |
| `machines: ["Fill-1"]` | `resources` | Infer capabilities from name prefix |
| `machine_breaks` | `resource.calendar` | Build windows around breaks |
| `deadline_hour: 15.0` | `due: datetime` | Convert decimal hour to timestamp |
| `operations: [{step, type, minutes}]` | `route` | Sort by step, rename fields |

**Implementation Highlights**:

```python
class ClientBAdapter(ScheduleAdapter):
    def to_cdm(self, raw_input):
        return ScheduleRequest(
            horizon=self._parse_horizon(raw_input["shift_window"]),
            resources=self._parse_resources(raw_input["machines"], raw_input["machine_breaks"]),
            products=self._parse_products(raw_input["orders"]),
            changeover_matrix_minutes=self._parse_changeover_matrix(raw_input["setup_times"])
        )

    def _parse_horizon(self, shift_window: str) -> Horizon:
        # "11/03/2025 08:00 - 16:00" -> Horizon(start, end)
        ...

    def _parse_resources(self, machines, breaks) -> List[Resource]:
        # Infer capabilities, build calendars
        ...
```

**Calendar Construction**:
```python
# No breaks → Full shift
calendar = [(horizon.start, horizon.end)]

# With breaks → Split around them
breaks = [{"machine": "Fill-1", "start": "12:00", "end": "12:30"}]
# Results in:
calendar = [
    (08:00, 12:00),  # Before break
    (12:30, 16:00)   # After break
]
```

### 2.5 Adapter Factory

Supports two routing strategies:

**Strategy 1: Explicit Client ID**
```python
{
  "client_id": "client_b",
  "shift_window": "...",
  ...
}
```

Factory extracts `client_id` and routes to registered adapter.

**Strategy 2: Schema Fingerprinting**
```python
def _detect_adapter(self, raw_input):
    if "shift_window" in raw_input and "orders" in raw_input:
        return ClientBAdapter()

    if "horizon" in raw_input and "products" in raw_input:
        return ClientAAdapter()

    raise ValueError("Unknown format")
```

**Detection Rules**:
- Client A: Has `horizon` + `products`
- Client B: Has `shift_window` + `orders`
- Client C: Custom logic (e.g., check for specific vendor fields)

**Why fingerprinting?**
- Allows backward compatibility when clients can't add `client_id`
- Graceful handling of evolving schemas
- Fallback when explicit routing unavailable

### 2.6 Adding Client C

**Scenario**: New client with XML format converted to JSON.

**Steps**:
1. Create `ClientCAdapter(ScheduleAdapter)`
2. Implement `to_cdm()` with client-specific logic
3. Register with factory:
```python
factory = AdapterFactory()
factory.register_adapter(ClientCAdapter())
```

**What changes**:
- New file: `src/adapters/client_c.py`
- New test: `tests/test_adapters.py::test_client_c_adapter`

**What stays the same**:
- Core solver (`src/solver/engine.py`) - **unchanged**
- CDM models - **unchanged** (unless Client C needs new domain concepts)
- Validation logic - **unchanged**
- API endpoint - **unchanged**

**Testing Strategy**:
```python
def test_client_c_adapter():
    adapter = ClientCAdapter()
    request = adapter.to_cdm(client_c_sample_data)

    # Verify transformation correctness
    assert request.products[0].id == "expected_value"

    # Ensure solver can handle it
    result = solve_schedule(request)
    assert isinstance(result, ScheduleResponse)
```

---

## 3. Offline-First Architecture

### 3.1 Problem Statement

Many factory sites have:
- Intermittent internet connectivity (4G cellular, rural locations)
- Security restrictions (air-gapped networks)
- Need for real-time scheduling even when cloud is unreachable

**Requirements**:
1. Full scheduling capability when offline
2. Data persistence across restarts
3. Eventual sync with cloud when online
4. Conflict resolution for concurrent edits
5. Graceful degradation (no analytics, no cross-site optimization)

### 3.2 Component Distribution

```
┌────────────────────────────────────────────────────────────┐
│                    FACTORY SITE (ON-PREMISE)               │
│                                                            │
│  ┌──────────────┐      ┌────────────────────────┐        │
│  │  Local ERP/  │─────▶│  Edge API (FastAPI)    │        │
│  │     UI       │      │  - All adapters        │        │
│  └──────────────┘      │  - Full solver         │        │
│                        │  - Validation          │        │
│                        └───────┬────────────────┘        │
│                                │                          │
│                        ┌───────▼────────────────┐        │
│                        │  SQLite / DuckDB       │        │
│                        │  - Schedule history    │        │
│                        │  - Pending sync queue  │        │
│                        └───────┬────────────────┘        │
│                                │                          │
│                        ┌───────▼────────────────┐        │
│                        │  Sync Agent (Background)│       │
│                        │  - Monitors connectivity│       │
│                        │  - Pushes when online   │       │
│                        └───────┬────────────────┘        │
└────────────────────────────────┼────────────────────────┘
                                 │ HTTPS (when available)
                                 │
┌────────────────────────────────▼────────────────────────┐
│                     HARMONY CLOUD (CENTRAL)             │
│                                                         │
│  ┌────────────────────────────────────────────┐        │
│  │  Cloud API (FastAPI)                       │        │
│  │  - Ingests synced data from all sites      │        │
│  └─────────────────┬──────────────────────────┘        │
│                    │                                    │
│  ┌─────────────────▼──────────────────────────┐        │
│  │  PostgreSQL (Multi-Tenant)                 │        │
│  │  - Historical schedules across all sites   │        │
│  │  - Aggregate KPIs                          │        │
│  └─────────────────┬──────────────────────────┘        │
│                    │                                    │
│  ┌─────────────────▼──────────────────────────┐        │
│  │  Analytics Dashboard                       │        │
│  │  - Cross-site bottleneck analysis          │        │
│  │  - Trend detection                         │        │
│  │  - ML-powered suggestions                  │        │
│  └────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
```

### 3.3 Local Storage (Edge)

**Technology**: SQLite or DuckDB

**Why SQLite?**
- Zero configuration
- Single file database (easy backup)
- Embedded in application
- ACID transactions
- Good performance for <100k rows

**Schema**:
```sql
CREATE TABLE schedules (
    id TEXT PRIMARY KEY,
    site_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    input_json TEXT NOT NULL,      -- ScheduleRequest
    output_json TEXT,               -- ScheduleResponse
    status TEXT,                    -- 'pending', 'solved', 'failed'
    synced BOOLEAN DEFAULT FALSE,
    synced_at TIMESTAMP
);

CREATE TABLE sync_queue (
    event_id TEXT PRIMARY KEY,
    schedule_id TEXT REFERENCES schedules(id),
    event_type TEXT,                -- 'schedule_created', 'schedule_updated'
    payload TEXT,                   -- JSON event data
    created_at TIMESTAMP,
    retry_count INTEGER DEFAULT 0
);
```

**What's Stored**:
- Every schedule request and result
- Sync queue (events waiting to push to cloud)
- Local configuration (adapters, resource definitions)

### 3.4 Sync Strategy

**Architecture**: Event Sourcing + Append-Only Log

**Core Concept**: Every action is an immutable event. Sync is replaying events to cloud.

**Event Types**:
```python
ScheduleCreatedEvent:
    - event_id: UUID
    - site_id: str
    - schedule_id: str
    - request: ScheduleRequest
    - result: ScheduleResponse
    - timestamp: datetime

ScheduleUpdatedEvent:
    - event_id: UUID
    - schedule_id: str
    - changes: Dict
    - timestamp: datetime
```

**Sync Process**:
```python
class SyncAgent:
    def run_sync_cycle(self):
        if not self.is_online():
            return  # Skip if offline

        # Get pending events
        events = self.db.get_unsync_events(limit=100)

        for event in events:
            try:
                response = requests.post(
                    f"{CLOUD_API}/sync/events",
                    json=event.to_dict(),
                    timeout=10
                )

                if response.ok:
                    self.db.mark_synced(event.event_id)
                else:
                    self.db.increment_retry(event.event_id)

            except requests.ConnectionError:
                break  # Stop and retry later
```

**Sync Frequency**:
- Every 5 minutes when online
- Immediate retry after connectivity restored
- Exponential backoff for failed events

### 3.5 Conflict Resolution

**Scenario**: Two users modify the same schedule while offline.

**Strategy**: Last-Write-Wins (LWW) with Timestamp

```python
def resolve_conflict(local_event, cloud_event):
    if local_event.timestamp > cloud_event.timestamp:
        return local_event  # Local is newer
    else:
        return cloud_event  # Cloud is newer
```

**Why LWW?**
- Simple to implement and reason about
- Acceptable for scheduling domain (no strong consistency needs)
- Users are notified if their changes were overwritten

**Alternative Strategies**:
- **Site-Local Wins**: Factory always takes precedence (good for autonomy)
- **Manual Merge**: Flag conflicts for human resolution
- **CRDTs**: Complex but allows true concurrent editing

**Chosen**: Site-Local Wins for production schedules (factory has authority)

### 3.6 Offline Capabilities

**What Works Offline**:
- ✅ Full scheduling (all adapters, solver, validation)
- ✅ View past schedules
- ✅ Generate reports
- ✅ Local KPI calculation
- ✅ Export to CSV/JSON

**What Degrades Gracefully**:
- ❌ Cloud analytics (trend charts, cross-site comparisons)
- ❌ Remote monitoring (central dashboard shows site as offline)
- ❌ ML suggestions (requires cloud-trained models)
- ⚠️ Software updates (download when online, apply on restart)

**User Experience**:
```
┌────────────────────────────────────────┐
│  🔴 OFFLINE MODE                       │
│  Last synced: 2 hours ago              │
│                                        │
│  All scheduling functions available    │
│  Cloud analytics unavailable           │
│                                        │
│  [View Pending Changes (12)]          │
└────────────────────────────────────────┘
```

### 3.7 Data Loss Prevention

**Mechanisms**:

1. **WAL Mode** (Write-Ahead Logging):
```python
sqlite_conn.execute("PRAGMA journal_mode=WAL")
```
Protects against corruption during power loss.

2. **Periodic Backups**:
```bash
# Cron job every 6 hours
sqlite3 harmony.db ".backup harmony_backup_$(date +%Y%m%d_%H%M%S).db"
```

3. **Event Log Retention**:
```python
# Keep events for 30 days even after sync
DELETE FROM sync_queue
WHERE synced = TRUE
  AND synced_at < NOW() - INTERVAL '30 days'
```

4. **Cloud Replication**:
Once synced, cloud has copy. If site loses all data, re-download from cloud.

---

## 4. Testing Multi-Tenant System

### 4.1 Unit Tests (Adapters)

```python
def test_client_b_transforms_correctly():
    adapter = ClientBAdapter()
    raw = load_fixture("client_b_sample.json")
    request = adapter.to_cdm(raw)

    assert request.horizon.start == expected_start
    assert len(request.products) == 2
```

### 4.2 Integration Tests (End-to-End)

```python
def test_client_b_solves_successfully():
    factory = AdapterFactory()
    raw = load_fixture("client_b_sample.json")

    adapter = factory.get_adapter(raw)
    request = adapter.to_cdm(raw)
    result = solve_schedule(request)

    assert isinstance(result, ScheduleResponse)
    validate_schedule(request, result.assignments)
```

### 4.3 Contract Tests (Schema Validation)

```python
@pytest.mark.parametrize("client_fixture", [
    "client_a_sample.json",
    "client_b_sample.json",
    "client_c_sample.json"
])
def test_all_clients_produce_valid_cdm(client_fixture):
    factory = AdapterFactory()
    raw = load_fixture(client_fixture)

    adapter = factory.get_adapter(raw)
    request = adapter.to_cdm(raw)

    # Pydantic validation ensures CDM compliance
    assert isinstance(request, ScheduleRequest)
```

### 4.4 Consistency Tests (Same Problem, Different Formats)

```python
def test_client_a_and_b_yield_same_schedule():
    # Same factory scenario in two formats
    client_a_input = load_fixture("scenario_1_client_a.json")
    client_b_input = load_fixture("scenario_1_client_b.json")

    result_a = solve_with_adapter(client_a_input)
    result_b = solve_with_adapter(client_b_input)

    # Should have same tardiness (solver is deterministic)
    assert result_a.kpis.tardiness_minutes == result_b.kpis.tardiness_minutes
```

---

## 5. Future Extensions

### 5.1 Adding Client D (Hypothetical)

**Scenario**: Client D sends data via gRPC with Protobuf encoding.

**Implementation**:
```python
class ClientDAdapter(ScheduleAdapter):
    def to_cdm(self, raw_input: Dict[str, Any]) -> ScheduleRequest:
        # raw_input is already parsed protobuf -> dict
        return ScheduleRequest(
            horizon=self._parse_protobuf_horizon(raw_input["time_range"]),
            resources=self._parse_protobuf_resources(raw_input["machines"]),
            ...
        )
```

**API Layer**:
```python
@app.post("/schedule/protobuf")
async def schedule_protobuf(request: Request):
    body = await request.body()
    proto_msg = ScheduleRequestProto.FromString(body)
    raw_dict = proto_to_dict(proto_msg)

    adapter = ClientDAdapter()
    cdm_request = adapter.to_cdm(raw_dict)
    return solve_schedule(cdm_request)
```

**No changes to**: Solver, CDM, validation, KPIs.

### 5.2 Intelligent Scheduler Add-On

**Integration Points**:

1. **Natural Language → CDM**:
```python
User: "We have a maintenance window for Fill-1 from 1pm to 2pm"

NL Processor (LLM):
    → Parse intent: "add calendar break"
    → Extract entities: resource="Fill-1", start=13:00, end=14:00
    → Update CDM:
        request.resources["Fill-1"].calendar.insert(break_window)
```

2. **Conversational Updates**:
```python
User: "P-100 needs to be done earlier, try for 11am"

NL Processor:
    → Identify product: P-100
    → Parse constraint: due = 11:00
    → Re-solve with updated due date
```

3. **Implementation**:
```python
class NLAdapter(ScheduleAdapter):
    def __init__(self, llm_client):
        self.llm = llm_client

    def to_cdm(self, user_message: str, current_schedule: ScheduleRequest) -> ScheduleRequest:
        # LLM extracts structured updates
        updates = self.llm.extract_schedule_changes(user_message)

        # Apply updates to existing CDM
        modified_schedule = apply_updates(current_schedule, updates)
        return modified_schedule
```

**Why This Fits CDM**:
- NL is just another input format
- LLM produces CDM updates
- Core solver unchanged

---

## 6. Deployment Topologies

### 6.1 Cloud-Only (Client A)

Client A has reliable internet and prefers SaaS.

```
Client A ERP → HTTPS → Harmony Cloud API → Solver → Response
```

**Characteristics**:
- Centralized
- Auto-updates
- Cloud analytics available
- Requires internet

### 6.2 Edge + Cloud (Client B)

Client B has factory sites with poor connectivity.

```
Factory UI → Edge API (on-premise) → Local SQLite
                ↓ (when online)
            Cloud API → PostgreSQL → Analytics
```

**Characteristics**:
- Offline-capable
- Local data sovereignty
- Cloud sync for analytics
- Hybrid model

### 6.3 Fully Offline (Client C)

Client C has air-gapped network (defense contractor).

```
Factory UI → Edge API (isolated) → Local DB
     ↓
Manual export to USB → Transferred to analytics network
```

**Characteristics**:
- No automatic sync
- Manual data transfer
- Full local control
- Delayed analytics

---

## 7. Summary

### Architecture Principles

1. **Separation of Concerns**: Adapters ↔ CDM ↔ Solver
2. **Extensibility**: New clients via adapter pattern
3. **Offline-First**: Full capability without cloud
4. **Event Sourcing**: Reliable sync with append-only log
5. **Type Safety**: Pydantic validates all boundaries

### Key Decisions

| Decision | Choice | Alternative | Rationale |
|----------|--------|-------------|-----------|
| Adapter pattern | Yes | If-else in solver | Clean separation, extensible |
| Auto-detection | Yes | Require client_id | Backward compatibility |
| Local DB | SQLite | PostgreSQL | Embedded, zero config |
| Sync model | Event sourcing | Polling | Reliable, no data loss |
| Conflict resolution | LWW | CRDTs | Simple, fits domain |

### What's Implemented

✅ Canonical Data Model (Pydantic)
✅ Client A Adapter (passthrough)
✅ Client B Adapter (full transformation)
✅ Adapter Factory (detection + routing)
✅ Tests (6 new tests, all passing)

### What's Designed (Not Implemented)

📋 Offline-first edge deployment
📋 SQLite event log
📋 Sync agent
📋 Cloud analytics dashboard
📋 NL integration
