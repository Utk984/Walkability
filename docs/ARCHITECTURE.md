# System Architecture

## Overview

The Walkability Platform follows a clean, modular architecture with clear separation between the backend API and frontend UI.

## High-Level Architecture

```
┌─────────────────┐         ┌──────────────────┐
│  React Frontend │ ◄─────► │  FastAPI Backend │
│   (Port 3000)   │  HTTP   │   (Port 8000)    │
└─────────────────┘         └──────────────────┘
                                     │
                                     ▼
                            ┌─────────────────┐
                            │  GeoJSON Data   │
                            │   (On Disk)     │
                            └─────────────────┘
```

## Backend Architecture

### Layered Structure

```
┌────────────────────────────────────────┐
│         API Layer (routes/)            │
│  ┌──────┬───────┬──────┬────────┐     │
│  │Walk. │Environ│Paths │Profile │     │
│  └──────┴───────┴──────┴────────┘     │
├────────────────────────────────────────┤
│      Request Models (models/)          │
│      Pydantic Validation               │
├────────────────────────────────────────┤
│      Service Layer (services/)         │
│      Data Loading & Caching            │
├────────────────────────────────────────┤
│    Analysis Modules (src/analysis/)    │
│  ┌──────────┬────────────┬──────────┐ │
│  │Walkabil. │Environment │Pathfind. │ │
│  └──────────┴────────────┴──────────┘ │
├────────────────────────────────────────┤
│      Data Access (src/data/)           │
│      GeoPandas, File I/O               │
└────────────────────────────────────────┘
```

### Key Components

#### 1. **API Layer** (`app/routes/`)
- Modular route files by domain
- Request validation using Pydantic
- Response formatting
- Error handling

#### 2. **Configuration** (`app/config.py`)
- Centralized settings
- Environment-based configuration
- API keys management
- Path definitions

#### 3. **Service Layer** (`app/services/`)
- Data loading and caching
- Business logic orchestration
- Coordinates between analysis modules

#### 4. **Analysis Modules** (`src/analysis/`)
- **Walkability Analysis**: Sector scoring, POI analysis
- **Environmental Analysis**: GVI/SVF calculations
- **Pathfinding**: Multi-criteria route finding
- **Map Visualization**: Folium map generation

#### 5. **Data Access** (`src/data/`)
- GeoJSON loading
- Data preprocessing
- Search utilities

## Frontend Architecture

### Component Structure

```
App.jsx
├── LeftSidebar.jsx
├── RightSidebar.jsx
├── ChatBox.jsx
├── Directions.jsx
└── Map Container (dangerouslySetInnerHTML)
```

### Data Flow

```
┌──────────────┐
│ User Action  │
└──────┬───────┘
       ▼
┌──────────────┐
│ API Call     │  (api/endpoints.js)
└──────┬───────┘
       ▼
┌──────────────┐
│ Backend      │  (FastAPI processes)
└──────┬───────┘
       ▼
┌──────────────┐
│ Response     │
└──────┬───────┘
       ▼
┌──────────────┐
│ State Update │  (useState)
└──────┬───────┘
       ▼
┌──────────────┐
│ UI Render    │
└──────────────┘
```

## Data Flow

### Startup Sequence

1. **Backend starts** → Loads GeoJSON data into memory
2. **Pathfinding initializes** → Builds NetworkX graph
3. **Frontend starts** → Requests initial choropleth map
4. **Map displays** → User can interact

### Request Flow Example: Sector Analysis

```
User clicks "Analyze Sector 22"
    ↓
Frontend: walkabilityAPI.analyzeSector("22")
    ↓
Backend: POST /map/sector-analysis
    ↓
Router: walkability.py → analyze_sector()
    ↓
Service: get_data() → returns cached GeoDataFrames
    ↓
Analysis: analyze_sector_amenities(data, "22")
    ↓ (filters POIs, creates map, calculates stats)
Response: {map: HTML, summary: {...}, categories: [...]}
    ↓
Frontend: Updates state → Renders map
```

## Key Design Decisions

### 1. **In-Memory Data Storage**
- **Why**: Fast access, no database overhead for read-only geospatial data
- **Trade-off**: Higher memory usage, data updates require restart

### 2. **Folium for Maps**
- **Why**: Python-native, integrates with GeoPandas, rich visualizations
- **Trade-off**: Server-side rendering, HTML injection in frontend

### 3. **Modular Routes**
- **Why**: Better organization, easier maintenance, clear separation of concerns
- **Trade-off**: More files to navigate

### 4. **Pydantic Validation**
- **Why**: Type safety, automatic API docs, clear contracts
- **Trade-off**: Additional boilerplate

### 5. **Centralized API Client**
- **Why**: DRY principle, consistent error handling, easy to modify endpoints
- **Trade-off**: Indirect function calls

## Scalability Considerations

### Current Limitations
- Single-threaded data loading
- In-memory data storage
- Server-side map rendering

### Potential Improvements
- PostgreSQL/PostGIS for data storage
- Redis for caching
- Client-side map rendering (Leaflet.js)
- Async data loading
- Horizontal scaling with load balancer

## Security

### Current Implementation
- CORS restricted to localhost
- Environment variables for API keys
- No authentication (local development)

### Production Recommendations
- Add authentication (JWT tokens)
- Rate limiting
- Input sanitization
- HTTPS only
- Proper CORS configuration

## Performance

### Optimization Strategies
- Data loaded once at startup (caching)
- NetworkX graph pre-built
- Spatial indexing in GeoPandas
- Debounced search inputs (frontend)

### Bottlenecks
- Large GeoJSON file loading
- Complex spatial operations
- Map HTML generation

## Monitoring & Debugging

### Development
- FastAPI auto-reload
- React hot module replacement
- Browser DevTools for frontend
- FastAPI `/docs` for API testing

### Logging
- Console logs in development
- Request/response interceptors
- Error stack traces

## Extension Points

### Adding New Features

1. **New API Endpoint**:
   - Add route in appropriate file (`app/routes/`)
   - Add Pydantic model (`app/models/schemas.py`)
   - Add frontend API call (`frontend/src/api/endpoints.js`)

2. **New Analysis Type**:
   - Create module in `src/analysis/`
   - Import in route file
   - Expose via API endpoint

3. **New Data Source**:
   - Update `data_loader.py`
   - Modify GeoDataFrame structure
   - Update dependent analysis modules

## Testing Strategy

While not implemented, recommended approach:

```
├── Unit Tests
│   ├── Analysis functions
│   ├── Data loading
│   └── Utility functions
├── Integration Tests
│   ├── API endpoints
│   └── Service layer
└── E2E Tests
    └── User workflows
```

