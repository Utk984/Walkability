"""Environmental analysis endpoints"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.models.schemas import (
    EnvironmentalSectorRequest,
    GreenCorridorsRequest,
    EnvironmentalPathRequest,
    EnvironmentalComparisonRequest,
    TopEnvironmentalRequest,
    EnvironmentalRouteRequest,
    EnvironmentalWalkabilityRequest,
    GreenCircuitRequest
)
from app.services.data_loader import get_data
from app.analysis.environmental_analysis import (
    analyze_sector_environmental_quality,
    find_green_corridors,
    suggest_environmental_path,
    compare_environmental_quality,
    get_top_environmental_sectors
)
from app.analysis.enhanced_pathfinding import (
    find_environmental_route_with_pois,
    analyze_walkability_by_environment,
    suggest_green_walking_circuit
)

router = APIRouter(prefix="/environmental", tags=["environmental"])


@router.post("/sector-analysis")
def analyze_environmental_sector(request: EnvironmentalSectorRequest):
    """Analyze environmental quality of a specific sector"""
    try:
        data = get_data()
        map_obj, summary = analyze_sector_environmental_quality(data, request.sector_name)
        
        if isinstance(summary, str):
            return {"type": "error", "description": summary}
        
        return {
            "map": map_obj._repr_html_(),
            "summary": summary,
            "description": f"Environmental analysis of Sector {request.sector_name}."
        }
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"type": "error", "description": f"Error: {str(e)}"}
        )


@router.post("/green-corridors")
def find_green_corridors_endpoint(request: GreenCorridorsRequest):
    """Find green corridors in the city or specific sector"""
    try:
        data = get_data()
        map_obj, description = find_green_corridors(data, request.sector_name, request.min_gvi)
        return {
            "map": map_obj._repr_html_(),
            "description": description
        }
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"type": "error", "description": f"Error: {str(e)}"}
        )


@router.post("/suggest-path")
def suggest_environmental_path_endpoint(request: EnvironmentalPathRequest):
    """Suggest environmentally optimized walking paths between POIs"""
    try:
        data = get_data()
        map_obj, description = suggest_environmental_path(
            data, request.sector_name, request.poi_type, request.optimize_for
        )
        return {
            "map": map_obj._repr_html_(),
            "description": description
        }
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"type": "error", "description": f"Error: {str(e)}"}
        )


@router.post("/compare-sectors")
def compare_environmental_sectors(request: EnvironmentalComparisonRequest):
    """Compare environmental quality between two sectors"""
    try:
        data = get_data()
        map_obj, description = compare_environmental_quality(data, request.sector1, request.sector2)
        return {
            "map": map_obj._repr_html_(),
            "description": description
        }
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"type": "error", "description": f"Error: {str(e)}"}
        )


@router.post("/top-sectors")
def get_top_environmental_sectors_endpoint(request: TopEnvironmentalRequest):
    """Get top sectors by environmental criteria"""
    try:
        data = get_data()
        map_obj, description = get_top_environmental_sectors(data, request.criteria, request.k)
        return {
            "map": map_obj._repr_html_(),
            "description": description
        }
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"type": "error", "description": f"Error: {str(e)}"}
        )


@router.post("/route-with-pois")
def find_environmental_route_endpoint(request: EnvironmentalRouteRequest):
    """Find environmental route that includes specific POIs"""
    try:
        data = get_data()
        map_obj, description = find_environmental_route_with_pois(
            data, request.sector_name, request.poi_type,
            request.optimize_for, request.max_walk_distance
        )
        return {
            "map": map_obj._repr_html_(),
            "description": description
        }
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"type": "error", "description": f"Error: {str(e)}"}
        )


@router.post("/walkability-analysis")
def analyze_environmental_walkability(request: EnvironmentalWalkabilityRequest):
    """Analyze city-wide walkability based on environmental thresholds"""
    try:
        data = get_data()
        map_obj, description = analyze_walkability_by_environment(
            data, request.gvi_threshold, request.svf_threshold
        )
        return {
            "map": map_obj._repr_html_(),
            "description": description
        }
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"type": "error", "description": f"Error: {str(e)}"}
        )


@router.post("/green-circuit")
def suggest_green_circuit_endpoint(request: GreenCircuitRequest):
    """Suggest a green walking circuit in a sector"""
    try:
        data = get_data()
        map_obj, description = suggest_green_walking_circuit(
            data, request.sector_name, request.circuit_length
        )
        return {
            "map": map_obj._repr_html_(),
            "description": description
        }
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"type": "error", "description": f"Error: {str(e)}"}
        )
