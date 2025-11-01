import geopandas as gpd
import pandas as pd
import folium
from branca.colormap import linear
from config import CATEGORY_MAP, CATEGORY_COLORS


def analyze_sector_amenities(data: dict, sector_name: str):
    """
    Analyze amenities within a specific sector using comprehensive walkability scores.
    
    Args:
        data: Dict containing sectors_gdf and pois_gdf
        sector_name: Name of the sector to analyze
    
    Returns:
        tuple: (map, summary_dict, category_counts_df)
    """
    sectors_gdf = data["sectors_gdf"]
    pois_gdf = data["pois_gdf"]

    # Try to get comprehensive analysis first
    try:
        from src.analysis.comprehensive_walkability import get_sector_analysis_from_scores
        comprehensive_analysis = get_sector_analysis_from_scores(sector_name)
        
        if "error" not in comprehensive_analysis:
            # Use comprehensive analysis
            use_comprehensive = True
            sector_info = comprehensive_analysis
        else:
            use_comprehensive = False
    except:
        use_comprehensive = False

    # Fallback to basic analysis if comprehensive not available
    matching = sectors_gdf[sectors_gdf["sector_name"] == sector_name]
    if matching.empty:
        return None, f"Sector '{sector_name}' not found.", None

    sector_poly = matching.iloc[0].geometry
    pois_in_sector = pois_gdf[pois_gdf.geometry.within(sector_poly)].copy()
    category_counts = {cat: 0 for cat in CATEGORY_MAP.keys()}

    # Map center at this sector's centroid
    centroid = (
        matching
        .to_crs(epsg=3857)
        .centroid
        .to_crs(epsg=4326)
        .iloc[0]
    )
    m = folium.Map(location=[centroid.y, centroid.x], zoom_start=14)

    category_layers = {
        cat: folium.FeatureGroup(name=cat) for cat in CATEGORY_MAP.keys()
    }

    for _, row in pois_in_sector.iterrows():
        primary_type = row.get("primary_type")
        if primary_type not in CATEGORY_COLORS:
            continue

        category_counts[primary_type] += 1

        popup_text = f"<div style='min-width: 200px;'>{row.get('name', 'Unnamed POI')}<br>{row['secondary_type']}</div>"

        # Get coordinates from geometry
        coords = [row.geometry.y, row.geometry.x]

        folium.CircleMarker(
            location=coords,
            radius=5,
            popup=popup_text,
            color=CATEGORY_COLORS[primary_type],
            fill=True,
            fill_color=CATEGORY_COLORS[primary_type],
            fill_opacity=0.7,
            weight=1
        ).add_to(category_layers[primary_type])

    for layer in category_layers.values():
        m.add_child(layer)
    folium.LayerControl().add_to(m)

    category_counts_df = pd.DataFrame({
        "Category": list(category_counts.keys()),
        "Count": list(category_counts.values())
    }).sort_values("Count", ascending=False)

    # Create comprehensive summary
    if use_comprehensive:
        summary = {
            "Sector": sector_name,
            "Comprehensive Walk Score": round(sector_info["overall_score"], 1),
            "Walk Score": round(sector_info["overall_score"], 1),
            "Rank": f"{sector_info['rank']} of {sector_info['total_sectors']}",
            "Percentile": f"{sector_info['percentile']}th",
            "Total POIs": len(pois_in_sector),
            "Category Distribution": category_counts,
            "Component Scores": {
                "POI Accessibility": sector_info["components"]["POI Accessibility"]["score"],
                "POI Diversity": sector_info["components"]["POI Diversity"]["score"],
                "Environmental Quality": sector_info["components"]["Environmental Quality"]["score"],
                "Green Infrastructure": sector_info["components"]["Green Infrastructure"]["score"]
            },
            "Component Details": {
                "POI Accessibility": sector_info["components"]["POI Accessibility"]["details"],
                "POI Diversity": sector_info["components"]["POI Diversity"]["details"],
                "Environmental Quality": sector_info["components"]["Environmental Quality"]["details"],
                "Green Infrastructure": sector_info["components"]["Green Infrastructure"]["details"]
            }
        }
    else:
        # Fallback to basic summary
        walk_score = matching.iloc[0].get("walk_score")
        total_pois = matching.iloc[0].get("total_pois", len(pois_in_sector))

        summary = {
            "Sector": sector_name,
            "Walk Score": float(walk_score) if walk_score is not None else None,
            "Total POIs": int(total_pois),
            "Category Distribution": category_counts
        }

    return m, summary, category_counts_df


