"use client";

import React, { useState, useEffect, useMemo } from "react";
import { Product, TurnResponse, Transaction } from "@/types";
import { DEMO_SCENARIOS } from "@/lib/demoScenarios";
import {
  fetchProducts,
  fetchSupportedLanguages,
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
import { AgentHandoffModal } from "@/components/AgentHandoffModal";
import { Loader2, AlertCircle } from "lucide-react";

export default function Home() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loadingProducts, setLoadingProducts] = useState(true);
  const [activeSession, setActiveSession] = useState<TurnResponse | null>(null);
  const [supportedLanguages, setSupportedLanguages] = useState<Record<string, string>>({
    "mr-IN": "मराठी",
    "hi-IN": "हिन्दी",
    "en-IN": "English",
  });
  const [selectedLanguage, setSelectedLanguage] = useState("mr-IN");
  const [customerId, setCustomerId] = useState("CUST-1001");
  const [customerTransactions, setCustomerTransactions] = useState<Transaction[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [calmVoiceNotice, setCalmVoiceNotice] = useState<string | null>(null);
  const [pendingTurn, setPendingTurn] = useState<TurnResponse | null>(null);
  const [editableTranscript, setEditableTranscript] = useState<string | null>(null);
  const [showTransactionsModal, setShowTransactionsModal] = useState(false);
  const [showAgentModal, setShowAgentModal] = useState(false);
  const [createdTicketId, setCreatedTicketId] = useState<string | null>(null);
  const [confirmedReferenceId, setConfirmedReferenceId] = useState<string | undefined>(undefined);

  // Load initial product catalog, languages, and mock customer transactions
  useEffect(() => {
    async function load() {
      try {
        setLoadingProducts(true);
        const [prodData, custData, langsData] = await Promise.all([
          fetchProducts(),
          fetchCustomerTransactions(customerId).catch(() => ({ customer: null, transactions: [] })),
          fetchSupportedLanguages().catch(() => ({
            "mr-IN": "मराठी",
            "hi-IN": "हिन्दी",
            "en-IN": "English",
          })),
        ]);
        setProducts(prodData);
        if (custData && custData.transactions) {
          setCustomerTransactions(custData.transactions);
        }
        if (langsData && Object.keys(langsData).length > 0) {
          const map = langsData as Record<string, string>;
          setSupportedLanguages(map);
          if (!map[selectedLanguage]) {
            setSelectedLanguage("mr-IN");
          }
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
    setCalmVoiceNotice(null);
    setPendingTurn(null);
    setEditableTranscript(null);
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

  const handleLoadScenario = (journeyId: string) => {
    const scenario = DEMO_SCENARIOS[journeyId];
    if (!scenario) return;
    setError(null);
    setCalmVoiceNotice(null);
    setPendingTurn(null);
    setEditableTranscript(null);
    setCreatedTicketId(null);
    setConfirmedReferenceId(undefined);
    // Deep copy seedData
    const seeded = JSON.parse(JSON.stringify(scenario.seedData));
    setActiveSession(seeded);
  };

  const handleSendMessage = async (text: string) => {
    if (!activeSession || isThinking) return;
    setError(null);
    setCalmVoiceNotice(null);
    setPendingTurn(null);
    setEditableTranscript(null);
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
    setCalmVoiceNotice(null);
    try {
      setIsThinking(true);
      const updated = await sendTurnMessage(activeSession.session_id, {
        audioFile: audioBlob,
        languageCode: selectedLanguage,
        synthesizeSpeech: true,
      });

      // Show returned transcript in editable field so user can correct and resubmit before state updates
      if (updated.transcript) {
        setPendingTurn(updated);
        setEditableTranscript(updated.transcript);
      } else {
        setActiveSession(updated);
      }
    } catch (err: any) {
      if (err.status === 503 || err.fallback === "text") {
        // If STT returns 503 with fallback "text", switch to the text input and show one calm line:
        // "Voice isn't available right now. You can type instead."
        setCalmVoiceNotice("Voice isn't available right now. You can type instead.");
      } else {
        setError(err.message || "Voice turn failed");
      }
    } finally {
      setIsThinking(false);
    }
  };

  const handleResubmitTranscript = async (correctedText: string) => {
    setPendingTurn(null);
    setEditableTranscript(null);
    await handleSendMessage(correctedText);
  };

  const handleAcceptTranscript = () => {
    if (pendingTurn) {
      setActiveSession(pendingTurn);
      setPendingTurn(null);
      setEditableTranscript(null);
    }
  };

  // Detect any inferred amount in the state for the Read-Back Card
  const inferredField = useMemo(() => {
    if (!activeSession?.state?.fields) return null;
    for (const [name, f] of Object.entries(activeSession.state.fields)) {
      if (f.status === "inferred" && f.value !== null && f.value !== undefined) {
        return { name, value: f.value, label: f.label || name };
      }
    }
    return null;
  }, [activeSession]);

  const handleConfirmInferred = async (fieldName: string, value: any) => {
    // Yes marks the field confirmed
    await handleSendMessage(`Yes, ₹${Number(value).toLocaleString("en-IN")} is correct`);
  };

  const handleEditInferred = async (fieldName: string, newValue: any) => {
    await handleSendMessage(String(newValue));
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
    handleSendMessage(`Loan Account ${txn.account_id} with pending amount of ${txn.amount}`);
  };

  const handleAgentHandoff = () => {
    setShowAgentModal(true);
  };

  const handleReset = () => {
    setActiveSession(null);
    setError(null);
    setCalmVoiceNotice(null);
    setPendingTurn(null);
    setEditableTranscript(null);
    setCreatedTicketId(null);
    setConfirmedReferenceId(undefined);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#F5F7FA] text-[#1B2A41]">
      {/* Top Bar with Language Selector from GET /api/languages and Agent Handoff */}
      <TopBar
        selectedLanguage={selectedLanguage}
        onLanguageChange={setSelectedLanguage}
        customerId={customerId}
        onReset={handleReset}
        onLoadScenario={handleLoadScenario}
        onViewTransactions={() => setShowTransactionsModal(true)}
        onTalkToAgent={handleAgentHandoff}
        supportedLanguages={supportedLanguages}
      />

      {/* Global Error Notice */}
      {error && (
        <div className="bg-red-50 border-b border-red-200 px-4 sm:px-6 py-2 flex items-center justify-between text-xs text-red-800">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0 text-red-700" />
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
          <div className="flex-1 flex flex-col items-center justify-center space-y-2 py-20 text-xs text-[#475569]">
            <Loader2 className="w-6 h-6 animate-spin text-[#002E6E]" />
            <span>Connecting to BhashaFinance AI services...</span>
          </div>
        ) : !activeSession ? (
          <StartScreen
            products={products}
            onSelectJourney={handleStartJourney}
            onLoadScenario={handleLoadScenario}
            isLoading={isThinking}
          />
        ) : (
          <div className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[calc(100vh-65px)] lg:h-[calc(100vh-65px)]">
            {/* Left Column: Conversation */}
            <div className="lg:col-span-7 h-[500px] lg:h-full">
              <ConversationPanel
                messages={activeSession.state.messages || []}
                citations={activeSession.citations || []}
                isThinking={isThinking}
                onSendMessage={handleSendMessage}
                onSendAudio={handleSendAudio}
                audioBase64={activeSession.audio_base64}
                replyAudioUrl={activeSession.reply_audio_url}
                targetFieldWhy={activeSession.target_field_why}
                targetFieldName={activeSession.target_field}
                onTalkToAgent={handleAgentHandoff}
                inferredField={inferredField}
                onConfirmInferred={handleConfirmInferred}
                onEditInferred={handleEditInferred}
                editableTranscript={editableTranscript}
                onResubmitTranscript={handleResubmitTranscript}
                onAcceptTranscript={handleAcceptTranscript}
                calmNotice={calmVoiceNotice}
                onDismissCalmNotice={() => setCalmVoiceNotice(null)}
              />
            </div>

            {/* Right Column: Journey State Panel */}
            <div className="lg:col-span-5 h-[650px] lg:h-full">
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

      {/* Talk to an Agent Zero-Repetition Modal */}
      <AgentHandoffModal
        sessionId={activeSession?.session_id || "demo_sess_1001"}
        isOpen={showAgentModal}
        onClose={() => setShowAgentModal(false)}
      />
    </div>
  );
}

