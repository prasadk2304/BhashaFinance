"use client";

import React from "react";
import { Globe, User, ShieldCheck, RefreshCw } from "lucide-react";

interface TopBarProps {
  selectedLanguage: string;
  onLanguageChange: (lang: string) => void;
  customerId: string;
  onReset: () => void;
  onViewTransactions?: () => void;
}

export const LANGUAGES = [
  { code: "en-IN", label: "English" },
  { code: "hi-IN", label: "हिन्दी (Hindi)" },
  { code: "hinglish", label: "Hinglish" },
  { code: "kn-IN", label: "ಕನ್ನಡ (Kannada)" },
  { code: "ta-IN", label: "தமிழ் (Tamil)" },
];

export const TopBar: React.FC<TopBarProps> = ({
  selectedLanguage,
  onLanguageChange,
  customerId,
  onReset,
  onViewTransactions,
}) => {
  return (
    <header className="bg-white border-b border-[#E1E8F0] px-6 py-3 flex items-center justify-between sticky top-0 z-20">
      {/* Brand & Product Name */}
      <div className="flex items-center space-x-3">
        <div className="w-8 h-8 rounded-lg bg-[#002E6E] flex items-center justify-center text-white font-bold text-sm">
          BF
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-base font-semibold text-[#1B2A41] tracking-tight">
              BhashaFinance AI
            </h1>
            <span className="text-[11px] font-medium uppercase tracking-wider px-2 py-0.5 rounded bg-[#F5F7FA] border border-[#E1E8F0] text-[#002E6E]">
              Paytm Lending
            </span>
            <span className="text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-amber-50 border border-amber-200 text-amber-800">
              Sample
            </span>
          </div>
          <p className="text-xs text-[#6B7C93]">
            Voice-First Multilingual Journey Assistant
          </p>
        </div>
      </div>

      {/* Language Selector & Customer Profile */}
      <div className="flex items-center space-x-3">
        {/* Language selector */}
        <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-[#E1E8F0] bg-white text-xs text-[#1B2A41]">
          <Globe className="w-3.5 h-3.5 text-[#002E6E]" />
          <select
            value={selectedLanguage}
            onChange={(e) => onLanguageChange(e.target.value)}
            className="bg-transparent text-xs font-medium text-[#1B2A41] focus:outline-none cursor-pointer"
          >
            {LANGUAGES.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.label}
              </option>
            ))}
          </select>
        </div>

        {/* Customer Badge */}
        {onViewTransactions && (
          <button
            onClick={onViewTransactions}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-[#E1E8F0] bg-white hover:bg-[#F5F7FA] text-xs font-medium text-[#1B2A41] transition-colors"
          >
            <User className="w-3.5 h-3.5 text-[#00BAF2]" />
            <span className="tabular-nums">{customerId}</span>
          </button>
        )}

        {/* Reset / New Journey */}
        <button
          onClick={onReset}
          className="flex items-center space-x-1 px-3 py-1.5 rounded-lg border border-[#E1E8F0] text-xs font-medium text-[#6B7C93] hover:text-[#1B2A41] hover:bg-[#F5F7FA] transition-colors"
          title="Start New Journey"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>New</span>
        </button>
      </div>
    </header>
  );
};

