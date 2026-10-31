import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ReviewReadinessCard } from "./ReviewReadinessCard";

const reviewCase = {
  review_case_id: "REV-1234",
  session_id: "session-1234",
  journey_id: "personal_loan",
  status: "material_requested",
  packet: {
    document_checklist: [
      { key: "pan", label: "PAN availability", purpose: "Demo KYC readiness", status: "ready", required: true },
      { key: "bank_statement_6_months", label: "Six-month bank statement", purpose: "Income evidence", status: "requested", required: true },
    ],
  },
  readiness: { outcome: "Needs supporting material", factors: ["Supporting material still needed: Six-month bank statement."] },
  created_at: "2026-10-31T00:00:00Z",
  material_requests: [
    { material_key: "bank_statement_6_months", message: "Please mark the six-month statement as ready.", created_at: "2026-10-31T00:00:00Z" },
  ],
};

describe("ReviewReadinessCard", () => {
  afterEach(cleanup);

  it("renders only the masked packet and exposes a reviewer material request", () => {
    render(<ReviewReadinessCard reviewCase={reviewCase} languageCode="mr-IN" onReadDetails={vi.fn()} />);

    expect(screen.getByText("Needs supporting material")).toBeTruthy();
    expect(screen.getByText("Please mark the six-month statement as ready.")).toBeTruthy();
    expect(screen.queryByText("ABCDE1234F")).toBeNull();
  });

  it("sends only the masked review summary to read-back in the selected language", () => {
    const onReadDetails = vi.fn();
    render(<ReviewReadinessCard reviewCase={reviewCase} languageCode="hi-IN" onReadDetails={onReadDetails} />);

    fireEvent.click(screen.getByRole("button", { name: "Read masked details" }));

    expect(onReadDetails).toHaveBeenCalledWith(expect.not.stringContaining("ABCDE1234F"), "hi-IN");
    expect(onReadDetails.mock.calls[0][0]).toContain("Six-month bank statement");
  });
});

