// File: src/components/Sidebar.jsx
import React, { useState } from "react";
import axios from "axios";

export default function Sidebar({ visible, toggle, resultData, setResultData }) {
  const [queryType, setQueryType] = useState("Walk Score Map");
  const [topK, setTopK] = useState(5);
  const [sector, setSector] = useState("17");
  const [secondSector, setSecondSector] = useState("22");
  const [isLoading, setIsLoading] = useState(false);

  // Environmental analysis specific states
  const [minGvi, setMinGvi] = useState(20.0);
  const [poiType, setPoiType] = useState("restaurant");
  const [optimizeFor, setOptimizeFor] = useState("gvi");
  const [environmentalCriteria, setEnvironmentalCriteria] = useState("gvi");
  const [maxWalkDistance, setMaxWalkDistance] = useState(1000);
  const [gviThreshold, setGviThreshold] = useState(25.0);
  const [svfThreshold, setSvfThreshold] = useState(30.0);
  const [circuitLength, setCircuitLength] = useState("short");

  const handleSubmit = async () => {
    if (isLoading) return;
    
    setIsLoading(true);
    try {
      let response;
      
      switch (queryType) {
        case "Walk Score Map":
          response = await axios.get("http://localhost:8000/map/choropleth");
          setResultData({
            map: response.data,
            description: "Walk score choropleth map of Chandigarh"
          });
          break;

        case "Top Walkable Sectors":
          response = await axios.post("http://localhost:8000/map/top-sectors", { k: topK });
          setResultData(response.data);
          break;

        case "Lowest Walkable Sectors":
          response = await axios.post("http://localhost:8000/map/bottom-sectors", { k: topK });
          setResultData(response.data);
          break;

        case "Analyze a Sector":
          response = await axios.post("http://localhost:8000/map/sector-analysis", { sector_name: sector });
          setResultData(response.data);
          break;

        case "Compare Sectors":
          response = await axios.post("http://localhost:8000/map/compare-sectors", {
            sector1: sector,
            sector2: secondSector
          });
          setResultData(response.data);
          break;

        // Environmental Analysis Options
        case "Environmental Sector Analysis":
          response = await axios.post("http://localhost:8000/environmental/sector-analysis", { 
            sector_name: sector 
          });
          setResultData(response.data);
          break;

        case "Find Green Corridors":
          response = await axios.post("http://localhost:8000/environmental/green-corridors", {
            sector_name: sector === "All" ? null : sector,
            min_gvi: minGvi
          });
          setResultData(response.data);
          break;

        case "Environmental Path Suggestion":
          response = await axios.post("http://localhost:8000/environmental/suggest-path", {
            sector_name: sector,
            poi_type: poiType,
            optimize_for: optimizeFor
          });
          setResultData(response.data);
          break;

        case "Compare Environmental Quality":
          response = await axios.post("http://localhost:8000/environmental/compare-sectors", {
            sector1: sector,
            sector2: secondSector
          });
          setResultData(response.data);
          break;

        case "Top Environmental Sectors":
          response = await axios.post("http://localhost:8000/environmental/top-sectors", {
            criteria: environmentalCriteria,
            k: topK
          });
          setResultData(response.data);
          break;

        case "Environmental Route with POIs":
          response = await axios.post("http://localhost:8000/environmental/route-with-pois", {
            sector_name: sector,
            poi_type: poiType,
            optimize_for: optimizeFor,
            max_walk_distance: maxWalkDistance
          });
          setResultData(response.data);
          break;

        case "Environmental Walkability Analysis":
          response = await axios.post("http://localhost:8000/environmental/walkability-analysis", {
            gvi_threshold: gviThreshold,
            svf_threshold: svfThreshold
          });
          setResultData(response.data);
          break;

        case "Green Walking Circuit":
          response = await axios.post("http://localhost:8000/environmental/green-circuit", {
            sector_name: sector,
            circuit_length: circuitLength
          });
          setResultData(response.data);
          break;
      }
    } catch (error) {
      console.error("Error executing query:", error);
      setResultData({
        type: "error",
        description: "An error occurred while processing your request."
      });
    } finally {
      setIsLoading(false);
    }
  };

  const renderFormFields = () => {
    const isEnvironmentalQuery = [
      "Environmental Sector Analysis",
      "Find Green Corridors", 
      "Environmental Path Suggestion",
      "Compare Environmental Quality",
      "Top Environmental Sectors",
      "Environmental Route with POIs",
      "Environmental Walkability Analysis",
      "Green Walking Circuit"
    ].includes(queryType);

    return (
      <>
        {/* Standard fields for most queries */}
        {(queryType === "Top Walkable Sectors" || 
          queryType === "Lowest Walkable Sectors" || 
          queryType === "Top Environmental Sectors") && (
          <>
            <label className="block mb-2 text-sm">Number of Sectors</label>
            <input
              type="number"
              className="w-full p-2 border mb-4"
              value={topK}
              onChange={(e) => setTopK(parseInt(e.target.value) || 5)}
              min="1"
              max="20"
            />
          </>
        )}

        {(queryType === "Analyze a Sector" || 
          queryType === "Environmental Sector Analysis" ||
          queryType === "Environmental Path Suggestion" ||
          queryType === "Environmental Route with POIs" ||
          queryType === "Green Walking Circuit" ||
          (queryType === "Find Green Corridors" && sector !== "All")) && (
          <>
            <label className="block mb-2 text-sm">Sector Number</label>
            <input
              type="text"
              className="w-full p-2 border mb-4"
              value={sector}
              onChange={(e) => setSector(e.target.value)}
              placeholder="e.g., 17, 22, 48"
            />
          </>
        )}

        {(queryType === "Compare Sectors" || queryType === "Compare Environmental Quality") && (
          <>
            <label className="block mb-2 text-sm">First Sector</label>
            <input
              type="text"
              className="w-full p-2 border mb-2"
              value={sector}
              onChange={(e) => setSector(e.target.value)}
              placeholder="e.g., 17"
            />
            <label className="block mb-2 text-sm">Second Sector</label>
            <input
              type="text"
              className="w-full p-2 border mb-4"
              value={secondSector}
              onChange={(e) => setSecondSector(e.target.value)}
              placeholder="e.g., 22"
            />
          </>
        )}

        {/* Environmental-specific fields */}
        {queryType === "Find Green Corridors" && (
          <>
            <label className="block mb-2 text-sm">Scope</label>
            <select
              className="w-full p-2 border mb-2"
              value={sector}
              onChange={(e) => setSector(e.target.value)}
            >
              <option value="All">All Sectors</option>
              <option value="17">Sector 17</option>
              <option value="22">Sector 22</option>
              <option value="48">Sector 48</option>
            </select>
            <label className="block mb-2 text-sm">Minimum GVI (Green View Index)</label>
            <input
              type="number"
              step="0.1"
              className="w-full p-2 border mb-4"
              value={minGvi}
              onChange={(e) => setMinGvi(parseFloat(e.target.value) || 20.0)}
              min="0"
              max="100"
            />
          </>
        )}

        {(queryType === "Environmental Path Suggestion" || queryType === "Environmental Route with POIs") && (
          <>
            <label className="block mb-2 text-sm">POI Type</label>
            <select
              className="w-full p-2 border mb-2"
              value={poiType}
              onChange={(e) => setPoiType(e.target.value)}
            >
              <option value="restaurant">Restaurant</option>
              <option value="cafe">Cafe</option>
              <option value="park">Park</option>
              <option value="hospital">Hospital</option>
              <option value="school">School</option>
              <option value="grocery_store">Grocery Store</option>
            </select>
            <label className="block mb-2 text-sm">Optimize For</label>
            <select
              className="w-full p-2 border mb-4"
              value={optimizeFor}
              onChange={(e) => setOptimizeFor(e.target.value)}
            >
              <option value="gvi">High Vegetation (GVI)</option>
              <option value="svf">Good Shade (Low SVF)</option>
              {queryType === "Environmental Route with POIs" && (
                <option value="balanced">Balanced Quality</option>
              )}
            </select>
          </>
        )}

        {queryType === "Top Environmental Sectors" && (
          <>
            <label className="block mb-2 text-sm">Environmental Criteria</label>
            <select
              className="w-full p-2 border mb-4"
              value={environmentalCriteria}
              onChange={(e) => setEnvironmentalCriteria(e.target.value)}
            >
              <option value="gvi">Vegetation (GVI)</option>
              <option value="svf">Shade (Low SVF)</option>
              <option value="combined">Combined Score</option>
            </select>
          </>
        )}

        {queryType === "Environmental Route with POIs" && (
          <>
            <label className="block mb-2 text-sm">Max Walking Distance (meters)</label>
            <input
              type="number"
              className="w-full p-2 border mb-4"
              value={maxWalkDistance}
              onChange={(e) => setMaxWalkDistance(parseInt(e.target.value) || 1000)}
              min="100"
              max="5000"
              step="100"
            />
          </>
        )}

        {queryType === "Environmental Walkability Analysis" && (
          <>
            <label className="block mb-2 text-sm">GVI Threshold (minimum vegetation)</label>
            <input
              type="number"
              step="0.1"
              className="w-full p-2 border mb-2"
              value={gviThreshold}
              onChange={(e) => setGviThreshold(parseFloat(e.target.value) || 25.0)}
              min="0"
              max="100"
            />
            <label className="block mb-2 text-sm">SVF Threshold (maximum for shade)</label>
            <input
              type="number"
              step="0.1"
              className="w-full p-2 border mb-4"
              value={svfThreshold}
              onChange={(e) => setSvfThreshold(parseFloat(e.target.value) || 30.0)}
              min="0"
              max="100"
            />
          </>
        )}

        {queryType === "Green Walking Circuit" && (
          <>
            <label className="block mb-2 text-sm">Circuit Length</label>
            <select
              className="w-full p-2 border mb-4"
              value={circuitLength}
              onChange={(e) => setCircuitLength(e.target.value)}
            >
              <option value="short">Short (&lt; 1km)</option>
              <option value="medium">Medium (1-2km)</option>
              <option value="long">Long (&gt; 2km)</option>
            </select>
          </>
        )}
      </>
    );
  };

  return (
    <div
      className={`absolute top-0 left-0 h-full bg-white shadow-lg z-50 transition-all duration-300 ${
        visible ? "w-80" : "w-12"
      }`}
    >
      <div className="flex items-center justify-between p-2 bg-gray-100 border-b">
        <button
          onClick={toggle}
          className="text-xs px-2 py-1 bg-blue-600 text-white rounded"
        >
          {visible ? "‹" : "›"}
        </button>
        <span className="text-sm font-bold">{visible && "Explorer"}</span>
      </div>

      {visible && (
        <div className="p-4 overflow-y-auto" style={{ height: 'calc(100vh - 48px)' }}>
          <label className="block mb-2 text-sm font-medium">Query Type</label>
          <select
            className="w-full p-2 border mb-4"
            value={queryType}
            onChange={(e) => setQueryType(e.target.value)}
            disabled={isLoading}
          >
            <optgroup label="Basic Walkability">
              <option>Walk Score Map</option>
              <option>Top Walkable Sectors</option>
              <option>Lowest Walkable Sectors</option>
              <option>Analyze a Sector</option>
              <option>Compare Sectors</option>
            </optgroup>
            <optgroup label="Environmental Analysis">
              <option>Environmental Sector Analysis</option>
              <option>Find Green Corridors</option>
              <option>Environmental Path Suggestion</option>
              <option>Compare Environmental Quality</option>
              <option>Top Environmental Sectors</option>
              <option>Environmental Route with POIs</option>
              <option>Environmental Walkability Analysis</option>
              <option>Green Walking Circuit</option>
            </optgroup>
          </select>

          {renderFormFields()}

          <button
            className={`w-full px-4 py-2 rounded font-medium transition-colors ${
              isLoading
                ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                : "bg-blue-600 text-white hover:bg-blue-700"
            }`}
            onClick={handleSubmit}
            disabled={isLoading}
          >
            {isLoading ? (
              <div className="flex items-center justify-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Processing...
              </div>
            ) : (
              "Execute Query"
            )}
          </button>

          {resultData?.description && (
            <div className="mt-4 p-3 border-t">
              <h3 className="font-bold text-sm">Result</h3>
              <p className="text-sm whitespace-pre-line">{resultData.description}</p>
            </div>
          )}

          {resultData?.table && (
            <div className="mt-4">
              <h3 className="font-bold text-sm mb-2">Details</h3>
              <table className="w-full text-xs border">
                <thead>
                  <tr>
                    {Object.keys(resultData.table[0]).map((col) => (
                      <th key={col} className="border p-1">{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {resultData.table.map((row, idx) => (
                    <tr key={idx}>
                      {Object.values(row).map((val, i) => (
                        <td key={i} className="border p-1">{val}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          
          {resultData?.summary && (
            <div className="mt-4">
              <h3 className="font-bold text-sm mb-2">Summary</h3>
              <table className="w-full text-xs border">
                <tbody>
                  {Object.entries(resultData.summary).map(([key, val], idx) => {
                    if (typeof val === "object" && val !== null) {
                      return (
                        <tr key={idx}>
                          <td className="border p-1 font-semibold">{key}</td>
                          <td className="border p-1">
                            <table className="text-xs w-full">
                              <tbody>
                                {Object.entries(val).map(([subKey, subVal], i) => (
                                  <tr key={i}>
                                    <td className="border px-1">{subKey}</td>
                                    <td className="border px-1">{subVal}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </td>
                        </tr>
                      );
                    } else {
                      return (
                        <tr key={idx}>
                          <td className="border p-1 font-semibold">{key}</td>
                          <td className="border p-1">{val}</td>
                        </tr>
                      );
                    }
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
