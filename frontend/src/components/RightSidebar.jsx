// File: src/components/RightSidebar.jsx
import React, { useState } from "react";
import axios from "axios";

export default function RightSidebar({ visible, toggle, setResultData }) {
  // Profile state
  const [userType, setUserType] = useState("Working Professional");
  const [gender, setGender] = useState("Male");
  const [age, setAge] = useState("18-27");
  const [userInfo, setUserInfo] = useState("");

  // Weights and results state
  const [weights, setWeights] = useState(null);
  const [dynamicScores, setDynamicScores] = useState(null);
  const [insights, setInsights] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // Age options
  const ageOptions = [
    "18-27", "28-37", "38-47", "48-57", "58-67", "68-77", "70+"
  ];

  const handleGenerate = async () => {
    if (isLoading) return;
    
    setIsLoading(true);
    try {
      // Step 1: Generate weights based on profile
      const weightsResponse = await axios.post("http://localhost:8000/profile/generate-weights", {
        user_type: userType,
        gender: gender,
        age: age,
        additional_info: userInfo
      });
      
      const generatedWeights = weightsResponse.data.weights;
      setWeights(generatedWeights);
      
      // Step 2: Calculate dynamic walk scores using these weights
      const scoresResponse = await axios.post("http://localhost:8000/profile/calculate-dynamic-scores", {
        category_weights: generatedWeights,
        include_insights: true
      });
      
      setDynamicScores(scoresResponse.data);
      setInsights(scoresResponse.data.insights);
      
      // Profile results will be displayed in the right sidebar only
      // Removed setResultData call to prevent left sidebar updates
      
    } catch (error) {
      console.error("Error generating profile analysis:", error);
      // Keep error display in left sidebar for debugging
      setResultData({
        type: "error",
        description: "Failed to generate profile analysis. Please try again."
      });
    } finally {
      setIsLoading(false);
    }
  };

  const generateProfileSummary = (data, profile) => {
    const topSector = data.summary.top_sector;
    const avgWalkability = data.summary.average_walkability;
    const insights = data.insights;
    
    let summary = `🚶‍♂️ Your Personalized Walkability Analysis\n\n`;
    summary += `👤 Profile: ${profile.user_type}, ${profile.gender}, ${profile.age}\n`;
    summary += `🏆 Best Match: ${topSector.name} (Score: ${topSector.score}/100)\n`;
    summary += `📊 City Average: ${avgWalkability}/100\n\n`;
    
    if (data.top_recommendations && data.top_recommendations.length > 0) {
      summary += `🎯 Top Recommendations for You:\n`;
      data.top_recommendations.slice(0, 3).forEach((rec, i) => {
        summary += `${i + 1}. ${rec.sector} (${rec.score}/100) - ${rec.reason}\n`;
      });
      summary += `\n`;
    }
    
    if (insights.summary) {
      summary += `💡 ${insights.summary}\n`;
    }
    
    return summary;
  };

  // Colors matching your Streamlit CSS
  const categoryColors = {
    "Essential Services": "#3366cc",
    "Food and Drinks": "#dc3545",
    "Shopping": "#9932cc",
    "Entertainment": "#fd7e14",
    "Tourism": "#28a745",
    "Sports": "#006400",
    "Public Transport": "#343a40"
  };

  return (
    <div
      className={`absolute top-0 right-0 h-full bg-white shadow-xl z-50 transition-all duration-300 ${
        visible ? "w-80" : "w-12"
      }`}
    >
      {/* Header with toggle */}
      <div className="flex items-center justify-between p-2 bg-gray-100 border-b">
        <span className="text-sm font-bold">{visible && "Your Profile"}</span>
        <button
          onClick={toggle}
          className="text-xs px-2 py-1 bg-blue-600 text-white rounded"
        >
          {visible ? "›" : "‹"}
        </button>
      </div>

      {/* Body */}
      {visible && (
        <div className="p-4 overflow-y-auto space-y-4 text-sm" style={{ height: 'calc(100vh - 48px)' }}>
          {/* User Type */}
          <div>
            <label className="block mb-1 font-medium">Who are you?</label>
            <select
              className="w-full p-2 border"
              value={userType}
              onChange={(e) => setUserType(e.target.value)}
              disabled={isLoading}
            >
              {[
                "Working Professional",
                "Student",
                "Tourist",
                "Senior Citizen",
                "Family with Kids"
              ].map((opt) => (
                <option key={opt}>{opt}</option>
              ))}
            </select>
          </div>

          {/* Gender */}
          <div>
            <label className="block mb-1 font-medium">Gender</label>
            <div className="space-x-2">
              {["Male", "Female", "Other"].map((g) => (
                <label key={g}>
                  <input
                    type="radio"
                    className="mr-1"
                    name="gender"
                    value={g}
                    checked={gender === g}
                    onChange={() => setGender(g)}
                    disabled={isLoading}
                  />
                  {g}
                </label>
              ))}
            </div>
          </div>

          {/* Age */}
          <div>
            <label className="block mb-1 font-medium">Age Group</label>
            <select
              className="w-full p-2 border"
              value={age}
              onChange={(e) => setAge(e.target.value)}
              disabled={isLoading}
            >
              {ageOptions.map((opt) => (
                <option key={opt}>{opt}</option>
              ))}
            </select>
          </div>

          {/* Additional Info */}
          <div>
            <label className="block mb-1 font-medium">Additional Details</label>
            <textarea
              rows={3}
              className="w-full p-2 border"
              placeholder="Food preferences, interests, mobility needs..."
              value={userInfo}
              onChange={(e) => setUserInfo(e.target.value)}
              disabled={isLoading}
            />
          </div>

          {/* Generate Button */}
          <button
            className={`w-full py-2 rounded font-medium transition-colors ${
              isLoading
                ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                : "bg-green-600 text-white hover:bg-green-700"
            }`}
            onClick={handleGenerate}
            disabled={isLoading}
          >
            {isLoading ? (
              <div className="flex items-center justify-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Analyzing Profile...
              </div>
            ) : (
              "Generate My Walkability Profile"
            )}
          </button>

          {/* Weights display */}
          {weights && (
            <div>
              <h3 className="font-bold mb-2">Category Weights</h3>
              <div className="space-y-2">
                {Object.entries(weights).map(([cat, w]) => {
                  const pct = Math.round(w * 100);
                  return (
                    <div key={cat}>
                      <div className="flex justify-between">
                        <span className="text-xs">{cat}</span>
                        <span className="text-xs">{pct}%</span>
                      </div>
                      <div className="h-2 rounded bg-gray-200">
                        <div
                          className="h-full rounded"
                          style={{
                            width: `${pct}%`,
                            backgroundColor: categoryColors[cat] || "#000"
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Comprehensive Walkability Results */}
          {dynamicScores && (
            <div>
              <h3 className="font-bold mb-2">Your Walkability Analysis</h3>
              <div className="space-y-2 text-xs">
                <div className="bg-blue-50 p-2 rounded">
                  <div className="font-medium">🏆 Best Match</div>
                  <div>{dynamicScores.summary.top_sector.name}</div>
                  <div>Score: {dynamicScores.summary.top_sector.score}/100</div>
                </div>
                
                <div className="bg-gray-50 p-2 rounded">
                  <div className="font-medium">📊 Analysis</div>
                  <div>City Average: {dynamicScores.summary.average_walkability}/100</div>
                  <div>Total Sectors: {dynamicScores.summary.total_sectors}</div>
                </div>
              </div>
            </div>
          )}

          {/* Top Recommendations */}
          {dynamicScores && dynamicScores.top_recommendations && (
            <div>
              <h3 className="font-bold mb-2">🎯 Top Recommendations</h3>
              <div className="space-y-1">
                {dynamicScores.top_recommendations.slice(0, 5).map((rec, i) => (
                  <div key={i} className="text-xs bg-green-50 p-2 rounded">
                    <div className="font-medium">#{i + 1} Sector {rec.sector}</div>
                    <div className="text-gray-600">{rec.reason}</div>
                    <div className="text-blue-600">Score: {rec.score}/100</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Additional Insights */}
          {insights && (
            <div>
              <h3 className="font-bold mb-2">💡 Additional Insights</h3>
              
              {/* Priority Matches */}
              {insights.priority_matches && insights.priority_matches.length > 0 && (
                <div className="mb-3">
                  <div className="font-medium text-xs mb-1">Priority Matches:</div>
                  {insights.priority_matches.slice(0, 3).map((match, i) => (
                    <div key={i} className="text-xs bg-yellow-50 p-2 rounded mb-1">
                      <div className="font-medium">Sector {match.name}</div>
                      <div className="text-gray-600">{match.matches.join(", ")}</div>
                      <div className="text-blue-600">Score: {match.score}/100</div>
                    </div>
                  ))}
                </div>
              )}
              
              {/* Environmental Highlights */}
              {insights.environmental_highlights && insights.environmental_highlights.length > 0 && (
                <div className="mb-3">
                  <div className="font-medium text-xs mb-1">🌳 Green Highlights:</div>
                  {insights.environmental_highlights.slice(0, 2).map((env, i) => (
                    <div key={i} className="text-xs bg-green-50 p-2 rounded mb-1">
                      <div className="font-medium">Sector {env.name}</div>
                      <div className="text-gray-600">{env.description}</div>
                      <div className="text-green-600">GVI: {env.gvi}%</div>
                    </div>
                  ))}
                </div>
              )}
              
              {/* Summary */}
              {insights.summary && (
                <div className="text-xs bg-blue-50 p-2 rounded">
                  <div className="font-medium mb-1">Summary:</div>
                  <div>{insights.summary}</div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
