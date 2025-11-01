import folium
import pandas as pd
import numpy as np
import networkx as nx
from typing import Dict, List, Tuple, Optional
from geopy.distance import geodesic

# Import the environmental graph utilities
from src.analysis.environmental_analysis import (
    _build_environmental_graph, _find_nearest_node, 
    _calculate_path_stats, _create_path_map
)


def find_environmental_route_with_pois(data: dict, sector_name: str, poi_type: str, 
                                     optimize_for: str = "gvi", 
                                     max_walk_distance: float = 1000) -> tuple[folium.Map, str]:
    """
    Find an optimal walking route using the walk network that includes specific POIs and optimizes environmental conditions.
    
    Args:
        data: Dictionary containing GeoDataFrames
        sector_name: Sector to analyze
        poi_type: Type of POI to include (secondary_type)
        optimize_for: "gvi" for vegetation, "svf" for shade, "balanced" for both
        max_walk_distance: Maximum walking distance in meters
        
    Returns:
        tuple: (folium.Map, description_string)
    """
    nodes_gdf = data["nodes_gdf"]
    edges_gdf = data["edges_gdf"] 
    pois_gdf = data["pois_gdf"]
    sectors_gdf = data["sectors_gdf"]
    
    # Filter data for the sector with explicit error handling
    try:
        sector_nodes = nodes_gdf[nodes_gdf["sector_name"] == sector_name].copy()
        sector_pois = pois_gdf[
            (pois_gdf["sector_name"] == sector_name) & 
            (pois_gdf["secondary_type"] == poi_type)
        ].copy()
    except Exception as e:
        m = folium.Map(location=[30.7333, 76.7794], zoom_start=12)
        return m, f"Error filtering data for Sector {sector_name}: {str(e)}"
    
    if sector_nodes.empty:
        m = folium.Map(location=[30.7333, 76.7794], zoom_start=12)
        return m, f"No environmental data found for Sector {sector_name}"
        
    if sector_pois.empty:
        m = folium.Map(location=[30.7333, 76.7794], zoom_start=12)
        return m, f"No {poi_type}s found in Sector {sector_name}"
    
    # Filter edges to this sector with safe handling
    try:
        sector_node_ids = set(sector_nodes['osmid'].tolist())
        if not sector_node_ids:
            m = folium.Map(location=[30.7333, 76.7794], zoom_start=12)
            return m, f"No valid node IDs found in Sector {sector_name}"
            
        # Use explicit boolean conditions to avoid Series ambiguity
        u_mask = edges_gdf['u'].isin(sector_node_ids)
        v_mask = edges_gdf['v'].isin(sector_node_ids)
        sector_edges = edges_gdf[u_mask & v_mask].copy()
        
        if sector_edges.empty:
            m = folium.Map(location=[30.7333, 76.7794], zoom_start=12)
            return m, f"No walking paths found in Sector {sector_name}"
            
    except Exception as e:
        m = folium.Map(location=[30.7333, 76.7794], zoom_start=12)
        return m, f"Error filtering edges for Sector {sector_name}: {str(e)}"
    
    # Build environmental graph
    try:
        graph, nodes_dict = _build_environmental_graph(sector_nodes, sector_edges)
        if not graph.nodes():
            m = folium.Map(location=[30.7333, 76.7794], zoom_start=12)
            return m, f"Could not build walk network for Sector {sector_name}"
    except Exception as e:
        m = folium.Map(location=[30.7333, 76.7794], zoom_start=12)
        return m, f"Error building environmental graph: {str(e)}"
    
    # Find nearest nodes to POIs
    poi_nodes = []
    for _, poi in sector_pois.iterrows():
        try:
            poi_lat, poi_lon = poi.geometry.y, poi.geometry.x
            nearest_node = _find_nearest_node(poi_lat, poi_lon, nodes_dict)
            if nearest_node:
                poi_nodes.append({
                    'poi': poi,
                    'node_id': nearest_node,
                    'coords': (poi_lat, poi_lon)
                })
        except Exception:
            continue  # Skip POIs with geometry issues
    
    if len(poi_nodes) < 2:
        m = folium.Map(location=[30.7333, 76.7794], zoom_start=12)
        return m, f"Could not find walk network nodes near {poi_type}s"
    
    # Choose weight attribute based on optimization criteria
    if optimize_for == "gvi":
        weight_attr = 'gvi_weight'
        criteria_desc = "high vegetation (GVI)"
        path_color = "green"
    elif optimize_for == "svf":
        weight_attr = 'svf_weight'
        criteria_desc = "good shade (low SVF)"
        path_color = "blue"
    else:  # balanced
        # For balanced, we'll use a combined weight
        # Add combined weight to all edges
        for u, v, d in graph.edges(data=True):
            combined_weight = (d['gvi_weight'] + d['svf_weight']) / 2
            graph[u][v]['combined_weight'] = combined_weight
        weight_attr = 'combined_weight'
        criteria_desc = "balanced environmental quality"
        path_color = "purple"
    
    # Find routes between POIs and rank them
    poi_routes = []
    
    for i in range(len(poi_nodes)):
        for j in range(i + 1, len(poi_nodes)):
            start_node = poi_nodes[i]['node_id']
            end_node = poi_nodes[j]['node_id']
            
            try:
                # Find path optimized for environmental criteria
                path = nx.shortest_path(graph, start_node, end_node, weight=weight_attr)
                stats = _calculate_path_stats(path, graph, nodes_dict)
                
                # Check distance constraint
                if stats['length'] <= max_walk_distance:
                    poi_routes.append({
                        'path': path,
                        'stats': stats,
                        'start_poi': poi_nodes[i],
                        'end_poi': poi_nodes[j],
                        'env_score': _calculate_environmental_score(stats, optimize_for)
                    })
                    
            except nx.NetworkXNoPath:
                continue
            except Exception:
                continue  # Skip paths with calculation issues
    
    if not poi_routes:
        m = folium.Map(location=[30.7333, 76.7794], zoom_start=12)
        return m, f"No walking routes found between {poi_type}s within {max_walk_distance}m"
    
    # Sort routes by environmental score (best first)
    poi_routes.sort(key=lambda x: x['env_score'], reverse=True)
    
    # Create map with the best route
    best_route = poi_routes[0]
    
    start_coords = best_route['start_poi']['coords']
    end_coords = best_route['end_poi']['coords']
    
    m = _create_path_map(best_route['path'], graph, nodes_dict, start_coords, end_coords, 
                        path_color, f"Environmental Route ({criteria_desc})")
    
    # Add all POI markers
    for poi_info in poi_nodes:
        poi = poi_info['poi']
        coords = poi_info['coords']
        
        # Highlight the connected POIs
        if poi_info in [best_route['start_poi'], best_route['end_poi']]:
            icon_color = "red"
            icon = "star"
        else:
            icon_color = "orange" 
            icon = "cutlery"
            
        folium.Marker(
            location=list(coords),
            popup=f"<b>{poi['name']}</b><br>Type: {poi['secondary_type']}",
            icon=folium.Icon(color=icon_color, icon=icon)
        ).add_to(m)
    
    # Add alternative routes if available
    route_descriptions = []
    for i, route in enumerate(poi_routes[:3]):  # Show top 3 routes
        start_name = route['start_poi']['poi']['name']
        end_name = route['end_poi']['poi']['name']
        stats = route['stats']
        
        route_descriptions.append(
            f"{i+1}. {start_name} → {end_name} "
            f"({stats['length']:.0f}m, GVI: {stats['avg_gvi']:.1f}, SVF: {stats['avg_svf']:.1f})"
        )
    
    description = (f"Environmental route optimization for Sector {sector_name}:\n\n"
                  f"Criteria: {criteria_desc}\n"
                  f"Max distance: {max_walk_distance}m\n"
                  f"Found {len(poi_routes)} viable route(s)\n\n"
                  f"Route options:\n" + "\n".join(route_descriptions))
    
    return m, description


