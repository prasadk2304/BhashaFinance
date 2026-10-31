"use client";

import React, { useState, useRef, useEffect } from "react";
import { MessageEntry } from "@/types";
import {
  Mic,
  MicOff,
  Send,
  Loader2,
  Volume2,
  ShieldCheck,
  User,
  MessageSquare,
  HelpCircle,
  Headphones,
  CheckCircle2,
} from "lucide-react";

interface ConversationPanelProps {
  messages: MessageEntry[];
  citations?: string[];
  isThinking: boolean;
  onSendMessage: (text: string) => void;
  onSendAudio: (audioBlob: Blob) => void;
  audioBase64?: string | null;
  targetFieldWhy?: string;
  targetFieldName?: string;
  onTalkToAgent?: () => void;
}

export type VoiceState = "idle" | "listening" | "thinking" | "speaking";

export const ConversationPanel: React.FC<ConversationPanelProps> = ({
  messages,
  citations = [],
  isThinking,
  onSendMessage,
  onSendAudio,
  audioBase64,
  targetFieldWhy,
  targetFieldName,
  onTalkToAgent,
}) => {
  const [inputText, setInputText] = useState("");
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [showWhyTooltip, setShowWhyTooltip] = useState<boolean>(true);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  useEffect(() => {
    if (isThinking) {
      setVoiceState("thinking");
    } else if (voiceState === "thinking") {
      setVoiceState("idle");
    }
  }, [isThinking]);

  useEffect(() => {
    if (audioBase64) {
      try {
        const audioSrc = `data:audio/wav;base64,${audioBase64}`;
        if (!audioPlayerRef.current) {
          audioPlayerRef.current = new Audio();
        }
        audioPlayerRef.current.src = audioSrc;
        setVoiceState("speaking");
        audioPlayerRef.current.onended = () => {
          setVoiceState("idle");
        };
        audioPlayerRef.current.play().catch(() => {
          setVoiceState("idle");
        });
      } catch (err) {
        setVoiceState("idle");
      }
    }
  }, [audioBase64]);

  const handleStartRecording = async () => {
    setVoiceError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/wav" });
        stream.getTracks().forEach((track) => track.stop());
        setVoiceState("thinking");
        onSendAudio(audioBlob);
      };

      mediaRecorder.start();
      setVoiceState("listening");
    } catch (err: any) {
      setVoiceError("Microphone access unavailable. Please use text input fallback.");
      setVoiceState("idle");
    }
  };

  const handleStopRecording = () => {
    if (mediaRecorderRef.current && voiceState === "listening") {
      mediaRecorderRef.current.stop();
    }
  };

  const handleSubmitText = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = inputText.trim();
    if (!trimmed || isThinking) return;
    setInputText("");
    onSendMessage(trimmed);
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg border border-[#E1E8F0] overflow-hidden">
      {/* Conversation Header */}
      <div className="px-4 py-3 border-b border-[#E1E8F0] flex items-center justify-between bg-[#F5F7FA]">
        <div className="flex items-center space-x-2">
          <div className="w-2.5 h-2.5 rounded-full bg-[#002E6E]" />
          <h2 className="text-xs font-semibold uppercase tracking-wider text-[#1B2A41]">
            Conversation Transcript
          </h2>
        </div>
        <div className="flex items-center space-x-2">
          {onTalkToAgent && (
            <button
              type="button"
              onClick={onTalkToAgent}
              className="inline-flex items-center space-x-1 text-[11px] font-semibold text-[#002E6E] bg-white border border-[#E1E8F0] px-2 py-1 rounded hover:bg-[#F5F7FA] transition-colors"
              title="Pass journey state to specialist without repeating"
            >
              <Headphones className="w-3 h-3 text-[#00BAF2]" />
              <span>Talk to Agent</span>
            </button>
          )}
          <span className="text-[11px] font-medium text-[#475569] hidden sm:inline">
            Voice & Text Fallback
          </span>
        </div>
      </div>

      {/* Transcript Messages Feed */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-[#475569]">
            <MessageSquare className="w-8 h-8 text-[#002E6E] mb-2" />
            <p className="text-xs font-semibold text-[#1B2A41]">Session Started</p>
            <p className="text-[11px] mt-1 text-[#475569] max-w-xs">
              Speak using the microphone or type below (e.g. "80k", "1.5 lakh", "2 years").
            </p>
          </div>
        ) : (
          messages.map((msg, index) => {
            const isUser = msg.sender === "user";
            return (
              <div
                key={index}
                className={`flex items-start space-x-2.5 ${
                  isUser ? "flex-row-reverse space-x-reverse" : "flex-row"
                }`}
              >
                {/* Avatar Icon */}
                <div
                  className={`w-7 h-7 rounded flex items-center justify-center flex-shrink-0 text-white ${
                    isUser ? "bg-[#002E6E]" : "bg-[#1B2A41]"
                  }`}
                >
                  {isUser ? <User className="w-3.5 h-3.5" /> : <ShieldCheck className="w-3.5 h-3.5" />}
                </div>

                {/* Message Bubble */}
                <div
                  className={`max-w-[85%] rounded-lg px-4 py-2.5 text-xs leading-relaxed ${
                    isUser
                      ? "bg-[#002E6E] text-white"
                      : "bg-[#F5F7FA] text-[#1B2A41] border border-[#E1E8F0]"
                  }`}
                >
                  <p className="whitespace-pre-line">{msg.text}</p>

                  {/* Grounding Citations Pills */}
                  {!isUser && citations.length > 0 && index === messages.length - 1 && (
                    <div className="mt-2.5 pt-2 border-t border-[#E1E8F0] flex flex-wrap gap-1.5 items-center">
                      <span className="text-[10px] uppercase font-bold text-[#475569]">
                        Policy Sources:
                      </span>
                      {citations.map((cId) => (
                        <span
                          key={cId}
                          className="text-[10px] font-mono font-medium px-1.5 py-0.5 rounded bg-white border border-[#E1E8F0] text-[#002E6E]"
                        >
                          {cId}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* "Why am I asking this?" Tooltip for Planner Questions */}
                  {!isUser && targetFieldWhy && index === messages.length - 1 && (
                    <div className="mt-2 pt-2 border-t border-[#E1E8F0]">
                      <button
                        type="button"
                        onClick={() => setShowWhyTooltip(!showWhyTooltip)}
                        className="inline-flex items-center space-x-1 text-[11px] font-semibold text-[#002E6E] hover:text-[#00BAF2] transition-colors"
                        aria-label="Why am I asking this question?"
                      >
                        <HelpCircle className="w-3.5 h-3.5 text-[#00BAF2]" />
                        <span>Why am I asking this?</span>
                      </button>
                      {showWhyTooltip && (
                        <div className="mt-1.5 p-2.5 rounded bg-blue-50 border border-blue-200 text-[#1B2A41] text-[11px] leading-relaxed shadow-sm">
                          <p className="font-semibold text-[#002E6E] mb-0.5 flex items-center space-x-1">
                            <CheckCircle2 className="w-3 h-3 text-[#002E6E]" />
                            <span>Purpose of this question:</span>
                          </p>
                          <p className="text-[#334155]">{targetFieldWhy}</p>
                        </div>
                      )}
                    </div>
                  )}

                  <span
                    className={`text-[10px] block mt-1.5 font-mono ${
                      isUser ? "text-blue-200" : "text-[#475569]"
                    }`}
                  >
                    {new Date(msg.timestamp).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
              </div>
            );
          })
        )}

        {/* Thinking Indicator */}
        {isThinking && (
          <div className="flex items-center space-x-2 text-xs text-[#475569] py-2">
            <Loader2 className="w-4 h-4 animate-spin text-[#002E6E]" />
            <span>Calculating deterministic rules...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Voice Error Banner */}
      {voiceError && (
        <div className="px-4 py-2 bg-amber-50 border-t border-amber-200 text-amber-900 text-xs flex items-center justify-between">
          <span>{voiceError}</span>
          <button
            onClick={() => setVoiceError(null)}
            className="text-amber-950 font-bold underline ml-2"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Active Voice State Chip (Listening / Thinking / Speaking) */}
      {voiceState !== "idle" && (
        <div className="px-4 py-2 bg-blue-50/90 border-t border-blue-200 flex items-center justify-between text-xs text-[#002E6E]">
          <div className="flex items-center space-x-2">
            {voiceState === "listening" && (
              <>
                <span className="w-2.5 h-2.5 rounded-full bg-red-600 animate-ping" />
                <span className="font-semibold text-red-700">Listening to your voice... (click mic or send text)</span>
              </>
            )}
            {voiceState === "thinking" && (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin text-[#002E6E]" />
                <span className="font-semibold text-[#002E6E]">Thinking... validating numbers with deterministic rules</span>
              </>
            )}
            {voiceState === "speaking" && (
              <>
                <Volume2 className="w-3.5 h-3.5 text-[#00BAF2] animate-pulse" />
                <span className="font-semibold text-[#002E6E]">Speaking response via Sarvam TTS (bulbul:v3)...</span>
              </>
            )}
          </div>
          <span className="text-[11px] text-[#475569] font-medium hidden sm:inline">
            Text input ready below
          </span>
        </div>
      )}

      {/* Input Controls Bar */}
      <div className="p-3 border-t border-[#E1E8F0] bg-[#F5F7FA]">
        <div className="flex items-center space-x-2">
          {/* Mic Button */}
          <button
            type="button"
            onClick={voiceState === "listening" ? handleStopRecording : handleStartRecording}
            disabled={isThinking}
            aria-label={voiceState === "listening" ? "Stop microphone recording" : "Start microphone recording"}
            className={`w-10 h-10 rounded flex items-center justify-center flex-shrink-0 transition-colors ${
              voiceState === "listening"
                ? "bg-red-600 text-white"
                : voiceState === "speaking"
                ? "bg-[#002E6E] text-white"
                : "bg-white border border-[#E1E8F0] text-[#002E6E] hover:bg-[#E1E8F0]/40"
            }`}
            title={voiceState === "listening" ? "Stop Recording" : "Speak via Microphone"}
          >
            {voiceState === "listening" ? (
              <MicOff className="w-4 h-4" />
            ) : voiceState === "speaking" ? (
              <Volume2 className="w-4 h-4" />
            ) : (
              <Mic className="w-4 h-4" />
            )}
          </button>

          {/* Text Input Fallback */}
          <form onSubmit={handleSubmitText} className="flex-1 flex items-center space-x-2">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Speak or type (e.g. '80k', '1.5 lakh', '2 years')..."
              disabled={isThinking}
              aria-label="User response input"
              className="flex-1 h-10 px-3 rounded border border-[#E1E8F0] bg-white text-xs text-[#1B2A41] placeholder-[#475569] focus:outline-none focus:border-[#002E6E]"
            />
            <button
              type="submit"
              disabled={isThinking || !inputText.trim()}
              aria-label="Send message"
              className="h-10 px-4 rounded bg-[#002E6E] text-white text-xs font-semibold flex items-center justify-center space-x-1 hover:bg-[#002456] transition-colors disabled:opacity-50"
            >
              <span>Send</span>
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
