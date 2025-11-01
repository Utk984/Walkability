import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from app.config import CATEGORY_MAP


def calculate_dynamic_walk_scores(data: dict, category_weights: Dict[str, float]) -> pd.DataFrame:
    """
    Calculate new walk scores for all sectors based on dynamic category weights.
    Also incorporates environmental and infrastructure features.
    
    Args:
        data: Dictionary containing GeoDataFrames
        category_weights: Dictionary mapping category names to weights (should sum to 1.0)
        
    Returns:
        pandas.DataFrame: Sectors with updated walk scores and feature breakdown
    """
    
    sectors_gdf = data["sectors_gdf"].copy()
    pois_gdf = data["pois_gdf"] 
    nodes_gdf = data["nodes_gdf"]
    edges_gdf = data["edges_gdf"]
    
    # Initialize results list
    results = []
    
    for _, sector in sectors_gdf.iterrows():
        sector_name = sector["sector_name"]
        sector_geometry = sector.geometry
        
        # 1. Calculate Category-based POI Scores (main component)
        category_scores = _calculate_category_scores(pois_gdf, sector_geometry, category_weights)
        
        # 2. Calculate Environmental Quality Score
        env_score = _calculate_environmental_score(nodes_gdf, sector_name)
        
        # 3. Calculate Infrastructure Quality Score  
        infra_score = _calculate_infrastructure_score(edges_gdf, nodes_gdf, sector_name)
        
        # 4. Calculate Connectivity Score
        connectivity_score = _calculate_connectivity_score(edges_gdf, nodes_gdf, sector_name)
        
        # 5. Combine all scores into final walk score
        # Main weight on POI categories (80%), environmental (10%), infrastructure (5%), connectivity (5%)
        final_walk_score = (
            category_scores["total_score"] * 0.80 +
            env_score * 0.10 + 
            infra_score * 0.05 +
            connectivity_score * 0.05
        )
        
        # Cap at 100 and handle NaN values
        final_walk_score = min(final_walk_score, 100.0) if not pd.isna(final_walk_score) else 0.0
        
        # Collect results
        result = {
            "sector_name": sector_name,
            "dynamic_walk_score": final_walk_score,
            "poi_score": category_scores["total_score"],
            "environmental_score": env_score,
            "infrastructure_score": infra_score, 
            "connectivity_score": connectivity_score,
            "original_walk_score": sector.get("walk_score", 0),
            # Category breakdown
            **{f"{cat}_score": category_scores["category_scores"][cat] 
               for cat in category_weights.keys()},
            # Feature counts for analysis
            "total_pois": category_scores["total_pois"],
            "avg_gvi": _get_sector_avg_gvi(nodes_gdf, sector_name),
            "avg_svf": _get_sector_avg_svf(nodes_gdf, sector_name),
            "total_nodes": len(nodes_gdf[nodes_gdf["sector_name"] == sector_name]),
            "total_edges": _count_sector_edges(edges_gdf, nodes_gdf, sector_name)
        }
        
        results.append(result)
    
    # Create DataFrame and add ranking
    results_df = pd.DataFrame(results)
    
    # Handle NaN values before ranking
    results_df["dynamic_walk_score"] = results_df["dynamic_walk_score"].fillna(0.0)
    results_df["original_walk_score"] = results_df["original_walk_score"].fillna(0.0)
    
    # Add ranking
    results_df["walk_score_rank"] = results_df["dynamic_walk_score"].rank(ascending=False, method="dense")
    results_df["score_improvement"] = results_df["dynamic_walk_score"] - results_df["original_walk_score"]
    
    return results_df.sort_values("dynamic_walk_score", ascending=False)


def _calculate_category_scores(pois_gdf, sector_geometry, category_weights: Dict[str, float]) -> Dict:
    """Calculate weighted POI category scores for a sector."""
    
    # Find POIs within sector
    sector_pois = pois_gdf[pois_gdf.geometry.within(sector_geometry)]
    
    # Count POIs by category
    category_counts = {}
    for category, poi_types in CATEGORY_MAP.items():
        count = len(sector_pois[sector_pois["secondary_type"].isin(poi_types)])
        category_counts[category] = count
    
    # Calculate scores for each category (normalize to 0-100 scale)
    category_scores = {}
    max_poi_count = 50  # Assume 50 POIs of one type is "excellent"
    
    for category, count in category_counts.items():
        # Convert count to score (0-100)
        raw_score = min((count / max_poi_count) * 100, 100)
        
        # Apply category weight
        weighted_score = raw_score * category_weights.get(category, 0)
        category_scores[category] = weighted_score
    
    # Total score is sum of weighted category scores
    total_score = sum(category_scores.values())
    
    return {
        "category_scores": category_scores,
        "total_score": total_score,
        "total_pois": len(sector_pois),
        "category_counts": category_counts
    }


