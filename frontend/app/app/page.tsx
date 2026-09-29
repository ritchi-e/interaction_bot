"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Card } from "@/components/ui";
import { api, rows, type CallRow, type Campaign } from "@/lib/api";

type Alert = { id: number; message: string; created_at: string };

export default function DashboardPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [calls, setCalls] = useState<CallRow[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);

  useEffect(() => {
    api<Campaign[] | { results: Campaign[] }>("/api/campaigns/").then((data) => setCampaigns(rows(data))).catch(() => {});
    api<CallRow[] | { results: CallRow[] }>("/api/calls/").then((data) => setCalls(rows(data))).catch(() => {});
    api<Alert[] | { results: Alert[] }>("/api/handoffs/").then((data) => setAlerts(rows(data))).catch(() => {});
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-3xl">Today</h1>
        <p className="text-ink/70">Replies become calls. Anything the agent cannot answer becomes a handoff.</p>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <p className="text-sm text-ink/60">Campaigns</p>
          <p className="font-serif text-4xl">{campaigns.length}</p>
        </Card>
        <Card>
          <p className="text-sm text-ink/60">Calls</p>
          <p className="font-serif text-4xl">{calls.length}</p>
        </Card>
        <Card>
          <p className="text-sm text-ink/60">People waiting on a human</p>
          <p className="font-serif text-4xl">{alerts.length}</p>
        </Card>
      </div>
      <Card>
        <h2 className="font-serif text-xl">Handoffs</h2>
        {alerts.length === 0 && <p className="mt-2 text-sm text-ink/60">None right now.</p>}
        <ul className="mt-3 space-y-2 text-sm">
          {alerts.map((alert) => (
            <li key={alert.id} className="rounded-md bg-paper px-3 py-2">
              {alert.message}
            </li>
          ))}
        </ul>
        <Link href="/app/campaigns" className="mt-4 inline-block text-sm text-pine">
          Set up a campaign
        </Link>
      </Card>
    </div>
  );
}
