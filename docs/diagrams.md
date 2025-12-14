# Architecture Diagrams

## 1. Multi-Tenant Data Flow

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  Client A   │      │  Client B   │      │  Client C   │
│   (JSON)    │      │  (Legacy)   │      │  (Future)   │
└──────┬──────┘      └──────┬──────┘      └──────┬──────┘
       │                    │                    │
       │  HTTP POST         │  HTTP POST         │  HTTP POST
       │  /schedule         │  /schedule         │  /schedule
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │   Adapter Factory     │
                │                       │
                │ if "orders" → Client B│
                │ if "products"→Client A│
                │ if "client_id" → Exact│
                └───────────┬───────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
    ┌──────────┐      ┌──────────┐      ┌──────────┐
    │ Client A │      │ Client B │      │ Client C │
    │ Adapter  │      │ Adapter  │      │ Adapter  │
    └────┬─────┘      └────┬─────┘      └────┬─────┘
         │                 │                  │
         │   to_cdm()      │   to_cdm()       │   to_cdm()
         │                 │                  │
         └─────────────────┼──────────────────┘
                           │
                           ▼
                   ┌───────────────┐
                   │      CDM      │
                   │ScheduleRequest│
                   └───────┬───────┘
                           │
                           ▼
                   ┌───────────────┐
                   │ Core Solver   │
                   │  (OR-Tools)   │
                   │               │
                   │ - Constraints │
                   │ - Objective   │
                   │ - Search      │
                   └───────┬───────┘
                           │
                           ▼
                   ┌───────────────┐
                   │   Validation  │
                   │   & KPIs      │
                   └───────┬───────┘
                           │
                           ▼
                   ┌───────────────┐
                   │ScheduleResponse│
                   │               │
                   │ - assignments │
                   │ - kpis        │
                   └───────────────┘
```

## 2. Offline-First Architecture

```
┌───────────────────────────────────────────────────────────┐
│                  FACTORY SITE (Edge)                      │
│                                                           │
│  ┌──────────────┐                                        │
│  │  Local ERP   │                                        │
│  │  or Web UI   │                                        │
│  └──────┬───────┘                                        │
│         │ HTTP                                           │
│         ▼                                                 │
│  ┌───────────────────────────────┐                      │
│  │  Edge API (FastAPI)           │                      │
│  │  - Adapters (A, B, C)         │                      │
│  │  - Core Solver                │                      │
│  │  - Validation                 │                      │
│  │  Port: 8000                   │                      │
│  └──────┬────────────────────────┘                      │
│         │                                                 │
│         ▼                                                 │
│  ┌───────────────────────────────┐                      │
│  │  SQLite Database              │                      │
│  │                               │                      │
│  │  schedules:                   │                      │
│  │  - id, input, output, synced  │                      │
│  │                               │                      │
│  │  sync_queue:                  │                      │
│  │  - event_id, payload, retry   │                      │
│  └──────┬────────────────────────┘                      │
│         │                                                 │
│         ▼                                                 │
│  ┌───────────────────────────────┐                      │
│  │  Sync Agent (Background)      │                      │
│  │                               │                      │
│  │  while True:                  │                      │
│  │    if online:                 │                      │
│  │      push_events()            │                      │
│  │    sleep(5 min)               │                      │
│  └──────┬────────────────────────┘                      │
│         │                                                 │
└─────────┼───────────────────────────────────────────────┘
          │
          │ HTTPS (when available)
          │ POST /sync/events
          │
┌─────────▼───────────────────────────────────────────────┐
│              HARMONY CLOUD (Central)                    │
│                                                         │
│  ┌────────────────────────────────────────┐            │
│  │  Cloud API                             │            │
│  │  - POST /sync/events                   │            │
│  │  - GET /analytics/site/:id             │            │
│  └─────────┬──────────────────────────────┘            │
│            │                                            │
│            ▼                                            │
│  ┌────────────────────────────────────────┐            │
│  │  PostgreSQL (Multi-Tenant)             │            │
│  │                                        │            │
│  │  events:                               │            │
│  │  - event_id, site_id, type, payload    │            │
│  │                                        │            │
│  │  schedules:                            │            │
│  │  - id, site_id, created_at, kpis       │            │
│  └─────────┬──────────────────────────────┘            │
│            │                                            │
│            ▼                                            │
│  ┌────────────────────────────────────────┐            │
│  │  Analytics Dashboard                   │            │
│  │                                        │            │
│  │  - Tardiness trends                    │            │
│  │  - Cross-site comparison               │            │
│  │  - Bottleneck detection                │            │
│  │  - ML predictions                      │            │
│  └────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────┘
```

## 3. Client B Adapter Transformation

```
┌──────────────────────────────────────┐
│      Client B Input (Legacy)         │
├──────────────────────────────────────┤
│ {                                    │
│   "shift_window":                    │
│     "11/03/2025 08:00 - 16:00",     │
│                                      │
│   "machines": ["Fill-1", "Label-1"], │
│                                      │
│   "machine_breaks": [                │
│     {"machine": "Fill-1",            │
│      "start": "12:00",               │
│      "end": "12:30"}                 │
│   ],                                 │
│                                      │
│   "orders": [                        │
│     {                                │
│       "order_id": "ORD-100",         │
│       "product_family": "standard",  │
│       "deadline_hour": 15.0,         │
│       "operations": [                │
│         {"step": 1, "type": "fill",  │
│          "minutes": 30}              │
│       ]                              │
│     }                                │
│   ]                                  │
│ }                                    │
└─────────────┬────────────────────────┘
              │
              │ ClientBAdapter.to_cdm()
              │
              ├─► _parse_horizon()
              │   "11/03/2025 08:00 - 16:00"
              │   → Horizon(start=datetime(...), end=datetime(...))
              │
              ├─► _parse_resources()
              │   "Fill-1" → capability="fill" (infer from name)
              │   break 12:00-12:30 → calendar=[(08:00, 12:00), (12:30, 16:00)]
              │
              ├─► _parse_products()
              │   "order_id" → "id"
              │   "deadline_hour" 15.0 → due=datetime(hour=15, min=0)
              │   operations sorted by step → route
              │
              ├─► _parse_changeover_matrix()
              │   setup_times → values dict
              │
              ▼
