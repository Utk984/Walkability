import React, { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import axios from "axios";

export default function AutocompleteInput({
  value,
  onChange,
  placeholder,
  className = "",
}) {
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0, width: 0 });
  const debounceTimeout = useRef(null);
  const inputRef = useRef(null);
  const suggestionsRef = useRef(null);

  // Update dropdown position
  const updateDropdownPosition = () => {
    if (inputRef.current) {
      const rect = inputRef.current.getBoundingClientRect();
      setDropdownPosition({
        top: rect.bottom + window.scrollY,
        left: rect.left + window.scrollX,
        width: rect.width
      });
    }
  };

  // Debounced search function
  const searchPOIs = async (query) => {
    if (!query.trim() || query.length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    setIsLoading(true);
    try {
      const response = await axios.post("http://localhost:8000/search/pois", {
        query: query,
        limit: 8
      });
      setSuggestions(response.data.results);
      setShowSuggestions(true);
      updateDropdownPosition();
    } catch (error) {
      console.error("Error searching POIs:", error);
      setSuggestions([]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle input change with debouncing
  const handleInputChange = (e) => {
    const newValue = e.target.value;
    onChange(newValue);

    // Clear existing timeout
    if (debounceTimeout.current) {
      clearTimeout(debounceTimeout.current);
    }

    // Set new timeout for search
    debounceTimeout.current = setTimeout(() => {
      searchPOIs(newValue);
    }, 300);
  };

  // Handle suggestion selection
  const handleSuggestionClick = (suggestion) => {
    onChange(suggestion.name);
    setShowSuggestions(false);
    setSuggestions([]);
  };

  // Handle click outside to close suggestions
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        inputRef.current &&
        !inputRef.current.contains(event.target) &&
        suggestionsRef.current &&
        !suggestionsRef.current.contains(event.target)
      ) {
        setShowSuggestions(false);
      }
    };

    const handleScroll = () => {
      if (showSuggestions) {
        updateDropdownPosition();
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    window.addEventListener("scroll", handleScroll);
    window.addEventListener("resize", handleScroll);
    
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      window.removeEventListener("scroll", handleScroll);
      window.removeEventListener("resize", handleScroll);
      if (debounceTimeout.current) {
        clearTimeout(debounceTimeout.current);
      }
    };
  }, [showSuggestions]);

  // Dropdown component to be rendered in portal
  const dropdown = showSuggestions && suggestions.length > 0 && (
    <div
      ref={suggestionsRef}
      className="fixed bg-white border border-gray-300 rounded-b shadow-lg max-h-64 overflow-y-auto z-[9999]"
      style={{
        top: `${dropdownPosition.top}px`,
        left: `${dropdownPosition.left}px`,
        width: `${dropdownPosition.width}px`
      }}
    >
      {suggestions.map((suggestion, index) => (
        <div
          key={index}
          className="p-3 hover:bg-gray-100 cursor-pointer border-b border-gray-100 last:border-b-0"
          onClick={() => handleSuggestionClick(suggestion)}
        >
          <div className="font-medium text-sm">{suggestion.name}</div>
          <div className="text-xs text-gray-500 mt-1">
            {suggestion.primary_type}
            {suggestion.secondary_type && ` • ${suggestion.secondary_type}`}
            {suggestion.sector_name && ` • Sector ${suggestion.sector_name}`}
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <div className="relative">
      <input
        ref={inputRef}
        type="text"
        className={`${className} ${isLoading ? 'bg-gray-50' : ''}`}
        placeholder={placeholder}
        value={value}
        onChange={handleInputChange}
        onFocus={() => {
          if (suggestions.length > 0) {
            setShowSuggestions(true);
            updateDropdownPosition();
          }
        }}
      />
      
      {isLoading && (
        <div className="absolute right-2 top-2">
          <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      )}

      {createPortal(dropdown, document.body)}
    </div>
  );
} 