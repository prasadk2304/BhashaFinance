"use client";

import React, { useState, useRef, useEffect } from "react";
import { MessageEntry } from "@/types";
import { Mic, MicOff, Send, Loader2, Volume2, ShieldCheck, User, Sparkles } from "lucide-react";

interface ConversationPanelProps {
  messages: MessageEntry[];
  citations?: string[];
  isThinking: boolean;
  onSendMessage: (text: string) => void;
  onSendAudio: (audioBlob: Blob) => void;
  audioBase64?: string | null;
}

export type VoiceState = "idle" | "listening" | "thinking" | "speaking";

export const ConversationPanel: React.FC<ConversationPanelProps> = ({
  messages,
  citations = [],
  isThinking,
  onSendMessage,
  onSendAudio,
  audioBase64,
}) => {
  const [inputText, setInputText] = useState("");
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [voiceError, setVoiceError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  // Voice state transition when thinking changes
  useEffect(() => {
    if (isThinking) {
      setVoiceState("thinking");
    } else if (voiceState === "thinking") {
      setVoiceState("idle");
    }
  }, [isThinking]);

  // Play TTS audio if returned
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
      <div className="px-5 py-3 border-b border-[#E1E8F0] flex items-center justify-between bg-[#F5F7FA]">
        <div className="flex items-center space-x-2">
          <div className="w-2.5 h-2.5 rounded-full bg-[#00BAF2]" />
          <h2 className="text-xs font-semibold uppercase tracking-wider text-[#1B2A41]">
            Interactive Assistant
          </h2>
        </div>
        <div className="text-[11px] text-[#6B7C93] flex items-center space-x-1">
          <span>Voice & Text Enabled</span>
        </div>
      </div>

      {/* Transcript Messages Feed */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-[#6B7C93]">
            <Sparkles className="w-8 h-8 text-[#00BAF2] mb-2" />
            <p className="text-xs font-medium">Session initialized</p>
            <p className="text-[11px] mt-1 text-[#6B7C93]">
              Speak into your microphone or type an amount below (e.g. "80k", "1.5 lakh").
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
                  className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 text-white ${
                    isUser ? "bg-[#002E6E]" : "bg-[#00BAF2]"
                  }`}
                >
                  {isUser ? <User className="w-3.5 h-3.5" /> : <ShieldCheck className="w-3.5 h-3.5" />}
                </div>

                {/* Message Bubble */}
                <div
                  className={`max-w-[80%] rounded-lg px-4 py-2.5 text-xs leading-relaxed ${
                    isUser
                      ? "bg-[#002E6E] text-white"
                      : "bg-[#F5F7FA] text-[#1B2A41] border border-[#E1E8F0]"
                  }`}
                >
                  <p className="whitespace-pre-line">{msg.text}</p>

                  {/* Render citations pills if present */}
                  {!isUser && citations.length > 0 && index === messages.length - 1 && (
                    <div className="mt-2.5 pt-2 border-t border-[#E1E8F0]/80 flex flex-wrap gap-1.5 items-center">
                      <span className="text-[10px] uppercase font-semibold text-[#6B7C93]">
                        Grounded in:
                      </span>
                      {citations.map((cId) => (
                        <span
                          key={cId}
                          className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white border border-[#E1E8F0] text-[#002E6E]"
                        >
                          {cId}
                        </span>
                      ))}
                    </div>
                  )}

                  <span
                    className={`text-[9px] block mt-1.5 ${
                      isUser ? "text-blue-100" : "text-[#6B7C93]"
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

        {/* Thinking indicator */}
        {isThinking && (
          <div className="flex items-center space-x-2 text-xs text-[#6B7C93] py-2">
            <Loader2 className="w-4 h-4 animate-spin text-[#00BAF2]" />
            <span>Processing deterministic calculations...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Voice Error Banner */}
      {voiceError && (
        <div className="px-4 py-1.5 bg-amber-50 border-t border-amber-200 text-amber-800 text-[11px] flex items-center justify-between">
          <span>{voiceError}</span>
          <button
            onClick={() => setVoiceError(null)}
            className="text-amber-900 font-semibold hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Input Controls Bar */}
      <div className="p-3.5 border-t border-[#E1E8F0] bg-[#F5F7FA]">
        <div className="flex items-center space-x-2">
          {/* Mic Button with state styling */}
          <button
            type="button"
            onClick={voiceState === "listening" ? handleStopRecording : handleStartRecording}
            disabled={isThinking}
            className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 transition-all ${
              voiceState === "listening"
                ? "bg-red-500 text-white animate-pulse"
                : voiceState === "speaking"
                ? "bg-[#00BAF2] text-white"
                : "bg-white border border-[#E1E8F0] text-[#002E6E] hover:bg-[#E1E8F0]/50"
            }`}
            title={voiceState === "listening" ? "Stop Recording" : "Speak via Voice"}
          >
            {voiceState === "listening" ? (
              <MicOff className="w-4 h-4" />
            ) : voiceState === "speaking" ? (
              <Volume2 className="w-4 h-4 animate-bounce" />
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
              className="flex-1 h-10 px-3.5 rounded-lg border border-[#E1E8F0] bg-white text-xs text-[#1B2A41] placeholder-[#6B7C93] focus:outline-none focus:border-[#002E6E] transition-colors"
            />
            <button
              type="submit"
              disabled={isThinking || !inputText.trim()}
              className="h-10 px-4 rounded-lg bg-[#002E6E] text-white text-xs font-semibold flex items-center justify-center space-x-1 hover:bg-[#002456] transition-colors disabled:opacity-50"
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

