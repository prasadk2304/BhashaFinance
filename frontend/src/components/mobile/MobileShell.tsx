"use client";

import { Activity, House, Map, Mic, UserRound } from "lucide-react";
import React from "react";

export type MobileTab = "home" | "journeys" | "activity" | "profile";

export function MobileShell({ activeTab, onTabChange, onVoiceOpen, children }: {
  activeTab: MobileTab; onTabChange: (tab: MobileTab) => void; onVoiceOpen: () => void; children: React.ReactNode;
}) {
  const tabs = [["home", "Home", House], ["journeys", "Journeys", Map], ["activity", "Activity", Activity], ["profile", "Profile", UserRound]] as const;
  return <div className="mobile-shell"><div className="mobile-scroll">{children}</div><nav className="mobile-tabs" aria-label="Primary navigation">
    {tabs.slice(0, 2).map(([id, label, Icon]) => <button key={id} onClick={() => onTabChange(id)} className={`mobile-tab ${activeTab === id ? "active" : ""}`} aria-label={label}><Icon/><span>{label}</span></button>)}
    <button className="voice-tab" onClick={onVoiceOpen} aria-label="Open voice assistant"><Mic/></button>
    {tabs.slice(2).map(([id, label, Icon]) => <button key={id} onClick={() => onTabChange(id)} className={`mobile-tab ${activeTab === id ? "active" : ""}`} aria-label={label}><Icon/><span>{label}</span></button>)}
  </nav></div>;
}
