// File: src/App.jsx
import React, { useState, useEffect } from "react";
import Sidebar from "./components/LeftSidebar";
import RightSidebar from "./components/RightSidebar";
import ChatBox from "./components/ChatBox";
import Directions from "./components/Directions";
import axios from "axios";

export default function App() {
  const [mapHtml, setMapHtml] = useState("");
  const [resultData, setResultData] = useState(null);

  const [userQuery, setUserQuery] = useState("");
  const [execute, setExecute] = useState(false);
  const [showLeft, setShowLeft] = useState(true);
  const [showRight, setShowRight] = useState(true);

  const leftWidth  = showLeft  ? 350 : 78;
  const rightWidth = showRight ? 350 : 78;

  // Load initial choropleth map
  useEffect(() => {
    axios.get("http://localhost:8000/map/choropleth").then((res) => {
      setMapHtml(res.data);
    });
  }, []);

  // Update map when resultData changes
  useEffect(() => {
    if (resultData?.map) {
      setMapHtml(resultData.map);
    }
  }, [resultData]);

  // Handle chat queries
  useEffect(() => {
    if (execute && userQuery) {
      axios
        .post("http://localhost:8000/query", { query: userQuery })
        .then((res) => {
          setResultData(res.data);
        });
    }
  }, [execute, userQuery]);

  const toggleSidebar = () => {
    setShowLeft(!showLeft);
  };

  return (
    <div className="w-screen h-screen relative overflow-hidden">
      <Sidebar
        visible={showLeft}
        toggle={toggleSidebar}
        setUserQuery={setUserQuery}
        setExecute={setExecute}
        resultData={resultData}
        setResultData={setResultData}
      />
      <RightSidebar 
        visible={showRight} 
        toggle={() => setShowRight(!showRight)} 
        setResultData={setResultData} 
      />

      {/* Walk Paths Component at the top */}
      <Directions
        leftOffset={leftWidth}
        rightOffset={rightWidth}
        setMapHtml={setMapHtml}
        setResultData={setResultData}
      />

      {/* Chatbox at bottom center */}
      <ChatBox
        leftOffset={leftWidth}
        rightOffset={rightWidth}
        setMapHtml={setMapHtml}
        setResultData={setResultData}
      />

      <div className="absolute top-0 left-0 w-full h-full z-10">
        <div
          dangerouslySetInnerHTML={{ __html: mapHtml }}
          className="w-full h-full"
        />
      </div>
    </div>
  );
}
