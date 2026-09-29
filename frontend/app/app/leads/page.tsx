"use client";

import { useEffect, useState } from "react";
import { api, rows } from "@/lib/api";

type Lead = { id: string; name: string; phone_e164: string; campaign_name: string | null; created_at: string };

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);

  useEffect(() => {
    api<Lead[] | { results: Lead[] }>("/api/leads/").then((data) => setLeads(rows(data)));
  }, []);

  return (
    <div>
      <h1 className="font-serif text-3xl">Leads</h1>
      <p className="mb-4 text-sm text-ink/70">People who replied on WhatsApp.</p>
      <div className="overflow-hidden rounded-xl border border-line bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-paper text-ink/60">
            <tr>
              <th className="px-4 py-2 font-medium">Name</th>
              <th className="px-4 py-2 font-medium">Phone</th>
              <th className="px-4 py-2 font-medium">Campaign</th>
            </tr>
          </thead>
          <tbody>
            {leads.map((lead) => (
              <tr key={lead.id} className="border-t border-line">
                <td className="px-4 py-2">{lead.name || "—"}</td>
                <td className="px-4 py-2">{lead.phone_e164}</td>
                <td className="px-4 py-2">{lead.campaign_name || "—"}</td>
              </tr>
            ))}
            {leads.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-ink/50" colSpan={3}>No replies yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
