import folium
import pandas as pd
import numpy as np
import networkx as nx
from typing import Dict, List, Tuple, Optional
from geopy.distance import geodesic
from src.analysis.pathfinding import MultiCriteriaPathfinder


def _build_environmental_graph(nodes_gdf, edges_gdf):
    """
    Build NetworkX graph from nodes and edges with environmental weights.
    Similar to MultiCriteriaPathfinder._build_graph() but using GeoDataFrames.
    """
    G = nx.Graph()
    
    # Create a mapping from osmid to node data
    nodes_dict = {}
    for _, node in nodes_gdf.iterrows():
        osmid = node['osmid']
        nodes_dict[osmid] = {
            'lat': node.geometry.y,
            'lon': node.geometry.x,
            'gvi': node.get('gvi', 0),
            'svf': node.get('svf', 50),
            'sector': node.get('sector_name', '')
        }
        G.add_node(osmid, **nodes_dict[osmid])
    
    # Add edges with environmental weights
    for _, edge in edges_gdf.iterrows():
        u, v = edge['u'], edge['v']
        if u in nodes_dict and v in nodes_dict:
            length = edge['length']
            
            # For GVI: higher GVI should have lower cost (better path)
            u_gvi = nodes_dict[u]['gvi']
            v_gvi = nodes_dict[v]['gvi']
            avg_gvi = (u_gvi + v_gvi) / 2
            gvi_weight = length / (avg_gvi + 1)  # +1 to avoid division by zero
            
            # For SVF: lower SVF should have lower cost (more shade)
            u_svf = nodes_dict[u]['svf']
            v_svf = nodes_dict[v]['svf']
            avg_svf = (u_svf + v_svf) / 2
            svf_weight = length * (avg_svf / 100)
            
            G.add_edge(u, v, 
                      length=length,
                      gvi_weight=gvi_weight,
                      svf_weight=svf_weight)
    
    return G, nodes_dict


def _find_nearest_node(target_lat, target_lon, nodes_dict):
    """Find the nearest walk network node to a given coordinate"""
    min_dist = float('inf')
    nearest_node = None
    
    for osmid, data in nodes_dict.items():
        dist = geodesic((target_lat, target_lon), (data['lat'], data['lon'])).meters
        if dist < min_dist:
            min_dist = dist
            nearest_node = osmid
    
    return nearest_node if min_dist < 500 else None  # 500m threshold


def _calculate_path_stats(path, graph, nodes_dict):
    """Calculate environmental statistics for a path"""
    if len(path) < 2:
        return {'total_gvi': 0, 'total_svf': 0, 'length': 0, 'avg_gvi': 0, 'avg_svf': 0}
    
    total_length = 0
    total_gvi = 0
    total_svf = 0
    
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edge_length = graph[u][v]['length']
        total_length += edge_length
        
        # Add GVI and SVF values for this segment
        u_gvi = nodes_dict[u]['gvi']
        v_gvi = nodes_dict[v]['gvi']
        avg_gvi = (u_gvi + v_gvi) / 2
        total_gvi += avg_gvi * edge_length
        
        u_svf = nodes_dict[u]['svf']
        v_svf = nodes_dict[v]['svf']
        avg_svf = (u_svf + v_svf) / 2
        total_svf += avg_svf * edge_length
    
    return {
        'length': total_length,
        'total_gvi': total_gvi,
        'total_svf': total_svf,
        'avg_gvi': total_gvi / total_length if total_length > 0 else 0,
        'avg_svf': total_svf / total_length if total_length > 0 else 0
    }


