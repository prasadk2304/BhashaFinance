"use client";

import React from "react";
import { Globe, User, RefreshCw, PlayCircle, Headphones } from "lucide-react";
import { DEMO_SCENARIOS } from "@/lib/demoScenarios";
import { getVerifiedLanguages } from "@/config/languages";

interface TopBarProps {
  selectedLanguage: string;
  onLanguageChange: (lang: string) => void;
  customerId: string;
  onReset: () => void;
  onLoadScenario: (scenarioId: string) => void;
  onViewTransactions?: () => void;
  onTalkToAgent?: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  selectedLanguage,
  onLanguageChange,
  customerId,
  onReset,
  onLoadScenario,
  onViewTransactions,
  onTalkToAgent,
}) => {
  // Strict guard: only verified languages from SUPPORTED_LANGUAGES config are shown
  const verifiedLanguages = getVerifiedLanguages();
  return (
    <header className="bg-white border-b border-[#E1E8F0] px-4 sm:px-6 py-3 flex items-center justify-between sticky top-0 z-20">
      {/* Brand & Product Identity */}
      <div className="flex items-center space-x-3">
        <div className="w-8 h-8 rounded bg-[#002E6E] flex items-center justify-center text-white font-bold text-xs tracking-wider">
          BF
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-sm sm:text-base font-bold text-[#1B2A41] tracking-tight">
              BhashaFinance AI
            </h1>
            <span className="hidden sm:inline-block text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-[#F5F7FA] border border-[#E1E8F0] text-[#002E6E]">
              Paytm Lending
            </span>
            <span className="text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-amber-50 border border-amber-300 text-amber-900">
              Sample
            </span>
          </div>
          <p className="text-xs text-[#475569] hidden sm:block">
            Voice-First Multilingual Journey Assistant
          </p>
        </div>
      </div>

      {/* Controls & Demo Actions */}
      <div className="flex items-center space-x-2 sm:space-x-3">
        {/* Seeded Demo Scenario Selector */}
        <div className="hidden md:flex items-center space-x-1.5 px-2.5 py-1.5 rounded border border-[#E1E8F0] bg-white text-xs text-[#1B2A41]">
          <PlayCircle className="w-3.5 h-3.5 text-[#002E6E]" />
          <select
            defaultValue=""
            onChange={(e) => {
              if (e.target.value) {
                onLoadScenario(e.target.value);
                e.target.value = "";
              }
            }}
            aria-label="Select Seeded Demo Scenario"
            className="bg-transparent text-xs font-semibold text-[#1B2A41] focus:outline-none cursor-pointer"
          >
            <option value="" disabled>
              Load Demo Scenario...
            </option>
            {Object.values(DEMO_SCENARIOS).map((sc) => (
              <option key={sc.id} value={sc.journey_id}>
                {sc.title}
              </option>
            ))}
          </select>
        </div>

        {/* Strict Guarded Language Selector (Shows ONLY languages in SUPPORTED_LANGUAGES) */}
        <div className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded border border-[#E1E8F0] bg-white text-xs text-[#1B2A41]">
          <Globe className="w-3.5 h-3.5 text-[#002E6E]" />
          <select
            value={selectedLanguage}
            onChange={(e) => onLanguageChange(e.target.value)}
            aria-label="Select Interface Language"
            className="bg-transparent text-xs font-semibold text-[#1B2A41] focus:outline-none cursor-pointer"
          >
            {verifiedLanguages.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.nativeLabel} ({lang.label})
              </option>
            ))}
          </select>
        </div>

        {/* Talk to an Agent Handoff Button */}
        {onTalkToAgent && (
          <button
            onClick={onTalkToAgent}
            aria-label="Transfer to human agent with zero repetition"
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-[#002E6E] text-white hover:bg-[#002252] text-xs font-semibold transition-colors shadow-sm"
            title="Connect with Priority Support Agent"
          >
            <Headphones className="w-3.5 h-3.5 text-[#00BAF2]" />
            <span className="hidden sm:inline">Talk to Agent</span>
          </button>
        )}

        {/* Customer Ledger Button */}
        {onViewTransactions && (
          <button
            onClick={onViewTransactions}
            aria-label={`View ledger for customer ${customerId}`}
            className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1.5 rounded border border-[#E1E8F0] bg-white hover:bg-[#F5F7FA] text-xs font-medium text-[#1B2A41] transition-colors"
          >
            <User className="w-3.5 h-3.5 text-[#002E6E]" />
            <span className="tabular-nums font-mono">{customerId}</span>
          </button>
        )}

        {/* Demo Reset Button */}
        <button
          onClick={onReset}
          aria-label="Reset current session to clean state"
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded border border-[#E1E8F0] bg-white text-xs font-semibold text-[#1B2A41] hover:bg-[#F5F7FA] active:bg-[#E1E8F0] transition-colors"
          title="Reset to New Clean Session"
        >
          <RefreshCw className="w-3.5 h-3.5 text-[#002E6E]" />
          <span>Demo Reset</span>
        </button>
      </div>
    </header>
  );
};
