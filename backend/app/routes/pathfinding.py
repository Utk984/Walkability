"""Pathfinding and routing endpoints"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.models.schemas import WalkPathsRequest
from app.analysis.pathfinding import get_walk_paths, initialize_pathfinder

router = APIRouter(tags=["pathfinding"])


@router.post("/walk-paths")
def get_walking_paths(request: WalkPathsRequest):
    """Get multiple walking paths between two destinations"""
    result = get_walk_paths(request.destination_a, request.destination_b)
    
    if "error" in result:
        return JSONResponse(
            status_code=400,
            content={"type": "error", "description": result["error"]}
        )
    
    return {
        "map": result["map"],
        "paths": result["paths"],
        "description": result["description"],
        "start_coords": result["start_coords"],
        "end_coords": result["end_coords"]
    }

