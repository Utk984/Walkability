import json
import numpy as np
import networkx as nx
from geopy.distance import geodesic
from typing import List, Dict, Tuple, Optional
import folium


class MultiCriteriaPathfinder:
    def __init__(self, nodes_path: str, edges_path: str, pois_path: str):
        """Initialize pathfinder with walking network data"""
        self.nodes = self._load_nodes(nodes_path)
        self.edges = self._load_edges(edges_path)
        self.pois = self._load_pois(pois_path)
        self.graph = self._build_graph()
        
    def _format_distance(self, meters: float) -> str:
        """Format distance as meters or kilometers"""
        if meters >= 1000:
            return f"{meters/1000:.1f} km"
        else:
            return f"{meters:.0f}m"
        
    def _load_nodes(self, path: str) -> Dict:
        """Load walk nodes with GVI and SVF data"""
        with open(path, 'r') as f:
            data = json.load(f)
        
        nodes = {}
        for feature in data['features']:
            osmid = feature['properties']['osmid']
            nodes[osmid] = {
                'lat': feature['geometry']['coordinates'][1],
                'lon': feature['geometry']['coordinates'][0],
                'gvi': feature['properties'].get('gvi', 0),
                'svf': feature['properties'].get('svf', 50),  # default SVF
                'sector': feature['properties'].get('sector_name', '')
            }
        return nodes
    
    def _load_edges(self, path: str) -> List[Dict]:
        """Load walk edges with length data"""
        with open(path, 'r') as f:
            data = json.load(f)
        
        edges = []
        for feature in data['features']:
            props = feature['properties']
            edges.append({
                'u': props['u'],
                'v': props['v'],
                'length': props['length'],  # in meters
                'highway': props.get('highway', 'residential'),
                'coordinates': feature['geometry']['coordinates']
            })
        return edges
    
    def _load_pois(self, path: str) -> Dict:
        """Load POIs for destination matching"""
        with open(path, 'r') as f:
            data = json.load(f)
        
        pois = {}
        for feature in data['features']:
            name = feature['properties'].get('name', '')
            if name:
                pois[name.lower()] = {
                    'name': name,
                    'lat': feature['geometry']['coordinates'][1],
                    'lon': feature['geometry']['coordinates'][0],
                    'primary_type': feature['properties'].get('primary_type', ''),
                    'sector': feature['properties'].get('sector_name', '')
                }
        return pois
    
    def _build_graph(self) -> nx.Graph:
        """Build NetworkX graph from nodes and edges"""
        G = nx.Graph()
        
        # Add nodes with attributes
        for osmid, data in self.nodes.items():
            G.add_node(osmid, **data)
        
        # Add edges with weights
        for edge in self.edges:
            u, v = edge['u'], edge['v']
            if u in self.nodes and v in self.nodes:
                # Calculate different weights
                length = edge['length']  # meters
                
                # For GVI: higher GVI should have lower cost (better path)
                # Use inverse relationship: weight = length / (gvi + 1)
                u_gvi = self.nodes[u]['gvi']
                v_gvi = self.nodes[v]['gvi']
                avg_gvi = (u_gvi + v_gvi) / 2
                gvi_weight = length / (avg_gvi + 1)  # +1 to avoid division by zero
                
                # For SVF: lower SVF should have lower cost (more shade)
                # Use direct relationship: weight = length * (svf / 100)
                u_svf = self.nodes[u]['svf']
                v_svf = self.nodes[v]['svf']
                avg_svf = (u_svf + v_svf) / 2
                svf_weight = length * (avg_svf / 100)
                
                G.add_edge(u, v, 
                          length=length,
                          gvi_weight=gvi_weight,
                          svf_weight=svf_weight,
                          coordinates=edge['coordinates'])
        
        return G
    
    def find_nearest_node(self, lat: float, lon: float) -> Optional[int]:
        """Find the nearest walk network node to a given coordinate"""
        min_dist = float('inf')
        nearest_node = None
        
        for osmid, data in self.nodes.items():
            dist = geodesic((lat, lon), (data['lat'], data['lon'])).meters
            if dist < min_dist:
                min_dist = dist
                nearest_node = osmid
        
        return nearest_node if min_dist < 500 else None  # 500m threshold
    
    def find_poi_location(self, poi_name: str) -> Optional[Tuple[float, float]]:
        """Find lat/lon for a POI by name"""
        poi_name_lower = poi_name.lower()
        if poi_name_lower in self.pois:
            poi = self.pois[poi_name_lower]
            return (poi['lat'], poi['lon'])
        return None
    
    def _calculate_path_stats(self, path: List[int]) -> Dict:
        """Calculate total GVI and SVF statistics for a path"""
        if len(path) < 2:
            return {'total_gvi': 0, 'total_svf': 0, 'length': 0}
        
        total_length = 0
        total_gvi = 0
        total_svf = 0
        
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            edge_length = self.graph[u][v]['length']
            total_length += edge_length
            
            # Add GVI and SVF values for this segment
            # Weight by the edge length for fair comparison
            u_gvi = self.nodes[u]['gvi']
            v_gvi = self.nodes[v]['gvi']
            avg_gvi = (u_gvi + v_gvi) / 2
            total_gvi += avg_gvi * edge_length
            
            u_svf = self.nodes[u]['svf']
            v_svf = self.nodes[v]['svf']
            avg_svf = (u_svf + v_svf) / 2
            total_svf += avg_svf * edge_length
        
        return {
            'length': total_length,
            'total_gvi': total_gvi,
            'total_svf': total_svf,
            'avg_gvi': total_gvi / total_length if total_length > 0 else 0,
            'avg_svf': total_svf / total_length if total_length > 0 else 0
        }

    def calculate_paths(self, start_name: str, end_name: str) -> Dict:
        """Calculate multiple paths between start and end destinations"""
        # Find coordinates for start and end
        start_coords = self.find_poi_location(start_name)
        end_coords = self.find_poi_location(end_name)
        
        if not start_coords or not end_coords:
            return {"error": "Could not find one or both destinations"}
        
        # Find nearest nodes
        start_node = self.find_nearest_node(*start_coords)
        end_node = self.find_nearest_node(*end_coords)
        
        if not start_node or not end_node:
            return {"error": "Could not find walking network near destinations"}
        
        try:
            # 1. Shortest path (by length)
            shortest_path = nx.shortest_path(self.graph, start_node, end_node, weight='length')
            shortest_stats = self._calculate_path_stats(shortest_path)
            
            # 2. Max GVI path (with constraint)
            max_gvi_result = self._find_constrained_path(start_node, end_node, 'gvi_weight', 
                                                        shortest_stats['length'])
            
            # 3. Min SVF path (with constraint)
            min_svf_result = self._find_constrained_path(start_node, end_node, 'svf_weight', 
                                                        shortest_stats['length'])
            
            # Create result with detailed statistics
            paths = {
                'shortest': {
                    'path': shortest_path,
                    'stats': shortest_stats,
                    'type': 'fastest',
                    'description': f"Fastest route ({self._format_distance(shortest_stats['length'])})"
                }
            }
            
            # Add max GVI path if different from shortest
            if max_gvi_result and max_gvi_result['path'] != shortest_path:
                paths['max_gvi'] = {
                    'path': max_gvi_result['path'],
                    'stats': max_gvi_result['stats'],
                    'type': 'most_green',
                    'description': f"Most green route ({self._format_distance(max_gvi_result['stats']['length'])}, GVI: {max_gvi_result['stats']['avg_gvi']:.1f})"
                }
            
            # Add min SVF path if different from others
            if (min_svf_result and 
                min_svf_result['path'] != shortest_path and 
                (not max_gvi_result or min_svf_result['path'] != max_gvi_result['path'])):
                paths['min_svf'] = {
                    'path': min_svf_result['path'],
                    'stats': min_svf_result['stats'],
                    'type': 'most_shade',
                    'description': f"Most shade route ({self._format_distance(min_svf_result['stats']['length'])}, SVF: {min_svf_result['stats']['avg_svf']:.1f})"
                }
            
            # Generate map with POI names
            map_html = self._create_paths_map(paths, start_coords, end_coords, start_name, end_name)
            
            return {
                'paths': paths,
                'map': map_html,
                'start_coords': start_coords,
                'end_coords': end_coords,
                'description': f"Found {len(paths)} walking path(s) from {start_name} to {end_name}"
            }
            
        except nx.NetworkXNoPath:
            return {"error": "No walking path found between destinations"}
    
    def _find_constrained_path(self, start: int, end: int, weight_attr: str, 
                             max_length: float) -> Optional[Dict]:
        """Find path optimizing criteria with length constraint"""
        try:
            # Find path optimizing the criteria
            path = nx.shortest_path(self.graph, start, end, weight=weight_attr)
            
            # Calculate detailed statistics
            stats = self._calculate_path_stats(path)
            
            # Check constraint: path can be at most 1km longer than shortest
            if stats['length'] <= max_length + 1000:  # 1000 meters = 1km
                return {'path': path, 'stats': stats}
            else:
                return None
                
        except nx.NetworkXNoPath:
            return None
    
    def _create_paths_map(self, paths: Dict, start_coords: Tuple, end_coords: Tuple, 
                         start_name: str, end_name: str) -> str:
        """Create Folium map with multiple paths"""
        # Center map on midpoint
        center_lat = (start_coords[0] + end_coords[0]) / 2
        center_lon = (start_coords[1] + end_coords[1]) / 2
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=14)
        
        # Add start and end markers with POI information
        folium.Marker(
            start_coords,
            popup=f"<div style='min-width: 200px;'><b>Start:</b> {start_name}</div>",
            tooltip=start_name,
            icon=folium.Icon(color='green', icon='play')
        ).add_to(m)
        
        folium.Marker(
            end_coords,
            popup=f"<div style='min-width: 200px;'><b>End:</b> {end_name}</div>",
            tooltip=end_name,
            icon=folium.Icon(color='red', icon='stop')
        ).add_to(m)
        
        # Path colors and styles
        path_styles = {
            'shortest': {'color': 'blue', 'weight': 5, 'opacity': 0.8},
            'max_gvi': {'color': 'green', 'weight': 4, 'opacity': 0.7},
            'min_svf': {'color': 'purple', 'weight': 4, 'opacity': 0.7}
        }
        
        # Add paths to map
        for path_type, path_data in paths.items():
            if not path_data['path']:
                continue
                
            coordinates = []
            for node_id in path_data['path']:
                if node_id in self.nodes:
                    node = self.nodes[node_id]
                    coordinates.append([node['lat'], node['lon']])
            
            if coordinates:
                style = path_styles[path_type]
                stats = path_data['stats']
                popup_text = (f"<div style='min-width: 250px;'>"
                            f"<b>{path_data['description']}</b><br>"
                            f"Length: {self._format_distance(stats['length'])}<br>"
                            f"Avg GVI: {stats['avg_gvi']:.1f}<br>"
                            f"Avg SVF: {stats['avg_svf']:.1f}"
                            f"</div>")
                
                folium.PolyLine(
                    coordinates,
                    popup=popup_text,
                    tooltip=path_data['description'],
                    **style
                ).add_to(m)
        
        return m._repr_html_()


# Initialize global pathfinder instance
pathfinder = None

def initialize_pathfinder():
    """Initialize the pathfinder with data files"""
    global pathfinder
    try:
        pathfinder = MultiCriteriaPathfinder(
            "data/walk_nodes.geojson",
            "data/walk_edges.geojson", 
            "data/pois.geojson"
        )
        return True
    except Exception as e:
        print(f"Error initializing pathfinder: {e}")
        return False

def get_walk_paths(start_name: str, end_name: str) -> Dict:
    """Get walking paths between two destinations"""
    global pathfinder
    if not pathfinder:
        if not initialize_pathfinder():
            return {"error": "Pathfinding system not available"}
    
    return pathfinder.calculate_paths(start_name, end_name) 