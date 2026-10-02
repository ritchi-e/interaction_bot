"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, rows, type CallRow } from "@/lib/api";
import { endedByLabel, formatDuration, latestAttempt } from "@/lib/calls";

export default function CallsPage() {
  const [calls, setCalls] = useState<CallRow[]>([]);

  useEffect(() => {
    api<CallRow[] | { results: CallRow[] }>("/api/calls/").then((data) => setCalls(rows(data)));
  }, []);

  return (
    <div>
      <h1 className="font-serif text-3xl">Calls</h1>
      <p className="mb-4 text-sm text-ink/70">Status, and whether the call had to be handed to a person.</p>
      <div className="overflow-hidden rounded-xl border border-line bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-paper text-ink/60">
            <tr>
              <th className="px-4 py-2 font-medium">When</th>
              <th className="px-4 py-2 font-medium">Person</th>
              <th className="px-4 py-2 font-medium">Campaign</th>
              <th className="px-4 py-2 font-medium">Length</th>
              <th className="px-4 py-2 font-medium">Hung up by</th>
              <th className="px-4 py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {calls.map((call) => (
              <tr key={call.id} className="border-t border-line">
                <td className="px-4 py-2">{new Date(call.created_at).toLocaleString("en-IN")}</td>
                <td className="px-4 py-2">
                  <Link href={`/app/calls/${call.id}`} className="text-pine">
                    {call.lead_name || call.phone_e164}
                  </Link>
                </td>
                <td className="px-4 py-2">{call.campaign_name}</td>
                <td className="px-4 py-2">{formatDuration(latestAttempt(call.attempts)?.duration_seconds)}</td>
                <td className="px-4 py-2">{endedByLabel(latestAttempt(call.attempts))}</td>
                <td className="px-4 py-2">
                  {call.status}
                  {call.skip_reason ? ` · ${call.skip_reason}` : ""}
                  {call.disposition ? ` · ${call.disposition}` : ""}
                </td>
              </tr>
            ))}
            {calls.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-ink/50" colSpan={6}>No calls yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
