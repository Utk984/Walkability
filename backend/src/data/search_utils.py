from fuzzywuzzy import fuzz
from typing import List, Dict
from .data_loader import load_pois_for_search


def search_pois_fuzzy(query: str, limit: int = 10) -> List[Dict]:
    """
    Search POIs by name using fuzzy matching.
    
    Args:
        query: Search query string
        limit: Maximum number of results to return
    
    Returns:
        List of POI dictionaries with match scores
    """
    if not query.strip():
        return []
    
    pois = load_pois_for_search()
    query = query.lower().strip()
    results = []
    
    for poi in pois:
        poi_name = poi['properties'].get('name', '')
        if not poi_name:
            continue
            
        # Calculate fuzzy match score
        score = fuzz.partial_ratio(query, poi_name.lower())
        
        # Only include results with reasonable match scores
        if score >= 60:
            results.append({
                "name": poi_name,
                "primary_type": poi['properties'].get('primary_type', ''),
                "secondary_type": poi['properties'].get('secondary_type', ''),
                "sector_name": poi['properties'].get('sector_name', ''),
                "coordinates": poi['geometry']['coordinates'],
                "score": score
            })
    
    # Sort by score (descending) and limit results
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:limit]


def find_poi_by_name(poi_name: str) -> Dict:
    """
    Find a specific POI by exact name match.
    
    Args:
        poi_name: Exact name of the POI
    
    Returns:
        POI dictionary or None if not found
    """
    pois = load_pois_for_search()
    poi_name_lower = poi_name.lower()
    
    for poi in pois:
        if poi['properties'].get('name', '').lower() == poi_name_lower:
            return {
                "name": poi['properties']['name'],
                "primary_type": poi['properties'].get('primary_type', ''),
                "secondary_type": poi['properties'].get('secondary_type', ''),
                "sector_name": poi['properties'].get('sector_name', ''),
                "coordinates": poi['geometry']['coordinates']
            }
    
    return None 