def _calculate_environmental_score(stats, optimize_for):
    """Calculate environmental score for path ranking"""
    if optimize_for == "gvi":
        return stats['avg_gvi']
    elif optimize_for == "svf":
        return 100 - stats['avg_svf']  # Lower SVF is better
    else:  # balanced
        return (stats['avg_gvi'] + (100 - stats['avg_svf'])) / 2


def analyze_walkability_by_environment(data: dict, gvi_threshold: float = 25.0, 
                                     svf_threshold: float = 30.0) -> tuple[folium.Map, str]:
    """
    Analyze city-wide walkability based on environmental thresholds using the walk network.
    
    Args:
        data: Dictionary containing GeoDataFrames
        gvi_threshold: Minimum GVI for good walkability
        svf_threshold: Maximum SVF for comfortable walking (more shade)
        
    Returns:
        tuple: (folium.Map, description_string)
    """
    nodes_gdf = data["nodes_gdf"]
    edges_gdf = data["edges_gdf"]
    sectors_gdf = data["sectors_gdf"]
    
    # Build the walk network graph
    graph, nodes_dict = _build_environmental_graph(nodes_gdf, edges_gdf)
    
    # Classify nodes based on environmental quality
    good_nodes = nodes_gdf[
        (nodes_gdf["gvi"] >= gvi_threshold) & 
        (nodes_gdf["svf"] <= svf_threshold)
    ]
    
    moderate_nodes = nodes_gdf[
        ((nodes_gdf["gvi"] >= gvi_threshold) & (nodes_gdf["svf"] > svf_threshold)) |
        ((nodes_gdf["gvi"] < gvi_threshold) & (nodes_gdf["svf"] <= svf_threshold))
    ]
    
    poor_nodes = nodes_gdf[
        (nodes_gdf["gvi"] < gvi_threshold) & 
        (nodes_gdf["svf"] > svf_threshold)
    ]
    
    # Find connected components of good environmental nodes
    good_node_ids = set(good_nodes['osmid'])
    good_subgraph = graph.subgraph(good_node_ids)
    good_components = list(nx.connected_components(good_subgraph))
    good_components = [list(comp) for comp in good_components if len(comp) >= 5]
    
    # Create map
    m = folium.Map(location=[30.7333, 76.7794], zoom_start=12)
    
    # Add sector boundaries
    folium.GeoJson(
        sectors_gdf,
        style_function=lambda x: {"color": "gray", "weight": 1, "fillOpacity": 0.1}
    ).add_to(m)
    
    # Add connected good environmental areas
    component_colors = ["darkgreen", "green", "lightgreen", "forestgreen", "limegreen"]
    
    for i, component in enumerate(good_components[:5]):  # Show top 5 components
        color = component_colors[i % len(component_colors)]
        
        # Find a sample path within this component to show connectivity
        if len(component) >= 2:
            component_graph = good_subgraph.subgraph(component)
            
            # Find a representative path (diameter of the component)
            try:
                # Get the diameter path of this component
                diameter_path = []
                max_length = 0
                
                # Sample pairs to find a good representative path
                import random
                sample_nodes = random.sample(component, min(10, len(component)))
                
                for j, start in enumerate(sample_nodes):
                    for end in sample_nodes[j+1:]:
                        try:
                            path = nx.shortest_path(component_graph, start, end)
                            stats = _calculate_path_stats(path, graph, nodes_dict)
                            if stats['length'] > max_length:
                                max_length = stats['length']
                                diameter_path = path
                        except nx.NetworkXNoPath:
                            continue
                
                if diameter_path:
                    # Draw the representative path
                    coordinates = []
                    for node_id in diameter_path:
                        if node_id in nodes_dict:
                            node = nodes_dict[node_id]
                            coordinates.append([node['lat'], node['lon']])
                    
                    if coordinates:
                        stats = _calculate_path_stats(diameter_path, graph, nodes_dict)
                        popup_text = (f"<b>Good Environmental Area {i+1}</b><br>"
                                    f"Connected nodes: {len(component)}<br>"
                                    f"Sample path: {stats['length']:.0f}m<br>"
                                    f"Avg GVI: {stats['avg_gvi']:.1f}<br>"
                                    f"Avg SVF: {stats['avg_svf']:.1f}")
                        
                        folium.PolyLine(
                            coordinates,
                            popup=popup_text,
                            color=color,
                            weight=3,
                            opacity=0.8
                        ).add_to(m)
                        
            except (nx.NetworkXError, ValueError):
                pass
    
    # Add sample nodes with color coding (limited for performance)
    for category, nodes, color, label in [
        ("Excellent", good_nodes, "green", "High GVI + Good Shade"),
        ("Moderate", moderate_nodes, "yellow", "Mixed Conditions"),
        ("Poor", poor_nodes, "red", "Low GVI + High Sun Exposure")
    ]:
        sample_size = min(100, len(nodes))  # Limit for performance
        sample_nodes = nodes.sample(sample_size) if len(nodes) > sample_size else nodes
        
        for _, node in sample_nodes.iterrows():
            lat, lon = node.geometry.y, node.geometry.x
            gvi, svf = node["gvi"], node["svf"]
            
            folium.CircleMarker(
                location=[lat, lon],
                radius=2,
                popup=f"<b>{label}</b><br>GVI: {gvi:.1f}<br>SVF: {svf:.1f}<br>Sector: {node['sector_name']}",
                color=color,
                fill=True,
                fillOpacity=0.7
            ).add_to(m)
    
    # Calculate connectivity statistics
    total_good_connectivity = sum(len(comp) for comp in good_components)
    
    description = (f"Environmental Walkability Analysis:\n\n"
                  f"Thresholds: GVI ≥ {gvi_threshold}, SVF ≤ {svf_threshold}\n\n"
                  f"Node Distribution:\n"
                  f"- Excellent conditions: {len(good_nodes)} nodes ({len(good_nodes)/len(nodes_gdf)*100:.1f}%)\n"
                  f"- Moderate conditions: {len(moderate_nodes)} nodes ({len(moderate_nodes)/len(nodes_gdf)*100:.1f}%)\n"
                  f"- Poor conditions: {len(poor_nodes)} nodes ({len(poor_nodes)/len(nodes_gdf)*100:.1f}%)\n\n"
                  f"Connectivity Analysis:\n"
                  f"- {len(good_components)} connected good environmental areas\n"
                  f"- {total_good_connectivity} nodes in connected areas\n"
                  f"- Average cluster size: {total_good_connectivity/len(good_components):.1f} nodes" if good_components else "- No connected areas found")
    
    return m, description


