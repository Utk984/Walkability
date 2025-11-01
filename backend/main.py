from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, Optional
import folium

# Import from reorganized modules
from src.data.data_loader import load_geospatial_data
from src.analysis.map_visualization import create_walkscore_choropleth
from src.analysis.walkability_analysis import (
    get_top_walkscore_sectors,
    get_bottom_walkscore_sectors,
    analyze_sector_amenities,
    compare_sectors
)
# Import environmental analysis functions
from src.analysis.environmental_analysis import (
    analyze_sector_environmental_quality,
    find_green_corridors,
    suggest_environmental_path,
    compare_environmental_quality,
    get_top_environmental_sectors
)
from src.analysis.enhanced_pathfinding import (
    find_environmental_route_with_pois,
    analyze_walkability_by_environment,
    suggest_green_walking_circuit
)
from src.data.search_utils import search_pois_fuzzy
from src.api.ai_chat import process_walkability_query
from src.analysis.pathfinding import get_walk_paths, initialize_pathfinder

# Import profile weight generation functions
from src.api.profile_weights import generate_profile_weights, get_default_weights
from src.analysis.dynamic_walkability import (
    calculate_dynamic_walk_scores, compare_walk_scores, generate_profile_insights
)

# Comprehensive walkability imports
from src.analysis.comprehensive_walkability import (
    ComprehensiveWalkabilityCalculator,
    calculate_walkability_with_profile, 
    generate_profile_based_insights,
    load_latest_walkability_scores,
    get_sector_analysis_from_scores
)

