"use client";

import React, { useState } from "react";
import { Transaction } from "@/types";
import {
  LifeBuoy,
  AlertTriangle,
  Clock,
  CheckCircle2,
  Ticket,
  Headphones,
  Link,
  ShieldCheck,
  CreditCard,
  FileText,
} from "lucide-react";

interface PaymentHelpViewProps {
  transactions: Transaction[];
  onSelectTransaction: (txn: Transaction) => void;
  onRaiseTicket: () => void;
  onAgentHandoff: () => void;
  createdTicketId?: string | null;
}

export const PaymentHelpView: React.FC<PaymentHelpViewProps> = ({
  transactions,
  onSelectTransaction,
  onRaiseTicket,
  onAgentHandoff,
  createdTicketId,
}) => {
  const [selectedTxnId, setSelectedTxnId] = useState<string>(
    transactions.find((t) => t.status === "failed")?.transaction_id || transactions[0]?.transaction_id || ""
  );

  const selectedTxn = transactions.find((t) => t.transaction_id === selectedTxnId) || transactions[0];
  const isFailed = selectedTxn?.status === "failed";

  // Check if multiple failures exist in history
  const failedCount = transactions.filter((t) => t.status === "failed").length;
  const isRepeatedFailure = failedCount >= 1;

  const handleSelect = (id: string) => {
    setSelectedTxnId(id);
    const found = transactions.find((t) => t.transaction_id === id);
    if (found) onSelectTransaction(found);
  };

  return (
    <div className="space-y-6">
      {/* 1. Transaction Picker */}
      <div className="bg-white rounded-lg border border-[#E1E8F0] p-5 space-y-3">
        <div className="flex items-center justify-between border-b border-[#E1E8F0] pb-2.5">
          <div className="flex items-center space-x-2">
            <CreditCard className="w-4 h-4 text-[#002E6E]" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-[#1B2A41]">
              Select Disputed Transaction
            </h3>
          </div>
          <span className="text-[11px] text-[#6B7C93]">From Verified Ledger</span>
        </div>

        <div className="grid grid-cols-1 gap-2">
          {transactions.map((txn) => {
            const isSelected = txn.transaction_id === selectedTxnId;
            const isTxnFailed = txn.status === "failed";

            return (
              <div
                key={txn.transaction_id}
                onClick={() => handleSelect(txn.transaction_id)}
                className={`p-3 rounded-lg border cursor-pointer transition-all flex items-center justify-between ${
                  isSelected
                    ? "border-[#002E6E] bg-blue-50/40"
                    : "border-[#E1E8F0] hover:bg-[#F5F7FA]"
                }`}
              >
                <div className="flex items-center space-x-2.5">
                  <div
                    className={`w-3 h-3 rounded-full ${
                      isTxnFailed ? "bg-red-500" : "bg-[#0F9D58]"
                    }`}
                  />
                  <div>
                    <span className="text-xs font-semibold text-[#1B2A41] block">
                      {txn.description}
                    </span>
                    <span className="text-[10px] text-[#6B7C93] font-mono">
                      {txn.transaction_id} • {txn.date}
                    </span>
                  </div>
                </div>

                <div className="text-right">
                  <span className="text-xs font-bold tabular-nums font-mono text-[#1B2A41] block">
                    ₹ {txn.amount.toLocaleString("en-IN")}
                  </span>
                  <span
                    className={`text-[9px] uppercase font-bold px-1.5 py-0.2 rounded ${
                      isTxnFailed
                        ? "bg-red-50 text-red-700 border border-red-200"
                        : "bg-green-50 text-green-700 border border-green-200"
                    }`}
                  >
                    {txn.status}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 2. Repeated Failure Banner */}
      {isRepeatedFailure && isFailed && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 space-y-1.5">
          <div className="flex items-center space-x-2 text-red-800 font-semibold text-xs">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>Repeated Auto-Debit Failure Notice</span>
          </div>
          <p className="text-[11px] text-red-700 leading-relaxed">
            Repeated auto-debit failure detected. Bank NACH e-mandate may be blocked by your issuing bank. Complete repayment using instant UPI settlement below to prevent negative credit bureau reporting.
          </p>
        </div>
      )}

      {/* 3. Transaction Status Card */}
      {selectedTxn && (
        <div className="bg-white rounded-lg border border-[#E1E8F0] p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-[#E1E8F0] pb-3">
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-[#1B2A41]">
                Transaction Diagnostic Card
              </h3>
              <span className="text-[11px] text-[#6B7C93] font-mono">
                {selectedTxn.account_id}
              </span>
            </div>
            <span
              className={`text-xs font-bold px-2 py-0.5 rounded border ${
                isFailed
                  ? "bg-red-50 border-red-200 text-red-700"
                  : "bg-green-50 border-green-200 text-green-700"
              }`}
            >
              {selectedTxn.status.toUpperCase()}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs bg-[#F5F7FA] p-3.5 rounded-lg border border-[#E1E8F0]">
            <div>
              <span className="text-[#6B7C93] text-[11px] block">Pending Installment</span>
              <span className="font-bold tabular-nums font-mono text-[#002E6E] text-sm">
                ₹ {selectedTxn.amount.toLocaleString("en-IN")}
              </span>
            </div>
            <div>
              <span className="text-[#6B7C93] text-[11px] block">Bounce Waiver Offer</span>
              <span className="font-bold text-green-700 text-sm">
                100% (₹ 350 waived)
              </span>
            </div>
          </div>
        </div>
      )}

      {/* 4. Timeline Component */}
      <div className="bg-white rounded-lg border border-[#E1E8F0] p-5 space-y-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-[#1B2A41]">
          Dispute Resolution Lifecycle
        </h3>

        <div className="relative pl-6 space-y-5 border-l-2 border-[#E1E8F0] ml-2">
          {/* Step 1 */}
          <div className="relative">
            <div className="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-[#002E6E] text-white flex items-center justify-center text-[9px] font-bold">
              1
            </div>
            <div className="text-xs">
              <span className="font-semibold text-[#1B2A41] block">
                Auto-Debit Initiated via NACH
              </span>
              <span className="text-[11px] text-[#6B7C93]">
                Automated monthly clearing scheduled on billing cycle date.
              </span>
            </div>
          </div>

          {/* Step 2 */}
          <div className="relative">
            <div className="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-red-500 text-white flex items-center justify-center text-[9px] font-bold">
              2
            </div>
            <div className="text-xs">
              <span className="font-semibold text-red-700 block">
                Clearing Bounce Recorded
              </span>
              <span className="text-[11px] text-[#6B7C93]">
                Bank reported clearing disruption / insufficient balance response.
              </span>
            </div>
          </div>

          {/* Step 3 */}
          <div className="relative">
            <div className="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-[#00BAF2] text-white flex items-center justify-center text-[9px] font-bold">
              3
            </div>
            <div className="text-xs">
              <span className="font-semibold text-[#002E6E] block">
                48-Hour Late Fee Waiver Active
              </span>
              <span className="text-[11px] text-[#6B7C93]">
                Grace window applied: full ₹350 bounce fee waiver if cleared within 48h.
              </span>
            </div>
          </div>

          {/* Step 4 */}
          <div className="relative">
            <div className="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-[#0F9D58] text-white flex items-center justify-center text-[9px] font-bold">
              4
            </div>
            <div className="text-xs">
              <span className="font-semibold text-green-800 block">
                Instant Settlement Token Ready
              </span>
              <span className="text-[11px] text-[#6B7C93]">
                Pay securely via UPI / debit card with automated real-time reconciliation.
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 5. Resolution ETA with Source Citation Chip */}
      <div className="bg-[#F5F7FA] border border-[#E1E8F0] rounded-lg p-4 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-1.5 text-xs text-[#1B2A41] font-semibold">
            <Clock className="w-3.5 h-3.5 text-[#002E6E]" />
            <span>Resolution ETA: Instant via UPI / 24-48 Hours Bank Clearing</span>
          </div>

          {/* Source Citation Chip */}
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white border border-[#E1E8F0] text-[#002E6E]">
            Source: kb-payment_help-1
          </span>
        </div>
        <p className="text-[11px] text-[#6B7C93] leading-relaxed">
          Grounded in official policy: payments made via verified instant settlement links reflect in borrower ledger immediately, preventing adverse reporting to credit bureaus.
        </p>
      </div>

      {/* 6. Raise-Ticket Button & Agent Handoff Button */}
      <div className="space-y-3">
        {createdTicketId ? (
          <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-xs text-green-900 font-mono flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-green-700 flex-shrink-0" />
            <span>Support Ticket Created: {createdTicketId} (Sample)</span>
          </div>
        ) : (
          <button
            onClick={onRaiseTicket}
            className="w-full h-10 px-4 rounded-lg bg-[#002E6E] hover:bg-[#002456] text-white text-xs font-semibold flex items-center justify-center space-x-2 transition-colors"
          >
            <Ticket className="w-4 h-4" />
            <span>Raise Formal Dispute Ticket</span>
          </button>
        )}

        <button
          onClick={onAgentHandoff}
          className="w-full h-10 px-4 rounded-lg border border-[#E1E8F0] bg-white hover:bg-[#F5F7FA] text-[#1B2A41] text-xs font-semibold flex items-center justify-center space-x-2 transition-colors"
        >
          <Headphones className="w-4 h-4 text-[#00BAF2]" />
          <span>Connect with Lending Specialist (Sample Handoff)</span>
        </button>
      </div>
    </div>
  );
};

