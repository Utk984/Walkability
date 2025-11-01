"""User profile and personalized walkability endpoints"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.models.schemas import ProfileWeightsRequest, DynamicWalkScoreRequest
from app.services.data_loader import get_data
from app.api.profile_weights import generate_profile_weights, get_default_weights
from app.analysis.comprehensive_walkability import (
    calculate_walkability_with_profile,
    generate_profile_based_insights
)

router = APIRouter(prefix="/profile", tags=["profile"])


@router.post("/generate-weights")
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


@router.get("/default-weights")
def get_default_user_weights():
    """Get default equal weights for all categories"""
    return {"weights": get_default_weights()}


@router.post("/calculate-dynamic-scores")
def calculate_dynamic_scores(request: DynamicWalkScoreRequest):
    """Calculate comprehensive walkability scores based on user profile weights"""
    try:
        data = get_data()
        
        print(f"🔄 Calculating walkability with profile weights: {request.category_weights}")
        updated_sectors = calculate_walkability_with_profile(
            data=data,
            profile_weights=request.category_weights,
            save_to_file=True
        )
        
        insights = generate_profile_based_insights(updated_sectors, request.category_weights)
        
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
                "calculation_message": "Walkability recalculated based on your preferences"
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

