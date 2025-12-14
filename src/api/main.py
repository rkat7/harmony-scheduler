from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.models.cdm import ScheduleRequest, ScheduleResponse, ScheduleError
from src.solver.engine import solve_schedule
from src.adapters.factory import AdapterFactory

app = FastAPI(
    title="Harmony Production Scheduler",
    description="Constraint-based production scheduling API",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

adapter_factory = AdapterFactory()


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/schedule", response_model=ScheduleResponse | ScheduleError)
async def create_schedule(request: Request):
    """
    Generate a production schedule that minimizes total tardiness.

    Accepts multiple input formats (Client A, Client B, etc.) and
    automatically transforms to canonical format.

    Constraints:
    - Operations can only run on resources with required capabilities
    - No resource can handle multiple operations simultaneously
    - Operations within a product follow route order
    - All operations must fit within resource calendars
    - Changeover time added when switching product families on same resource
    - All times within the specified horizon
    """
    try:
        # Get raw JSON
        raw_input = await request.json()

        # Auto-detect client format and transform to CDM
        adapter = adapter_factory.get_adapter(raw_input)
        schedule_request = adapter.to_cdm(raw_input)

        # Solve
        result = solve_schedule(schedule_request)

        # Handle infeasible case
        if isinstance(result, ScheduleError):
            return JSONResponse(
                status_code=422,
                content=result.model_dump()
            )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
