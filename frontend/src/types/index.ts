export type FieldStatus = "missing" | "inferred" | "confirmed";

export type FieldSource =
  | "user_input"
  | "regex_parser"
  | "llm_extraction"
  | "rule_inference"
  | "default";

export interface StateField {
  name: string;
  value: any;
  status: FieldStatus;
  source: FieldSource;
  label?: string;
  unit?: string;
  prompt_question?: string;
}

export interface ConsentState {
  requested: boolean;
  granted: boolean;
  consent_text?: string;
  granted_at?: string;
  method?: string;
}

export interface MessageEntry {
  sender: "user" | "assistant" | "system";
  text: string;
  timestamp: string;
  audio_url?: string;
}

export interface CalculationResult {
  journey_id: string;
  sample_label: string;
  is_synthetic: boolean;
  disclosures: string[];
  metrics: Record<string, any>;
  schedule?: Array<Record<string, any>>;
  explanation?: string;
}

export interface JourneyState {
  session_id: string;
  journey_id: string;
  status: "collecting" | "calculated" | "awaiting_consent" | "submitted" | "rejected";
  fields: Record<string, StateField>;
  calculation?: CalculationResult | null;
  consent: ConsentState;
  messages: MessageEntry[];
  created_at: string;
  updated_at: string;
}

export interface TurnResponse {
  session_id: string;
  journey_id: string;
  reply_text: string;
  state: JourneyState;
  next_action: string;
  target_field?: string;
  results?: CalculationResult | null;
  calculation?: CalculationResult | null;
  citations: string[];
  audio_base64?: string | null;
}

export interface Product {
  journey_id: string;
  title: string;
  description: string;
  category: string;
  required_fields: string[];
  sample_label: string;
  disclosures: string[];
}

export interface Transaction {
  transaction_id: string;
  customer_id: string;
  account_id: string;
  amount: number;
  type: string;
  status: string;
  description: string;
  date: string;
  sample_label: string;
}

export interface Ticket {
  ticket_id: string;
  session_id: string;
  category: string;
  issue_description: string;
  resolution_plan?: string;
  status: string;
  created_at: string;
  sample_label: string;
}
