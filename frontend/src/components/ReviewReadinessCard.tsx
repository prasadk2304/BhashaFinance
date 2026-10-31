"use client";

import React from "react";
import { FileText, ShieldCheck, Volume2 } from "lucide-react";
import { ReviewCase } from "@/types";

interface ReviewReadinessCardProps {
  reviewCase: ReviewCase;
  languageCode: string;
  onReadDetails: (text: string, languageCode: string) => void;
}

function statusLabel(status: string) {
  return status.replace(/_/g, " ");
}

export function buildMaskedReviewReadback(reviewCase: ReviewCase): string {
  const checklist = reviewCase.packet.document_checklist
    .map((item) => `${item.label}: ${statusLabel(item.status)}.`)
    .join(" ");
  const requests = reviewCase.material_requests.map((request) => request.message).join(" ");
  return [
    `Sample human review status: ${reviewCase.readiness.outcome}.`,
    ...reviewCase.readiness.factors,
    checklist,
    requests,
  ].filter(Boolean).join(" ");
}

export function ReviewReadinessCard({ reviewCase, languageCode, onReadDetails }: ReviewReadinessCardProps) {
  const maskedPreviews = Object.entries(reviewCase.packet.masked_previews || {});

  return (
    <section className="card review-readiness" aria-label="Human review readiness">
      <div className="row-between review-title">
        <div>
          <p className="eyebrow">Sample human review</p>
          <h3>{reviewCase.readiness.outcome}</h3>
        </div>
        <ShieldCheck aria-hidden="true" />
      </div>
      <p>Only masked details and readiness statuses are shared in this demo.</p>
      <ul className="review-factors">
        {reviewCase.readiness.factors.map((factor) => <li key={factor}>{factor}</li>)}
      </ul>
      {maskedPreviews.length > 0 && <div className="masked-preview" aria-label="Masked details preview">
        {maskedPreviews.map(([key, value]) => <span key={key}>{key.replace(/_/g, " ")}: <strong>{value}</strong></span>)}
      </div>}
      <div className="review-checklist">
        {reviewCase.packet.document_checklist.map((item) => <div key={item.key}>
          <FileText aria-hidden="true" />
          <span><strong>{item.label}</strong><small>{item.purpose}</small></span>
          <em className={`badge ${item.status}`}>{statusLabel(item.status)}</em>
        </div>)}
      </div>
      {reviewCase.material_requests.length > 0 && <section className="review-request" aria-label="Material requested by reviewer">
        <strong>Action needed</strong>
        {reviewCase.material_requests.map((request) => <p key={`${request.material_key}-${request.created_at}`}>{request.message}</p>)}
      </section>}
      <button className="secondary full" onClick={() => onReadDetails(buildMaskedReviewReadback(reviewCase), languageCode)} aria-label="Read masked details">
        <Volume2 aria-hidden="true" /> Read details
      </button>
    </section>
  );
}