def suggest_green_walking_circuit(data: dict, sector_name: str, 
                                circuit_length: str = "short") -> tuple[folium.Map, str]:
    """
    Suggest a circular walking route using the walk network that maximizes environmental quality.
    
    Args:
        data: Dictionary containing GeoDataFrames
        sector_name: Sector to create circuit in
        circuit_length: "short" (500m), "medium" (1km), "long" (2km)
        
    Returns:
        tuple: (folium.Map, description_string)
    """
    nodes_gdf = data["nodes_gdf"]
    edges_gdf = data["edges_gdf"]
    pois_gdf = data["pois_gdf"]
    sectors_gdf = data["sectors_gdf"]
    
    # Set circuit parameters
    distance_targets = {
        "short": 500,
        "medium": 1000,
        "long": 2000
    }
    target_distance = distance_targets.get(circuit_length, 1000)
    
    # Filter nodes for the sector
    sector_nodes = nodes_gdf[nodes_gdf["sector_name"] == sector_name]
    sector_pois = pois_gdf[pois_gdf["sector_name"] == sector_name]
    
    if sector_nodes.empty:
        m = folium.Map(location=[30.7333, 76.7794], zoom_start=12)
        return m, f"No data found for Sector {sector_name}"
    
    # Filter edges to this sector
    sector_node_ids = set(sector_nodes['osmid'])
    sector_edges = edges_gdf[
        (edges_gdf['u'].isin(sector_node_ids)) & 
        (edges_gdf['v'].isin(sector_node_ids))
    ]
    
    # Build environmental graph
    graph, nodes_dict = _build_environmental_graph(sector_nodes, sector_edges)
    
    # Find high-quality environmental nodes
    high_gvi_nodes = sector_nodes[sector_nodes["gvi"] > sector_nodes["gvi"].quantile(0.8)]
    low_svf_nodes = sector_nodes[sector_nodes["svf"] < sector_nodes["svf"].quantile(0.2)]
    
    # Combine for optimal nodes (intersection of high GVI and low SVF is best)
    optimal_node_ids = set(high_gvi_nodes['osmid']) & set(low_svf_nodes['osmid'])
    if not optimal_node_ids:
        # Fallback to just high GVI nodes
        optimal_node_ids = set(high_gvi_nodes['osmid'])
    
    # Get sector center for circuit creation
    sector_geom = sectors_gdf[sectors_gdf["sector_name"] == sector_name]
    if not sector_geom.empty:
        sector_center = sector_geom.geometry.centroid.iloc[0]
        center_lat, center_lon = sector_center.y, sector_center.x
    else:
        center_lat = sector_nodes.geometry.y.mean()
        center_lon = sector_nodes.geometry.x.mean()
    
    # Find circuit by exploring from optimal nodes
    circuit_nodes = []
    circuit_path = []
    
    if optimal_node_ids and len(graph.nodes()) > 5:
        # Start from the optimal node closest to sector center
        start_node = None
        min_distance = float('inf')
        
        for node_id in optimal_node_ids:
            if node_id in nodes_dict:
                node = nodes_dict[node_id]
                dist = geodesic((center_lat, center_lon), (node['lat'], node['lon'])).meters
                if dist < min_distance:
                    min_distance = dist
                    start_node = node_id
        
        if start_node:
            # Use DFS to create a circuit of approximately target distance
            circuit_path = _create_environmental_circuit(graph, start_node, target_distance, nodes_dict)
    
    # Create map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=14)
    
    # Add sector boundary
    if not sector_geom.empty:
        folium.GeoJson(
            sector_geom.iloc[0].geometry,
            style_function=lambda x: {"color": "blue", "weight": 2, "fillOpacity": 0.1}
        ).add_to(m)
    
    if circuit_path and len(circuit_path) > 2:
        # Create the circuit visualization
        m = _create_path_map(circuit_path, graph, nodes_dict, 
                            path_color="green", path_name=f"Green Walking Circuit ({circuit_length})")
        
        # Calculate circuit statistics
        stats = _calculate_path_stats(circuit_path, graph, nodes_dict)
        
        # Add sector boundary to the existing map
        if not sector_geom.empty:
            folium.GeoJson(
                sector_geom.iloc[0].geometry,
                style_function=lambda x: {"color": "blue", "weight": 2, "fillOpacity": 0.1}
            ).add_to(m)
        
        # Add nearby POIs as points of interest
        for _, poi in sector_pois.iterrows():
            if poi.get('secondary_type') in ['restaurant', 'cafe', 'park']:
                lat, lon = poi.geometry.y, poi.geometry.x
                
                folium.Marker(
                    location=[lat, lon],
                    popup=f"<b>{poi['name']}</b><br>Type: {poi['secondary_type']}",
                    icon=folium.Icon(color="orange", icon="info-sign", prefix="glyphicon")
                ).add_to(m)
        
        # Count nearby amenities
        restaurant_count = len(sector_pois[sector_pois["secondary_type"] == "restaurant"])
        cafe_count = len(sector_pois[sector_pois["secondary_type"] == "cafe"])
        park_count = len(sector_pois[sector_pois["primary_type"] == "Tourism"])
        
        description = (f"Green Walking Circuit - Sector {sector_name}:\n\n"
                      f"Circuit type: {circuit_length} (target: {target_distance}m)\n"
                      f"Actual length: {stats['length']:.0f}m\n"
                      f"Route points: {len(circuit_path)}\n\n"
                      f"Environmental quality:\n"
                      f"- Average GVI: {stats['avg_gvi']:.1f} (vegetation level)\n"
                      f"- Average SVF: {stats['avg_svf']:.1f} (shade level)\n\n"
                      f"Nearby amenities:\n"
                      f"- Restaurants: {restaurant_count}\n"
                      f"- Cafes: {cafe_count}\n"
                      f"- Parks/Tourist spots: {park_count}")
    else:
        # No suitable circuit found
        description = (f"Could not create a suitable green walking circuit in Sector {sector_name}. "
                      f"Try a different sector or adjust the circuit length.")
    
    return m, description


