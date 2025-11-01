import React, { useState } from "react";
import axios from "axios";
import AutocompleteInput from "./AutocompleteInput";

export default function Directions({
  leftOffset = 0,
  rightOffset = 0,
  setMapHtml,
  setResultData,
}) {
  const [visible, setVisible] = useState(false);
  const [destA, setDestA] = useState("");
  const [destB, setDestB] = useState("");

  const handleGetWalkPaths = async () => {
    if (!destA.trim() || !destB.trim()) {
      alert("Please enter both destinations");
      return;
    }

    try {
      const response = await axios.post("http://localhost:8000/walk-paths", {
        destination_a: destA,
        destination_b: destB
      });
      
      if (response.data.map) {
        setMapHtml(response.data.map);
      }
      setResultData(response.data);
    } catch (error) {
      console.error("Error getting walk paths:", error);
      setResultData({
        type: "error",
        description: "An error occurred while getting walk paths."
      });
    }
  };

  return (
    <div
      style={{
        top: "1rem",                 // float 1rem from the top
        left: `${leftOffset}px`,     // gap for left sidebar
        right: `${rightOffset}px`,   // gap for right sidebar
      }}
      className={`absolute z-50 bg-white shadow-lg rounded-b-lg transition-all duration-300
        ${visible ? "max-h-48 overflow-auto" : "h-8 overflow-visible"}`}
    >
      {/* header bar */}
      <div className="flex items-center justify-end bg-gray-200 border-b p-2">
        {visible && <span className="font-bold mr-auto">Directions</span>}
        <button
          onClick={() => setVisible((v) => !v)}
          className="text-xs px-2 py-1 bg-blue-600 text-white rounded"
        >
          {visible ? "▲" : "▼"}
        </button>
      </div>

      {/* body */}
      {visible && (
        <div className="p-4">
          <div className="flex gap-4 mb-4">
            <div className="flex-1">
              <label className="block mb-1 text-sm font-medium">Destination A</label>
              <AutocompleteInput
                value={destA}
                onChange={setDestA}
                placeholder="Enter starting destination..."
                className="w-full p-2 border rounded"
              />
            </div>
            
            <div className="flex-1">
              <label className="block mb-1 text-sm font-medium">Destination B</label>
              <AutocompleteInput
                value={destB}
                onChange={setDestB}
                placeholder="Enter ending destination..."
                className="w-full p-2 border rounded"
              />
            </div>
          </div>
          
          <button
            className="bg-blue-600 text-white px-6 py-2 rounded w-full hover:bg-blue-700 transition-colors"
            onClick={handleGetWalkPaths}
          >
            Get Walk Paths
          </button>
        </div>
      )}
    </div>
  );
} 