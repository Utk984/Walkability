import folium
from branca.colormap import linear
import geopandas as gpd


def create_walkscore_choropleth(data: dict) -> folium.Map:
    """
    Create a choropleth map showing walk scores across sectors.
    
    Args:
        data: Dict containing sectors_gdf with walk_score column
    
    Returns:
        folium.Map: Interactive choropleth map
    """
    sectors_gdf = data["sectors_gdf"]

    # Sanity check for required columns
    if "walk_score" not in sectors_gdf.columns:
        raise KeyError("sectors_gdf must contain 'walk_score' column.")

    city_center = [30.7333, 76.7794]
    m = folium.Map(location=city_center, zoom_start=12)

    # Build continuous colormap for walk_score
    colormap = linear.YlOrRd_09.scale(
        sectors_gdf["walk_score"].min(),
        sectors_gdf["walk_score"].max()
    )
    colormap.caption = "Walkability Score"
    colormap.background = "white"
    colormap.add_to(m)

    # Determine available columns for tooltip
    tooltip_fields = ["sector_name", "walk_score"]
    tooltip_aliases = ["Sector", "Walkability Score"]
    
    # Add additional fields if available (from comprehensive scores)
    if "total_pois" in sectors_gdf.columns:
        tooltip_fields.append("total_pois")
        tooltip_aliases.append("Total POIs")
    elif "total_pois_x" in sectors_gdf.columns:
        tooltip_fields.append("total_pois_x")
        tooltip_aliases.append("Total POIs")
    
    if "environmental_score" in sectors_gdf.columns:
        tooltip_fields.append("environmental_score")
        tooltip_aliases.append("Environmental Score")
    
    if "raw_gvi" in sectors_gdf.columns:
        tooltip_fields.append("raw_gvi")
        tooltip_aliases.append("Green Visibility Index")

    # Add GeoJSON with style_function and tooltip
    folium.GeoJson(
        sectors_gdf,
        style_function=lambda feature: {
            "fillColor": colormap(feature["properties"]["walk_score"]),
            "color": "black",
            "weight": 1,
            "fillOpacity": 0.7
        },
        tooltip=folium.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=tooltip_aliases,
            localize=True
        )
    ).add_to(m)

    return m


def create_sector_highlight_map(sectors_gdf: gpd.GeoDataFrame, 
                               highlighted_sectors: gpd.GeoDataFrame,
                               highlight_color: str = "#FF0000",
                               highlight_description: str = "Highlighted") -> folium.Map:
    """
    Create a map with specific sectors highlighted.
    
    Args:
        sectors_gdf: All sectors geodataframe
        highlighted_sectors: Sectors to highlight
        highlight_color: Color for highlighted sectors
        highlight_description: Description for the highlight
    
    Returns:
        folium.Map: Map with highlighted sectors
    """
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

    # Highlight specific sectors
    for _, row in highlighted_sectors.iterrows():
        single = gpd.GeoDataFrame(
            [row],
            geometry=[row.geometry],
            crs=sectors_gdf.crs
        )
        tooltip = (
            f"Sector: {row['sector_name']}<br>"
            f"Walk Score: {row['walk_score']:.2f}<br>"
            f"Total POIs: {row['total_pois']}"
        )
        folium.GeoJson(
            single,
            style_function=lambda _: {
                "fillColor": highlight_color,
                "color": highlight_color.replace("FF", "88"),  # Darker border
                "weight": 2,
                "fillOpacity": 0.7
            },
            tooltip=tooltip
        ).add_to(m)

    return m


def create_comparison_map(sectors_gdf: gpd.GeoDataFrame, 
                         sector1_name: str, sector2_name: str,
                         summary1: dict, summary2: dict) -> folium.Map:
    """
    Create a map comparing two sectors side by side.
    
    Args:
        sectors_gdf: All sectors geodataframe
        sector1_name: Name of first sector
        sector2_name: Name of second sector
        summary1: Summary stats for sector 1
        summary2: Summary stats for sector 2
    
    Returns:
        folium.Map: Comparison map
    """
    m = folium.Map(location=[30.7333, 76.7794], zoom_start=12)

    s1_gdf = sectors_gdf[sectors_gdf["sector_name"] == sector1_name]
    s2_gdf = sectors_gdf[sectors_gdf["sector_name"] == sector2_name]

    if s1_gdf.empty or s2_gdf.empty:
        missing = sector1_name if s1_gdf.empty else sector2_name
        raise ValueError(f"Sector '{missing}' not found.")

    folium.GeoJson(
        s1_gdf,
        style_function=lambda _: {
            "fillColor": "#FF5555",
            "color": "#AA0000",
            "weight": 2,
            "fillOpacity": 0.5
        },
        tooltip=(f"Sector {sector1_name}: Walk Score {summary1['Walk Score']:.2f}, "
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
        tooltip=(f"Sector {sector2_name}: Walk Score {summary2['Walk Score']:.2f}, "
                 f"POIs: {summary2['Total POIs']}")
    ).add_to(m)

    return m 