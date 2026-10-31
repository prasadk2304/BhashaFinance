"use client";

import React, { useState } from "react";
import {
  AlertCircle,
  Sliders,
  CheckCircle2,
  Calendar,
  FileCheck,
  TrendingDown,
  ShieldAlert,
  ArrowRight,
  Info,
} from "lucide-react";

interface RejectionExplainerViewProps {
  currentFoir?: number;
  monthlyIncome?: number;
  existingEmis?: number;
  rejectionReasonCode?: string;
}

export const RejectionExplainerView: React.FC<RejectionExplainerViewProps> = ({
  currentFoir = 62.0,
  monthlyIncome = 50000,
  existingEmis = 20000,
  rejectionReasonCode = "HIGH_FOIR",
}) => {
  // Two what-if sliders (amount and tenure)
  const [whatIfAmount, setWhatIfAmount] = useState<number>(100000);
  const [whatIfTenure, setWhatIfTenure] = useState<number>(36);

  // Re-apply checklist
  const [checklist, setChecklist] = useState([
    { id: "cool", title: "Observe 90-Day Cooling-Off Period", done: true, desc: "Avoid multiple hard credit inquiries." },
    { id: "util", title: "Reduce Credit Card Utilization < 30%", done: false, desc: "Brings score up by 15-25 points." },
    { id: "timely", title: "Pay Next 3 EMI Cycles on Time", done: false, desc: "Restores clean bureau reporting history." },
    { id: "coapp", title: "Add Earning Family Co-Applicant", done: false, desc: "Increases household income & lowers debt ratio." },
  ]);

  // Deterministic What-If recalculation
  const benchmarkRate = 12.5;
  const r = benchmarkRate / (12 * 100);
  const comp = Math.pow(1 + r, whatIfTenure);
  const whatIfEmi = Math.round((whatIfAmount * r * comp) / (comp - 1));
  const newTotalDebt = existingEmis + whatIfEmi;
  const newFoirPct = monthlyIncome > 0 ? (newTotalDebt / monthlyIncome) * 100 : 0;
  const isWhatIfEligible = newFoirPct <= 50.0;

  const coolingDate = new Date();
  coolingDate.setDate(coolingDate.getDate() + 90);
  const formattedCoolingDate = coolingDate.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  const toggleItem = (id: string) => {
    setChecklist((prev) =>
      prev.map((item) => (item.id === id ? { ...item, done: !item.done } : item))
    );
  };

  return (
    <div className="space-y-6">
      {/* 1. Reason Card with Numbers vs Sample Thresholds */}
      <div className="bg-white rounded-lg border border-[#E1E8F0] p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-[#E1E8F0] pb-3">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-red-600" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-[#1B2A41]">
              Decline Analysis: {rejectionReasonCode}
            </h3>
          </div>
          <span className="text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-red-50 border border-red-200 text-red-700">
            Declined
          </span>
        </div>

        {/* Numbers vs Benchmark Threshold Comparison */}
        <div className="space-y-3">
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-[#6B7C93]">Borrower Debt-to-Income (FOIR):</span>
              <span className="font-bold tabular-nums font-mono text-red-600">
                {currentFoir}% (Exceeds Limit)
              </span>
            </div>
            <div className="w-full h-2.5 bg-[#E1E8F0] rounded-full overflow-hidden relative">
              <div
                className="h-full bg-red-500 rounded-full"
                style={{ width: `${Math.min(100, currentFoir)}%` }}
              />
            </div>
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-[#6B7C93]">Lending Partner Safety Ceiling:</span>
              <span className="font-bold tabular-nums font-mono text-[#002E6E]">
                50.0% Max Threshold
              </span>
            </div>
            <div className="w-full h-2.5 bg-[#E1E8F0] rounded-full overflow-hidden">
              <div className="h-full bg-[#002E6E] rounded-full" style={{ width: "50%" }} />
            </div>
          </div>

          <div className="p-3 bg-red-50/60 rounded-lg border border-red-200 text-xs text-red-800 space-y-1">
            <span className="font-bold block">Excess Debt Variance: +{(currentFoir - 50.0).toFixed(1)}%</span>
            <p className="text-[11px] text-red-700 leading-relaxed">
              Your ongoing monthly loan obligations (₹ {existingEmis.toLocaleString("en-IN")}) combined with the requested loan EMI breach standard lender risk guidelines.
            </p>
          </div>
        </div>
      </div>

      {/* 2. Two What-If Controls (Amount & Tenure) with Live Recalculation */}
      <div className="bg-white rounded-lg border border-[#E1E8F0] p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-[#E1E8F0] pb-3">
          <div className="flex items-center space-x-2">
            <Sliders className="w-4 h-4 text-[#002E6E]" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-[#1B2A41]">
              What-If Approval Simulation
            </h3>
          </div>
          <span className="text-[10px] text-[#6B7C93]">Test alternate parameters</span>
        </div>

        {/* Control 1: Loan Amount */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs">
            <span className="text-[#6B7C93]">1. What-If Loan Amount:</span>
            <span className="font-bold tabular-nums font-mono text-[#002E6E]">
              ₹ {whatIfAmount.toLocaleString("en-IN")}
            </span>
          </div>
          <input
            type="range"
            min={25000}
            max={300000}
            step={5000}
            value={whatIfAmount}
            onChange={(e) => setWhatIfAmount(Number(e.target.value))}
            className="w-full h-1.5 bg-[#E1E8F0] rounded-lg appearance-none cursor-pointer accent-[#002E6E]"
          />
          <div className="flex justify-between text-[10px] text-[#6B7C93] font-mono">
            <span>₹ 25k</span>
            <span>₹ 1.5 Lakh</span>
            <span>₹ 3 Lakh</span>
          </div>
        </div>

        {/* Control 2: Tenure */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs">
            <span className="text-[#6B7C93]">2. What-If Repayment Tenure:</span>
            <span className="font-bold tabular-nums font-mono text-[#002E6E]">
              {whatIfTenure} Months
            </span>
          </div>
          <input
            type="range"
            min={12}
            max={48}
            step={6}
            value={whatIfTenure}
            onChange={(e) => setWhatIfTenure(Number(e.target.value))}
            className="w-full h-1.5 bg-[#E1E8F0] rounded-lg appearance-none cursor-pointer accent-[#002E6E]"
          />
          <div className="flex justify-between text-[10px] text-[#6B7C93] font-mono">
            <span>12M</span>
            <span>24M</span>
            <span>36M</span>
            <span>48M</span>
          </div>
        </div>

        {/* What-If Live Recalculation Results */}
        <div className="p-3.5 bg-[#F5F7FA] rounded-lg border border-[#E1E8F0] space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-[#6B7C93]">Simulated EMI:</span>
            <span className="font-bold font-mono text-[#002E6E]">
              ₹ {whatIfEmi.toLocaleString("en-IN")} / mo
            </span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-[#6B7C93]">Simulated New FOIR:</span>
            <span className="font-bold font-mono text-[#1B2A41]">
              {newFoirPct.toFixed(1)}% of income
            </span>
          </div>

          <div
            className={`pt-2 border-t border-[#E1E8F0] flex items-center space-x-2 text-xs font-semibold ${
              isWhatIfEligible ? "text-green-700" : "text-amber-700"
            }`}
          >
            {isWhatIfEligible ? (
              <>
                <CheckCircle2 className="w-4 h-4 text-green-700" />
                <span>Simulated parameters bring FOIR below 50% limit!</span>
              </>
            ) : (
              <>
                <TrendingDown className="w-4 h-4 text-amber-700" />
                <span>Still exceeds 50% threshold. Try longer tenure or lower loan amount.</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* 3. Re-Apply Readiness Checklist */}
      <div className="bg-white rounded-lg border border-[#E1E8F0] p-5 space-y-3">
        <div className="flex items-center justify-between border-b border-[#E1E8F0] pb-2.5">
          <div className="flex items-center space-x-2">
            <FileCheck className="w-4 h-4 text-[#002E6E]" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-[#1B2A41]">
              Recovery Roadmap (90-Day Tracker)
            </h3>
          </div>
          <span className="text-[11px] font-mono text-[#002E6E]">
            Eligible: {formattedCoolingDate}
          </span>
        </div>

        <div className="space-y-2">
          {checklist.map((item) => (
            <div
              key={item.id}
              onClick={() => toggleItem(item.id)}
              className="p-3 rounded-lg border border-[#E1E8F0] hover:bg-[#F5F7FA] cursor-pointer text-xs flex items-start space-x-3 transition-colors"
            >
              <div
                className={`w-4 h-4 rounded flex items-center justify-center border mt-0.5 ${
                  item.done
                    ? "bg-[#002E6E] border-[#002E6E] text-white"
                    : "border-[#E1E8F0] bg-white"
                }`}
              >
                {item.done && <CheckCircle2 className="w-3 h-3" />}
              </div>
              <div>
                <span className={`block font-semibold ${item.done ? "text-[#1B2A41]" : "text-[#6B7C93]"}`}>
                  {item.title}
                </span>
                <span className="text-[11px] text-[#6B7C93]">{item.desc}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 4. Strict Regulatory Disclaimer: NEVER PROMISE APPROVAL */}
      <div className="bg-gray-100 border border-[#E1E8F0] rounded-lg p-4 space-y-1.5">
        <div className="flex items-center space-x-2 text-[#1B2A41] font-semibold text-xs">
          <ShieldAlert className="w-4 h-4 text-amber-600 flex-shrink-0" />
          <span>Statutory Underwriting Disclosure</span>
        </div>
        <p className="text-[11px] text-[#6B7C93] leading-relaxed">
          <strong>Important:</strong> Re-application and simulated what-if adjustments do not guarantee loan approval. Final sanction is subject to independent credit bureau verification, updated bank statement scrutiny, and partner lending institution underwriting policy at the time of formal application.
        </p>
      </div>
    </div>
  );
};

