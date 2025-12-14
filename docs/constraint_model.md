# Constraint Model Documentation

## Overview

This scheduler solves a multi-resource job-shop scheduling problem with precedence constraints, resource calendars, and family-based changeovers. The implementation uses Google OR-Tools CP-SAT solver.

## Decision Variables

For each operation `i` in the schedule:

- **`start[i]`**: Integer variable representing start time (minutes from horizon start)
  - Domain: `[horizon_start, horizon_end]`

- **`end[i]`**: Integer variable representing end time (minutes from horizon start)
  - Domain: `[horizon_start, horizon_end]`

- **`resource[i]`**: Integer variable representing assigned resource index
  - Domain: Indices of resources with required capability

- **`interval[i, r]`**: Optional interval variable for each resource `r`
  - Active only when operation `i` is assigned to resource `r`
  - Used for no-overlap constraints

- **`is_assigned[i, r]`**: Boolean variable
  - True if operation `i` is assigned to resource `r`
  - Exactly one must be true per operation

## Hard Constraints

### 1. Duration Constraint
```
end[i] = start[i] + duration[i]
```
Each operation takes exactly its specified duration.

### 2. Precedence Constraint
```
start[next_op] >= end[prev_op]
```
For operations in the same product's route, later operations cannot start until earlier ones complete.

### 3. Resource Capability
```
resource[i] ∈ eligible_resources[capability[i]]
```
Operations can only be assigned to resources with the required capability.

### 4. No Overlap
```
NoOverlap(intervals on resource r) for all resources r
```
At most one operation can execute on a resource at any time.

### 5. Calendar Compliance
```
∃ window ∈ calendar[resource[i]] :
    start[i] >= window.start AND end[i] <= window.end
```
Operations must fit entirely within one of the resource's working windows.

### 6. Horizon Bounds
```
horizon_start <= start[i] < end[i] <= horizon_end
```
All times must fall within the scheduling horizon.

### 7. Exactly One Resource
```
sum(is_assigned[i, r] for r in eligible_resources) = 1
```
Each operation must be assigned to exactly one resource.

## Objective Function

**Minimize total tardiness:**

```
minimize: sum(max(0, completion_time[p] - due_time[p]) for p in products)
```

Where `completion_time[p]` is the end time of the last operation in product `p`'s route.

Tardiness is measured in minutes. Products completed before their due date contribute 0 to the objective.

## Changeover Handling

Changeovers are implicit in this model:
- When scheduling, the solver naturally minimizes tardiness
- Family transitions require setup time (from changeover matrix)
- This is currently enforced in KPI calculation but could be added as explicit constraints

**Future Enhancement**: Add explicit changeover intervals between operations of different families on the same resource.

## Implementation Notes

### Time Representation
- All times converted to integer minutes from horizon start
- Simplifies constraint arithmetic and solver performance
- Converted back to ISO datetime in output

### Resource Assignment
- Uses optional interval variables per resource
- Boolean channeling ensures exactly one resource selected
- Allows CP-SAT to efficiently handle resource allocation

### Calendar Windows
- For each assignment, solver ensures operation fits in at least one window
- Boolean OR over all windows for a resource
- Handles breaks, shifts, maintenance periods

## Assumptions

1. **No preemption**: Operations run to completion once started
2. **Fixed routes**: Product operation sequence is immutable
3. **Deterministic durations**: No uncertainty in operation times
4. **Infinite buffers**: No blocking between operations
5. **Family-based changeover**: Setup depends only on product families, not specific products
6. **No parallel operations**: Each product follows strictly sequential route

## Solver Parameters

- **Time limit**: Configurable (default 30 seconds)
- **Optimality**: Solver seeks optimal solution within time limit
- **Feasibility**: Returns first feasible solution if optimal not found