# Load data once at startup
data = load_geospatial_data()

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Initialize pathfinder on startup"""
    print("Initializing pathfinding system...")
    success = initialize_pathfinder()
    if success:
        print("Pathfinding system initialized successfully!")
    else:
        print("Warning: Pathfinding system failed to initialize")

# Allow React frontend to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

class SectorAnalysisRequest(BaseModel):
    sector_name: str

class SectorComparisonRequest(BaseModel):
    sector1: str
    sector2: str

class TopBottomRequest(BaseModel):
    k: int = 5

class ChatRequest(BaseModel):
    text: str

class POISearchRequest(BaseModel):
    query: str
    limit: int = 10

class WalkPathsRequest(BaseModel):
    destination_a: str
    destination_b: str

# Environmental analysis request models
class EnvironmentalSectorRequest(BaseModel):
    sector_name: str

class GreenCorridorsRequest(BaseModel):
    sector_name: str = None
    min_gvi: float = 20.0

class EnvironmentalPathRequest(BaseModel):
    sector_name: str
    poi_type: str = "restaurant"
    optimize_for: str = "gvi"

class EnvironmentalComparisonRequest(BaseModel):
    sector1: str
    sector2: str

class TopEnvironmentalRequest(BaseModel):
    criteria: str = "gvi"  # "gvi", "svf", or "combined"
    k: int = 5

class EnvironmentalRouteRequest(BaseModel):
    sector_name: str
    poi_type: str
    optimize_for: str = "gvi"  # "gvi", "svf", or "balanced"
    max_walk_distance: float = 1000

class EnvironmentalWalkabilityRequest(BaseModel):
    gvi_threshold: float = 25.0
    svf_threshold: float = 30.0

class GreenCircuitRequest(BaseModel):
    sector_name: str
    circuit_length: str = "short"  # "short", "medium", "long"

# Profile-based walkability request models
class ProfileWeightsRequest(BaseModel):
    user_type: str
    gender: str
    age: str
    additional_info: str = ""

class DynamicWalkScoreRequest(BaseModel):
    category_weights: Dict[str, float]
    include_insights: bool = True

# Comprehensive Walkability Endpoints

class ComprehensiveWalkabilityRequest(BaseModel):
    buffer_radius: float = 500.0
    custom_weights: Optional[Dict[str, float]] = None

class SectorBreakdownRequest(BaseModel):
    sector_name: str

class UpdateScoresRequest(BaseModel):
    buffer_radius: float = 500.0
    component_weights: Optional[Dict[str, float]] = None
    save_to_file: bool = True

@app.get("/")
def root():
    return {"message": "Chandigarh Walkability API is running."}

@app.get("/map/choropleth")
def get_choropleth():
    """Returns comprehensive walkability score choropleth map"""
    # Load latest comprehensive scores or use default data
    comprehensive_scores = load_latest_walkability_scores()
    if comprehensive_scores is not None:
        # Use comprehensive scores with proper column mapping
        temp_data = data.copy()
        temp_data["sectors_gdf"] = comprehensive_scores.copy()
        # Map comprehensive_walk_score to walk_score for compatibility
        temp_data["sectors_gdf"]["walk_score"] = temp_data["sectors_gdf"]["comprehensive_walk_score"]
        map_obj = create_walkscore_choropleth(temp_data)
    else:
        # Fallback to original data if no comprehensive scores available
        map_obj = create_walkscore_choropleth(data)
    return map_obj._repr_html_()

@app.post("/map/top-sectors")
def get_top_sectors(request: TopBottomRequest):
    """Returns top k sectors by walk score"""
    map_obj, table_df = get_top_walkscore_sectors(data, request.k)
    return {
        "map": map_obj._repr_html_(),
        "table": table_df.to_dict(orient="records"),
        "description": f"Top {request.k} sectors in Chandigarh by walk score."
    }

@app.post("/map/bottom-sectors")
def get_bottom_sectors(request: TopBottomRequest):
    """Returns bottom k sectors by walk score"""
    map_obj, table_df = get_bottom_walkscore_sectors(data, request.k)
    return {
        "map": map_obj._repr_html_(),
        "table": table_df.to_dict(orient="records"),
        "description": f"Bottom {request.k} sectors in Chandigarh by walk score."
    }

@app.post("/map/sector-analysis")
def analyze_sector(request: SectorAnalysisRequest):
    """Returns analysis of a specific sector"""
    map_obj, summary_dict, category_counts_df = analyze_sector_amenities(data, request.sector_name)
    if isinstance(summary_dict, str):
        return {"type": "error", "description": summary_dict}
    return {
        "map": map_obj._repr_html_(),
        "summary": summary_dict,
        "category_counts": category_counts_df.to_dict(orient="records"),
        "description": f"Analysis of amenities in Sector {request.sector_name}."
    }

@app.post("/map/compare-sectors")
def compare_sectors_endpoint(request: SectorComparisonRequest):
    """Returns comparison of two sectors"""
    map_obj, summary_comp, comparison_df = compare_sectors(data, request.sector1, request.sector2)
    if isinstance(summary_comp, str):
        return {"type": "error", "description": summary_comp}
    return {
        "map": map_obj._repr_html_(),
        "summary": summary_comp,
        "comparison": comparison_df.to_dict(orient="records"),
        "description": f"Comparison of Sector {request.sector1} and Sector {request.sector2}."
    }

@app.post("/walk-paths")
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

@app.post("/search/pois")
def search_pois(request: POISearchRequest):
    """Search POIs by name with fuzzy matching"""
    results = search_pois_fuzzy(request.query, request.limit)
    return {"results": results}

@app.post("/chat")
def handle_chat(req: ChatRequest):
    """Handle AI chat queries about geospatial data"""
    try:
        result = process_walkability_query(req.text, data, "fun")
        
        chat_out = {
            "description": result.get("description", ""),
            "map": result["map"]._repr_html_() if "map" in result else None
        }
        return JSONResponse(chat_out)
    except Exception as e:
        print(f"Error processing query: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={
                "type": "error",
                "description": f"Error processing query: {str(e)}"
            }
        )

# Environmental Analysis Endpoints

@app.post("/environmental/sector-analysis")
def analyze_environmental_sector(request: EnvironmentalSectorRequest):
    """Analyze environmental quality of a specific sector"""
    try:
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

@app.post("/environmental/green-corridors")
def find_green_corridors_endpoint(request: GreenCorridorsRequest):
    """Find green corridors in the city or specific sector"""
    try:
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

@app.post("/environmental/suggest-path")
def suggest_environmental_path_endpoint(request: EnvironmentalPathRequest):
    """Suggest environmentally optimized walking paths between POIs"""
    try:
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

@app.post("/environmental/compare-sectors")
def compare_environmental_sectors(request: EnvironmentalComparisonRequest):
    """Compare environmental quality between two sectors"""
    try:
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

@app.post("/environmental/top-sectors")
def get_top_environmental_sectors_endpoint(request: TopEnvironmentalRequest):
    """Get top sectors by environmental criteria"""
    try:
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

@app.post("/environmental/route-with-pois")
def find_environmental_route_endpoint(request: EnvironmentalRouteRequest):
    """Find environmental route that includes specific POIs"""
    try:
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

@app.post("/environmental/walkability-analysis")
def analyze_environmental_walkability(request: EnvironmentalWalkabilityRequest):
    """Analyze city-wide walkability based on environmental thresholds"""
    try:
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

@app.post("/environmental/green-circuit")
def suggest_green_circuit_endpoint(request: GreenCircuitRequest):
    """Suggest a green walking circuit in a sector"""
    try:
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

# Profile-based Walkability Endpoints

@app.post("/profile/generate-weights")
def generate_user_weights(request: ProfileWeightsRequest):
    """Generate category weights based on user profile"""
    try:
        weights = generate_profile_weights(
            request.user_type, 
            request.gender, 
            request.age, 
            request.additional_info
        )
        return {
            "weights": weights,
            "profile": {
                "user_type": request.user_type,
                "gender": request.gender,
                "age": request.age,
                "additional_info": request.additional_info
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"type": "error", "description": f"Error generating weights: {str(e)}"}
        )

@app.get("/profile/default-weights")
def get_default_user_weights():
    """Get default equal weights for all categories"""
    return {"weights": get_default_weights()}

@app.post("/profile/calculate-dynamic-scores")
def calculate_dynamic_scores(request: DynamicWalkScoreRequest):
    """Calculate comprehensive walkability scores based on user profile weights and provide sector suggestions"""
    try:
        # Use the new comprehensive walkability pipeline with profile weights
        from src.analysis.comprehensive_walkability import (
            calculate_walkability_with_profile, 
            generate_profile_based_insights
        )
        
        # Calculate comprehensive scores with user's POI category weights
        print(f"🔄 Calculating walkability with profile weights: {request.category_weights}")
        updated_sectors = calculate_walkability_with_profile(
            data=data,
            profile_weights=request.category_weights,
            save_to_file=True  # Save updated scores for other endpoints to use
        )
        
        # Generate insights focused on sector suggestions
        insights = generate_profile_based_insights(updated_sectors, request.category_weights)
        
        # Get summary statistics
        top_sector = updated_sectors.nlargest(1, 'comprehensive_walk_score').iloc[0]
        avg_score = updated_sectors['comprehensive_walk_score'].mean()
        
        response_data = {
            "status": "success",
            "profile_weights": request.category_weights,
            "summary": {
                "total_sectors": len(updated_sectors),
                "average_walkability": round(avg_score, 1),
                "top_sector": {
                    "name": top_sector["sector_name"],
                    "score": round(top_sector["comprehensive_walk_score"], 1)
                },
                "calculation_message": f"Walkability recalculated based on your preferences"
            },
            "insights": insights,
            "top_recommendations": [
                {
                    "sector": rec["name"],
                    "score": rec["score"],
                    "reason": rec["reason"]
                } for rec in insights["recommended_sectors"]
            ]
        }
        
        # Add additional insights if requested
        if request.include_insights:
            response_data["priority_matches"] = insights.get("priority_matches", [])
            response_data["environmental_highlights"] = insights.get("environmental_highlights", [])
            response_data["detailed_summary"] = insights.get("summary", "")
        
        return response_data
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=400,
            content={"type": "error", "description": f"Error calculating profile-based walkability: {str(e)}"}
        )

@app.post("/walkability/comprehensive/calculate")
def calculate_comprehensive_walkability(request: ComprehensiveWalkabilityRequest):
    """Calculate comprehensive walkability scores for all sectors"""
    try:
        # Use the available function with custom POI weights if provided
        updated_sectors = calculate_walkability_with_profile(
            data=data,
            profile_weights=request.custom_weights,
            save_to_file=True
        )
        
        # Get summary statistics
        stats = {
            "total_sectors": len(updated_sectors),
            "mean_score": float(updated_sectors['comprehensive_walk_score'].mean()),
            "median_score": float(updated_sectors['comprehensive_walk_score'].median()),
            "std_score": float(updated_sectors['comprehensive_walk_score'].std()),
            "min_score": float(updated_sectors['comprehensive_walk_score'].min()),
            "max_score": float(updated_sectors['comprehensive_walk_score'].max()),
            "top_sector": {
                "name": updated_sectors.loc[updated_sectors['comprehensive_walk_score'].idxmax(), 'sector_name'],
                "score": float(updated_sectors['comprehensive_walk_score'].max())
            },
            "bottom_sector": {
                "name": updated_sectors.loc[updated_sectors['comprehensive_walk_score'].idxmin(), 'sector_name'],
                "score": float(updated_sectors['comprehensive_walk_score'].min())
            }
        }
        
        # Get top 10 and bottom 10 sectors
        top_sectors = updated_sectors.nlargest(10, 'comprehensive_walk_score')[
            ['sector_name', 'comprehensive_walk_score', 'total_pois', 'raw_gvi', 'raw_svf']
        ].to_dict(orient='records')
        
        bottom_sectors = updated_sectors.nsmallest(10, 'comprehensive_walk_score')[
            ['sector_name', 'comprehensive_walk_score', 'total_pois', 'raw_gvi', 'raw_svf']
        ].to_dict(orient='records')
        
        return {
            "status": "success",
            "statistics": stats,
            "top_sectors": top_sectors,
            "bottom_sectors": bottom_sectors,
            "calculation_parameters": {
                "buffer_radius": request.buffer_radius,
                "custom_weights": request.custom_weights
            }
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"type": "error", "description": f"Error calculating comprehensive walkability: {str(e)}"}
        )

@app.post("/walkability/comprehensive/sector-breakdown")
def get_comprehensive_sector_breakdown(request: SectorBreakdownRequest):
    """Get detailed score breakdown for a specific sector"""
    try:
        # Use the available function that loads scores from file
        breakdown = get_sector_analysis_from_scores(request.sector_name)
        
        if "error" in breakdown:
            return JSONResponse(
                status_code=404,
                content={"type": "error", "description": breakdown["error"]}
            )
        
        return {
            "status": "success",
            "breakdown": breakdown
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"type": "error", "description": f"Error getting sector breakdown: {str(e)}"}
        )

@app.post("/walkability/comprehensive/update-weights")
def update_walkability_weights(request: UpdateScoresRequest):
    """Update component weights and recalculate walkability scores"""
    try:
        # Initialize calculator with custom weights
        calculator = ComprehensiveWalkabilityCalculator(buffer_radius=request.buffer_radius)
        
        if request.component_weights:
            calculator.update_component_weights(request.component_weights)
        
        # Calculate updated scores
        updated_sectors = calculator.calculate_comprehensive_scores(data)
        
        # Optionally save to file
        if request.save_to_file:
            import os
            output_path = "data/processed/sectors_with_comprehensive_walkability.geojson"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            updated_sectors.to_file(output_path, driver='GeoJSON')
        
        # Get comparison with previous scores if available
        comparison_stats = {
            "scores_updated": len(updated_sectors),
            "component_weights": calculator.component_weights,
            "buffer_radius": request.buffer_radius
        }
        
        return {
            "status": "success",
            "message": "Walkability scores updated successfully",
            "comparison": comparison_stats,
            "top_5_sectors": updated_sectors.nlargest(5, 'comprehensive_walk_score')[
                ['sector_name', 'comprehensive_walk_score']
            ].to_dict(orient='records')
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"type": "error", "description": f"Error updating walkability weights: {str(e)}"}
        )

@app.get("/walkability/comprehensive/default-weights")
def get_comprehensive_default_weights():
    """Get default component weights for comprehensive walkability calculation"""
    calculator = ComprehensiveWalkabilityCalculator()
    return {
        "default_weights": calculator.component_weights,
        "description": {
            "poi_count": "Accessibility - how many POIs are nearby",
            "poi_diversity": "Variety - different types of POIs available", 
            "poi_dispersion": "Spatial distribution - how evenly POIs are spread",
            "environmental": "Environmental quality - GVI and SVF combined",
            "green_corridors": "Green infrastructure - connectivity to green areas"
        }
    }

@app.get("/walkability/comprehensive/map")
def get_comprehensive_walkability_map():
    """Get a choropleth map showing comprehensive walkability scores"""
    try:
        # Load existing comprehensive scores or calculate new ones
        updated_sectors = load_latest_walkability_scores()
        if updated_sectors is None:
            # Calculate new scores if none exist
            updated_sectors = calculate_walkability_with_profile(
                data=data,
                profile_weights=None,
                save_to_file=True
            )
        
        # Create choropleth map
        city_center = [30.7333, 76.7794]  # Chandigarh coordinates
        m = folium.Map(location=city_center, zoom_start=12)
        
        folium.Choropleth(
            geo_data=updated_sectors,
            data=updated_sectors,
            columns=['sector_name', 'comprehensive_walk_score'],
            key_on='feature.properties.sector_name',
            fill_color='YlOrRd',
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name='Comprehensive Walkability Score'
        ).add_to(m)
        
        # Add tooltips with detailed information
        for _, sector in updated_sectors.iterrows():
            folium.Marker(
                location=[sector.geometry.centroid.y, sector.geometry.centroid.x],
                popup=folium.Popup(
                    f"""
                    <b>{sector['sector_name']}</b><br>
                    Comprehensive Score: {sector['comprehensive_walk_score']:.1f}<br>
                    POIs: {int(sector['total_pois'])}<br>
                    GVI: {sector['raw_gvi']:.1f}<br>
                    SVF: {sector['raw_svf']:.1f}<br>
                    Green Nodes: {int(sector.get('green_nodes', 0))}
                    """,
                    max_width=300
                ),
                icon=folium.Icon(color='blue', icon='info-sign')
            ).add_to(m)
        
        return {
            "map": m._repr_html_(),
            "description": f"Comprehensive walkability map showing scores for {len(updated_sectors)} sectors"
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"type": "error", "description": f"Error creating comprehensive walkability map: {str(e)}"}
        )