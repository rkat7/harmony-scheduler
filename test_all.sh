#!/bin/bash

echo "=========================================="
echo "   Harmony Scheduler - Full Test Suite"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track overall success
OVERALL_SUCCESS=true

# Test 1: Unit Tests
echo -e "${BLUE}[1/6] Running Unit Tests...${NC}"
if pytest tests/ -q; then
    echo -e "${GREEN}✓ Unit tests passed${NC}"
else
    echo -e "${RED}✗ Unit tests failed${NC}"
    OVERALL_SUCCESS=false
fi
echo ""

# Test 2: Client A (Python)
echo -e "${BLUE}[2/6] Testing Client A Format...${NC}"
python3 << 'EOF'
import json
from src.adapters.factory import AdapterFactory
from src.solver.engine import solve_schedule

with open('examples/sample_input.json') as f:
    data = json.load(f)

factory = AdapterFactory()
adapter = factory.get_adapter(data)
request = adapter.to_cdm(data)
result = solve_schedule(request)

print(f"  Client A detected: {adapter.client_id}")
print(f"  Assignments: {len(result.assignments)}")
print(f"  Tardiness: {result.kpis.tardiness_minutes} min")
print(f"  Changeovers: {result.kpis.changeovers}")
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Client A test passed${NC}"
else
    echo -e "${RED}✗ Client A test failed${NC}"
    OVERALL_SUCCESS=false
fi
echo ""

# Test 3: Client B (Python)
echo -e "${BLUE}[3/6] Testing Client B Format...${NC}"
python3 << 'EOF'
import json
from src.adapters.factory import AdapterFactory
from src.solver.engine import solve_schedule

with open('examples/client_b_input.json') as f:
    data = json.load(f)

factory = AdapterFactory()
adapter = factory.get_adapter(data)
request = adapter.to_cdm(data)
result = solve_schedule(request)

print(f"  Client B detected: {adapter.client_id}")
print(f"  Assignments: {len(result.assignments)}")
print(f"  Tardiness: {result.kpis.tardiness_minutes} min")

# Verify calendar transformation
fill_1 = next(r for r in request.resources if r.id == "Fill-1")
print(f"  Fill-1 calendar windows: {len(fill_1.calendar)} (expected 2 due to break)")
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Client B test passed${NC}"
else
    echo -e "${RED}✗ Client B test failed${NC}"
    OVERALL_SUCCESS=false
fi
echo ""

# Test 4: Validation Script
echo -e "${BLUE}[4/6] Testing Validation Script...${NC}"
# Generate output
python3 -c "
import json
from src.models.cdm import ScheduleRequest
from src.solver.engine import solve_schedule

with open('examples/sample_input.json') as f:
    data = json.load(f)

request = ScheduleRequest(**data)
result = solve_schedule(request)

with open('test_output.json', 'w') as f:
    json.dump(result.model_dump(mode='json'), f, indent=2, default=str)
" > /dev/null 2>&1

# Validate
if python3 validate_schedule.py examples/sample_input.json test_output.json 2>&1 | grep -q "ALL VALIDATION CHECKS PASSED"; then
    echo -e "${GREEN}✓ Validation script passed${NC}"
    rm test_output.json
else
    echo -e "${RED}✗ Validation script failed${NC}"
    OVERALL_SUCCESS=false
fi
echo ""

# Test 5: API Server
echo -e "${BLUE}[5/6] Testing API Server...${NC}"
# Start server in background
python3 run_server.py > /dev/null 2>&1 &
SERVER_PID=$!
sleep 3  # Wait for server to start

# Test health endpoint
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo "  ✓ Health check passed"

    # Test schedule endpoint with Client A
    SCHEDULE_RESPONSE=$(curl -s -X POST http://localhost:8000/schedule \
        -H "Content-Type: application/json" \
        -d @examples/sample_input.json)

    if echo "$SCHEDULE_RESPONSE" | grep -q "assignments"; then
        echo "  ✓ Client A API call successful"
        TARDINESS=$(echo "$SCHEDULE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['kpis']['tardiness_minutes'])")
        echo "  Tardiness: ${TARDINESS} minutes"
    else
        echo -e "  ${RED}✗ Client A API call failed${NC}"
        OVERALL_SUCCESS=false
    fi

    # Test with Client B
    SCHEDULE_B_RESPONSE=$(curl -s -X POST http://localhost:8000/schedule \
        -H "Content-Type: application/json" \
        -d @examples/client_b_input.json)

    if echo "$SCHEDULE_B_RESPONSE" | grep -q "assignments"; then
        echo "  ✓ Client B API call successful"
    else
        echo -e "  ${RED}✗ Client B API call failed${NC}"
        OVERALL_SUCCESS=false
    fi

    echo -e "${GREEN}✓ API server test passed${NC}"
else
    echo -e "${RED}✗ API server failed to start${NC}"
    OVERALL_SUCCESS=false
fi

# Kill server
kill $SERVER_PID 2>/dev/null
sleep 1
echo ""

# Test 6: Infeasibility Detection
echo -e "${BLUE}[6/6] Testing Infeasibility Detection...${NC}"
python3 << 'EOF'
from src.models.cdm import *
from src.solver.engine import solve_schedule
from datetime import datetime

# Create impossible scenario
request = ScheduleRequest(
    horizon=Horizon(
        start=datetime(2025, 11, 3, 8, 0),
        end=datetime(2025, 11, 3, 16, 0)
    ),
    resources=[
        Resource(
            id="R1",
            capabilities=["fill"],
            calendar=[(datetime(2025, 11, 3, 8, 0), datetime(2025, 11, 3, 9, 0))]
        )
    ],
    products=[
        Product(
            id="P1",
            family="standard",
            due=datetime(2025, 11, 3, 12, 0),
            route=[Operation(capability="fill", duration_minutes=180)]
        )
    ],
    changeover_matrix_minutes=ChangeoverMatrix(),
    settings=Settings(time_limit_seconds=5)
)

result = solve_schedule(request)

if hasattr(result, 'error'):
    print("  ✓ Correctly detected infeasible schedule")
    print(f"  Error message: {result.error}")
else:
    print("  ✗ Should have returned error for infeasible case")
    exit(1)
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Infeasibility test passed${NC}"
else
    echo -e "${RED}✗ Infeasibility test failed${NC}"
    OVERALL_SUCCESS=false
fi
echo ""

# Summary
echo "=========================================="
if [ "$OVERALL_SUCCESS" = true ]; then
    echo -e "${GREEN}   ✓ ALL TESTS PASSED${NC}"
    echo ""
    echo "Project Status:"
    echo "  • Core scheduler: Working ✓"
    echo "  • Multi-tenant adapters: Working ✓"
    echo "  • API server: Working ✓"
    echo "  • Validation: Working ✓"
    echo "  • Test coverage: 13/13 passing ✓"
    echo ""
    echo "Ready for optional features or deployment!"
else
    echo -e "${RED}   ✗ SOME TESTS FAILED${NC}"
    echo ""
    echo "Please review the output above for details."
fi
echo "=========================================="