def _calculate_environmental_score(nodes_gdf, sector_name: str) -> float:
    """Calculate environmental quality score based on GVI and SVF."""
    
    sector_nodes = nodes_gdf[nodes_gdf["sector_name"] == sector_name]
    
    if sector_nodes.empty:
        return 50.0  # Default middle score
    
    # Calculate average GVI and SVF
    avg_gvi = sector_nodes["gvi"].mean()
    avg_svf = sector_nodes["svf"].mean()
    
    # GVI score: higher is better (0-100)
    gvi_score = min(avg_gvi, 100.0)
    
    # SVF score: lower is better for shade, so invert (0-100)  
    svf_score = max(100.0 - avg_svf, 0.0)
    
    # Combine GVI and SVF (equal weight)
    environmental_score = (gvi_score + svf_score) / 2
    
    return environmental_score


def _calculate_infrastructure_score(edges_gdf, nodes_gdf, sector_name: str) -> float:
    """Calculate infrastructure quality score based on road network properties."""
    
    # Get sector nodes and edges
    sector_nodes = nodes_gdf[nodes_gdf["sector_name"] == sector_name]
    
    if sector_nodes.empty:
        return 50.0
    
    sector_node_ids = set(sector_nodes["osmid"])
    sector_edges = edges_gdf[
        (edges_gdf["u"].isin(sector_node_ids)) & 
        (edges_gdf["v"].isin(sector_node_ids))
    ]
    
    if sector_edges.empty:
        return 30.0  # Poor score for no internal roads
    
    # Calculate infrastructure metrics
    
    # 1. Road type quality (highway classification)
    road_quality_score = _calculate_road_quality_score(sector_edges)
    
    # 2. Network density (edges per area - approximated by node count)
    if len(sector_nodes) > 0:
        density_score = min((len(sector_edges) / len(sector_nodes)) * 20, 100)
    else:
        density_score = 0
    
    # 3. Average edge length (shorter edges = more granular network)
    avg_length = sector_edges["length"].mean() if not sector_edges.empty else 1000
    length_score = max(100 - (avg_length / 20), 0)  # Prefer shorter segments
    
    # Combine scores
    infrastructure_score = (road_quality_score * 0.5 + density_score * 0.3 + length_score * 0.2)
    
    return min(infrastructure_score, 100.0)


def _calculate_road_quality_score(edges_gdf) -> float:
    """Score road quality based on highway types."""
    
    if edges_gdf.empty:
        return 30.0
    
    # Road type scoring
    road_scores = {
        "pedestrian": 100,
        "footway": 100, 
        "path": 90,
        "cycleway": 85,
        "residential": 80,
        "living_street": 85,
        "service": 70,
        "tertiary": 60,
        "secondary": 50,
        "primary": 40,
        "trunk": 30,
        "motorway": 10
    }
    
    # Calculate weighted average based on edge lengths
    total_length = 0
    weighted_score = 0
    
    for _, edge in edges_gdf.iterrows():
        highway_type = edge.get("highway", "residential")
        length = edge.get("length", 100)
        score = road_scores.get(highway_type, 60)  # Default to 60
        
        weighted_score += score * length
        total_length += length
    
    if total_length > 0:
        return weighted_score / total_length
    else:
        return 60.0


def _calculate_connectivity_score(edges_gdf, nodes_gdf, sector_name: str) -> float:
    """Calculate connectivity score based on network topology."""
    
    sector_nodes = nodes_gdf[nodes_gdf["sector_name"] == sector_name]
    
    if sector_nodes.empty:
        return 50.0
    
    sector_node_ids = set(sector_nodes["osmid"])
    sector_edges = edges_gdf[
        (edges_gdf["u"].isin(sector_node_ids)) & 
        (edges_gdf["v"].isin(sector_node_ids))
    ]
    
    if len(sector_nodes) < 2:
        return 30.0
    
    # Calculate connectivity metrics
    
    # 1. Edge-to-node ratio (higher = more connected)
    if len(sector_nodes) > 0:
        connectivity_ratio = len(sector_edges) / len(sector_nodes)
        ratio_score = min(connectivity_ratio * 25, 100)  # Normalize
    else:
        ratio_score = 0
    
    # 2. Calculate node degrees (connections per node)
    node_degrees = {}
    for _, edge in sector_edges.iterrows():
        u, v = edge["u"], edge["v"]
        node_degrees[u] = node_degrees.get(u, 0) + 1
        node_degrees[v] = node_degrees.get(v, 0) + 1
    
    if node_degrees:
        avg_degree = sum(node_degrees.values()) / len(node_degrees)
        degree_score = min(avg_degree * 15, 100)  # Normalize
    else:
        degree_score = 30.0
    
    # Combine scores
    connectivity_score = (ratio_score * 0.6 + degree_score * 0.4)
    
    return min(connectivity_score, 100.0)


