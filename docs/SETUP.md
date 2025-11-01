# Setup Guide

## Prerequisites

- **Python 3.9+** with pip
- **Node.js 14+** with npm
- **Git**

## Backend Setup

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment** [[memory:4081650]]
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables** (optional)
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys if using AI features
   ```

5. **Go back to project root**
   ```bash
   cd ..
   ```

## Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Go back to project root**
   ```bash
   cd ..
   ```

## Running the Application

**Start both backend and frontend:**
```bash
./run.sh
```

This will start:
- Backend at: `http://localhost:8000`
- Frontend at: `http://localhost:3000`
- API docs at: `http://localhost:8000/docs`

Press `Ctrl+C` to stop both services.

## Data Files

The application expects the following data files in `backend/data/`:
- `sectors.geojson` - Chandigarh sector boundaries
- `pois.geojson` - Points of Interest
- `walk_nodes.geojson` - Walkable network nodes
- `walk_edges.geojson` - Walkable network edges
- `boundary.geojson` - City boundary

## Troubleshooting

### Backend Issues

**Import errors:**
- Make sure you're in the backend directory
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

**Data loading errors:**
- Check that all required geojson files are in `backend/data/`
- Verify file permissions

### Frontend Issues

**Port already in use:**
```bash
# Kill process on port 3000
npx kill-port 3000
```

**Build errors:**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

## Development

- Backend runs on port 8000 with auto-reload enabled
- Frontend runs on port 3000 with hot module replacement
- API documentation is available at `/docs` on the backend

