"use client";

import React, { useState, useEffect } from "react";
import { Product, TurnResponse, Transaction } from "@/types";
import {
  fetchProducts,
  createSession,
  sendTurnMessage,
  confirmSession,
  createTicket,
  fetchCustomerTransactions,
} from "@/lib/api";
import { TopBar } from "@/components/TopBar";
import { StartScreen } from "@/components/StartScreen";
import { ConversationPanel } from "@/components/ConversationPanel";
import { JourneyStatePanel } from "@/components/JourneyStatePanel";
import { CustomerTransactionsModal } from "@/components/CustomerTransactionsModal";
import { Loader2, AlertCircle } from "lucide-react";

export default function Home() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loadingProducts, setLoadingProducts] = useState(true);
  const [activeSession, setActiveSession] = useState<TurnResponse | null>(null);
  const [selectedLanguage, setSelectedLanguage] = useState("en-IN");
  const [customerId, setCustomerId] = useState("CUST-1001");
  const [customerTransactions, setCustomerTransactions] = useState<Transaction[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showTransactionsModal, setShowTransactionsModal] = useState(false);
  const [createdTicketId, setCreatedTicketId] = useState<string | null>(null);
  const [confirmedReferenceId, setConfirmedReferenceId] = useState<string | undefined>(undefined);

  // Load initial product catalog and mock customer transactions
  useEffect(() => {
    async function load() {
      try {
        setLoadingProducts(true);
        const [prodData, custData] = await Promise.all([
          fetchProducts(),
          fetchCustomerTransactions(customerId).catch(() => ({ customer: null, transactions: [] })),
        ]);
        setProducts(prodData);
        if (custData && custData.transactions) {
          setCustomerTransactions(custData.transactions);
        }
      } catch (err: any) {
        setError("Unable to connect to BhashaFinance backend. Ensure FastAPI server is running on :8000.");
      } finally {
        setLoadingProducts(false);
      }
    }
    load();
  }, [customerId]);

  const handleStartJourney = async (journeyId: string) => {
    setError(null);
    setCreatedTicketId(null);
    setConfirmedReferenceId(undefined);
    try {
      setIsThinking(true);
      const sessionData = await createSession(journeyId, customerId);
      setActiveSession(sessionData);
    } catch (err: any) {
      setError(err.message || "Failed to start journey");
    } finally {
      setIsThinking(false);
    }
  };

  const handleSendMessage = async (text: string) => {
    if (!activeSession || isThinking) return;
    setError(null);
    try {
      setIsThinking(true);
      const updated = await sendTurnMessage(activeSession.session_id, {
        text,
        languageCode: selectedLanguage,
      });
      setActiveSession(updated);
    } catch (err: any) {
      setError(err.message || "Message delivery failed");
    } finally {
      setIsThinking(false);
    }
  };

  const handleSendAudio = async (audioBlob: Blob) => {
    if (!activeSession || isThinking) return;
    setError(null);
    try {
      setIsThinking(true);
      const updated = await sendTurnMessage(activeSession.session_id, {
        audioFile: audioBlob,
        languageCode: selectedLanguage,
        synthesizeSpeech: true,
      });
      setActiveSession(updated);
    } catch (err: any) {
      setError(err.message || "Voice turn failed");
    } finally {
      setIsThinking(false);
    }
  };

  const handleGrantConsent = async () => {
    if (!activeSession || isConfirming) return;
    try {
      setIsConfirming(true);
      const confRes = await confirmSession(activeSession.session_id, true, "Explicit customer consent granted");
      setConfirmedReferenceId(confRes.reference_id);
      // Advance session state
      const updated = await sendTurnMessage(activeSession.session_id, {
        text: "I agree and give explicit consent",
      });
      setActiveSession(updated);
    } catch (err: any) {
      setError(err.message || "Failed to record consent");
    } finally {
      setIsConfirming(false);
    }
  };

  const handleDeclineConsent = async () => {
    if (!activeSession || isConfirming) return;
    try {
      setIsConfirming(true);
      await confirmSession(activeSession.session_id, false, "Customer requested input modification");
      const updated = await sendTurnMessage(activeSession.session_id, {
        text: "Change inputs",
      });
      setActiveSession(updated);
    } catch (err: any) {
      setError(err.message || "Failed to update state");
    } finally {
      setIsConfirming(false);
    }
  };

  const handleCreateTicket = async () => {
    if (!activeSession) return;
    try {
      const ticket = await createTicket(
        activeSession.session_id,
        "auto_debit_waiver",
        "Disputed bounce fee on active loan with automated 48-hour waiver."
      );
      setCreatedTicketId(ticket.ticket_id);
      alert(`Sample service ticket created successfully: ${ticket.ticket_id}`);
    } catch (err: any) {
      setError(err.message || "Failed to create ticket");
    }
  };

  const handleSelectTransactionFromPicker = (txn: Transaction) => {
    if (!activeSession) return;
    // Auto-message into session
    handleSendMessage(`Loan Account ${txn.account_id} with pending amount of ${txn.amount}`);
  };

  const handleAgentHandoff = () => {
    alert("Live Support Handoff: Connecting to Paytm Lending Support Queue (Sample Queue Pos #1)... An advisor will assist shortly.");
  };

  const handleReset = () => {
    setActiveSession(null);
    setError(null);
    setCreatedTicketId(null);
    setConfirmedReferenceId(undefined);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#F5F7FA] text-[#1B2A41]">
      {/* Top Bar */}
      <TopBar
        selectedLanguage={selectedLanguage}
        onLanguageChange={setSelectedLanguage}
        customerId={customerId}
        onReset={handleReset}
        onViewTransactions={() => setShowTransactionsModal(true)}
      />

      {/* Global Error Notice */}
      {error && (
        <div className="bg-red-50 border-b border-red-200 px-6 py-2 flex items-center justify-between text-xs text-red-700">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="font-semibold underline ml-4">
            Dismiss
          </button>
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col">
        {loadingProducts ? (
          <div className="flex-1 flex flex-col items-center justify-center space-y-2 py-20 text-xs text-[#6B7C93]">
            <Loader2 className="w-6 h-6 animate-spin text-[#002E6E]" />
            <span>Connecting to BhashaFinance AI services...</span>
          </div>
        ) : !activeSession ? (
          <StartScreen
            products={products}
            onSelectJourney={handleStartJourney}
            isLoading={isThinking}
          />
        ) : (
          <div className="flex-1 max-w-7xl w-full mx-auto p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-65px)]">
            {/* Left Column: Conversation */}
            <div className="lg:col-span-7 h-full">
              <ConversationPanel
                messages={activeSession.state.messages || []}
                citations={activeSession.citations || []}
                isThinking={isThinking}
                onSendMessage={handleSendMessage}
                onSendAudio={handleSendAudio}
                audioBase64={activeSession.audio_base64}
              />
            </div>

            {/* Right Column: Journey State Panel */}
            <div className="lg:col-span-5 h-full">
              <JourneyStatePanel
                state={activeSession.state}
                calculation={activeSession.results || activeSession.calculation}
                onGrantConsent={handleGrantConsent}
                onDeclineConsent={handleDeclineConsent}
                onCreateTicket={handleCreateTicket}
                isConfirming={isConfirming}
                transactions={customerTransactions}
                onSelectTransaction={handleSelectTransactionFromPicker}
                onAgentHandoff={handleAgentHandoff}
                createdTicketId={createdTicketId}
                confirmedReferenceId={confirmedReferenceId}
              />
            </div>
          </div>
        )}
      </main>

      {/* Synthetic Customer Transactions Modal */}
      {showTransactionsModal && (
        <CustomerTransactionsModal
          customerId={customerId}
          onClose={() => setShowTransactionsModal(false)}
        />
      )}
    </div>
  );
}

