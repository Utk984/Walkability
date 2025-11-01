// File: src/components/ChatBox.jsx
import React, { useState } from "react";
import axios from "axios";

export default function ChatBox({
  leftOffset = 0,
  rightOffset = 0,
  setMapHtml,
  setResultData,
}) {
  const [visible, setVisible] = useState(false);
  const [text, setText] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async () => {
    const q = text.trim();
    if (!q || isLoading) return;
    
    setIsLoading(true);
    try {
      const response = await axios.post("http://localhost:8000/chat", { text: q });
      setResultData(response.data);
      if (response.data.map) setMapHtml(response.data.map);
      setText(""); // clear on success
    } catch (err) {
      console.error("Chat API error:", err);
      setResultData({
        type: "error",
        description: "Failed to process your request. Please try again."
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div
      style={{
        bottom: "1rem",              // float 1rem above the very bottom
        left: `${leftOffset}px`,     // gap for left sidebar
        right: `${rightOffset}px`,   // gap for right sidebar
      }}
      className={`absolute z-50 bg-white shadow-lg rounded-t-lg transition-all duration-300
        ${visible ? "max-h-48 overflow-auto" : "h-8 overflow-visible"}`}
    >
      {/* header bar */}
      <div className="flex items-center justify-end bg-gray-200 border-b p-2">
        {visible && (
          <div className="flex items-center mr-auto">
            <span className="font-bold">Chat</span>
            {isLoading && (
              <div className="ml-2 flex items-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                <span className="ml-1 text-xs text-gray-600">Processing...</span>
              </div>
            )}
          </div>
        )}
        <button
          onClick={() => setVisible((v) => !v)}
          className="text-xs px-2 py-1 bg-blue-600 text-white rounded"
        >
          {visible ? "▼" : "▲"}
        </button>
      </div>

      {/* body */}
      {visible && (
        <div className="p-4 flex flex-col flex-1">
          <textarea
            className="flex-1 p-2 border mb-2 rounded resize-none"
            placeholder="Ask me something..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={isLoading}
          />
          <button
            onClick={handleSubmit}
            disabled={isLoading || !text.trim()}
            className={`py-2 rounded font-medium transition-colors ${
              isLoading || !text.trim()
                ? "bg-gray-300 text-gray-500 cursor-not-allowed" 
                : "bg-green-600 text-white hover:bg-green-700"
            }`}
          >
            {isLoading ? (
              <div className="flex items-center justify-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Processing...
              </div>
            ) : (
              "Submit"
            )}
          </button>
        </div>
      )}
    </div>
  );
}
