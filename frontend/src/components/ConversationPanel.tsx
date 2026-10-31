"use client";

import React, { useState, useRef, useEffect } from "react";
import { MessageEntry } from "@/types";
import {
  Mic,
  Square,
  X,
  Send,
  Loader2,
  Volume2,
  ShieldCheck,
  User,
  MessageSquare,
  HelpCircle,
  Headphones,
  CheckCircle2,
  Edit2,
  Check,
} from "lucide-react";
import { API_BASE } from "@/lib/api";

export type VoiceState = "idle" | "listening" | "thinking" | "speaking";

interface InferredFieldInfo {
  name: string;
  value: any;
  label?: string;
}

interface ConversationPanelProps {
  messages: MessageEntry[];
  citations?: string[];
  isThinking: boolean;
  onSendMessage: (text: string) => void;
  onSendAudio: (audioBlob: Blob) => Promise<void> | void;
  audioBase64?: string | null;
  replyAudioUrl?: string | null;
  languageCode?: string;
  targetFieldWhy?: string;
  targetFieldName?: string;
  onTalkToAgent?: () => void;
  // Read-back card props
  inferredField?: InferredFieldInfo | null;
  onConfirmInferred?: (fieldName: string, value: any) => void;
  onEditInferred?: (fieldName: string, newValue: any) => void;
  // Editable transcript review props
  editableTranscript?: string | null;
  onResubmitTranscript?: (correctedText: string) => void;
  onAcceptTranscript?: () => void;
  // 503 Fallback calm notice
  calmNotice?: string | null;
  onDismissCalmNotice?: () => void;
}

