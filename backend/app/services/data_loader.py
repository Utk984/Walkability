"""Data loading and management"""
from app.data.data_loader import load_geospatial_data

# Global data cache
_data_cache = None


def initialize_data():
    """Load geospatial data once at startup"""
    global _data_cache
    if _data_cache is None:
        _data_cache = load_geospatial_data()
    return _data_cache


def get_data():
    """Get cached geospatial data"""
    if _data_cache is None:
        return initialize_data()
    return _data_cache
