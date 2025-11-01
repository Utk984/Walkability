import geopandas as gpd
import pandas as pd
import json
import os


def load_geospatial_data(
    sectors_fp: str = "data/sectors.geojson",
    pois_fp: str = "data/pois.geojson",
    nodes_fp: str = "data/walk_nodes.geojson",
    edges_fp: str = "data/walk_edges.geojson"
) -> dict:
    """
    Reads four geospatial files and processes them for the walkability application.
    
    Args:
        sectors_fp: Path to sectors GeoJSON with sector_name, walk_score, geometry
        pois_fp: Path to POIs GeoJSON with primary_type, coordinates, etc.
        nodes_fp: Path to walk nodes GeoJSON with svf, gvi, node_sector
        edges_fp: Path to walk edges GeoJSON with OSM tags
    
    Returns:
        dict: Contains processed GeoDataFrames for sectors, pois, nodes, edges
    """
    # Load sector polygons
    sectors_gdf = gpd.read_file(sectors_fp)
    if sectors_gdf.crs is None or sectors_gdf.crs.to_epsg() != 4326:
        sectors_gdf = sectors_gdf.to_crs(epsg=4326)

    # Load POIs and convert to GeoDataFrame
    pois_gdf = gpd.read_file(pois_fp)
    if pois_gdf.crs is None or pois_gdf.crs.to_epsg() != 4326:
        pois_gdf = pois_gdf.to_crs(epsg=4326)

    # Count total POIs per sector
    poi_counts = (
        pois_gdf.groupby("sector_name")
        .size()
        .rename("total_pois")
        .reset_index()
    )

    # Merge total_pois into sectors_gdf
    sectors_enriched = sectors_gdf.merge(
        poi_counts,
        on="sector_name",
        how="left"
    )
    sectors_enriched["total_pois"] = sectors_enriched["total_pois"].fillna(0).astype(int)

    # Load walk nodes
    nodes_gdf = gpd.read_file(nodes_fp)
    if nodes_gdf.crs is None or nodes_gdf.crs.to_epsg() != 4326:
        nodes_gdf = nodes_gdf.to_crs(epsg=4326)

    # Load walk edges
    edges_gdf = gpd.read_file(edges_fp)
    if edges_gdf.crs is None or edges_gdf.crs.to_epsg() != 4326:
        edges_gdf = edges_gdf.to_crs(epsg=4326)

    return {
        "sectors_gdf": sectors_enriched,
        "pois_gdf": pois_gdf,
        "nodes_gdf": nodes_gdf,
        "edges_gdf": edges_gdf
    }


def load_pois_for_search():
    """Load POI data specifically for search functionality"""
    pois_path = os.path.join("data", "pois.geojson")
    with open(pois_path, 'r') as f:
        pois_data = json.load(f)
    return pois_data['features']