def _create_environmental_circuit(graph, start_node, target_distance, nodes_dict):
    """
    Create a circuit path using DFS that approximately matches target distance.
    """
    if start_node not in graph:
        return []
    
    visited = set()
    path = [start_node]
    current_distance = 0
    current_node = start_node
    
    # DFS-based circuit creation
    while current_distance < target_distance * 0.8:  # 80% of target to allow for return
        visited.add(current_node)
        
        # Find unvisited neighbors with good environmental scores
        neighbors = []
        for neighbor in graph.neighbors(current_node):
            if neighbor not in visited:
                edge_length = graph[current_node][neighbor]['length']
                if current_distance + edge_length < target_distance * 0.9:
                    # Score neighbor by environmental quality
                    neighbor_gvi = nodes_dict[neighbor]['gvi']
                    neighbor_svf = nodes_dict[neighbor]['svf']
                    env_score = neighbor_gvi - (neighbor_svf / 2)
                    neighbors.append((neighbor, edge_length, env_score))
        
        if not neighbors:
            break
        
        # Choose neighbor with best environmental score
        neighbors.sort(key=lambda x: x[2], reverse=True)
        next_node, edge_length, _ = neighbors[0]
        
        path.append(next_node)
        current_distance += edge_length
        current_node = next_node
        
        # Stop if we have a reasonable circuit length
        if len(path) > 20:  # Prevent overly long circuits
            break
    
    # Try to close the circuit back to start
    if current_node != start_node and len(path) > 3:
        try:
            return_path = nx.shortest_path(graph, current_node, start_node, weight='length')
            if len(return_path) > 1:  # Remove the duplicate current_node
                path.extend(return_path[1:])
        except nx.NetworkXNoPath:
            pass
    
    return path if len(path) >= 3 else [] 