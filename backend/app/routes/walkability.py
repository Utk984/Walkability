"""Walkability analysis endpoints"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.models.schemas import (
    SectorAnalysisRequest,
    SectorComparisonRequest,
    TopBottomRequest,
    ComprehensiveWalkabilityRequest,
    SectorBreakdownRequest,
    UpdateScoresRequest
)
from app.services.data_loader import get_data
from app.analysis.walkability_analysis import (
    get_top_walkscore_sectors,
    get_bottom_walkscore_sectors,
    analyze_sector_amenities,
    compare_sectors
)
from app.analysis.map_visualization import create_walkscore_choropleth
from app.analysis.comprehensive_walkability import (
    ComprehensiveWalkabilityCalculator,
    calculate_walkability_with_profile,
    load_latest_walkability_scores,
    get_sector_analysis_from_scores
)
import folium
import os

router = APIRouter(tags=["walkability"])


@router.get("/map/choropleth")
def get_choropleth():
    """Returns comprehensive walkability score choropleth map"""
    data = get_data()
    comprehensive_scores = load_latest_walkability_scores()
    
    if comprehensive_scores is not None:
        temp_data = data.copy()
        temp_data["sectors_gdf"] = comprehensive_scores.copy()
        temp_data["sectors_gdf"]["walk_score"] = temp_data["sectors_gdf"]["comprehensive_walk_score"]
        map_obj = create_walkscore_choropleth(temp_data)
    else:
        map_obj = create_walkscore_choropleth(data)
    
    return map_obj._repr_html_()


@router.post("/map/top-sectors")
def get_top_sectors(request: TopBottomRequest):
    """Returns top k sectors by walk score"""
    data = get_data()
    map_obj, table_df = get_top_walkscore_sectors(data, request.k)
    return {
        "map": map_obj._repr_html_(),
        "table": table_df.to_dict(orient="records"),
        "description": f"Top {request.k} sectors in Chandigarh by walk score."
    }


@router.post("/map/bottom-sectors")
def get_bottom_sectors(request: TopBottomRequest):
    """Returns bottom k sectors by walk score"""
    data = get_data()
    map_obj, table_df = get_bottom_walkscore_sectors(data, request.k)
    return {
        "map": map_obj._repr_html_(),
        "table": table_df.to_dict(orient="records"),
        "description": f"Bottom {request.k} sectors in Chandigarh by walk score."
    }


@router.post("/map/sector-analysis")
def analyze_sector(request: SectorAnalysisRequest):
    """Returns analysis of a specific sector"""
    data = get_data()
    map_obj, summary_dict, category_counts_df = analyze_sector_amenities(data, request.sector_name)
    
    if isinstance(summary_dict, str):
        return {"type": "error", "description": summary_dict}
    
    return {
        "map": map_obj._repr_html_(),
        "summary": summary_dict,
        "category_counts": category_counts_df.to_dict(orient="records"),
        "description": f"Analysis of amenities in Sector {request.sector_name}."
    }


@router.post("/map/compare-sectors")
def compare_sectors_endpoint(request: SectorComparisonRequest):
    """Returns comparison of two sectors"""
    data = get_data()
    map_obj, summary_comp, comparison_df = compare_sectors(data, request.sector1, request.sector2)
    
    if isinstance(summary_comp, str):
        return {"type": "error", "description": summary_comp}
    
    return {
        "map": map_obj._repr_html_(),
        "summary": summary_comp,
        "comparison": comparison_df.to_dict(orient="records"),
        "description": f"Comparison of Sector {request.sector1} and Sector {request.sector2}."
    }


@router.post("/walkability/comprehensive/calculate")
def calculate_comprehensive_walkability(request: ComprehensiveWalkabilityRequest):
    """Calculate comprehensive walkability scores for all sectors"""
    try:
        data = get_data()
        updated_sectors = calculate_walkability_with_profile(
            data=data,
            profile_weights=request.custom_weights,
            save_to_file=True
        )
        
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


@router.post("/walkability/comprehensive/sector-breakdown")
def get_comprehensive_sector_breakdown(request: SectorBreakdownRequest):
    """Get detailed score breakdown for a specific sector"""
    try:
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


@router.post("/walkability/comprehensive/update-weights")
def update_walkability_weights(request: UpdateScoresRequest):
    """Update component weights and recalculate walkability scores"""
    try:
        data = get_data()
        calculator = ComprehensiveWalkabilityCalculator(buffer_radius=request.buffer_radius)
        
        if request.component_weights:
            calculator.update_component_weights(request.component_weights)
        
        updated_sectors = calculator.calculate_comprehensive_scores(data)
        
        if request.save_to_file:
            output_path = "data/processed/sectors_with_comprehensive_walkability.geojson"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            updated_sectors.to_file(output_path, driver='GeoJSON')
        
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


@router.get("/walkability/comprehensive/default-weights")
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


@router.get("/walkability/comprehensive/map")
def get_comprehensive_walkability_map():
    """Get a choropleth map showing comprehensive walkability scores"""
    try:
        data = get_data()
        updated_sectors = load_latest_walkability_scores()
        
        if updated_sectors is None:
            updated_sectors = calculate_walkability_with_profile(
                data=data,
                profile_weights=None,
                save_to_file=True
            )
        
        city_center = [30.7333, 76.7794]
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
