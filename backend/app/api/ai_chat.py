import folium
import json
from google import genai
from app.config import CATEGORY_MAP, CATEGORY_COLORS, PLANNER_PROMPT, CODER_PROMPT


def process_walkability_query(user_query: str, data: dict, function_name: str = "fun") -> dict:
    """
    Process a user query using a two-agent AI system:
    1. Planner Agent: Analyzes query and creates detailed action plan
    2. Coder Agent: Implements the action plan as Python code
    
    Args:
        user_query: Natural language query from user
        data: Dictionary containing sectors_gdf, pois_gdf, nodes_gdf, edges_gdf
        function_name: Expected function name in generated code
    
    Returns:
        dict: Contains 'map' (folium.Map) and 'description' (str)
    """
    client = genai.Client(api_key="AIzaSyCSTZkQaegvbC9l-aId5qLXhZF-rwYZq24")

    try:
        # Step 1: Planner Agent - Analyze query and create action plan
        print(f"🔍 Planner Agent analyzing query: '{user_query}'")
        print("="*50)
        
        planner_prompt = PLANNER_PROMPT.replace("{user_query}", user_query)
        planner_prompt = planner_prompt.replace("{category_map}", str(CATEGORY_MAP))
        
        planner_response = client.models.generate_content(
            model="gemini-2.5-flash-preview-04-17",
            contents=planner_prompt
        )
        
        action_plan = planner_response.text
        print("📋 Action Plan Created:")
        print(action_plan)
        print("="*50)
        
        # Step 2: Coder Agent - Implement the action plan
        print("💻 Coder Agent implementing action plan...")
        print("="*50)
        
        coder_prompt = CODER_PROMPT.replace("{action_plan}", action_plan)
        
        coder_response = client.models.generate_content(
            model="gemini-2.5-flash-preview-04-17",
            contents=coder_prompt
        )
        
        generated_code = coder_response.text
        print("Generated code:")
        print(generated_code)
        print("="*50)
        
    except Exception as api_error:
        if "API key expired" in str(api_error) or "API_KEY_INVALID" in str(api_error):
            raise ValueError("Gemini API key has expired. Please update the API key in the ai_chat.py file.")
        elif "quota" in str(api_error).lower():
            raise ValueError("Gemini API quota exceeded. Please check your API usage limits.")
        else:
            raise ValueError(f"Error calling Gemini API: {str(api_error)}")

    # Clean the generated code
    cleaned_code = _clean_code_block(generated_code)
    
    print("🔧 Cleaned code:")
    print(cleaned_code)
    print("="*50)

    # Safe execution of generated code
    # Import all necessary modules that the generated code might need
    try:
        # Import the analysis modules
        from app.analysis.walkability_analysis import (
            analyze_sector_amenities, compare_sectors, 
            get_top_walkscore_sectors, get_bottom_walkscore_sectors
        )
        from app.analysis.map_visualization import (
            create_walkscore_choropleth, create_sector_highlight_map, create_comparison_map
        )
        from app.analysis.pathfinding import initialize_pathfinder, get_walk_paths
        from app.data.data_loader import load_geospatial_data
        
        # Import new environmental analysis functions
        from app.analysis.environmental_analysis import (
            analyze_sector_environmental_quality, find_green_corridors,
            suggest_environmental_path, compare_environmental_quality,
            get_top_environmental_sectors
        )
        
        # Import enhanced pathfinding functions
        from app.analysis.enhanced_pathfinding import (
            find_environmental_route_with_pois, analyze_walkability_by_environment,
            suggest_green_walking_circuit
        )
        
        # Add geopy for distance calculations
        from geopy.distance import geodesic
        
        local_ns = {
            "folium": folium,
            "data": data,  # Pass the data dictionary directly
            # Add other imports that might be commonly used
            "pd": __import__("pandas"),
            "gpd": __import__("geopandas"),
            "np": __import__("numpy"),
            # Add geopy for distance calculations
            "geodesic": geodesic,
            # Add all the analysis functions
            "analyze_sector_amenities": analyze_sector_amenities,
            "compare_sectors": compare_sectors,
            "get_top_walkscore_sectors": get_top_walkscore_sectors,
            "get_bottom_walkscore_sectors": get_bottom_walkscore_sectors,
            "create_walkscore_choropleth": create_walkscore_choropleth,
            "create_sector_highlight_map": create_sector_highlight_map,
            "create_comparison_map": create_comparison_map,
            "initialize_pathfinder": initialize_pathfinder,
            "get_walk_paths": get_walk_paths,
            "load_geospatial_data": load_geospatial_data,
            # Add environmental analysis functions
            "analyze_sector_environmental_quality": analyze_sector_environmental_quality,
            "find_green_corridors": find_green_corridors,
            "suggest_environmental_path": suggest_environmental_path,
            "compare_environmental_quality": compare_environmental_quality,
            "get_top_environmental_sectors": get_top_environmental_sectors,
            # Add enhanced pathfinding functions
            "find_environmental_route_with_pois": find_environmental_route_with_pois,
            "analyze_walkability_by_environment": analyze_walkability_by_environment,
            "suggest_green_walking_circuit": suggest_green_walking_circuit
        }
    except ImportError as ie:
        error_msg = f"Failed to import required modules: {str(ie)}"
        print(f"❌ Import error: {error_msg}")
        raise ValueError(error_msg)
    
    try:
        exec(cleaned_code, local_ns)
    except Exception as e:
        error_msg = f"Error executing generated code: {str(e)}"
        print(f"❌ Execution error: {error_msg}")
        print(f"Generated code was:\n{cleaned_code}")
        raise ValueError(error_msg)

    func = local_ns.get(function_name)
    if not callable(func):
        error_msg = f"Function '{function_name}' not found or not callable."
        print(f"❌ Function error: {error_msg}")
        print(f"Available functions in namespace: {[k for k, v in local_ns.items() if callable(v)]}")
        raise ValueError(error_msg)

    # Call the function and return results
    try:
        result = func(data)
        if isinstance(result, tuple) and len(result) == 2:
            map_obj, desc = result
            if isinstance(map_obj, folium.Map):
                print("✅ Successfully generated map and description")
                return {
                    "map": map_obj,
                    "description": desc
                }
            else:
                raise TypeError(f"Function did not return a folium.Map object, got {type(map_obj)}")
        else:
            raise TypeError(f"Function must return a tuple of (folium.Map, str), got {type(result)}")
    except Exception as e:
        error_msg = f"Error calling generated function: {str(e)}"
        print(f"❌ Function call error: {error_msg}")
        
        # Provide helpful debugging for common errors
        if "'type'" in str(e):
            error_msg += "\n\nHINT: The error mentions 'type' field. Make sure to use 'secondary_type' instead of 'type' when filtering POIs."
        elif "empty" in str(e).lower():
            error_msg += "\n\nHINT: Check if the filtered data is empty before processing."
            
        raise ValueError(error_msg)


def _clean_code_block(code: str) -> str:
    """
    Clean code block by removing markdown code fences.
    
    Args:
        code: Raw code string potentially with markdown formatting
    
    Returns:
        str: Cleaned code string
    """
    lines = code.strip().splitlines()
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines)