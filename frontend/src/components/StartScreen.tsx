"use client";

import React from "react";
import { Product } from "@/types";
import { Banknote, TrendingUp, LifeBuoy, AlertCircle, ArrowRight } from "lucide-react";

interface StartScreenProps {
  products: Product[];
  onSelectJourney: (journeyId: string) => void;
  isLoading: boolean;
}

const JOURNEY_ICONS: Record<string, React.ReactNode> = {
  personal_loan: <Banknote className="w-5 h-5 text-[#002E6E]" />,
  sip: <TrendingUp className="w-5 h-5 text-[#00BAF2]" />,
  payment_help: <LifeBuoy className="w-5 h-5 text-[#0F9D58]" />,
  loan_rejection: <AlertCircle className="w-5 h-5 text-amber-600" />,
};

export const StartScreen: React.FC<StartScreenProps> = ({
  products,
  onSelectJourney,
  isLoading,
}) => {
  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      {/* Header section */}
      <div className="mb-8 text-center max-w-2xl mx-auto">
        <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-[#E1E8F0]/50 text-xs font-semibold text-[#002E6E] mb-3">
          <span>Multilingual Lending & Wealth Assistant</span>
        </div>
        <h2 className="text-2xl font-bold text-[#1B2A41] tracking-tight">
          Select a Financial Journey
        </h2>
        <p className="text-sm text-[#6B7C93] mt-2">
          Experience voice-guided fintech journeys powered by deterministic Python rules.
          All offers and numbers are synthetic and labelled Sample.
        </p>
      </div>

      {/* 4 Journey Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {products.map((product) => {
          const icon = JOURNEY_ICONS[product.journey_id] || (
            <Banknote className="w-5 h-5 text-[#002E6E]" />
          );

          return (
            <div
              key={product.journey_id}
              className="bg-white rounded-lg border border-[#E1E8F0] p-6 flex flex-col justify-between hover:border-[#00BAF2] transition-colors"
            >
              <div>
                <div className="flex items-start justify-between mb-4">
                  <div className="w-10 h-10 rounded-lg bg-[#F5F7FA] border border-[#E1E8F0] flex items-center justify-center">
                    {icon}
                  </div>
                  <span className="text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-amber-50 border border-amber-200 text-amber-800">
                    {product.sample_label}
                  </span>
                </div>

                <h3 className="text-base font-semibold text-[#1B2A41] mb-1">
                  {product.title}
                </h3>
                <p className="text-xs text-[#6B7C93] mb-4 leading-relaxed">
                  {product.description}
                </p>

                {/* Required Fields Pill List */}
                <div className="mb-5">
                  <span className="text-[11px] font-semibold text-[#1B2A41] uppercase tracking-wider block mb-2">
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
              </div>

              {/* Action Button */}
              <div>
                <button
                  onClick={() => onSelectJourney(product.journey_id)}
                  disabled={isLoading}
                  className="w-full h-10 px-4 rounded-lg bg-[#002E6E] hover:bg-[#002456] text-white text-xs font-semibold flex items-center justify-center space-x-2 transition-colors disabled:opacity-50"
                >
                  <span>Start Journey</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Disclosures Footer */}
      <div className="mt-12 text-center border-t border-[#E1E8F0] pt-6">
        <p className="text-xs text-[#6B7C93]">
          Notice: BhashaFinance AI calculations are deterministic and non-binding. Every sample offer requires explicit customer consent before submission.
        </p>
      </div>
    </div>
  );
};
