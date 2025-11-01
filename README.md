# 🚶 Chandigarh Walkability Platform

A comprehensive geospatial analysis platform for evaluating and visualizing walkability in Chandigarh, India. The platform combines POI accessibility, environmental metrics (Green View Index, Sky View Factor), and intelligent pathfinding to provide personalized walkability scores.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![React](https://img.shields.io/badge/React-17.0+-blue.svg)

## ✨ Features

### 🗺️ **Walkability Analysis**
- Comprehensive walkability scoring based on POI density, diversity, and distribution
- Sector-by-sector analysis with detailed amenity breakdowns
- Side-by-side sector comparisons
- City-wide choropleth visualizations

### 🌳 **Environmental Metrics**
- **Green View Index (GVI)**: Measures visible vegetation along streets
- **Sky View Factor (SVF)**: Evaluates tree coverage and shade availability
- Green corridor identification and mapping
- Environmental route optimization

### 🚶 **Smart Pathfinding**
- Multiple route options between destinations:
  - **Shortest Path**: Quickest route
  - **Greenest Path**: Maximum vegetation exposure
  - **Shadiest Path**: Maximum tree coverage
- POI-aware routing with environmental considerations

### 👤 **Personalized Profiles**
- AI-powered weight generation based on user profiles:
  - Working Professionals
  - Students
  - Tourists
  - Senior Citizens
  - Families with Kids
- Custom walkability scoring based on individual preferences

### 💬 **Natural Language Interface**
- AI-powered chat for natural language queries
- Intelligent query parsing and visualization generation

## 🏗️ Project Structure

```
walkability/
├── backend/
│   ├── app/                   # Main application (all code here)
│   │   ├── main.py           # FastAPI app setup
│   │   ├── config.py         # Configuration
│   │   ├── routes/           # API endpoints by domain
│   │   ├── models/           # Pydantic schemas
│   │   ├── services/         # Data loading
│   │   ├── analysis/         # Core walkability logic
│   │   ├── api/              # AI & profile logic
│   │   └── data/             # Data utilities
│   ├── data/                 # GeoJSON data files
│   └── requirements.txt
│
├── frontend/
│   └── src/
│       ├── api/              # API client & endpoints
│       ├── components/       # React components
│       ├── hooks/            # Custom React hooks
│       └── utils/            # Utilities & constants
│
├── research/                 # Research materials
│   ├── notebooks/            # Jupyter notebooks
│   ├── scripts/              # Experimental scripts
│   └── literature/           # Research papers
│
├── docs/                     # Documentation
│   ├── SETUP.md              # Setup guide
│   └── API.md                # API reference
│
└── run.sh                    # Start backend server
```

## 🚀 Quick Start

### First Time Setup

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

**Frontend:**
```bash
cd frontend
npm install
cd ..
```

### Running the Application

```bash
# Start both backend and frontend together
./run.sh
```

**Access the application:**
- **Frontend:** `http://localhost:3000` 
- **Backend API:** `http://localhost:8000`
- **API Docs:** `http://localhost:8000/docs`

Press `Ctrl+C` to stop both services.

## 📊 Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **GeoPandas** - Geospatial data processing
- **NetworkX** - Graph-based pathfinding
- **Folium** - Interactive map generation
- **Shapely** - Geometric operations

### Frontend
- **React** - UI framework
- **Leaflet** - Interactive maps
- **Axios** - HTTP client
- **Tailwind CSS** - Styling

### Data
- **GeoJSON** - Geospatial data format
- **OpenStreetMap** - Network data source

## 📚 Documentation

- **[Setup Guide](docs/SETUP.md)** - Detailed installation and setup instructions
- **[API Reference](docs/API.md)** - Complete API endpoint documentation
- **[Research](research/README.md)** - Research materials and experiments

## 🎯 Use Cases

1. **Urban Planning**: Identify areas lacking walkable infrastructure
2. **Real Estate**: Evaluate neighborhood walkability scores
3. **Tourism**: Find green, pedestrian-friendly routes
4. **Health & Fitness**: Discover scenic walking circuits
5. **Environmental Studies**: Analyze urban greenery distribution

## 📈 Key Metrics

The platform analyzes walkability using multiple dimensions:

1. **POI Accessibility**: Count and density of nearby amenities
2. **POI Diversity**: Variety of different POI types
3. **Spatial Distribution**: How evenly POIs are spread
4. **Environmental Quality**: Green View Index + Sky View Factor
5. **Green Connectivity**: Access to green corridors

## 🔑 Environment Variables

Create a `.env` file in the backend directory (see `backend/.env.example`):

```bash
# Optional - Only needed for AI features
OPENAI_API_KEY=your_key_here
GOOGLE_MAPS_API_KEY=your_key_here
```

## 🤝 Contributing

This is a personal project, but suggestions and feedback are welcome! Feel free to open an issue for:
- Bug reports
- Feature requests
- Documentation improvements

## 📝 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- OpenStreetMap for network data
- Google Places API for POI data
- Research papers on walkability metrics (see `research/literature/`)

## 📧 Contact

For questions or collaboration opportunities, please open an issue on GitHub.

---

**Built with ❤️ for better urban walkability**
