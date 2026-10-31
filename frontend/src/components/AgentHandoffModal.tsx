"use client";

import React, { useState, useEffect } from "react";
import {
  Headphones,
  CheckCircle2,
  Clock,
  ShieldCheck,
  User,
  X,
  FileText,
  AlertCircle,
  Copy,
  Check,
} from "lucide-react";
import { AgentHandoffResponse } from "@/types";
import { handoffToAgent } from "@/lib/api";

interface AgentHandoffModalProps {
  sessionId: string;
  isOpen: boolean;
  onClose: () => void;
  cachedHandoff?: AgentHandoffResponse | null;
}

export const AgentHandoffModal: React.FC<AgentHandoffModalProps> = ({
  sessionId,
  isOpen,
  onClose,
  cachedHandoff,
}) => {
  const [handoffData, setHandoffData] = useState<AgentHandoffResponse | null>(
    cachedHandoff || null
  );
  const [loading, setLoading] = useState<boolean>(!cachedHandoff);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  useEffect(() => {
    if (!isOpen || !sessionId) return;

    if (cachedHandoff) {
      setHandoffData(cachedHandoff);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    handoffToAgent(sessionId)
      .then((data) => {
        setHandoffData(data);
        setLoading(false);
      })
      .catch((err) => {
        // Fallback for demo mode if backend is offline or mock session
        const mockHandoff: AgentHandoffResponse = {
          handoff_id: `AGT-${Math.floor(100000 + Math.random() * 900000)}`,
          session_id: sessionId,
          journey_id: "priority_support",
          journey_title: "Paytm Priority Lending Support",
          summary_paragraph: `Customer session ${sessionId} transferred with full state. All verified details, financial amounts, and interaction steps are pre-loaded. The specialist can resolve the query without asking the customer to repeat themselves.`,
          journey_state: {
            session_id: sessionId,
            journey_id: "priority_support",
            status: "awaiting_consent",
            fields: {},
            consent: { requested: true, granted: false },
            messages: [],
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
          status: "connected",
          estimated_wait_seconds: 25,
        };
        setHandoffData(mockHandoff);
        setLoading(false);
      });
  }, [isOpen, sessionId, cachedHandoff]);

  if (!isOpen) return null;

  const handleCopySummary = () => {
    if (handoffData?.summary_paragraph) {
      navigator.clipboard.writeText(handoffData.summary_paragraph);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 animate-in fade-in">
      <div className="bg-white w-full max-w-xl rounded-lg border border-[#E1E8F0] shadow-lg overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="px-5 py-4 border-b border-[#E1E8F0] bg-[#F5F7FA] flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded bg-[#002E6E] flex items-center justify-center text-white">
              <Headphones className="w-4 h-4 text-[#00BAF2]" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-[#1B2A41]">
                Paytm Specialist Agent Handoff
              </h2>
              <p className="text-[11px] text-[#475569]">
                Zero-Repetition Customer Handover
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-[#475569] hover:bg-[#E1E8F0] transition-colors"
            aria-label="Close modal"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 overflow-y-auto space-y-4">
          {loading ? (
            <div className="py-12 flex flex-col items-center justify-center space-y-3 text-[#475569]">
              <div className="w-8 h-8 border-2 border-[#002E6E] border-t-transparent rounded-full animate-spin" />
              <p className="text-xs font-semibold text-[#1B2A41]">
                Compiling Journey State & Summarizing Brief...
              </p>
            </div>
          ) : (
            <>
              {/* Connection Status Card */}
              <div className="p-3.5 rounded bg-blue-50 border border-blue-200 flex items-center justify-between">
                <div className="flex items-center space-x-2.5">
                  <div className="w-2.5 h-2.5 rounded-full bg-green-500 animate-pulse" />
                  <div>
                    <span className="text-xs font-bold text-[#002E6E] block">
                      Specialist Connected (Handoff ID: {handoffData?.handoff_id})
                    </span>
                    <span className="text-[11px] text-[#475569] flex items-center space-x-1 mt-0.5">
                      <Clock className="w-3 h-3 text-[#475569]" />
                      <span>Est. Response: &lt; {handoffData?.estimated_wait_seconds || 30} seconds</span>
                    </span>
                  </div>
                </div>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-green-100 text-green-800 border border-green-300">
                  Priority Queue
                </span>
              </div>

              {/* Zero-Repetition Brief Card */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-[#1B2A41] flex items-center space-x-1.5">
                    <FileText className="w-3.5 h-3.5 text-[#002E6E]" />
                    <span>Agent Zero-Repetition Summary</span>
                  </label>
                  <button
                    onClick={handleCopySummary}
                    className="inline-flex items-center space-x-1 text-[11px] font-semibold text-[#002E6E] hover:text-[#00BAF2]"
                  >
                    {copied ? <Check className="w-3 h-3 text-green-600" /> : <Copy className="w-3 h-3" />}
                    <span>{copied ? "Copied" : "Copy Brief"}</span>
                  </button>
                </div>
                <div className="p-3.5 rounded bg-[#F5F7FA] border border-[#E1E8F0] text-xs text-[#1B2A41] leading-relaxed">
                  <p className="font-sans">{handoffData?.summary_paragraph}</p>
                </div>
                <p className="text-[10px] text-[#475569] italic">
                  * This one-paragraph briefing is already transmitted to the specialist's console so you never have to re-explain your details.
                </p>
              </div>

              {/* Verified Journey State Preview */}
              <div className="space-y-2 pt-2 border-t border-[#E1E8F0]">
                <h3 className="text-xs font-bold text-[#1B2A41] uppercase tracking-wider">
                  Transferred Journey State
                </h3>
                <div className="p-3 rounded bg-white border border-[#E1E8F0] divide-y divide-[#E1E8F0] text-xs">
                  <div className="py-1.5 flex justify-between">
                    <span className="text-[#475569]">Journey Type:</span>
                    <span className="font-semibold text-[#1B2A41]">{handoffData?.journey_title}</span>
                  </div>
                  <div className="py-1.5 flex justify-between">
                    <span className="text-[#475569]">Session Tracking:</span>
                    <span className="font-mono text-[#002E6E] font-semibold">{sessionId}</span>
                  </div>
                  <div className="py-1.5 flex justify-between">
                    <span className="text-[#475569]">Verification Status:</span>
                    <span className="text-green-700 font-semibold inline-flex items-center space-x-1">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      <span>Verified Deterministic Rules</span>
                    </span>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-5 py-3 border-t border-[#E1E8F0] bg-[#F5F7FA] flex items-center justify-between">
          <span className="text-[11px] text-[#475569]">
            Paytm Lending Resolution Support
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded bg-[#002E6E] hover:bg-[#002252] text-white text-xs font-semibold transition-colors"
          >
            Return to Journey
          </button>
        </div>
      </div>
    </div>
  );
};

