export type User = {
  id: number;
  email: string;
  organisation: string;
  organisation_name: string;
  organisation_slug: string;
};

export type Campaign = {
  id: string;
  name: string;
  language: "hi" | "en_in" | "hinglish";
  is_default: boolean;
  is_active: boolean;
  dograh_workflow_uuid: string;
  dograh_trigger_uuid: string;
  permission_message: string;
  tts_provider: string;
  tts_voice: string;
  agent_name: string;
  goal: string;
  offer_details: string;
  prices: { label: string; amount: string }[];
  faqs: { question: string; answer: string }[];
  allowed_topics: string[];
  forbidden_topics: string[];
  competitors: string[];
  handoff_message: string;
  keywords: string[];
};

export type CallRow = {
  id: string;
  status: string;
  skip_reason: string;
  scheduled_for: string | null;
  disposition: string;
  is_test: boolean;
  lead_name: string;
  phone_e164: string;
  campaign: string;
  campaign_name: string;
  created_at: string;
  attempts: {
    id: number;
    dograh_run_id: string;
    status: string;
    transcript: string;
    recording_url: string;
    error: string;
  }[];
  violations: { id: number; sentence: string; reason: string; created_at: string }[];
};

function errorMessage(payload: unknown, fallback: string) {
  const lines: string[] = [];
  const walk = (value: unknown) => {
    if (typeof value === "string" && value) lines.push(value);
    else if (Array.isArray(value)) value.forEach(walk);
    else if (value && typeof value === "object") Object.values(value).forEach(walk);
  };
  walk(payload);
  return lines[0] ?? fallback;
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window === "undefined" ? null : localStorage.getItem("token");
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Token ${token}`);
  const response = await fetch(path, { ...options, headers });
  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;
  if (response.status === 401 && typeof window !== "undefined") {
    localStorage.removeItem("token");
    if (window.location.pathname !== "/") window.location.href = "/";
  }
  if (!response.ok) throw new Error(errorMessage(payload, "Request failed"));
  return payload as T;
}

export function rows<T>(payload: T[] | { results: T[] }): T[] {
  return Array.isArray(payload) ? payload : payload.results;
}
