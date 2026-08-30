"use client";

import React from "react";

interface TabSelectProps<T extends string> {
  options: readonly T[] | T[];
  value: T;
  onChange: (val: T) => void;
  className?: string;
}

export function TabSelect<T extends string>({
  options,
  value,
  onChange,
  className = "",
}: TabSelectProps<T>) {
  return (
    <div className={`tab-container ${className}`}>
      {options.map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => onChange(option)}
          className={`tab-button ${
            value === option ? "tab-button-active" : ""
          }`}
        >
          {option}
        </button>
      ))}
    </div>
  );
}
