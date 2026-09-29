"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Card } from "@/components/ui";
import { api, type CallRow } from "@/lib/api";

export default function CallDetailPage() {
  const params = useParams<{ id: string }>();
  const [call, setCall] = useState<CallRow | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<CallRow>(`/api/calls/${params.id}/`).then(setCall).catch((err) => setError(err.message));
  }, [params.id]);

  if (error) return <p className="text-red-700">{error}</p>;
  if (!call) return <p>Loading…</p>;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="font-serif text-3xl">{call.lead_name || call.phone_e164}</h1>
        <p className="text-sm text-ink/70">
          {call.campaign_name} · {call.status}
          {call.disposition ? ` · ${call.disposition}` : ""}
        </p>
      </div>
      {call.attempts.map((attempt) => (
        <Card key={attempt.id}>
          <p className="text-sm text-ink/60">Run {attempt.dograh_run_id || "—"}</p>
          <pre className="mt-2 whitespace-pre-wrap text-sm">{attempt.transcript || "No transcript yet."}</pre>
          {attempt.recording_url && (
            <a className="mt-2 inline-block text-sm text-pine" href={attempt.recording_url}>
              Recording
            </a>
          )}
          {attempt.error && <p className="mt-2 text-sm text-red-700">{attempt.error}</p>}
        </Card>
      ))}
      <Card>
        <h2 className="font-serif text-xl">Context blocks</h2>
        {call.violations.length === 0 && <p className="mt-2 text-sm text-ink/60">None on this call.</p>}
        <ul className="mt-2 space-y-2 text-sm">
          {call.violations.map((violation) => (
            <li key={violation.id} className="rounded-md bg-paper px-3 py-2">
              <span className="font-medium">{violation.reason}.</span> {violation.sentence}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
