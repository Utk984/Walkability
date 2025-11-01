import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
from typing import Dict, List, Tuple, Optional
from scipy.spatial.distance import cdist
import math
from config import CATEGORY_MAP
import json

class ComprehensiveWalkabilityCalculator:
    """
    Advanced walkability calculator with proper POI category weighting and profile integration.
    """
    
    def __init__(self, buffer_radius: float = 500.0, poi_category_weights: Optional[Dict] = None):
        """
        Initialize the calculator.
        
        Args:
            buffer_radius: Buffer radius in meters for POI analysis (default 500m)
            poi_category_weights: Weights for different POI categories from user profile
        """
        self.buffer_radius = buffer_radius
        
        # Default component weights
        self.component_weights = {
            'poi_accessibility': 0.40,   # How many POIs nearby (weighted by category)
            'poi_diversity': 0.25,       # Variety of POI types
            'environmental': 0.25,       # GVI and SVF combined
            'green_infrastructure': 0.10 # Green connectivity
        }
        
        # POI category weights (from user profile or defaults)
        self.poi_category_weights = poi_category_weights or {
            'Commercial': 1.0,
            'Food & Dining': 1.0,
            'Health & Medical': 1.0,
            'Education': 1.0,
            'Transportation': 1.0,
            'Recreation & Entertainment': 1.0,
            'Services': 1.0
        }
        
        # Cache for expensive operations
        self._poi_categories_cache = {}
    
    def calculate_comprehensive_scores(self, data: Dict) -> gpd.GeoDataFrame:
        """
        Calculate comprehensive walkability scores for all sectors with proper differentiation.
        """
        sectors_gdf = data["sectors_gdf"].copy()
        nodes_gdf = data["nodes_gdf"]
        pois_gdf = data["pois_gdf"]
        
        print("🚀 Starting comprehensive walkability calculation...")
        print(f"📊 Processing {len(sectors_gdf)} sectors with {len(pois_gdf)} POIs...")
        
        # Pre-calculate POI categories
        pois_with_categories = self._preprocess_poi_categories(pois_gdf)
        
        results = []
        total_sectors = len(sectors_gdf)
        
        for idx, sector in sectors_gdf.iterrows():
            sector_name = sector["sector_name"]
            progress = f"({idx+1}/{total_sectors})"
            print(f"📍 Processing {sector_name} {progress}...")
            
            # Get nodes within this sector
            sector_nodes = nodes_gdf[nodes_gdf["sector_name"] == sector_name]
            
            if sector_nodes.empty:
                print(f"⚠️  No nodes found for {sector_name}")
                result = self._create_default_scores(sector_name)
            else:
                # Calculate proper sector-specific scores
                result = self._calculate_sector_scores_properly(
                    sector_name, sector_nodes, pois_with_categories, sector.geometry
                )
            
            results.append(result)
        
        # Create results DataFrame
        results_df = pd.DataFrame(results)
        
        # Merge with sectors
        updated_sectors = sectors_gdf.merge(
            results_df, 
            left_on="sector_name", 
            right_on="sector_name", 
            how="left"
        )
        
        # Update walk_score column
        updated_sectors["walk_score"] = updated_sectors["comprehensive_walk_score"]
        
        print("✅ Comprehensive walkability calculation completed!")
        
        # Print summary to verify different scores
        print(f"\n📊 Score Summary:")
        print(f"   Mean: {updated_sectors['comprehensive_walk_score'].mean():.1f}")
        print(f"   Min: {updated_sectors['comprehensive_walk_score'].min():.1f}")
        print(f"   Max: {updated_sectors['comprehensive_walk_score'].max():.1f}")
        print(f"   Std: {updated_sectors['comprehensive_walk_score'].std():.1f}")
        
        return updated_sectors
    
    def _preprocess_poi_categories(self, pois_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Pre-process POI categories."""
        pois_with_categories = pois_gdf.copy()
        
        categories = []
        for _, poi in pois_gdf.iterrows():
            poi_type = poi.get('secondary_type', poi.get('primary_type', ''))
            category = self._get_poi_category(poi_type)
            categories.append(category)
        
        pois_with_categories['category'] = categories
        return pois_with_categories
    
    def _get_poi_category(self, poi_type: str) -> str:
        """Get category for a POI type with caching."""
        if poi_type in self._poi_categories_cache:
            return self._poi_categories_cache[poi_type]
        
        for category, poi_types in CATEGORY_MAP.items():
            if poi_type in poi_types:
                self._poi_categories_cache[poi_type] = category
                return category
        
        self._poi_categories_cache[poi_type] = 'Services'  # Default category
        return 'Services'
    
    def _calculate_sector_scores_properly(self, sector_name: str, sector_nodes: gpd.GeoDataFrame, 
                                        pois_gdf: gpd.GeoDataFrame, sector_geometry) -> Dict:
        """Calculate proper sector-specific scores with real differentiation."""
        
        # Calculate environmental scores from actual node data
        if 'gvi' in sector_nodes.columns and len(sector_nodes) > 0:
            sector_gvi = sector_nodes['gvi'].mean()
            sector_svf = sector_nodes['svf'].mean() if 'svf' in sector_nodes.columns else 50.0
        else:
            sector_gvi = 0.0
            sector_svf = 50.0
        
        # Environmental scoring
        gvi_score = max(0.0, min(1.0, sector_gvi / 100.0))
        svf_score = max(0.0, min(1.0, 1.0 - (sector_svf / 100.0)))
        environmental_score = (gvi_score + svf_score) / 2
        
        # Green infrastructure scoring
        high_gvi_nodes = sector_nodes[sector_nodes['gvi'] > 30] if 'gvi' in sector_nodes.columns else gpd.GeoDataFrame()
        green_ratio = len(high_gvi_nodes) / len(sector_nodes) if len(sector_nodes) > 0 else 0
        green_infrastructure_score = green_ratio
        
        # POI analysis using multiple representative points in sector
        poi_metrics = self._calculate_poi_metrics_properly(sector_geometry, pois_gdf)
        
        # Calculate final comprehensive score using component weights
        comprehensive_score = (
            poi_metrics['weighted_poi_score'] * self.component_weights['poi_accessibility'] +
            poi_metrics['diversity_score'] * self.component_weights['poi_diversity'] +
            environmental_score * self.component_weights['environmental'] +
            green_infrastructure_score * self.component_weights['green_infrastructure']
        )
        
        result = {
            'sector_name': sector_name,
            'comprehensive_walk_score': comprehensive_score * 100,  # Scale to 0-100
            
            # Component scores
            'poi_accessibility_score': poi_metrics['weighted_poi_score'] * 100,
            'poi_diversity_score': poi_metrics['diversity_score'] * 100,
            'environmental_score': environmental_score * 100,
            'green_infrastructure_score': green_infrastructure_score * 100,
            
            # Raw metrics for analysis
            'total_pois': poi_metrics['total_pois'],
            'weighted_pois': poi_metrics['weighted_total'],
            'poi_categories': poi_metrics['unique_categories'],
            'raw_gvi': sector_gvi,
            'raw_svf': sector_svf,
            'green_nodes': len(high_gvi_nodes),
            'total_nodes': len(sector_nodes),
            
            # Detailed breakdown for insights
            'poi_breakdown': poi_metrics['category_breakdown'],
            'score_components': {
                'poi_accessibility': poi_metrics['weighted_poi_score'],
                'poi_diversity': poi_metrics['diversity_score'],
                'environmental_quality': environmental_score,
                'green_infrastructure': green_infrastructure_score
            }
        }
        
        return result
    
    def _calculate_poi_metrics_properly(self, sector_geometry, pois_gdf: gpd.GeoDataFrame) -> Dict:
        """Calculate POI metrics with proper category weighting and sector-specific analysis."""
        
        # Use sector centroid for buffer analysis
        sector_centroid = sector_geometry.centroid
        
        # Convert buffer radius from meters to degrees for WGS84
        # At Chandigarh latitude (~30.7°), 1 degree ≈ 111 km
        buffer_radius_degrees = self.buffer_radius / 111000.0  # Convert meters to degrees
        buffer = sector_centroid.buffer(buffer_radius_degrees)
        
        # Find POIs within buffer
        nearby_pois = pois_gdf[pois_gdf.geometry.within(buffer)]
        
        if nearby_pois.empty:
            return {
                'weighted_poi_score': 0.0,
                'diversity_score': 0.0,
                'total_pois': 0,
                'weighted_total': 0.0,
                'unique_categories': 0,
                'category_breakdown': {}
            }
        
        # Calculate category breakdown with weights
        category_counts = {}
        weighted_total = 0.0
        
        for _, poi in nearby_pois.iterrows():
            category = poi['category']
            weight = self.poi_category_weights.get(category, 1.0)
            
            if category not in category_counts:
                category_counts[category] = {'count': 0, 'weighted_count': 0.0}
            
            category_counts[category]['count'] += 1
            category_counts[category]['weighted_count'] += weight
            weighted_total += weight
        
        # Accessibility score (weighted POI count with logarithmic scaling)
        max_expected_weighted = 100  # Adjusted for realistic POI counts per sector
        weighted_poi_score = np.log(1 + weighted_total) / np.log(1 + max_expected_weighted)
        weighted_poi_score = min(weighted_poi_score, 1.0)
        
        # Diversity score (number of different categories)
        unique_categories = len(category_counts)
        total_categories = len(CATEGORY_MAP)
        diversity_score = unique_categories / total_categories
        
        return {
            'weighted_poi_score': weighted_poi_score,
            'diversity_score': diversity_score,
            'total_pois': len(nearby_pois),
            'weighted_total': weighted_total,
            'unique_categories': unique_categories,
            'category_breakdown': category_counts
        }
    
    def _create_default_scores(self, sector_name: str) -> Dict:
        """Create default scores for sectors with no data."""
        return {
            'sector_name': sector_name,
            'comprehensive_walk_score': 0.0,
            'poi_accessibility_score': 0.0,
            'poi_diversity_score': 0.0,
            'environmental_score': 0.0,
            'green_infrastructure_score': 0.0,
            'total_pois': 0,
            'weighted_pois': 0.0,
            'poi_categories': 0,
            'raw_gvi': 0.0,
            'raw_svf': 50.0,
            'green_nodes': 0,
            'total_nodes': 0,
            'poi_breakdown': {},
            'score_components': {
                'poi_accessibility': 0.0,
                'poi_diversity': 0.0,
                'environmental_quality': 0.0,
                'green_infrastructure': 0.0
            }
        }
    
    def update_poi_weights(self, new_weights: Dict[str, float]):
        """Update POI category weights (from user profile)."""
        self.poi_category_weights.update(new_weights)
        print(f"✅ Updated POI category weights: {self.poi_category_weights}")
    
    def update_component_weights(self, new_weights: Dict[str, float]):
        """Update component weights."""
        total_weight = sum(new_weights.values())
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"Component weights must sum to 1.0, got {total_weight}")
        
        self.component_weights.update(new_weights)
        print(f"✅ Updated component weights: {self.component_weights}")


def calculate_walkability_with_profile(data: Dict, profile_weights: Optional[Dict] = None, 
                                     save_to_file: bool = True) -> gpd.GeoDataFrame:
    """
    Main function to calculate walkability scores with optional profile weights.
    This is the core pipeline function.
    
    Args:
        data: Dictionary containing all geospatial data
        profile_weights: Optional POI category weights from user profile
        save_to_file: Whether to save results to file
        
    Returns:
        Updated sectors GeoDataFrame with comprehensive walkability scores
    """
    
    print("🔄 Starting walkability calculation pipeline...")
    
    # Initialize calculator with profile weights
    calculator = ComprehensiveWalkabilityCalculator(
        buffer_radius=500.0,
        poi_category_weights=profile_weights
    )
    
    # Calculate comprehensive scores
    updated_sectors = calculator.calculate_comprehensive_scores(data)
    
    # Save to file if requested
    if save_to_file:
        output_path = "data/processed/comprehensive_walkability_scores.geojson"
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        updated_sectors.to_file(output_path, driver='GeoJSON')
        print(f"💾 Scores saved to {output_path}")
    
    return updated_sectors


def load_latest_walkability_scores() -> Optional[gpd.GeoDataFrame]:
    """Load the most recently calculated walkability scores from file."""
    try:
        import os
        file_path = "data/processed/comprehensive_walkability_scores.geojson"
        if os.path.exists(file_path):
            return gpd.read_file(file_path)
        else:
            print("⚠️  No saved walkability scores found. Calculate scores first.")
            return None
    except Exception as e:
        print(f"❌ Error loading walkability scores: {e}")
        return None


def generate_profile_based_insights(df, profile_weights):
    """Generate insights and recommendations based on comprehensive walkability scores and user profile"""
    
    # Get top performing sectors
    top_sectors = df.nlargest(5, 'comprehensive_walk_score')
    
    # Create recommendations based on scores and profile
    recommendations = []
    for _, sector in top_sectors.iterrows():
        # Use the correct column name from the saved file
        poi_count = int(sector['total_pois_x']) if 'total_pois_x' in sector else 0
        
        recommendations.append({
            "name": sector['sector_name'],
            "score": round(sector['comprehensive_walk_score'], 1),
            "reason": f"High overall walkability with {poi_count} nearby amenities"
        })
    
    # Find sectors that match user priorities
    priority_matches = []
    
    # If user prioritizes restaurants/food
    if profile_weights and profile_weights.get('food_drinks', 0) > 0.15:
        food_focused = df[df['comprehensive_walk_score'] > df['comprehensive_walk_score'].mean()]
        if not food_focused.empty:
            best_food_sector = food_focused.nlargest(1, 'comprehensive_walk_score').iloc[0]
            priority_matches.append({
                "sector": best_food_sector['sector_name'],
                "priority": "Food & Dining",
                "score": round(best_food_sector['comprehensive_walk_score'], 1),
                "description": "Great for food enthusiasts with diverse dining options"
            })
    
    # If user prioritizes healthcare/essential services
    if profile_weights and profile_weights.get('essential_services', 0) > 0.3:
        essential_focused = df[df['comprehensive_walk_score'] > df['comprehensive_walk_score'].mean()]
        if not essential_focused.empty:
            best_essential_sector = essential_focused.nlargest(1, 'comprehensive_walk_score').iloc[0]
            priority_matches.append({
                "sector": best_essential_sector['sector_name'],
                "priority": "Essential Services",
                "score": round(best_essential_sector['comprehensive_walk_score'], 1),
                "description": "Excellent access to healthcare, banks, and essential services"
            })
    
    # Environmental highlights for high GVI sectors
    environmental_highlights = []
    high_green_sectors = df[df['raw_gvi'] > df['raw_gvi'].mean() + df['raw_gvi'].std()]
    
    for _, sector in high_green_sectors.head(3).iterrows():
        environmental_highlights.append({
            "sector": sector['sector_name'],
            "gvi": round(sector['raw_gvi'], 1),
            "feature": "High green visibility",
            "benefit": "Great for nature lovers and outdoor activities"
        })
    
    # Generate summary
    avg_score = df['comprehensive_walk_score'].mean()
    top_score = df['comprehensive_walk_score'].max()
    
    summary = f"Based on your preferences, we've identified {len(recommendations)} top sectors. "
    summary += f"Average walkability score is {avg_score:.1f}, with the best sector scoring {top_score:.1f}. "
    
    if profile_weights:
        primary_interest = max(profile_weights.items(), key=lambda x: x[1])
        summary += f"Given your interest in {primary_interest[0].replace('_', ' ')}, we've highlighted sectors that excel in this area."
    
    return {
        "recommended_sectors": recommendations,
        "priority_matches": priority_matches,
        "environmental_highlights": environmental_highlights,
        "summary": summary,
        "total_analyzed": len(df),
        "score_range": {
            "min": round(df['comprehensive_walk_score'].min(), 1),
            "max": round(df['comprehensive_walk_score'].max(), 1),
            "mean": round(avg_score, 1)
        }
    }


def get_sector_analysis_from_scores(sector_name: str) -> Dict:
    """Get detailed sector analysis using the latest comprehensive scores."""
    
    scores_gdf = load_latest_walkability_scores()
    if scores_gdf is None:
        return {"error": "No walkability scores available. Calculate scores first."}
    
    sector_data = scores_gdf[scores_gdf['sector_name'] == sector_name]
    if sector_data.empty:
        return {"error": f"Sector {sector_name} not found"}
    
    sector = sector_data.iloc[0]
    
    # Use the correct column names from the saved file
    total_pois = int(sector['total_pois_x']) if 'total_pois_x' in sector else 0
    weighted_pois = sector.get('weighted_pois', 0)
    poi_categories = int(sector.get('poi_categories', 0))
    green_nodes = int(sector.get('green_nodes', 0))
    total_nodes = int(sector.get('total_nodes', 0))
    
    # Create comprehensive analysis
    analysis = {
        "sector_name": sector_name,
        "overall_score": round(sector['comprehensive_walk_score'], 1),
        "rank": int((scores_gdf['comprehensive_walk_score'] > sector['comprehensive_walk_score']).sum() + 1),
        "total_sectors": len(scores_gdf),
        
        "components": {
            "POI Accessibility": {
                "score": round(sector['poi_accessibility_score'], 1),
                "details": f"{total_pois} POIs nearby (weighted: {weighted_pois:.1f})"
            },
            "POI Diversity": {
                "score": round(sector['poi_diversity_score'], 1),
                "details": f"{poi_categories} different amenity types"
            },
            "Environmental Quality": {
                "score": round(sector['environmental_score'], 1),
                "details": f"GVI: {sector['raw_gvi']:.1f}%, SVF: {sector['raw_svf']:.1f}%"
            },
            "Green Infrastructure": {
                "score": round(sector['green_infrastructure_score'], 1),
                "details": f"{green_nodes} green nodes out of {total_nodes}"
            }
        },
        
        "poi_breakdown": sector.get('poi_breakdown', {}),
        "percentile": round((1 - (int((scores_gdf['comprehensive_walk_score'] > sector['comprehensive_walk_score']).sum()) / len(scores_gdf))) * 100, 1)
    }
    
    return analysis 