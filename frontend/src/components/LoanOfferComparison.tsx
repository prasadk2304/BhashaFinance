"use client";

import React, { useState } from "react";
import {
  Sliders,
  CheckCircle2,
  FileText,
  Info,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  Check,
  Percent,
  Calendar,
  Layers,
} from "lucide-react";

interface LoanOfferComparisonProps {
  initialAmount: number;
  initialTenure: number;
  monthlyIncome: number;
  existingEmis: number;
  annualRate: number;
  onConfirmApplication: (finalTerms: {
    amount: number;
    tenure: number;
    emi: number;
    totalRepayment: number;
    referenceId: string;
  }) => void;
  isConfirmed: boolean;
  confirmedReferenceId?: string;
}

export const LoanOfferComparison: React.FC<LoanOfferComparisonProps> = ({
  initialAmount,
  initialTenure,
  monthlyIncome,
  existingEmis,
  annualRate,
  onConfirmApplication,
  isConfirmed,
  confirmedReferenceId,
}) => {
  // Interactive sliders
  const [amount, setAmount] = useState<number>(initialAmount || 150000);
  const [tenure, setTenure] = useState<number>(initialTenure || 24);
  const [showAssumptions, setShowAssumptions] = useState<boolean>(false);
  const [consentChecked, setConsentChecked] = useState<boolean>(false);
  const [reviewMode, setReviewMode] = useState<boolean>(false);

  // Document checklist state
  const [docs, setDocs] = useState<{ id: string; name: string; checked: boolean }[]>([
    { id: "pan", name: "PAN Card (Identity Verification)", checked: true },
    { id: "aadhaar", name: "Aadhaar e-KYC (Instant Digilocker)", checked: true },
    { id: "bank_stmt", name: "3-Month Bank Statement (Net Banking fetch)", checked: true },
    { id: "salary_slip", name: "Latest Salary Slip (Optional / Prime tier)", checked: false },
  ]);

  // Deterministic EMI calculation
  const calculateEmiValue = (p: number, n: number, rAnnual: number) => {
    if (n <= 0 || p <= 0) return 0;
    const r = rAnnual / (12 * 100);
    const comp = Math.pow(1 + r, n);
    const emi = (p * r * comp) / (comp - 1);
    return Math.round(emi);
  };

  const currentEmi = calculateEmiValue(amount, tenure, annualRate);
  const totalRepayment = currentEmi * tenure;
  const totalInterest = totalRepayment - amount;
  const processingFee = Math.round(amount * 0.02);
  const gstOnFee = Math.round(processingFee * 0.18);
  const totalFee = processingFee + gstOnFee;

  // FOIR Calculation
  const totalMonthlyObligation = existingEmis + currentEmi;
  const foirPct = monthlyIncome > 0 ? (totalMonthlyObligation / monthlyIncome) * 100 : 0;
  const maxAllowableEmi = Math.max(0, monthlyIncome * 0.5 - existingEmis);
  const isFoirSafe = foirPct <= 50;

  // Alternative Comparison Offers
  const offers = [
    {
      id: "tenure_12",
      name: "12 Months Express",
      tenure: 12,
      rate: annualRate - 0.5,
      emi: calculateEmiValue(amount, 12, annualRate - 0.5),
      fee: Math.round(amount * 0.015),
      totalRepayment: calculateEmiValue(amount, 12, annualRate - 0.5) * 12,
      tag: "Lowest Interest",
    },
    {
      id: "current_plan",
      name: `Selected Plan (${tenure}M)`,
      tenure: tenure,
      rate: annualRate,
      emi: currentEmi,
      fee: totalFee,
      totalRepayment: totalRepayment,
      tag: "Best Balance",
      highlight: true,
    },
    {
      id: "tenure_36",
      name: "36 Months Flexible",
      tenure: 36,
      rate: annualRate + 0.5,
      emi: calculateEmiValue(amount, 36, annualRate + 0.5),
      fee: Math.round(amount * 0.02),
      totalRepayment: calculateEmiValue(amount, 36, annualRate + 0.5) * 36,
      tag: "Lowest EMI",
    },
  ];

  const handleToggleDoc = (id: string) => {
    setDocs((prev) =>
      prev.map((d) => (d.id === id ? { ...d, checked: !d.checked } : d))
    );
  };

  const handleMockSubmit = () => {
    if (!consentChecked) return;
    const refId = `SAMPLE-PAYTM-${Math.floor(100000 + Math.random() * 900000)}`;
    onConfirmApplication({
      amount,
      tenure,
      emi: currentEmi,
      totalRepayment,
      referenceId: refId,
    });
    setReviewMode(false);
  };

  return (
    <div className="space-y-6">
      {/* 1. Live Sliders & Recalculation */}
      <div className="bg-white rounded-lg border border-[#E1E8F0] p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-[#E1E8F0] pb-3">
          <div className="flex items-center space-x-2">
            <Sliders className="w-4 h-4 text-[#002E6E]" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-[#1B2A41]">
              Live Loan Customizer
            </h3>
          </div>
          <span className="text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-amber-50 border border-amber-200 text-amber-800">
            Sample
          </span>
        </div>

        {/* Amount Slider */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs">
            <span className="text-[#6B7C93]">Loan Amount</span>
            <span className="font-bold tabular-nums font-mono text-[#002E6E]">
              ₹ {amount.toLocaleString("en-IN")}
            </span>
          </div>
          <input
            type="range"
            min={25000}
            max={500000}
            step={5000}
            value={amount}
            onChange={(e) => setAmount(Number(e.target.value))}
            className="w-full h-1.5 bg-[#E1E8F0] rounded-lg appearance-none cursor-pointer accent-[#002E6E]"
          />
          <div className="flex justify-between text-[10px] text-[#6B7C93] font-mono">
            <span>₹ 25k</span>
            <span>₹ 2.5 Lakh</span>
            <span>₹ 5 Lakh</span>
          </div>
        </div>

        {/* Tenure Slider */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs">
            <span className="text-[#6B7C93]">Repayment Tenure</span>
            <span className="font-bold tabular-nums font-mono text-[#002E6E]">
              {tenure} Months ({Math.round((tenure / 12) * 10) / 10} Yrs)
            </span>
          </div>
          <input
            type="range"
            min={6}
            max={60}
            step={6}
            value={tenure}
            onChange={(e) => setTenure(Number(e.target.value))}
            className="w-full h-1.5 bg-[#E1E8F0] rounded-lg appearance-none cursor-pointer accent-[#002E6E]"
          />
          <div className="flex justify-between text-[10px] text-[#6B7C93] font-mono">
            <span>6M</span>
            <span>24M</span>
            <span>48M</span>
            <span>60M</span>
          </div>
        </div>

        {/* Live Metrics Summary Bar */}
        <div className="grid grid-cols-3 gap-3 pt-3 border-t border-[#E1E8F0] text-center">
          <div className="bg-[#F5F7FA] p-2.5 rounded-lg border border-[#E1E8F0]">
            <span className="text-[10px] text-[#6B7C93] block uppercase font-medium">Monthly EMI</span>
            <span className="text-sm font-bold text-[#002E6E] tabular-nums font-mono">
              ₹ {currentEmi.toLocaleString("en-IN")}
            </span>
          </div>
          <div className="bg-[#F5F7FA] p-2.5 rounded-lg border border-[#E1E8F0]">
            <span className="text-[10px] text-[#6B7C93] block uppercase font-medium">Total Interest</span>
            <span className="text-sm font-bold text-[#1B2A41] tabular-nums font-mono">
              ₹ {totalInterest.toLocaleString("en-IN")}
            </span>
          </div>
          <div className="bg-[#F5F7FA] p-2.5 rounded-lg border border-[#E1E8F0]">
            <span className="text-[10px] text-[#6B7C93] block uppercase font-medium">Total Repayment</span>
            <span className="text-sm font-bold text-[#1B2A41] tabular-nums font-mono">
              ₹ {totalRepayment.toLocaleString("en-IN")}
            </span>
          </div>
        </div>
      </div>

      {/* 2. FOIR Meter Component */}
      <div className="bg-white rounded-lg border border-[#E1E8F0] p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Percent className="w-4 h-4 text-[#002E6E]" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-[#1B2A41]">
              FOIR Risk Meter
            </h3>
          </div>
          <span
            className={`text-[11px] font-bold px-2 py-0.5 rounded border ${
              isFoirSafe
                ? "bg-green-50 border-green-200 text-green-700"
                : "bg-amber-50 border-amber-200 text-amber-700"
            }`}
          >
            {isFoirSafe ? "Safe Debt Ratio" : "FOIR Threshold Exceeded"}
          </span>
        </div>

        {/* Visual Progress Bar */}
        <div className="space-y-1">
          <div className="w-full h-3 bg-[#E1E8F0] rounded-full overflow-hidden relative">
            {/* 50% Threshold marker */}
            <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-black/40 z-10" />
            <div
              className={`h-full transition-all duration-300 ${
                isFoirSafe ? "bg-[#0F9D58]" : "bg-[#DB4437]"
              }`}
              style={{ width: `${Math.min(100, foirPct)}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-[#6B7C93] font-mono">
            <span>0%</span>
            <span className="font-semibold text-black">50% Benchmark Limit</span>
            <span>100%</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-[#E1E8F0]">
          <div>
            <span className="text-[11px] text-[#6B7C93] block">Calculated FOIR:</span>
            <span className="font-bold tabular-nums font-mono text-[#1B2A41]">
              {foirPct.toFixed(1)}% of income
            </span>
          </div>
          <div>
            <span className="text-[11px] text-[#6B7C93] block">Max Safe EMI:</span>
            <span className="font-bold tabular-nums font-mono text-[#002E6E]">
              ₹ {maxAllowableEmi.toLocaleString("en-IN")}
            </span>
          </div>
        </div>
      </div>

      {/* 3. Offer Comparison Table */}
      <div className="bg-white rounded-lg border border-[#E1E8F0] overflow-hidden">
        <div className="px-5 py-3 border-b border-[#E1E8F0] bg-[#F5F7FA] flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-[#002E6E]" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-[#1B2A41]">
              Sample Offer Comparison
            </h3>
          </div>
          <span className="text-[10px] text-[#6B7C93]">Non-binding illustration</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-[#F5F7FA] border-b border-[#E1E8F0] text-[11px] text-[#6B7C93] uppercase font-semibold">
                <th className="py-2.5 px-4">Plan Name</th>
                <th className="py-2.5 px-3">Tenure</th>
                <th className="py-2.5 px-3">Rate</th>
                <th className="py-2.5 px-3">Monthly EMI</th>
                <th className="py-2.5 px-3">Fee (2%+GST)</th>
                <th className="py-2.5 px-4">Total Repayment</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E1E8F0]">
              {offers.map((off) => (
                <tr
                  key={off.id}
                  className={`hover:bg-[#F5F7FA] transition-colors ${
                    off.highlight ? "bg-blue-50/50 font-medium" : ""
                  }`}
                >
                  <td className="py-3 px-4 flex items-center space-x-2">
                    <span className="text-[#1B2A41]">{off.name}</span>
                    <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-white border border-[#E1E8F0] text-[#002E6E]">
                      {off.tag}
                    </span>
                  </td>
                  <td className="py-3 px-3 tabular-nums font-mono">{off.tenure}M</td>
                  <td className="py-3 px-3 tabular-nums font-mono">{off.rate.toFixed(1)}%</td>
                  <td className="py-3 px-3 tabular-nums font-mono font-bold text-[#002E6E]">
                    ₹ {off.emi.toLocaleString("en-IN")}
                  </td>
                  <td className="py-3 px-3 tabular-nums font-mono">
                    ₹ {off.fee.toLocaleString("en-IN")}
                  </td>
                  <td className="py-3 px-4 tabular-nums font-mono font-semibold">
                    ₹ {off.totalRepayment.toLocaleString("en-IN")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 4. Assumptions Drawer / Accordion */}
      <div className="bg-white rounded-lg border border-[#E1E8F0] overflow-hidden">
        <button
          onClick={() => setShowAssumptions(!showAssumptions)}
          className="w-full px-5 py-3 flex items-center justify-between text-xs font-semibold text-[#1B2A41] bg-[#F5F7FA] hover:bg-[#E1E8F0]/40 transition-colors"
        >
          <div className="flex items-center space-x-2">
            <Info className="w-3.5 h-3.5 text-[#002E6E]" />
            <span>Deterministic Underwriting Assumptions</span>
          </div>
          {showAssumptions ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {showAssumptions && (
          <div className="p-4 space-y-2.5 text-xs text-[#6B7C93] border-t border-[#E1E8F0] bg-white">
            <div className="flex justify-between border-b border-[#E1E8F0] pb-1.5">
              <span>Benchmark Annual Interest Rate:</span>
              <span className="font-mono text-[#1B2A41]">{annualRate}% p.a. (Tiered risk-based)</span>
            </div>
            <div className="flex justify-between border-b border-[#E1E8F0] pb-1.5">
              <span>Standard Processing Fee:</span>
              <span className="font-mono text-[#1B2A41]">2.00% of loan amount + 18% GST</span>
            </div>
            <div className="flex justify-between border-b border-[#E1E8F0] pb-1.5">
              <span>Repayment Schedule:</span>
              <span className="font-mono text-[#1B2A41]">Equated Monthly Reducing Balance</span>
            </div>
            <div className="flex justify-between border-b border-[#E1E8F0] pb-1.5">
              <span>Maximum Allowable Debt Ceiling (FOIR):</span>
              <span className="font-mono text-[#1B2A41]">50.0% of verified monthly take-home</span>
            </div>
            <div className="flex justify-between">
              <span>Prepayment / Foreclosure Charges:</span>
              <span className="font-mono text-[#1B2A41]">0% after 6 successful EMI payments</span>
            </div>
          </div>
        )}
      </div>

      {/* 5. Document Checklist */}
      <div className="bg-white rounded-lg border border-[#E1E8F0] p-5 space-y-3">
        <div className="flex items-center space-x-2 border-b border-[#E1E8F0] pb-2.5">
          <FileText className="w-4 h-4 text-[#002E6E]" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-[#1B2A41]">
            Document Readiness Checklist
          </h3>
        </div>

        <div className="space-y-2">
          {docs.map((doc) => (
            <label
              key={doc.id}
              onClick={() => handleToggleDoc(doc.id)}
              className="flex items-center space-x-3 p-2.5 rounded-lg border border-[#E1E8F0] hover:bg-[#F5F7FA] cursor-pointer text-xs"
            >
              <div
                className={`w-4 h-4 rounded flex items-center justify-center border ${
                  doc.checked
                    ? "bg-[#002E6E] border-[#002E6E] text-white"
                    : "border-[#E1E8F0] bg-white"
                }`}
              >
                {doc.checked && <Check className="w-3 h-3" />}
              </div>
              <span className={doc.checked ? "text-[#1B2A41] font-medium" : "text-[#6B7C93]"}>
                {doc.name}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* 6. Review Screen & Consent Mock Submit */}
      <div className="bg-white rounded-lg border border-[#E1E8F0] p-5 space-y-4">
        {isConfirmed ? (
          <div className="p-4 rounded-lg bg-green-50 border border-green-200 space-y-2 text-center">
            <CheckCircle2 className="w-6 h-6 text-green-700 mx-auto" />
            <h4 className="text-sm font-bold text-green-800">
              Sample Loan Application Confirmed
            </h4>
            <p className="text-xs text-green-900 font-mono">
              Reference ID: {confirmedReferenceId}
            </p>
            <p className="text-[11px] text-green-700">
              Deterministic terms recorded. Non-binding demonstration application.
            </p>
          </div>
        ) : !reviewMode ? (
          <div>
            <button
              onClick={() => setReviewMode(true)}
              className="w-full h-10 px-4 rounded-lg bg-[#002E6E] hover:bg-[#002456] text-white text-xs font-semibold flex items-center justify-center space-x-2 transition-colors"
            >
              <span>Review Terms & Submit Application</span>
            </button>
          </div>
        ) : (
          <div className="space-y-4 border-t-2 border-[#002E6E] pt-4">
            <div className="space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#002E6E]">
                Final Review Summary (Sample)
              </h4>
              <div className="bg-[#F5F7FA] p-3 rounded-lg border border-[#E1E8F0] space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-[#6B7C93]">Loan Principal:</span>
                  <span className="font-mono font-bold">₹ {amount.toLocaleString("en-IN")}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6B7C93]">Tenure:</span>
                  <span className="font-mono font-bold">{tenure} Months</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6B7C93]">Monthly EMI:</span>
                  <span className="font-mono font-bold text-[#002E6E]">₹ {currentEmi.toLocaleString("en-IN")}/mo</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6B7C93]">Total Interest:</span>
                  <span className="font-mono">₹ {totalInterest.toLocaleString("en-IN")}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6B7C93]">Total Fees (with GST):</span>
                  <span className="font-mono">₹ {totalFee.toLocaleString("en-IN")}</span>
                </div>
              </div>
            </div>

            {/* Explicit Consent Checkbox */}
            <label className="flex items-start space-x-2.5 text-xs text-[#1B2A41] cursor-pointer">
              <input
                type="checkbox"
                checked={consentChecked}
                onChange={(e) => setConsentChecked(e.target.checked)}
                className="mt-0.5 rounded border-[#E1E8F0] text-[#002E6E] focus:ring-0 accent-[#002E6E]"
              />
              <span className="leading-relaxed">
                I give explicit consent to submit this <strong>Sample</strong> personal loan application under the calculated illustrative terms. I understand all data is synthetic and non-binding.
              </span>
            </label>

            {/* Primary Action Button */}
            <div className="flex items-center space-x-2 pt-2">
              <button
                onClick={handleMockSubmit}
                disabled={!consentChecked}
                className="flex-1 h-10 px-4 rounded-lg bg-[#002E6E] hover:bg-[#002456] text-white text-xs font-semibold flex items-center justify-center space-x-1.5 transition-colors disabled:opacity-50"
              >
                <ShieldCheck className="w-4 h-4" />
                <span>Confirm & Submit Sample Application</span>
              </button>
              <button
                onClick={() => setReviewMode(false)}
                className="h-10 px-3 rounded-lg border border-[#E1E8F0] bg-white text-xs text-[#6B7C93] hover:text-[#1B2A41]"
              >
                Back
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