export const ConversationPanel: React.FC<ConversationPanelProps> = ({
  messages,
  citations = [],
  isThinking,
  onSendMessage,
  onSendAudio,
  audioBase64,
  replyAudioUrl,
  languageCode = "mr-IN",
  targetFieldWhy,
  targetFieldName,
  onTalkToAgent,
  inferredField,
  onConfirmInferred,
  onEditInferred,
  editableTranscript,
  onResubmitTranscript,
  onAcceptTranscript,
  calmNotice,
  onDismissCalmNotice,
}) => {
  const [inputText, setInputText] = useState("");
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [showWhyTooltip, setShowWhyTooltip] = useState<boolean>(true);

  // Editable transcript local state
  const [localTranscript, setLocalTranscript] = useState<string>("");

  // Inferred amount edit mode local state
  const [isEditingInferred, setIsEditingInferred] = useState<boolean>(false);
  const [inferredEditInput, setInferredEditInput] = useState<string>("");

  // Audio recording timer & volume level states
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);
  const [audioLevel, setAudioLevel] = useState<number>(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<any>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);
  const textInputRef = useRef<HTMLInputElement>(null);
  const lastFallbackSpeechRef = useRef<string | null>(null);

  // Sync incoming editableTranscript
  useEffect(() => {
    if (editableTranscript) {
      setLocalTranscript(editableTranscript);
    }
  }, [editableTranscript]);

  // Focus text input when calm notice appears
  useEffect(() => {
    if (calmNotice) {
      textInputRef.current?.focus();
    }
  }, [calmNotice]);

  // Scroll to bottom on new message or thinking state change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking, editableTranscript, inferredField]);

  // Handle thinking state synchronization
  useEffect(() => {
    if (isThinking) {
      setVoiceState("thinking");
    } else if (voiceState === "thinking") {
      setVoiceState("idle");
    }
  }, [isThinking]);

  // Automatically play reply_audio_url or audioBase64 when received
  useEffect(() => {
    const playAudio = async () => {
      let src = "";
      if (replyAudioUrl) {
        src = replyAudioUrl.startsWith("http") ? replyAudioUrl : `${API_BASE}${replyAudioUrl}`;
      } else if (audioBase64) {
        src = `data:audio/wav;base64,${audioBase64}`;
      }

      if (!src) return;

      try {
        if (!audioPlayerRef.current) {
          audioPlayerRef.current = new Audio();
        }
        audioPlayerRef.current.src = src;
        setVoiceState("speaking");

        audioPlayerRef.current.onended = () => {
          setVoiceState("idle");
        };

        audioPlayerRef.current.onerror = () => {
          // If audio fails, show text only without an error popup
          setVoiceState("idle");
        };

        await audioPlayerRef.current.play().catch(() => {
          // If browser policy blocks autoplay or playback fails, fail silently
          setVoiceState("idle");
        });
      } catch {
        setVoiceState("idle");
      }
    };

    playAudio();
  }, [replyAudioUrl, audioBase64]);

  // Keep every journey voice-capable when the remote TTS provider has no
  // playable response. This uses the browser's installed language voice and
  // never sends extra customer data anywhere.
  useEffect(() => {
    if (replyAudioUrl || audioBase64 || !window.speechSynthesis) return;
    const latestAssistant = [...messages].reverse().find((message) => message.sender === "assistant");
    if (!latestAssistant?.text || latestAssistant.text === lastFallbackSpeechRef.current) return;

    const utterance = new SpeechSynthesisUtterance(latestAssistant.text);
    utterance.lang = languageCode;
    utterance.rate = 0.95;
    utterance.onstart = () => setVoiceState("speaking");
    utterance.onend = () => setVoiceState("idle");
    utterance.onerror = () => setVoiceState("idle");
    lastFallbackSpeechRef.current = latestAssistant.text;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  }, [messages, replyAudioUrl, audioBase64, languageCode]);

  // Plain Audio Level Meter using Web Audio API
  const startLevelMeter = (stream: MediaStream) => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      audioContextRef.current = ctx;
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 64;
      analyserRef.current = analyser;

      const source = ctx.createMediaStreamSource(stream);
      source.connect(analyser);

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const avg = sum / dataArray.length;
        setAudioLevel(Math.min(100, Math.round((avg / 128) * 100)));
        animationFrameRef.current = requestAnimationFrame(tick);
      };
      tick();
    } catch {
      // Audio level meter fallback
    }
  };

  const stopLevelMeter = () => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    analyserRef.current = null;
    setAudioLevel(0);
  };

  // Replay audio helper
  const handleReplayAudio = (url?: string) => {
    if (voiceState === "speaking") return;
    const targetUrl = url || replyAudioUrl;
    if (!targetUrl) return;

    const fullSrc = targetUrl.startsWith("http") || targetUrl.startsWith("data:")
      ? targetUrl
      : `${API_BASE}${targetUrl}`;

    try {
      if (!audioPlayerRef.current) {
        audioPlayerRef.current = new Audio();
      }
      audioPlayerRef.current.src = fullSrc;
      setVoiceState("speaking");

      audioPlayerRef.current.onended = () => {
        setVoiceState("idle");
      };

      audioPlayerRef.current.onerror = () => {
        // Fail silently
        setVoiceState("idle");
      };

      audioPlayerRef.current.play().catch(() => {
        setVoiceState("idle");
      });
    } catch {
      setVoiceState("idle");
    }
  };

  // Start recording using MediaRecorder (audio/webm)
  const handleStartRecording = async () => {
    setVoiceError(null);
    if (onDismissCalmNotice) onDismissCalmNotice();

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      audioChunksRef.current = [];

      let mimeType = "audio/webm;codecs=opus";
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = "audio/webm";
      }
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = "";
      }

      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, {
          type: mimeType || "audio/webm",
        });
        stopLevelMeter();
        if (timerRef.current) clearInterval(timerRef.current);
        stream.getTracks().forEach((track) => track.stop());
        mediaStreamRef.current = null;

        setVoiceState("thinking");
        onSendAudio(audioBlob);
      };

      recorder.start(250);
      setVoiceState("listening");
      setElapsedSeconds(0);
      startLevelMeter(stream);

      // Start 30 s timer
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = setInterval(() => {
        setElapsedSeconds((prev) => {
          if (prev >= 29) {
            handleStopRecording();
            return 30;
          }
          return prev + 1;
        });
      }, 1000);
    } catch (err: any) {
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setVoiceError("Microphone permission was denied. Please allow microphone access in your browser or use the text box below.");
      } else {
        setVoiceError("Microphone access unavailable. Please use the text box below.");
      }
      setVoiceState("idle");
    }
  };

  // Stop recording and process
  const handleStopRecording = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    stopLevelMeter();
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
  };

  // Cancel recording and reset
  const handleCancelRecording = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    stopLevelMeter();

    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.onstop = null;
      if (mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }
    }

    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }

    audioChunksRef.current = [];
    setVoiceState("idle");
    setElapsedSeconds(0);
  };

  // Text input submit
  const handleSubmitText = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = inputText.trim();
    if (!trimmed || isThinking) return;
    setInputText("");
    if (onDismissCalmNotice) onDismissCalmNotice();
    onSendMessage(trimmed);
  };

  // Confirm Inferred Amount
  const handleConfirmInferredAmount = () => {
    if (!inferredField) return;
    if (onConfirmInferred) {
      onConfirmInferred(inferredField.name, inferredField.value);
    } else {
      onSendMessage(`Yes, ₹${Number(inferredField.value).toLocaleString("en-IN")} is correct`);
    }
  };

  // Submit Inferred Amount Edit
  const handleSubmitInferredEdit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = inferredEditInput.trim();
    if (!trimmed || !inferredField) return;
    setIsEditingInferred(false);
    if (onEditInferred) {
      onEditInferred(inferredField.name, trimmed);
    } else {
      onSendMessage(trimmed);
    }
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
            Voice & Text Input
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
              Click the microphone button to speak in Marathi, or type below (e.g. "८० हजार", "80k", "1.5 lakh").
            </p>
          </div>
        ) : (
          messages.map((msg, index) => {
            const isUser = msg.sender === "user";
            const isLastAssistantMessage = !isUser && index === messages.length - 1;

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

                  {/* Replay Spoken Audio Button for Assistant Replies */}
                  {!isUser && (
                    <div className="mt-2 pt-1.5 border-t border-[#E1E8F0]/60 flex items-center justify-between">
                      <button
                        type="button"
                        onClick={() => handleReplayAudio(msg.audio_url || replyAudioUrl || undefined)}
                        disabled={voiceState === "speaking"}
                        className="inline-flex items-center space-x-1 text-[11px] font-semibold text-[#002E6E] hover:text-[#00BAF2] disabled:opacity-40 transition-colors"
                        title="Replay spoken response"
                      >
                        <Volume2 className="w-3.5 h-3.5 text-[#002E6E]" />
                        <span>Replay</span>
                      </button>

                      <span className="text-[10px] font-mono text-[#475569]">
                        {new Date(msg.timestamp).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </div>
                  )}

                  {/* Grounding Citations Pills */}
                  {!isUser && citations.length > 0 && isLastAssistantMessage && (
                    <div className="mt-2.5 pt-2 border-t border-[#E1E8F0] flex flex-wrap gap-1.5 items-center">
                      <span className="text-[10px] uppercase font-bold text-[#475569]">
                        Policy Grounding:
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

                  {/* "Why am I asking this?" Tooltip */}
                  {!isUser && targetFieldWhy && isLastAssistantMessage && (
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

                  {isUser && (
                    <span className="text-[10px] block mt-1.5 font-mono text-blue-200 text-right">
                      {new Date(msg.timestamp).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  )}
                </div>
              </div>
            );
          })
        )}

        {/* Read-Back Card for Inferred Amounts */}
        {inferredField && !isThinking && (
          <div className="p-3 bg-white border border-[#00BAF2] rounded-lg shadow-sm">
            <div className="flex items-center space-x-1.5 text-xs font-semibold text-[#002E6E] mb-1">
              <CheckCircle2 className="w-4 h-4 text-[#00BAF2]" />
              <span>Amount Verification Required</span>
            </div>

            {!isEditingInferred ? (
              <div>
                <p className="text-xs text-[#1B2A41] font-semibold">
                  ₹{Number(inferredField.value).toLocaleString("en-IN")}. Is this correct?
                </p>
                <div className="flex items-center space-x-2 mt-2.5">
                  <button
                    type="button"
                    onClick={handleConfirmInferredAmount}
                    className="px-3 py-1 bg-[#002E6E] text-white text-xs font-semibold rounded hover:bg-[#002456] transition-colors inline-flex items-center space-x-1"
                  >
                    <Check className="w-3 h-3" />
                    <span>Yes</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setIsEditingInferred(true);
                      setInferredEditInput(String(inferredField.value));
                    }}
                    className="px-3 py-1 bg-white border border-[#E1E8F0] text-[#1B2A41] text-xs font-semibold rounded hover:bg-[#F5F7FA] transition-colors inline-flex items-center space-x-1"
                  >
                    <Edit2 className="w-3 h-3 text-[#475569]" />
                    <span>Edit</span>
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleSubmitInferredEdit} className="mt-2 space-y-2">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-semibold text-[#1B2A41]">₹</span>
                  <input
                    type="text"
                    value={inferredEditInput}
                    onChange={(e) => setInferredEditInput(e.target.value)}
                    placeholder="Enter correct amount..."
                    className="flex-1 h-8 px-2.5 rounded border border-[#E1E8F0] text-xs text-[#1B2A41] bg-white focus:outline-none focus:border-[#002E6E]"
                    autoFocus
                  />
                  <button
                    type="submit"
                    className="h-8 px-3 rounded bg-[#002E6E] text-white text-xs font-semibold hover:bg-[#002456] transition-colors"
                  >
                    Save
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsEditingInferred(false)}
                    className="h-8 px-3 rounded border border-[#E1E8F0] text-[#1B2A41] text-xs font-semibold hover:bg-[#F5F7FA] transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}
          </div>
        )}

        {/* Editable Transcript Review Field (Shows returned transcript; user can correct and resubmit before state updates) */}
        {editableTranscript !== null && editableTranscript !== undefined && !isThinking && (
          <div className="p-3 bg-[#F5F7FA] border border-[#002E6E]/40 rounded-lg shadow-sm">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-semibold text-[#002E6E] flex items-center space-x-1">
                <Edit2 className="w-3.5 h-3.5 text-[#002E6E]" />
                <span>Heard Voice Transcript (Editable)</span>
              </span>
              <span className="text-[11px] text-[#475569]">Correct before state updates</span>
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="text"
                value={localTranscript}
                onChange={(e) => setLocalTranscript(e.target.value)}
                className="flex-1 h-9 px-3 text-xs border border-[#E1E8F0] rounded bg-white text-[#1B2A41] focus:outline-none focus:border-[#002E6E]"
              />
              <button
                type="button"
                onClick={() => {
                  if (onResubmitTranscript && localTranscript.trim()) {
                    onResubmitTranscript(localTranscript.trim());
                  }
                }}
                className="h-9 px-3 bg-[#002E6E] text-white text-xs font-semibold rounded hover:bg-[#002456] transition-colors flex-shrink-0"
              >
                Resubmit
              </button>
              <button
                type="button"
                onClick={() => {
                  if (onAcceptTranscript) onAcceptTranscript();
                }}
                className="h-9 px-3 border border-[#E1E8F0] bg-white text-[#1B2A41] text-xs font-semibold rounded hover:bg-[#F5F7FA] transition-colors flex-shrink-0"
              >
                Accept
              </button>
            </div>
          </div>
        )}

        {/* Loading Skeletons While Thinking */}
        {isThinking && (
          <div className="flex items-start space-x-2.5">
            <div className="w-7 h-7 rounded flex items-center justify-center flex-shrink-0 bg-[#1B2A41] text-white">
              <ShieldCheck className="w-3.5 h-3.5" />
            </div>
            <div className="max-w-[85%] rounded-lg p-3 bg-[#F5F7FA] border border-[#E1E8F0] space-y-2 animate-pulse w-72">
              <div className="h-3 bg-[#E1E8F0] rounded w-3/4"></div>
              <div className="h-3 bg-[#E1E8F0] rounded w-5/6"></div>
              <div className="h-3 bg-[#E1E8F0] rounded w-1/2"></div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Voice Error Banner (Microphone permission denied, etc.) */}
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

      {/* 503 Fallback Calm Line: "Voice isn't available right now. You can type instead." */}
      {calmNotice && (
        <div className="px-4 py-2 bg-[#F5F7FA] border-t border-[#E1E8F0] text-xs text-[#1B2A41] flex items-center justify-between">
          <span>{calmNotice}</span>
          <button
            type="button"
            onClick={onDismissCalmNotice}
            className="text-xs text-[#002E6E] font-semibold hover:underline ml-2"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Active Listening Toolbar with Elapsed Seconds, Level Meter, Stop Button, and Cancel Option */}
      {voiceState === "listening" && (
        <div className="px-4 py-2.5 bg-blue-50 border-t border-blue-200 flex items-center justify-between text-xs text-[#002E6E]">
          <div className="flex items-center space-x-3">
            <span className="w-2.5 h-2.5 rounded-full bg-red-600 animate-ping" />
            <span className="font-semibold text-red-700">
              Listening ({elapsedSeconds}s / 30s)
            </span>

            {/* Plain Audio Level Indicator */}
            <div className="flex items-center space-x-1 h-3.5 pl-1" title="Microphone Audio Level">
              {[15, 30, 50, 70, 85].map((threshold, idx) => (
                <div
                  key={idx}
                  className={`w-1 rounded-full transition-all duration-75 ${
                    audioLevel >= threshold ? "bg-[#002E6E] h-3.5" : "bg-[#E1E8F0] h-1.5"
                  }`}
                />
              ))}
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={handleCancelRecording}
              className="h-7 px-2.5 rounded border border-[#E1E8F0] bg-white text-[#1B2A41] text-xs font-semibold hover:bg-[#F5F7FA] transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleStopRecording}
              className="h-7 px-3 rounded bg-red-600 text-white text-xs font-semibold flex items-center space-x-1 hover:bg-red-700 transition-colors"
            >
              <Square className="w-3 h-3 fill-current" />
              <span>Stop</span>
            </button>
          </div>
        </div>
      )}

      {/* Speaking Indicator */}
      {voiceState === "speaking" && (
        <div className="px-4 py-2 bg-blue-50/90 border-t border-blue-200 flex items-center justify-between text-xs text-[#002E6E]">
          <div className="flex items-center space-x-2">
            <Volume2 className="w-3.5 h-3.5 text-[#00BAF2] animate-pulse" />
            <span className="font-semibold text-[#002E6E]">Playing spoken response...</span>
          </div>
          <span className="text-[11px] text-[#475569]">Mic disabled while speaking</span>
        </div>
      )}

      {/* Input Controls Bar */}
      <div className="p-3 border-t border-[#E1E8F0] bg-[#F5F7FA]">
        <div className="flex items-center space-x-2">
          {/* Mic Button: Disabled while speaking or thinking; Stop when listening */}
          <button
            type="button"
            onClick={voiceState === "listening" ? handleStopRecording : handleStartRecording}
            disabled={isThinking || voiceState === "speaking"}
            aria-label={voiceState === "listening" ? "Stop microphone recording" : "Start microphone recording"}
            className={`w-10 h-10 rounded flex items-center justify-center flex-shrink-0 transition-colors ${
              voiceState === "listening"
                ? "bg-red-600 text-white"
                : voiceState === "speaking"
                ? "bg-white border border-[#E1E8F0] text-[#94A3B8] opacity-50 cursor-not-allowed"
                : "bg-white border border-[#E1E8F0] text-[#002E6E] hover:bg-[#E1E8F0]/40"
            }`}
            title={
              voiceState === "speaking"
                ? "Microphone disabled while speaking"
                : voiceState === "listening"
                ? "Stop Recording"
                : "Speak via Microphone"
            }
          >
            {voiceState === "listening" ? (
              <Square className="w-4 h-4 fill-current" />
            ) : (
              <Mic className="w-4 h-4" />
            )}
          </button>

          {/* Text Input Fallback Always Available */}
          <form onSubmit={handleSubmitText} className="flex-1 flex items-center space-x-2">
            <input
              ref={textInputRef}
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
