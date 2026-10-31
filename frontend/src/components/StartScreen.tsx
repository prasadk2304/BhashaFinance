"use client";

import React from "react";
import { Product } from "@/types";
import { Banknote, TrendingUp, LifeBuoy, AlertCircle, ArrowRight, Play } from "lucide-react";
import { DEMO_SCENARIOS } from "@/lib/demoScenarios";

interface StartScreenProps {
  products: Product[];
  onSelectJourney: (journeyId: string) => void;
  onLoadScenario: (journeyId: string) => void;
  isLoading: boolean;
}

const JOURNEY_ICONS: Record<string, React.ReactNode> = {
  personal_loan: <Banknote className="w-5 h-5 text-[#002E6E]" />,
  sip: <TrendingUp className="w-5 h-5 text-[#002E6E]" />,
  payment_help: <LifeBuoy className="w-5 h-5 text-[#002E6E]" />,
  loan_rejection: <AlertCircle className="w-5 h-5 text-[#002E6E]" />,
};

export const StartScreen: React.FC<StartScreenProps> = ({
  products,
  onSelectJourney,
  onLoadScenario,
  isLoading,
}) => {
  return (
    <div className="max-w-5xl w-full mx-auto px-4 sm:px-6 py-8 sm:py-12">
      {/* Header section */}
      <div className="mb-8 text-center max-w-2xl mx-auto">
        <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded bg-[#E1E8F0]/60 text-xs font-semibold text-[#002E6E] mb-3">
          <span>Multilingual Lending & Wealth Assistant</span>
        </div>
        <h2 className="text-xl sm:text-2xl font-bold text-[#1B2A41] tracking-tight">
          Select a Financial Journey
        </h2>
        <p className="text-sm text-[#475569] mt-2 leading-relaxed">
          Voice-guided fintech journeys powered by deterministic Python rules.
          Every offer is synthetic and labelled Sample with mandatory explicit consent.
        </p>
      </div>

      {/* 4 Journey Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
        {products.map((product) => {
          const icon = JOURNEY_ICONS[product.journey_id] || (
            <Banknote className="w-5 h-5 text-[#002E6E]" />
          );
          const scenario = DEMO_SCENARIOS[product.journey_id];

          return (
            <div
              key={product.journey_id}
              className="bg-white rounded-lg border border-[#E1E8F0] p-6 flex flex-col justify-between hover:border-[#002E6E] transition-colors"
            >
              <div>
                <div className="flex items-start justify-between mb-3">
                  <div className="w-9 h-9 rounded bg-[#F5F7FA] border border-[#E1E8F0] flex items-center justify-center">
                    {icon}
                  </div>
                  <span className="text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-amber-50 border border-amber-300 text-amber-900">
                    {product.sample_label}
                  </span>
                </div>

                <h3 className="text-base font-bold text-[#1B2A41] mb-1">
                  {product.title}
                </h3>
                <p className="text-xs text-[#475569] mb-4 leading-relaxed">
                  {product.description}
                </p>

                {/* Required Fields Pill List */}
                <div className="mb-4">
                  <span className="text-[11px] font-semibold text-[#1B2A41] uppercase tracking-wider block mb-1.5">
                    Required Inputs:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {product.required_fields.map((f) => (
                      <span
                        key={f}
                        className="text-[11px] font-medium bg-[#F5F7FA] text-[#1B2A41] px-2 py-0.5 rounded border border-[#E1E8F0]"
                      >
                        {f.replace(/_/g, " ")}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Seeded Scenario Preview */}
                {scenario && (
                  <div className="mb-5 p-2.5 rounded bg-[#F5F7FA] border border-[#E1E8F0] text-xs">
                    <span className="text-[10px] uppercase font-bold text-[#002E6E] block mb-0.5">
                      Seeded Scenario:
                    </span>
                    <span className="font-semibold text-[#1B2A41] block">
                      {scenario.title}
                    </span>
                    <span className="text-[11px] text-[#475569] block">
                      {scenario.subtitle}
                    </span>
                  </div>
                )}
              </div>

              {/* Action Buttons: Start Fresh OR Load Seeded Scenario */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-[#E1E8F0]">
                <button
                  type="button"
                  onClick={() => onSelectJourney(product.journey_id)}
                  disabled={isLoading}
                  className="h-10 px-3 rounded bg-[#002E6E] hover:bg-[#002456] text-white text-xs font-semibold flex items-center justify-center space-x-1.5 transition-colors disabled:opacity-50"
                >
                  <span>Start Fresh</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>

                {scenario && (
                  <button
                    type="button"
                    onClick={() => onLoadScenario(product.journey_id)}
                    disabled={isLoading}
                    className="h-10 px-3 rounded border border-[#002E6E] bg-white hover:bg-blue-50 text-[#002E6E] text-xs font-semibold flex items-center justify-center space-x-1.5 transition-colors disabled:opacity-50"
                  >
                    <Play className="w-3 h-3 fill-[#002E6E]" />
                    <span>Seeded Demo</span>
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Disclosures Footer */}
      <div className="mt-8 text-center border-t border-[#E1E8F0] pt-6">
        <p className="text-xs text-[#475569]">
          Notice: BhashaFinance AI calculations are deterministic and non-binding. Every sample offer requires explicit customer consent before submission.
        </p>
      </div>
    </div>
  );
};
