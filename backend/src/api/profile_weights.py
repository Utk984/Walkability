import json
from google import genai
from typing import Dict, Any
from pydantic import BaseModel
from config import PROFILE_WEIGHTS_PROMPT

class CategoryWeights(BaseModel):
    """Pydantic model for category weights that ensures all required categories are present."""
    essential_services: float
    food_and_drinks: float  
    shopping: float
    entertainment: float
    tourism: float
    sports: float
    public_transport: float

def generate_profile_weights(user_type: str, gender: str, age: str, additional_info: str = "") -> Dict[str, float]:
    """
    Generate category weights based on user profile using LLM with structured output.
    
    Args:
        user_type: Type of user (Working Professional, Student, etc.)
        gender: User's gender
        age: User's age group
        additional_info: Additional user details and preferences
        
    Returns:
        Dict[str, float]: Category weights that sum to 1.0
    """
    
    
    # Default weights if API fails
    default_weights = {
        "Essential Services": 0.20,
        "Food and Drinks": 0.15,
        "Shopping": 0.10,
        "Entertainment": 0.10,
        "Tourism": 0.15,
        "Sports": 0.15,
        "Public Transport": 0.15
    }
    
    try:
        client = genai.Client(api_key="AIzaSyCSTZkQaegvbC9l-aId5qLXhZF-rwYZq24")
        
        # Format the prompt with user data
        prompt = PROFILE_WEIGHTS_PROMPT.format(
            user_type=user_type,
            gender=gender,
            age=age,
            additional_info=additional_info if additional_info.strip() else "None provided"
        )
        
        # Call Gemini API with structured output
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": CategoryWeights,
            }
        )
        
        # Get the parsed structured output
        weights_obj: CategoryWeights = response.parsed
        
        # Convert to the expected format with proper category names
        final_weights = {
            "Essential Services": weights_obj.essential_services,
            "Food and Drinks": weights_obj.food_and_drinks,
            "Shopping": weights_obj.shopping,
            "Entertainment": weights_obj.entertainment,
            "Tourism": weights_obj.tourism,
            "Sports": weights_obj.sports,
            "Public Transport": weights_obj.public_transport
        }
        
        # Validate that weights sum to approximately 1.0
        total = sum(final_weights.values())
        if abs(total - 1.0) > 0.01:  # Allow small floating point errors
            # Normalize weights to sum to 1.0
            final_weights = {k: v/total for k, v in final_weights.items()}
        
        # Ensure all weights are positive
        if any(w < 0 for w in final_weights.values()):
            print(f"❌ Negative weights detected, using defaults")
            return default_weights
        
        print(f"✅ Generated weights for {user_type}: {final_weights}")
        return final_weights
        
    except Exception as e:
        print(f"❌ Error generating profile weights: {e}")
        return default_weights


def get_default_weights() -> Dict[str, float]:
    """Get default equal weights for all categories."""
    return {
        "Essential Services": 0.143,  # 1/7
        "Food and Drinks": 0.143,
        "Shopping": 0.143,
        "Entertainment": 0.143,
        "Tourism": 0.143,
        "Sports": 0.143,
        "Public Transport": 0.142  # Slightly less to sum to 1.0
    } 