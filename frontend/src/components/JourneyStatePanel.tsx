"use client";

import React, { useState } from "react";
import { JourneyState, CalculationResult, Transaction } from "@/types";
import { LoanOfferComparison } from "./LoanOfferComparison";
import { SipCalculatorView } from "./SipCalculatorView";
import { PaymentHelpView } from "./PaymentHelpView";
import { RejectionExplainerView } from "./RejectionExplainerView";
import {
  CheckCircle2,
  Clock,
  AlertTriangle,
  FileText,
  ShieldCheck,
  Check,
  X,
  CreditCard,
  TrendingUp,
  Tag,
  Layers,
} from "lucide-react";

interface JourneyStatePanelProps {
  state: JourneyState;
  calculation?: CalculationResult | null;
  onGrantConsent: () => void;
  onDeclineConsent: () => void;
  onCreateTicket?: () => void;
  isConfirming: boolean;
  transactions?: Transaction[];
  onSelectTransaction?: (txn: Transaction) => void;
  onAgentHandoff?: () => void;
  createdTicketId?: string | null;
  confirmedReferenceId?: string;
}

export const JourneyStatePanel: React.FC<JourneyStatePanelProps> = ({
  state,
  calculation,
  onGrantConsent,
  onDeclineConsent,
  onCreateTicket,
  isConfirming,
  transactions = [],
  onSelectTransaction,
  onAgentHandoff,
  createdTicketId,
  confirmedReferenceId,
}) => {
  const fields = Object.values(state.fields || {});
  const isAwaitingConsent = state.status === "awaiting_consent";
  const isSubmitted = state.status === "submitted";

  // Tab switcher when calculated: "Overview" or "Interactive Studio"
  const [activeTab, setActiveTab] = useState<"overview" | "studio">("overview");

  // Progress Steps calculation
  const steps = [
    { id: "collecting", label: "Inputs", done: fields.some((f) => f.status === "confirmed") },
    { id: "calculated", label: "Calculation", done: !!calculation || isAwaitingConsent || isSubmitted },
    { id: "consent", label: "Consent", done: state.consent?.granted || isSubmitted },
    { id: "submitted", label: "Confirmed", done: isSubmitted },
  ];

  // Numerical inputs from state
  const monthlyIncome = Number(state.fields["monthly_income"]?.value || 50000);
  const loanAmount = Number(state.fields["loan_amount"]?.value || 150000);
  const tenureMonths = Number(state.fields["tenure_months"]?.value || 24);
  const existingEmis = Number(state.fields["existing_emis"]?.value || 0);
  const annualRate = Number(calculation?.metrics?.annual_interest_rate || 12.5);

  return (
    <div className="flex flex-col h-full bg-white rounded-lg border border-[#E1E8F0] overflow-y-auto">
      {/* Panel Header */}
      <div className="px-5 py-3 border-b border-[#E1E8F0] flex items-center justify-between bg-[#F5F7FA]">
        <div className="flex items-center space-x-2">
          <div className="w-2.5 h-2.5 rounded-full bg-[#002E6E]" />
          <h2 className="text-xs font-semibold uppercase tracking-wider text-[#1B2A41]">
            Journey State
          </h2>
        </div>
        <span className="text-[11px] font-mono text-[#6B7C93] uppercase">
          {state.journey_id.replace(/_/g, " ")}
        </span>
      </div>

      {/* Tabs when in calculated / advanced state */}
      <div className="px-5 pt-3 border-b border-[#E1E8F0] flex space-x-4 bg-white">
        <button
          onClick={() => setActiveTab("overview")}
          className={`pb-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === "overview"
              ? "border-[#002E6E] text-[#002E6E]"
              : "border-transparent text-[#6B7C93] hover:text-[#1B2A41]"
          }`}
        >
          Session Fields & Offer
        </button>
        <button
          onClick={() => setActiveTab("studio")}
          className={`pb-2.5 text-xs font-semibold border-b-2 transition-colors flex items-center space-x-1 ${
            activeTab === "studio"
              ? "border-[#002E6E] text-[#002E6E]"
              : "border-transparent text-[#6B7C93] hover:text-[#1B2A41]"
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Interactive Studio</span>
        </button>
      </div>

      <div className="p-5 space-y-6 flex-1">
        {activeTab === "studio" ? (
          /* ============================================================= */
          /* INTERACTIVE STUDIO TAB FOR EACH PRODUCT JOURNEY */
          /* ============================================================= */
          <div className="space-y-6">
            {state.journey_id === "personal_loan" && (
              <LoanOfferComparison
                initialAmount={loanAmount}
                initialTenure={tenureMonths}
                monthlyIncome={monthlyIncome}
                existingEmis={existingEmis}
                annualRate={annualRate}
                onConfirmApplication={(terms) => {
                  onGrantConsent();
                }}
                isConfirmed={isSubmitted}
                confirmedReferenceId={confirmedReferenceId || `SAMPLE-PAYTM-${state.session_id.slice(-6).toUpperCase()}`}
              />
            )}

            {state.journey_id === "sip" && (
              <SipCalculatorView
                initialMonthly={Number(state.fields["monthly_investment"]?.value || 5000)}
                initialYears={Number(state.fields["duration_years"]?.value || 5)}
                initialReturn={Number(state.fields["expected_annual_return"]?.value || 12)}
              />
            )}

            {state.journey_id === "payment_help" && (
              <PaymentHelpView
                transactions={transactions}
                onSelectTransaction={onSelectTransaction || (() => {})}
                onRaiseTicket={onCreateTicket || (() => {})}
                onAgentHandoff={onAgentHandoff || (() => {})}
                createdTicketId={createdTicketId}
              />
            )}

            {state.journey_id === "loan_rejection" && (
              <RejectionExplainerView
                currentFoir={Number(state.fields["current_score_or_foir"]?.value || 62.0)}
                monthlyIncome={monthlyIncome}
                existingEmis={existingEmis || 20000}
                rejectionReasonCode={String(state.fields["rejection_reason_code"]?.value || "HIGH_FOIR")}
              />
            )}
          </div>
        ) : (
          /* ============================================================= */
          /* OVERVIEW TAB (PROGRESS, FIELD ROWS & SUMMARY) */
          /* ============================================================= */
          <>
            {/* Progress Stepper */}
            <div className="flex items-center justify-between border-b border-[#E1E8F0] pb-4">
              {steps.map((st, i) => (
                <div key={st.id} className="flex items-center space-x-1.5">
                  <div
                    className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                      st.done
                        ? "bg-[#0F9D58] text-white"
                        : state.status === st.id
                        ? "bg-[#002E6E] text-white"
                        : "bg-[#E1E8F0] text-[#6B7C93]"
                    }`}
                  >
                    {st.done ? <Check className="w-3 h-3" /> : i + 1}
                  </div>
                  <span
                    className={`text-xs font-medium ${
                      st.done || state.status === st.id ? "text-[#1B2A41]" : "text-[#6B7C93]"
                    }`}
                  >
                    {st.label}
                  </span>
                  {i < steps.length - 1 && (
                    <div className="w-4 h-[1px] bg-[#E1E8F0] mx-1" />
                  )}
                </div>
              ))}
            </div>

            {/* Field Rows with Status & Source */}
            <div>
              <div className="flex items-center justify-between mb-2.5">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-[#1B2A41]">
                  Field Extractions
                </h3>
                <span className="text-[11px] text-[#6B7C93]">Deterministic Rules</span>
              </div>

              <div className="border border-[#E1E8F0] rounded-lg divide-y divide-[#E1E8F0] overflow-hidden text-xs">
                {fields.map((f) => {
                  const displayVal =
                    f.value !== null && f.value !== undefined
                      ? typeof f.value === "number"
                        ? `${f.unit === "₹" ? "₹ " : ""}${f.value.toLocaleString("en-IN")}${
                            f.unit && f.unit !== "₹" ? ` ${f.unit}` : ""
                          }`
                        : String(f.value)
                      : "—";

                  return (
                    <div
                      key={f.name}
                      className="px-3.5 py-2.5 flex items-center justify-between hover:bg-[#F5F7FA] transition-colors"
                    >
                      <div className="min-w-0 pr-2">
                        <span className="font-medium text-[#1B2A41] block truncate">
                          {f.label || f.name.replace(/_/g, " ")}
                        </span>
                        <span className="text-[10px] text-[#6B7C93] block">
                          src: {f.source}
                        </span>
                      </div>

                      <div className="flex items-center space-x-2 flex-shrink-0">
                        <span className="font-mono tabular-nums text-xs font-semibold text-[#1B2A41]">
                          {displayVal}
                        </span>

                        {/* Status Chip */}
                        <span
                          className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded border ${
                            f.status === "confirmed"
                              ? "bg-green-50 border-green-200 text-green-700"
                              : f.status === "inferred"
                              ? "bg-sky-50 border-sky-200 text-sky-700"
                              : "bg-gray-50 border-gray-200 text-gray-500"
                          }`}
                        >
                          {f.status}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Results Area */}
            {calculation && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-[#1B2A41]">
                    Calculated Offer
                  </h3>
                  <span className="text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-amber-50 border border-amber-200 text-amber-800">
                    {calculation.sample_label}
                  </span>
                </div>

                {/* Metrics Card */}
                <div className="bg-[#F5F7FA] border border-[#E1E8F0] rounded-lg p-4 space-y-3">
                  {/* Personal Loan Metrics */}
                  {calculation.journey_id === "personal_loan" && (
                    <>
                      <div className="flex items-center justify-between border-b border-[#E1E8F0] pb-2">
                        <span className="text-xs text-[#6B7C93]">Monthly EMI</span>
                        <span className="text-base font-bold text-[#002E6E] tabular-nums font-mono">
                          ₹ {calculation.metrics.monthly_emi_rounded?.toLocaleString("en-IN")} / mo
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <span className="text-[11px] text-[#6B7C93] block">Annual Rate</span>
                          <span className="font-semibold tabular-nums">
                            {calculation.metrics.annual_interest_rate}% p.a.
                          </span>
                        </div>
                        <div>
                          <span className="text-[11px] text-[#6B7C93] block">Tenure</span>
                          <span className="font-semibold tabular-nums">
                            {calculation.metrics.tenure_months} Months
                          </span>
                        </div>
                        <div>
                          <span className="text-[11px] text-[#6B7C93] block">Total Interest</span>
                          <span className="font-semibold tabular-nums">
                            ₹ {calculation.metrics.total_interest?.toLocaleString("en-IN")}
                          </span>
                        </div>
                        <div>
                          <span className="text-[11px] text-[#6B7C93] block">Total Payable</span>
                          <span className="font-semibold tabular-nums">
                            ₹ {calculation.metrics.total_amount_payable?.toLocaleString("en-IN")}
                          </span>
                        </div>
                        <div>
                          <span className="text-[11px] text-[#6B7C93] block">FOIR Ratio</span>
                          <span className="font-semibold tabular-nums">
                            {calculation.metrics.foir_percentage}%
                          </span>
                        </div>
                        <div>
                          <span className="text-[11px] text-[#6B7C93] block">Risk Status</span>
                          <span
                            className={`text-xs font-semibold ${
                              calculation.metrics.is_eligible ? "text-green-700" : "text-amber-700"
                            }`}
                          >
                            {calculation.metrics.eligibility_status}
                          </span>
                        </div>
                      </div>
                    </>
                  )}

                  {/* SIP Metrics */}
                  {calculation.journey_id === "sip" && (
                    <>
                      <div className="flex items-center justify-between border-b border-[#E1E8F0] pb-2">
                        <span className="text-xs text-[#6B7C93]">Projected Corpus</span>
                        <span className="text-base font-bold text-[#002E6E] tabular-nums font-mono">
                          ₹ {calculation.metrics.future_value_rounded?.toLocaleString("en-IN")}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <span className="text-[11px] text-[#6B7C93] block">Total Invested</span>
                          <span className="font-semibold tabular-nums">
                            ₹ {calculation.metrics.total_invested?.toLocaleString("en-IN")}
                          </span>
                        </div>
                        <div>
                          <span className="text-[11px] text-[#6B7C93] block">Est. Wealth Gain</span>
                          <span className="font-semibold text-green-700 tabular-nums">
                            + ₹ {Math.round(calculation.metrics.estimated_returns || 0).toLocaleString("en-IN")}
                          </span>
                        </div>
                      </div>
                    </>
                  )}

                  {/* Payment Help Metrics */}
                  {calculation.journey_id === "payment_help" && (
                    <>
                      <div className="flex items-center justify-between border-b border-[#E1E8F0] pb-2">
                        <span className="text-xs text-[#6B7C93]">Net Payable</span>
                        <span className="text-base font-bold text-[#002E6E] tabular-nums font-mono">
                          ₹ {calculation.metrics.net_payable?.toLocaleString("en-IN")}
                        </span>
                      </div>
                      <div className="text-xs space-y-1">
                        <p className="text-[#1B2A41] font-medium">
                          Resolution: {calculation.metrics.resolution_strategy}
                        </p>
                        <p className="text-[11px] text-green-700 font-semibold">
                          Waiver Applied: ₹ {calculation.metrics.late_fee_waiver}
                        </p>
                        <p className="text-[11px] font-mono text-[#002E6E]">
                          Token: {calculation.metrics.payment_token}
                        </p>
                      </div>
                    </>
                  )}

                  {/* Loan Rejection Metrics */}
                  {calculation.journey_id === "loan_rejection" && (
                    <div className="text-xs space-y-2">
                      <div className="flex items-center justify-between border-b border-[#E1E8F0] pb-2">
                        <span className="text-[#6B7C93]">Cooling Off Period</span>
                        <span className="font-bold text-[#002E6E]">
                          {calculation.metrics.cooling_off_days} Days
                        </span>
                      </div>
                      <p className="font-medium text-[#1B2A41]">
                        Target: {calculation.metrics.target_metric}
                      </p>
                      <p className="text-[11px] text-[#6B7C93]">
                        Eligible to Re-apply on: {calculation.metrics.reapply_eligible_date}
                      </p>
                    </div>
                  )}
                </div>

                {/* Explicit Consent Action Box (One Primary Button Per Screen) */}
                {isAwaitingConsent && (
                  <div className="p-4 rounded-lg bg-blue-50 border border-blue-200 space-y-3">
                    <div className="flex items-start space-x-2">
                      <ShieldCheck className="w-4 h-4 text-[#002E6E] mt-0.5 flex-shrink-0" />
                      <p className="text-xs text-[#002E6E] font-medium leading-relaxed">
                        Explicit customer consent is required before sample submission. Do you agree to proceed with this Sample application?
                      </p>
                    </div>

                    <div className="flex items-center space-x-2">
                      {/* Single Primary Button on screen */}
                      <button
                        onClick={onGrantConsent}
                        disabled={isConfirming}
                        className="flex-1 h-9 px-3 rounded-lg bg-[#002E6E] hover:bg-[#002456] text-white text-xs font-semibold flex items-center justify-center space-x-1 transition-colors disabled:opacity-50"
                      >
                        <Check className="w-3.5 h-3.5" />
                        <span>Grant Consent & Submit</span>
                      </button>

                      <button
                        onClick={onDeclineConsent}
                        disabled={isConfirming}
                        className="h-9 px-3 rounded-lg border border-[#E1E8F0] bg-white text-xs font-medium text-[#6B7C93] hover:text-[#1B2A41] transition-colors"
                      >
                        Modify
                      </button>
                    </div>
                  </div>
                )}

                {/* Submitted State */}
                {isSubmitted && (
                  <div className="p-4 rounded-lg bg-green-50 border border-green-200 space-y-2">
                    <div className="flex items-center space-x-2 text-green-800">
                      <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                      <span className="text-xs font-semibold">
                        Sample Application Confirmed
                      </span>
                    </div>
                    <p className="text-[11px] text-green-900 leading-relaxed font-mono">
                      Reference: {confirmedReferenceId || `SAMPLE-PAYTM-${state.session_id.slice(-6).toUpperCase()}`}
                    </p>

                    {onCreateTicket && calculation.journey_id === "payment_help" && (
                      <button
                        onClick={onCreateTicket}
                        className="mt-2 w-full h-8 px-3 rounded-lg border border-green-300 bg-white text-xs font-medium text-green-900 hover:bg-green-50 transition-colors"
                      >
                        Create Service Ticket
                      </button>
                    )}
                  </div>
                )}

                {/* Disclosures list */}
                {calculation.disclosures?.length > 0 && (
                  <div className="pt-2 border-t border-[#E1E8F0]">
                    <span className="text-[10px] uppercase font-bold text-[#6B7C93] block mb-1">
                      Sample Disclosures
                    </span>
                    <ul className="text-[10px] text-[#6B7C93] space-y-1 list-disc pl-3">
                      {calculation.disclosures.map((disc, idx) => (
                        <li key={idx}>{disc}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