def _create_path_map(path, graph, nodes_dict, start_coords=None, end_coords=None, 
                     path_color="green", path_name="Environmental Path"):
    """Create a folium map showing a path along walk edges"""
    if not path or len(path) < 2:
        return folium.Map(location=[30.7333, 76.7794], zoom_start=12)
    
    # Get coordinates for the path
    coordinates = []
    for node_id in path:
        if node_id in nodes_dict:
            node = nodes_dict[node_id]
            coordinates.append([node['lat'], node['lon']])
    
    if not coordinates:
        return folium.Map(location=[30.7333, 76.7794], zoom_start=12)
    
    # Center map on the path
    center_lat = sum(coord[0] for coord in coordinates) / len(coordinates)
    center_lon = sum(coord[1] for coord in coordinates) / len(coordinates)
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=14)
    
    # Add start/end markers if provided
    if start_coords:
        folium.Marker(
            start_coords,
            popup="<b>Start</b>",
            icon=folium.Icon(color='green', icon='play')
        ).add_to(m)
    
    if end_coords:
        folium.Marker(
            end_coords,
            popup="<b>End</b>",
            icon=folium.Icon(color='red', icon='stop')
        ).add_to(m)
    
    # Calculate path statistics
    stats = _calculate_path_stats(path, graph, nodes_dict)
    
    # Add the path
    popup_text = (f"<b>{path_name}</b><br>"
                 f"Length: {stats['length']:.0f}m<br>"
                 f"Avg GVI: {stats['avg_gvi']:.1f}<br>"
                 f"Avg SVF: {stats['avg_svf']:.1f}")
    
    folium.PolyLine(
        coordinates,
        popup=popup_text,
        color=path_color,
        weight=4,
        opacity=0.8
    ).add_to(m)
    
    # Add some path nodes for reference
    for i, node_id in enumerate(path[::max(1, len(path)//10)]):  # Sample every 10th node
        if node_id in nodes_dict:
            node = nodes_dict[node_id]
            folium.CircleMarker(
                location=[node['lat'], node['lon']],
                radius=3,
                popup=f"GVI: {node['gvi']:.1f}, SVF: {node['svf']:.1f}",
                color=path_color,
                fill=True,
                fillOpacity=0.6
            ).add_to(m)
    
    return m


def analyze_sector_environmental_quality(data: dict, sector_name: str) -> tuple[folium.Map, dict]:
    """
    Analyze environmental quality (GVI/SVF) of a specific sector.
    
    Args:
        data: Dictionary containing GeoDataFrames
        sector_name: Name of the sector to analyze
        
    Returns:
        tuple: (folium.Map, summary_dict)
    """
    nodes_gdf = data["nodes_gdf"]
    sectors_gdf = data["sectors_gdf"]
    
    # Filter nodes for the specific sector
    sector_nodes = nodes_gdf[nodes_gdf["sector_name"] == sector_name]
    
    if sector_nodes.empty:
        # Create default map
        m = folium.Map(location=[30.7333, 76.7794], zoom_start=12)
        return m, f"No environmental data found for Sector {sector_name}"
    
    # Calculate environmental statistics
    avg_gvi = sector_nodes["gvi"].mean()
    avg_svf = sector_nodes["svf"].mean()
    high_gvi_nodes = sector_nodes[sector_nodes["gvi"] > sector_nodes["gvi"].quantile(0.75)]
    low_svf_nodes = sector_nodes[sector_nodes["svf"] < sector_nodes["svf"].quantile(0.25)]
    
    # Get sector geometry for centering
    sector_geom = sectors_gdf[sectors_gdf["sector_name"] == sector_name]
    if not sector_geom.empty:
        sector_center = sector_geom.geometry.centroid.iloc[0]
        center_lat, center_lon = sector_center.y, sector_center.x
    else:
        # Use first node as center
        center_lat = sector_nodes.geometry.y.iloc[0]
        center_lon = sector_nodes.geometry.x.iloc[0]
    
    # Create map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=14)
    
    # Add sector boundary if available
    if not sector_geom.empty:
        folium.GeoJson(
            sector_geom.iloc[0].geometry,
            style_function=lambda x: {"color": "blue", "weight": 2, "fillOpacity": 0.1}
        ).add_to(m)
    
    # Color nodes by GVI levels
    for _, node in sector_nodes.iterrows():
        lat, lon = node.geometry.y, node.geometry.x
        gvi = node["gvi"]
        svf = node["svf"]
        
        # Color based on GVI: green = high, red = low
        if gvi > avg_gvi:
            color = "green"
            status = "High Vegetation"
        else:
            color = "red" 
            status = "Low Vegetation"
            
        folium.CircleMarker(
            location=[lat, lon],
            radius=4,
            popup=f"<b>Environmental Data</b><br>GVI: {gvi:.1f}<br>SVF: {svf:.1f}<br>Status: {status}",
            color=color,
            fill=True,
            fillOpacity=0.7
        ).add_to(m)
    
    # Prepare summary
    summary = {
        "sector": sector_name,
        "avg_gvi": round(avg_gvi, 2),
        "avg_svf": round(avg_svf, 2),
        "total_nodes": len(sector_nodes),
        "high_vegetation_nodes": len(high_gvi_nodes),
        "good_shade_nodes": len(low_svf_nodes),
        "environmental_score": round((avg_gvi - avg_svf/2), 2)  # Simple combined score
    }
    
    return m, summary


def find_green_corridors(data: dict, sector_name: str = None, min_gvi: float = 20.0) -> tuple[folium.Map, str]:
    """
    Find green corridors (connected paths with high GVI) using the walk network.
    
    Args:
        data: Dictionary containing GeoDataFrames
        sector_name: Optional sector to focus on
        min_gvi: Minimum GVI threshold for green corridors
        
    Returns:
        tuple: (folium.Map, description_string)
    """
    nodes_gdf = data["nodes_gdf"]
    edges_gdf = data["edges_gdf"]
    
    # Filter by sector if specified
    if sector_name:
        nodes_gdf = nodes_gdf[nodes_gdf["sector_name"] == sector_name]
        # Filter edges to only include those connecting nodes in this sector
        sector_node_ids = set(nodes_gdf['osmid'])
        edges_gdf = edges_gdf[
            (edges_gdf['u'].isin(sector_node_ids)) & 
            (edges_gdf['v'].isin(sector_node_ids))
        ]
        
    # Find high-GVI nodes
    green_nodes = nodes_gdf[nodes_gdf["gvi"] >= min_gvi]
    
    if green_nodes.empty:
        m = folium.Map(location=[30.7333, 76.7794], zoom_start=12)
        return m, f"No green corridors found with GVI >= {min_gvi}"
    
    # Build graph and find connected components of green nodes
    graph, nodes_dict = _build_environmental_graph(nodes_gdf, edges_gdf)
    
    # Find all green node IDs
    green_node_ids = set(green_nodes['osmid'])
    
    # Create subgraph of only green nodes and their connections
    green_subgraph = graph.subgraph(green_node_ids)
    
    # Find connected components (green corridors)
    green_corridors = list(nx.connected_components(green_subgraph))
    green_corridors = [list(component) for component in green_corridors if len(component) >= 3]
    
    # Center map on green nodes
    center_lat = green_nodes.geometry.y.mean()
    center_lon = green_nodes.geometry.x.mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13)
    
    # Add green corridors to map
    corridor_colors = ["darkgreen", "green", "lightgreen", "forestgreen", "limegreen"]
    
    for i, corridor in enumerate(green_corridors[:5]):  # Show top 5 corridors
        color = corridor_colors[i % len(corridor_colors)]
        
        # Find the longest path within this corridor
        if len(corridor) >= 2:
            # Create subgraph for this corridor
            corridor_graph = green_subgraph.subgraph(corridor)
            
            # Find the diameter (longest shortest path) of this corridor
            try:
                # Get all pairs shortest paths
                all_paths = dict(nx.all_pairs_shortest_path(corridor_graph))
                longest_path = []
                max_length = 0
                
                for source in all_paths:
                    for target in all_paths[source]:
                        if source != target:
                            path = all_paths[source][target]
                            path_stats = _calculate_path_stats(path, graph, nodes_dict)
                            if path_stats['length'] > max_length:
                                max_length = path_stats['length']
                                longest_path = path
                
                if longest_path:
                    # Add this corridor path to map
                    coordinates = []
                    for node_id in longest_path:
                        if node_id in nodes_dict:
                            node = nodes_dict[node_id]
                            coordinates.append([node['lat'], node['lon']])
                    
                    if coordinates:
                        stats = _calculate_path_stats(longest_path, graph, nodes_dict)
                        popup_text = (f"<b>Green Corridor {i+1}</b><br>"
                                    f"Length: {stats['length']:.0f}m<br>"
                                    f"Avg GVI: {stats['avg_gvi']:.1f}<br>"
                                    f"Nodes: {len(longest_path)}")
                        
                        folium.PolyLine(
                            coordinates,
                            popup=popup_text,
                            color=color,
                            weight=4,
                            opacity=0.8
                        ).add_to(m)
            
            except nx.NetworkXError:
                # If pathfinding fails, just show the nodes
                pass
        
        # Add corridor nodes
        for node_id in corridor:
            if node_id in nodes_dict:
                node = nodes_dict[node_id]
                node_data = nodes_gdf[nodes_gdf['osmid'] == node_id].iloc[0]
                gvi = node_data['gvi']
                
                folium.CircleMarker(
                    location=[node['lat'], node['lon']],
                    radius=4,
                    popup=f"<b>Green Node</b><br>GVI: {gvi:.1f}<br>Corridor {i+1}",
                    color=color,
                    fill=True,
                    fillOpacity=0.8
                ).add_to(m)
    
    description = f"Found {len(green_corridors)} green corridor(s) with GVI >= {min_gvi}"
    if sector_name:
        description += f" in Sector {sector_name}"
    
    if green_corridors:
        total_nodes = sum(len(corridor) for corridor in green_corridors)
        description += f". Total connected green nodes: {total_nodes}"
    
    return m, description


def suggest_environmental_path(data: dict, sector_name: str, poi_type: str = "restaurant", 
                             optimize_for: str = "gvi") -> tuple[folium.Map, str]:
    """
    Suggest walking paths between POIs that optimize environmental conditions using the walk network.
    
    Args:
        data: Dictionary containing GeoDataFrames
        sector_name: Sector to analyze
        poi_type: Type of POI to connect (secondary_type)
        optimize_for: "gvi" for high vegetation, "svf" for low sky view factor (shade)
        
    Returns:
        tuple: (folium.Map, description_string)
    """
    nodes_gdf = data["nodes_gdf"]
    edges_gdf = data["edges_gdf"]
    pois_gdf = data["pois_gdf"]
    sectors_gdf = data["sectors_gdf"]
    
    # Filter data for the sector
    sector_nodes = nodes_gdf[nodes_gdf["sector_name"] == sector_name]
    sector_pois = pois_gdf[
        (pois_gdf["sector_name"] == sector_name) & 
        (pois_gdf["secondary_type"] == poi_type)
    ]
    
    if sector_nodes.empty:
        m = folium.Map(location=[30.7333, 76.7794], zoom_start=12)
        return m, f"No environmental data found for Sector {sector_name}"
        
    if sector_pois.empty:
        m = folium.Map(location=[30.7333, 76.7794], zoom_start=12)
        return m, f"No {poi_type}s found in Sector {sector_name}"
    
    if len(sector_pois) < 2:
        m = folium.Map(location=[30.7333, 76.7794], zoom_start=12)
        return m, f"Need at least 2 {poi_type}s to create a path"
    
    # Filter edges to this sector
    sector_node_ids = set(sector_nodes['osmid'])
    sector_edges = edges_gdf[
        (edges_gdf['u'].isin(sector_node_ids)) & 
        (edges_gdf['v'].isin(sector_node_ids))
    ]
    
    # Build environmental graph
    graph, nodes_dict = _build_environmental_graph(sector_nodes, sector_edges)
    
    # Find nearest nodes to POIs
    poi_nodes = []
    for _, poi in sector_pois.iterrows():
        poi_lat, poi_lon = poi.geometry.y, poi.geometry.x
        nearest_node = _find_nearest_node(poi_lat, poi_lon, nodes_dict)
        if nearest_node:
            poi_nodes.append({
                'poi': poi,
                'node_id': nearest_node,
                'coords': (poi_lat, poi_lon)
            })
    
    if len(poi_nodes) < 2:
        m = folium.Map(location=[30.7333, 76.7794], zoom_start=12)
        return m, f"Could not find walk network nodes near {poi_type}s"
    
    # Find best environmental path between the two closest POIs
    best_path = None
    best_stats = None
    best_poi_pair = None
    
    weight_attr = 'gvi_weight' if optimize_for == 'gvi' else 'svf_weight'
    
    # Try all pairs of POIs and find the best environmental path
    for i in range(len(poi_nodes)):
        for j in range(i + 1, len(poi_nodes)):
            start_node = poi_nodes[i]['node_id']
            end_node = poi_nodes[j]['node_id']
            
            try:
                path = nx.shortest_path(graph, start_node, end_node, weight=weight_attr)
                stats = _calculate_path_stats(path, graph, nodes_dict)
                
                # Choose path based on optimization criteria
                if optimize_for == 'gvi':
                    score = stats['avg_gvi']
                else:  # svf
                    score = 100 - stats['avg_svf']  # Lower SVF is better
                
                if best_path is None or score > (best_stats.get('score', 0)):
                    best_path = path
                    best_stats = stats
                    best_stats['score'] = score
                    best_poi_pair = (poi_nodes[i], poi_nodes[j])
                    
            except nx.NetworkXNoPath:
                continue
    
    if not best_path:
        m = folium.Map(location=[30.7333, 76.7794], zoom_start=12)
        return m, f"No walking path found between {poi_type}s"
    
    # Create map with the environmental path
    start_coords = best_poi_pair[0]['coords']
    end_coords = best_poi_pair[1]['coords']
    
    color = "green" if optimize_for == 'gvi' else "blue"
    criteria_desc = "high vegetation (GVI)" if optimize_for == 'gvi' else "good shade (low SVF)"
    
    m = _create_path_map(best_path, graph, nodes_dict, start_coords, end_coords, 
                        color, f"Environmental Path ({criteria_desc})")
    
    # Add POI markers
    for poi_info in best_poi_pair:
        poi = poi_info['poi']
        coords = poi_info['coords']
        
        folium.Marker(
            location=list(coords),
            popup=f"<b>{poi['name']}</b><br>Type: {poi['secondary_type']}",
            icon=folium.Icon(color="red", icon="cutlery")
        ).add_to(m)
    
    description = (f"Environmental walking path in Sector {sector_name}:\n"
                  f"- Route optimized for {criteria_desc}\n"
                  f"- Length: {best_stats['length']:.0f}m\n"
                  f"- Average GVI: {best_stats['avg_gvi']:.1f}\n"
                  f"- Average SVF: {best_stats['avg_svf']:.1f}\n"
                  f"- Connects: {best_poi_pair[0]['poi']['name']} → {best_poi_pair[1]['poi']['name']}")
    
    return m, description


def compare_environmental_quality(data: dict, sector1: str, sector2: str) -> tuple[folium.Map, str]:
    """
    Compare environmental quality between two sectors.
    
    Args:
        data: Dictionary containing GeoDataFrames
        sector1: First sector name
        sector2: Second sector name
        
    Returns:
        tuple: (folium.Map, comparison_string)
    """
    nodes_gdf = data["nodes_gdf"]
    sectors_gdf = data["sectors_gdf"]
    
    # Get nodes for both sectors
    sector1_nodes = nodes_gdf[nodes_gdf["sector_name"] == sector1]
    sector2_nodes = nodes_gdf[nodes_gdf["sector_name"] == sector2]
    
    if sector1_nodes.empty or sector2_nodes.empty:
        m = folium.Map(location=[30.7333, 76.7794], zoom_start=12)
        return m, "One or both sectors have no environmental data"
    
    # Calculate statistics
    s1_gvi = sector1_nodes["gvi"].mean()
    s1_svf = sector1_nodes["svf"].mean()
    s2_gvi = sector2_nodes["gvi"].mean()
    s2_svf = sector2_nodes["svf"].mean()
    
    # Center map between both sectors
    all_nodes = pd.concat([sector1_nodes, sector2_nodes])
    center_lat = all_nodes.geometry.y.mean()
    center_lon = all_nodes.geometry.x.mean()
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)
    
    # Add sector boundaries with different colors
    for sector_name, color in [(sector1, "blue"), (sector2, "red")]:
        sector_geom = sectors_gdf[sectors_gdf["sector_name"] == sector_name]
        if not sector_geom.empty:
            folium.GeoJson(
                sector_geom.iloc[0].geometry,
                style_function=lambda x, color=color: {
                    "color": color, "weight": 2, "fillOpacity": 0.1
                }
            ).add_to(m)
    
    # Add environmental quality markers
    for sector_name, nodes, color in [
        (sector1, sector1_nodes, "blue"), 
        (sector2, sector2_nodes, "red")
    ]:
        sample_nodes = nodes.sample(min(20, len(nodes)))  # Sample for performance
        for _, node in sample_nodes.iterrows():
            lat, lon = node.geometry.y, node.geometry.x
            gvi, svf = node["gvi"], node["svf"]
            
            folium.CircleMarker(
                location=[lat, lon],
                radius=3,
                popup=f"<b>Sector {sector_name}</b><br>GVI: {gvi:.1f}<br>SVF: {svf:.1f}",
                color=color,
                fill=True,
                fillOpacity=0.6
            ).add_to(m)
    
    # Create comparison description
    gvi_winner = sector1 if s1_gvi > s2_gvi else sector2
    svf_winner = sector1 if s1_svf < s2_svf else sector2  # Lower SVF is better (more shade)
    
    description = (f"Environmental Quality Comparison:\n\n"
                  f"Sector {sector1}:\n"
                  f"- Average GVI: {s1_gvi:.1f} (vegetation)\n"
                  f"- Average SVF: {s1_svf:.1f} (sky openness)\n\n"
                  f"Sector {sector2}:\n"
                  f"- Average GVI: {s2_gvi:.1f} (vegetation)\n"
                  f"- Average SVF: {s2_svf:.1f} (sky openness)\n\n"
                  f"Winner for vegetation: Sector {gvi_winner}\n"
                  f"Winner for shade: Sector {svf_winner}")
    
    return m, description


def get_top_environmental_sectors(data: dict, criteria: str = "gvi", k: int = 5) -> tuple[folium.Map, str]:
    """
    Get top sectors by environmental criteria.
    
    Args:
        data: Dictionary containing GeoDataFrames
        criteria: "gvi" for vegetation, "svf" for shade, "combined" for both
        k: Number of top sectors to return
        
    Returns:
        tuple: (folium.Map, description_string)
    """
    nodes_gdf = data["nodes_gdf"]
    sectors_gdf = data["sectors_gdf"]
    
    # Calculate sector-level environmental statistics
    sector_stats = nodes_gdf.groupby("sector_name").agg({
        "gvi": "mean",
        "svf": "mean"
    }).round(2)
    
    # Calculate combined environmental score
    sector_stats["environmental_score"] = sector_stats["gvi"] - (sector_stats["svf"] / 2)
    
    # Sort by criteria
    if criteria == "gvi":
        top_sectors = sector_stats.nlargest(k, "gvi")
        title = f"Top {k} Sectors by Vegetation (GVI)"
    elif criteria == "svf":
        top_sectors = sector_stats.nsmallest(k, "svf")  # Lower SVF is better
        title = f"Top {k} Sectors by Shade (Low SVF)"
    else:  # combined
        top_sectors = sector_stats.nlargest(k, "environmental_score")
        title = f"Top {k} Sectors by Environmental Quality"
    
    # Create map
    m = folium.Map(location=[30.7333, 76.7794], zoom_start=12)
    
    # Color palette for ranking
    colors = ["darkgreen", "green", "lightgreen", "yellow", "orange"]
    
    # Add top sectors to map
    for i, (sector_name, stats) in enumerate(top_sectors.iterrows()):
        sector_geom = sectors_gdf[sectors_gdf["sector_name"] == sector_name]
        if not sector_geom.empty:
            color = colors[i % len(colors)]
            
            # Create popup with statistics
            popup_text = (f"<b>Sector {sector_name} (Rank {i+1})</b><br>"
                         f"GVI: {stats['gvi']}<br>"
                         f"SVF: {stats['svf']}<br>"
                         f"Environmental Score: {stats['environmental_score']:.2f}")
            
            folium.GeoJson(
                sector_geom.iloc[0].geometry,
                style_function=lambda x, color=color: {
                    "color": color, "weight": 3, "fillOpacity": 0.4
                },
                popup=folium.Popup(popup_text, max_width=300)
            ).add_to(m)
    
    # Create description
    description = f"{title}:\n\n"
    for i, (sector_name, stats) in enumerate(top_sectors.iterrows()):
        description += (f"{i+1}. Sector {sector_name}: "
                       f"GVI={stats['gvi']}, SVF={stats['svf']}, "
                       f"Score={stats['environmental_score']:.2f}\n")
    
    return m, description 