def _get_sector_avg_gvi(nodes_gdf, sector_name: str) -> float:
    """Get average GVI for a sector."""
    sector_nodes = nodes_gdf[nodes_gdf["sector_name"] == sector_name]
    return sector_nodes["gvi"].mean() if not sector_nodes.empty else 0.0


def _get_sector_avg_svf(nodes_gdf, sector_name: str) -> float:
    """Get average SVF for a sector."""
    sector_nodes = nodes_gdf[nodes_gdf["sector_name"] == sector_name]
    return sector_nodes["svf"].mean() if not sector_nodes.empty else 0.0


def _count_sector_edges(edges_gdf, nodes_gdf, sector_name: str) -> int:
    """Count edges within a sector."""
    sector_nodes = nodes_gdf[nodes_gdf["sector_name"] == sector_name]
    if sector_nodes.empty:
        return 0
    
    sector_node_ids = set(sector_nodes["osmid"])
    sector_edges = edges_gdf[
        (edges_gdf["u"].isin(sector_node_ids)) & 
        (edges_gdf["v"].isin(sector_node_ids))
    ]
    return len(sector_edges)


def compare_walk_scores(original_df: pd.DataFrame, dynamic_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compare original walk scores with dynamic scores.
    
    Args:
        original_df: Original sectors dataframe
        dynamic_df: Updated sectors dataframe with dynamic scores
        
    Returns:
        DataFrame with comparison metrics
    """
    
    comparison = dynamic_df[["sector_name", "dynamic_walk_score", "original_walk_score", "score_improvement", "walk_score_rank"]].copy()
    
    # Add ranking changes
    original_df_sorted = original_df.sort_values("walk_score", ascending=False).reset_index(drop=True)
    original_df_sorted["original_rank"] = range(1, len(original_df_sorted) + 1)
    
    comparison = comparison.merge(
        original_df_sorted[["sector_name", "original_rank"]], 
        on="sector_name", 
        how="left"
    )
    
    # Handle missing values in ranking
    comparison["original_rank"] = comparison["original_rank"].fillna(len(comparison))
    comparison["rank_change"] = comparison["original_rank"] - comparison["walk_score_rank"]
    
    # Add improvement categories
    comparison["improvement_category"] = pd.cut(
        comparison["score_improvement"],
        bins=[-np.inf, -10, -5, 5, 10, np.inf],
        labels=["Significant Decrease", "Moderate Decrease", "No Change", "Moderate Increase", "Significant Increase"]
    )
    
    return comparison.sort_values("dynamic_walk_score", ascending=False)


def generate_profile_insights(weights: Dict[str, float], dynamic_scores_df: pd.DataFrame) -> Dict[str, any]:
    """
    Generate insights about how the user profile affects walkability rankings.
    
    Args:
        weights: Category weights used
        dynamic_scores_df: DataFrame with dynamic walk scores
        
    Returns:
        Dictionary with insights and recommendations
    """
    
    # Find highest weighted categories
    sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
    top_categories = [cat for cat, weight in sorted_weights[:3]]
    
    # Find sectors that rank high in top categories
    top_sectors_for_profile = []
    
    for category in top_categories:
        score_col = f"{category}_score"
        if score_col in dynamic_scores_df.columns:
            top_sector = dynamic_scores_df.nlargest(1, score_col).iloc[0]
            top_sectors_for_profile.append({
                "category": category,
                "sector": top_sector["sector_name"],
                "score": top_sector[score_col]
            })
    
    # Find biggest winners and losers
    biggest_improver = dynamic_scores_df.nlargest(1, "score_improvement").iloc[0]
    biggest_decliner = dynamic_scores_df.nsmallest(1, "score_improvement").iloc[0]
    
    insights = {
        "profile_priorities": {
            "top_categories": top_categories,
            "category_weights": {cat: weights[cat] for cat in top_categories}
        },
        "recommended_sectors": top_sectors_for_profile,
        "ranking_changes": {
            "biggest_improver": {
                "sector": biggest_improver["sector_name"],
                "improvement": biggest_improver["score_improvement"],
                "new_rank": biggest_improver["walk_score_rank"]
            },
            "biggest_decliner": {
                "sector": biggest_decliner["sector_name"], 
                "decline": biggest_decliner["score_improvement"],
                "new_rank": biggest_decliner["walk_score_rank"]
            }
        },
        "summary_stats": {
            "avg_score_change": dynamic_scores_df["score_improvement"].mean(),
            "sectors_improved": len(dynamic_scores_df[dynamic_scores_df["score_improvement"] > 0]),
            "sectors_declined": len(dynamic_scores_df[dynamic_scores_df["score_improvement"] < 0])
        }
    }
    
    return insights 