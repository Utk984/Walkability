"""Search endpoints"""
from fastapi import APIRouter
from app.models.schemas import POISearchRequest
from app.data.search_utils import search_pois_fuzzy

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/pois")
def search_pois(request: POISearchRequest):
    """Search POIs by name with fuzzy matching"""
    results = search_pois_fuzzy(request.query, request.limit)
    return {"results": results}

