"""AI chat endpoints"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.models.schemas import ChatRequest
from app.services.data_loader import get_data
from app.api.ai_chat import process_walkability_query

router = APIRouter(tags=["chat"])


@router.post("/chat")
def handle_chat(req: ChatRequest):
    """Handle AI chat queries about geospatial data"""
    try:
        data = get_data()
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