def compare_sectors(data: dict, sector1: str, sector2: str):
    """
    Compare amenities and walkability between two sectors.
    
    Args:
        data: Dict containing geospatial data
        sector1: Name of first sector
        sector2: Name of second sector
    
    Returns:
        tuple: (map, summary_comparison_dict, comparison_df)
    """
    m1, summary1, counts1 = analyze_sector_amenities(data, sector1)
    m2, summary2, counts2 = analyze_sector_amenities(data, sector2)

    if isinstance(summary1, str) or isinstance(summary2, str):
        msg = ""
        if isinstance(summary1, str):
            msg += summary1 + "\n"
        if isinstance(summary2, str):
            msg += summary2 + "\n"
        return None, msg, None

    # Build comparison DataFrame with descriptive column names
    comp_df = pd.DataFrame({
        "Category": counts1["Category"],
        f"Sector {sector1}": counts1["Count"].values,
        f"Sector {sector2}": counts2["Count"].values,
        "Difference (Sector1 - Sector2)": counts1["Count"].values - counts2["Count"].values
    })

    walk_score1 = summary1["Walk Score"]
    walk_score2 = summary2["Walk Score"]
    total_pois1 = summary1["Total POIs"]
    total_pois2 = summary2["Total POIs"]

    walk_diff = abs(walk_score1 - walk_score2)
    poi_diff = abs(total_pois1 - total_pois2)
    higher_walk_sector = sector1 if walk_score1 > walk_score2 else sector2
    higher_poi_sector = sector1 if total_pois1 > total_pois2 else sector2

    # Prepare a user-friendly summary dictionary
    summary_comparison = {
        f"Sector {sector1} Walk Score": walk_score1,
        f"Sector {sector2} Walk Score": walk_score2,
        "Walk Score Gap (absolute)": walk_diff,
        "Sector with Higher Walk Score": f"Sector {higher_walk_sector}",
        f"Sector {sector1} Total POIs": total_pois1,
        f"Sector {sector2} Total POIs": total_pois2,
        "POI Gap (absolute)": poi_diff,
        "Sector with More POIs": f"Sector {higher_poi_sector}"
    }

    sectors_gdf = data["sectors_gdf"]
    m = folium.Map(location=[30.7333, 76.7794], zoom_start=12)

    s1_gdf = sectors_gdf[sectors_gdf["sector_name"] == sector1]
    s2_gdf = sectors_gdf[sectors_gdf["sector_name"] == sector2]

    if s1_gdf.empty or s2_gdf.empty:
        missing = sector1 if s1_gdf.empty else sector2
        return None, f"Sector '{missing}' not found.", None

    folium.GeoJson(
        s1_gdf,
        style_function=lambda _: {
            "fillColor": "#FF5555",
            "color": "#AA0000",
            "weight": 2,
            "fillOpacity": 0.5
        },
        tooltip=(f"Sector {sector1}: Walk Score {summary1['Walk Score']:.2f}, "
                 f"POIs: {summary1['Total POIs']}")
    ).add_to(m)

    folium.GeoJson(
        s2_gdf,
        style_function=lambda _: {
            "fillColor": "#5555FF",
            "color": "#0000AA",
            "weight": 2,
            "fillOpacity": 0.5
        },
        tooltip=(f"Sector {sector2}: Walk Score {summary2['Walk Score']:.2f}, "
                 f"POIs: {summary2['Total POIs']}")
    ).add_to(m)

    return m, summary_comparison, comp_df