┌──────────────────────────────────────┐
│      Canonical Data Model (CDM)      │
├──────────────────────────────────────┤
│ ScheduleRequest(                     │
│   horizon=Horizon(                   │
│     start=datetime(2025,11,3,8,0),   │
│     end=datetime(2025,11,3,16,0)     │
│   ),                                 │
│   resources=[                        │
│     Resource(                        │
│       id="Fill-1",                   │
│       capabilities=["fill"],         │
│       calendar=[                     │
│         (datetime(8:00), datetime(12:00)),│
│         (datetime(12:30), datetime(16:00))│
│       ]                              │
│     )                                │
│   ],                                 │
│   products=[                         │
│     Product(                         │
│       id="ORD-100",                  │
│       family="standard",             │
│       due=datetime(2025,11,3,15,0),  │
│       route=[                        │
│         Operation(capability="fill", │
│                   duration_minutes=30)│
│       ]                              │
│     )                                │
│   ]                                  │
│ )                                    │
└──────────────────────────────────────┘
```

## 4. Event Sourcing Sync Flow

```
┌─────────────────────────────────────────────┐
│  Edge: User creates schedule                │
└─────────────┬───────────────────────────────┘
              │
              ▼
      ┌───────────────────┐
      │  Solve schedule   │
      └────────┬──────────┘
               │
               ▼
      ┌──────────────────────────────────┐
      │  Store in SQLite:                │
      │  schedules table                 │
      │  {id, input, output, synced=false}│
      └────────┬─────────────────────────┘
               │
               ▼
      ┌──────────────────────────────────┐
      │  Create event:                   │
      │  sync_queue table                │
      │  {event_id, type='created',      │
      │   payload={schedule}, retry=0}   │
      └────────┬─────────────────────────┘
               │
               ▼
      ┌──────────────────────────────────┐
      │  Sync Agent wakes up (5 min)     │
      └────────┬─────────────────────────┘
               │
               ├──► Check connectivity
               │    ├─► Offline? → sleep, try later
               │    └─► Online? → continue
               │
               ▼
      ┌──────────────────────────────────┐
      │  Fetch unsync events (limit 100) │
      └────────┬─────────────────────────┘
               │
               │ for each event:
               ▼
      ┌──────────────────────────────────┐
      │  POST /sync/events               │
      │  {event_id, site_id, payload}    │
      └────────┬─────────────────────────┘
               │
               ├──► Success?
               │    ├─► Yes → mark_synced(event_id)
               │    └─► No → increment_retry(event_id)
               │
               ▼
      ┌──────────────────────────────────┐
      │  Cloud stores event:             │
      │  events table                    │
      │  {event_id, site_id, timestamp}  │
      └────────┬─────────────────────────┘
               │
               ▼
      ┌──────────────────────────────────┐
      │  Cloud materializes schedule:    │
      │  schedules table                 │
      │  (for analytics queries)         │
      └──────────────────────────────────┘
```

## 5. Adding Client C (Extensibility)

```
┌────────────────────────────────────────────────────┐
│  Step 1: Implement ClientCAdapter                  │
├────────────────────────────────────────────────────┤
│  class ClientCAdapter(ScheduleAdapter):            │
│      def to_cdm(self, raw_input):                  │
│          # Custom transformation logic             │
│          return ScheduleRequest(...)               │
└────────────────────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────┐
│  Step 2: Register with factory                     │
├────────────────────────────────────────────────────┤
│  factory = AdapterFactory()                        │
│  factory.register_adapter(ClientCAdapter())        │
└────────────────────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────┐
│  Step 3: Add detection rule (optional)             │
├────────────────────────────────────────────────────┤
│  def _detect_adapter(self, raw_input):             │
│      if "client_c_indicator" in raw_input:         │
│          return ClientCAdapter()                   │
└────────────────────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────┐
│  NO CHANGES NEEDED:                                │
│  ✓ Core Solver                                     │
│  ✓ CDM Models                                      │
│  ✓ Validation                                      │
│  ✓ KPI Calculation                                 │
│  ✓ API Endpoint                                    │
└────────────────────────────────────────────────────┘
```
