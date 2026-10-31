"use client";

import React, { useEffect, useState } from "react";
import { Transaction } from "@/types";
import { fetchCustomerTransactions } from "@/lib/api";
import { X, AlertCircle, CheckCircle2, Clock, ArrowUpRight } from "lucide-react";

interface CustomerTransactionsModalProps {
  customerId: string;
  onClose: () => void;
}

export const CustomerTransactionsModal: React.FC<CustomerTransactionsModalProps> = ({
  customerId,
  onClose,
}) => {
  const [customer, setCustomer] = useState<any>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const data = await fetchCustomerTransactions(customerId);
        setCustomer(data.customer);
        setTransactions(data.transactions);
      } catch (err: any) {
        setError(err.message || "Failed to load transactions");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [customerId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm p-4">
      <div className="bg-white rounded-lg border border-[#E1E8F0] shadow-modal w-full max-w-xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Modal Header */}
        <div className="px-5 py-4 border-b border-[#E1E8F0] flex items-center justify-between bg-[#F5F7FA]">
          <div>
            <h3 className="text-sm font-semibold text-[#1B2A41]">
              Customer Transaction Ledger (Sample)
            </h3>
            <p className="text-xs text-[#6B7C93]">
              {customer?.name || customerId} • Account: {customer?.active_loan_id || "PAYTM-LN-8812"}
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-lg border border-[#E1E8F0] flex items-center justify-center text-[#6B7C93] hover:text-[#1B2A41] hover:bg-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 overflow-y-auto flex-1 space-y-3">
          {loading ? (
            <div className="py-12 text-center text-xs text-[#6B7C93]">
              Loading mock transactions...
            </div>
          ) : error ? (
            <div className="py-8 text-center text-xs text-red-600">{error}</div>
          ) : (
            <div className="divide-y divide-[#E1E8F0] border border-[#E1E8F0] rounded-lg overflow-hidden">
              {transactions.map((txn) => {
                const isFailed = txn.status === "failed";
                return (
                  <div
                    key={txn.transaction_id}
                    className="p-3.5 flex items-center justify-between hover:bg-[#F5F7FA] transition-colors"
                  >
                    <div className="flex items-start space-x-3">
                      <div
                        className={`w-7 h-7 rounded-lg flex items-center justify-center mt-0.5 ${
                          isFailed
                            ? "bg-red-50 text-red-600 border border-red-200"
                            : "bg-green-50 text-green-600 border border-green-200"
                        }`}
                      >
                        {isFailed ? (
                          <AlertCircle className="w-4 h-4" />
                        ) : (
                          <CheckCircle2 className="w-4 h-4" />
                        )}
                      </div>
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="text-xs font-semibold text-[#1B2A41]">
                            {txn.type.replace(/_/g, " ").toUpperCase()}
                          </span>
                          <span
                            className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                              isFailed
                                ? "bg-red-50 text-red-700 border border-red-200"
                                : "bg-green-50 text-green-700 border border-green-200"
                            }`}
                          >
                            {txn.status}
                          </span>
                        </div>
                        <p className="text-[11px] text-[#6B7C93] mt-0.5">
                          {txn.description}
                        </p>
                        <span className="text-[10px] text-[#6B7C93] block font-mono">
                          {txn.date} • {txn.transaction_id}
                        </span>
                      </div>
                    </div>

                    <div className="text-right flex-shrink-0">
                      <span className="font-mono tabular-nums text-xs font-bold text-[#1B2A41] block">
                        ₹ {txn.amount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-5 py-3 border-t border-[#E1E8F0] bg-[#F5F7FA] flex items-center justify-between">
          <span className="text-[11px] text-[#6B7C93]">
            Synthetic customer transactions for support dispute resolution.
          </span>
          <button
            onClick={onClose}
            className="h-8 px-3 rounded-lg border border-[#E1E8F0] bg-white text-xs font-medium text-[#1B2A41] hover:bg-[#F5F7FA]"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

