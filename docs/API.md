# API Reference

Base URL: `http://localhost:8000`

## Walkability Endpoints

### `GET /map/choropleth`
Get comprehensive walkability choropleth map.

**Response:** HTML map representation

---

### `POST /map/top-sectors`
Get top k sectors by walk score.

**Request Body:**
```json
{
  "k": 5
}
```

---

### `POST /map/sector-analysis`
Analyze specific sector amenities.

**Request Body:**
```json
{
  "sector_name": "22"
}
```

---

### `POST /map/compare-sectors`
Compare two sectors.

**Request Body:**
```json
{
  "sector1": "22",
  "sector2": "17"
}
```

---

## Environmental Endpoints

### `POST /environmental/sector-analysis`
Analyze environmental quality of a sector.

**Request Body:**
```json
{
  "sector_name": "22"
}
```

---

### `POST /environmental/green-corridors`
Find green corridors in the city.

**Request Body:**
```json
{
  "sector_name": "22",  // Optional
  "min_gvi": 20.0
}
```

---

### `POST /environmental/top-sectors`
Get top sectors by environmental criteria.

**Request Body:**
```json
{
  "criteria": "gvi",  // "gvi", "svf", or "combined"
  "k": 5
}
```

---

## Pathfinding Endpoints

### `POST /walk-paths`
Get walking paths between two destinations.

**Request Body:**
```json
{
  "destination_a": "Elante Mall",
  "destination_b": "Rock Garden"
}
```

**Response:**
```json
{
  "map": "...",
  "paths": {
    "shortest": {...},
    "greenest": {...},
    "shadiest": {...}
  },
  "description": "...",
  "start_coords": [30.7333, 76.7794],
  "end_coords": [30.7400, 76.7900]
}
```

---

## Profile Endpoints

### `POST /profile/generate-weights`
Generate walkability weights based on user profile.

**Request Body:**
```json
{
  "user_type": "Working Professional",
  "gender": "Male",
  "age": "28-37",
  "additional_info": "Likes fitness"
}
```

---

### `POST /profile/calculate-dynamic-scores`
Calculate personalized walkability scores.

**Request Body:**
```json
{
  "category_weights": {
    "Essential Services": 0.25,
    "Food and Drinks": 0.20,
    "Shopping": 0.15,
    "Entertainment": 0.10,
    "Tourism": 0.10,
    "Sports": 0.15,
    "Public Transport": 0.05
  },
  "include_insights": true
}
```

---

## Chat Endpoint

### `POST /chat`
Natural language queries about walkability.

**Request Body:**
```json
{
  "text": "Show me the most walkable sectors"
}
```

---

## Search Endpoints

### `POST /search/pois`
Search for POIs with fuzzy matching.

**Request Body:**
```json
{
  "query": "elante",
  "limit": 10
}
```

---

## Health Check

### `GET /health`
Check API health status.

**Response:**
```json
{
  "status": "healthy"
}
```

---

For interactive API documentation, visit: `http://localhost:8000/docs`