def get_top_walkscore_sectors(data: dict, k: int = 5):
    """
    Get top k sectors by comprehensive walkability score.
    
    Args:
        data: Dict containing sectors_gdf
        k: Number of top sectors to return
    
    Returns:
        tuple: (map, DataFrame) for top-k sectors
    """
    # Load the latest comprehensive walkability scores
    try:
        from src.analysis.comprehensive_walkability import load_latest_walkability_scores
        comprehensive_sectors = load_latest_walkability_scores()
        
        if comprehensive_sectors is not None:
            # Use comprehensive scores
            sectors_gdf = comprehensive_sectors
            score_column = "comprehensive_walk_score"
            score_label = "Comprehensive Walk Score"
        else:
            # Fallback to original data
            sectors_gdf = data["sectors_gdf"]
            score_column = "walk_score"
            score_label = "Walk Score"
    except:
        # Fallback to original data
        sectors_gdf = data["sectors_gdf"]
        score_column = "walk_score"
        score_label = "Walk Score"

    # Sort sectors by score descending
    top_df = sectors_gdf.sort_values(score_column, ascending=False).head(k)

    city_center = [30.7333, 76.7794]
    m = folium.Map(location=city_center, zoom_start=12)

    # Add all sectors in light gray
    folium.GeoJson(
        sectors_gdf,
        style_function=lambda feature: {
            "fillColor": "#EEEEEE",
            "color": "#CCCCCC",
            "weight": 1,
            "fillOpacity": 0.5
        }
    ).add_to(m)

    # Highlight the top-k
    for _, row in top_df.iterrows():
        single = gpd.GeoDataFrame(
            [row],
            geometry=[row.geometry],
            crs=sectors_gdf.crs
        )
        
        # Get additional info for tooltip
        pois = row.get('total_pois', row.get('total_pois_y', row.get('total_pois_x', 0)))
        env_score = row.get('environmental_score', 0)
        gvi = row.get('raw_gvi', 0)
        
        tooltip = (
            f"Sector: {row['sector_name']}<br>"
            f"{score_label}: {row[score_column]:.1f}<br>"
            f"Total POIs: {int(pois)}<br>"
            f"Environmental Score: {env_score:.1f}<br>"
            f"GVI: {gvi:.1f}%"
        )
        
        folium.GeoJson(
            single,
            style_function=lambda _: {
                "fillColor": "#FF0000",
                "color": "#880000",
                "weight": 2,
                "fillOpacity": 0.7
            },
            tooltip=tooltip
        ).add_to(m)

    # Build DataFrame for output table
    pois_data = []
    env_data = []
    
    for _, row in top_df.iterrows():
        pois = row.get('total_pois', row.get('total_pois_y', row.get('total_pois_x', 0)))
        env = row.get('environmental_score', 0)
        pois_data.append(int(pois))
        env_data.append(f"{env:.1f}")
    
    top_table = pd.DataFrame({
        "Sector": top_df["sector_name"].values,
        score_label: [f"{score:.1f}" for score in top_df[score_column].values],
        "Total POIs": pois_data,
        "Environmental": env_data
    })

    return m, top_table


def get_bottom_walkscore_sectors(data: dict, k: int = 5):
    """
    Get bottom k sectors by comprehensive walkability score.
    
    Args:
        data: Dict containing sectors_gdf
        k: Number of bottom sectors to return
    
    Returns:
        tuple: (map, DataFrame) for bottom-k sectors
    """
    # Load the latest comprehensive walkability scores
    try:
        from src.analysis.comprehensive_walkability import load_latest_walkability_scores
        comprehensive_sectors = load_latest_walkability_scores()
        
        if comprehensive_sectors is not None:
            # Use comprehensive scores
            sectors_gdf = comprehensive_sectors
            score_column = "comprehensive_walk_score"
            score_label = "Comprehensive Walk Score"
        else:
            # Fallback to original data
            sectors_gdf = data["sectors_gdf"]
            score_column = "walk_score"
            score_label = "Walk Score"
    except:
        # Fallback to original data
        sectors_gdf = data["sectors_gdf"]
        score_column = "walk_score"
        score_label = "Walk Score"

    # Sort ascending (lowest) by score
    bottom_df = sectors_gdf.sort_values(score_column, ascending=True).head(k)

    city_center = [30.7333, 76.7794]
    m = folium.Map(location=city_center, zoom_start=12)

    # Add all sectors in light gray
    folium.GeoJson(
        sectors_gdf,
        style_function=lambda feature: {
            "fillColor": "#EEEEEE",
            "color": "#CCCCCC",
            "weight": 1,
            "fillOpacity": 0.5
        }
    ).add_to(m)

    # Highlight the bottom-k
    for _, row in bottom_df.iterrows():
        single = gpd.GeoDataFrame(
            [row],
            geometry=[row.geometry],
            crs=sectors_gdf.crs
        )
        
        # Get additional info for tooltip
        pois = row.get('total_pois', row.get('total_pois_y', row.get('total_pois_x', 0)))
        env_score = row.get('environmental_score', 0)
        gvi = row.get('raw_gvi', 0)
        
        tooltip = (
            f"Sector: {row['sector_name']}<br>"
            f"{score_label}: {row[score_column]:.1f}<br>"
            f"Total POIs: {int(pois)}<br>"
            f"Environmental Score: {env_score:.1f}<br>"
            f"GVI: {gvi:.1f}%"
        )
        
        folium.GeoJson(
            single,
            style_function=lambda _: {
                "fillColor": "#0000FF",
                "color": "#000088",
                "weight": 2,
                "fillOpacity": 0.7
            },
            tooltip=tooltip
        ).add_to(m)

    # Build DataFrame for output table
    pois_data = []
    env_data = []
    
    for _, row in bottom_df.iterrows():
        pois = row.get('total_pois', row.get('total_pois_y', row.get('total_pois_x', 0)))
        env = row.get('environmental_score', 0)
        pois_data.append(int(pois))
        env_data.append(f"{env:.1f}")
    
    bottom_table = pd.DataFrame({
        "Sector": bottom_df["sector_name"].values,
        score_label: [f"{score:.1f}" for score in bottom_df[score_column].values],
        "Total POIs": pois_data,
        "Environmental": env_data
    })

    return m, bottom_table 