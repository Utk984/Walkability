/**
 * Centralized API endpoint definitions
 */
import { apiClient } from './client';

// Walkability Endpoints
export const walkabilityAPI = {
  getChoropleth: () => 
    apiClient.get('/map/choropleth'),
  
  getTopSectors: (k = 5) => 
    apiClient.post('/map/top-sectors', { k }),
  
  getBottomSectors: (k = 5) => 
    apiClient.post('/map/bottom-sectors', { k }),
  
  analyzeSector: (sectorName) => 
    apiClient.post('/map/sector-analysis', { sector_name: sectorName }),
  
  compareSectors: (sector1, sector2) =>
    apiClient.post('/map/compare-sectors', { sector1, sector2 }),
  
  calculateComprehensive: (params = {}) =>
    apiClient.post('/walkability/comprehensive/calculate', params),
  
  getSectorBreakdown: (sectorName) =>
    apiClient.post('/walkability/comprehensive/sector-breakdown', { sector_name: sectorName }),
  
  getComprehensiveMap: () =>
    apiClient.get('/walkability/comprehensive/map'),
  
  getDefaultWeights: () =>
    apiClient.get('/walkability/comprehensive/default-weights'),
};

// Environmental Endpoints
export const environmentalAPI = {
  analyzeSector: (sectorName) =>
    apiClient.post('/environmental/sector-analysis', { sector_name: sectorName }),
  
  findGreenCorridors: (params = {}) =>
    apiClient.post('/environmental/green-corridors', params),
  
  suggestPath: (sectorName, poiType = 'restaurant', optimizeFor = 'gvi') =>
    apiClient.post('/environmental/suggest-path', {
      sector_name: sectorName,
      poi_type: poiType,
      optimize_for: optimizeFor
    }),
  
  compareSectors: (sector1, sector2) =>
    apiClient.post('/environmental/compare-sectors', { sector1, sector2 }),
  
  getTopSectors: (criteria = 'gvi', k = 5) =>
    apiClient.post('/environmental/top-sectors', { criteria, k }),
  
  findRouteWithPOIs: (params) =>
    apiClient.post('/environmental/route-with-pois', params),
  
  analyzeWalkability: (gviThreshold = 25.0, svfThreshold = 30.0) =>
    apiClient.post('/environmental/walkability-analysis', {
      gvi_threshold: gviThreshold,
      svf_threshold: svfThreshold
    }),
  
  suggestGreenCircuit: (sectorName, circuitLength = 'short') =>
    apiClient.post('/environmental/green-circuit', {
      sector_name: sectorName,
      circuit_length: circuitLength
    }),
};

// Pathfinding Endpoints
export const pathfindingAPI = {
  getWalkPaths: (destinationA, destinationB) =>
    apiClient.post('/walk-paths', {
      destination_a: destinationA,
      destination_b: destinationB
    }),
};

// Profile Endpoints
export const profileAPI = {
  generateWeights: (userType, gender, age, additionalInfo = '') =>
    apiClient.post('/profile/generate-weights', {
      user_type: userType,
      gender: gender,
      age: age,
      additional_info: additionalInfo
    }),
  
  getDefaultWeights: () =>
    apiClient.get('/profile/default-weights'),
  
  calculateDynamicScores: (categoryWeights, includeInsights = true) =>
    apiClient.post('/profile/calculate-dynamic-scores', {
      category_weights: categoryWeights,
      include_insights: includeInsights
    }),
};

// Chat Endpoints
export const chatAPI = {
  sendMessage: (text) =>
    apiClient.post('/chat', { text }),
};

// Search Endpoints
export const searchAPI = {
  searchPOIs: (query, limit = 10) =>
    apiClient.post('/search/pois', { query, limit }),
};

// Health Check
export const healthAPI = {
  check: () => apiClient.get('/health'),
};

