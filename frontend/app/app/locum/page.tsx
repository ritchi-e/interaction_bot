"use client";

import { useCallback, useEffect, useState } from "react";
import { api, rows, type LocumInterestRow } from "@/lib/api";

const LOCUM_CAMPAIGN_ID = "4e377637-2559-4707-9963-b13652dc7f96";

export default function LocumPage() {
  const [items, setItems] = useState<LocumInterestRow[]>([]);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState("");

  const load = useCallback(() => {
    api<LocumInterestRow[] | { results: LocumInterestRow[] }>("/api/locum-interests/").then((data) =>
      setItems(rows(data))
    );
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function syncLeads() {
    setSyncing(true);
    setMessage("");
    try {
      const result = await api<{ queued: number }>(`/api/campaigns/${LOCUM_CAMPAIGN_ID}/sync-locum/`, {
        method: "POST",
        body: "{}",
      });
      setMessage(`Queued ${result.queued} call(s) from the partner/placeholder API.`);
      load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-serif text-3xl">Locum interest</h1>
          <p className="text-sm text-ink/70">
            Doctors called about a Dr. Locum job. Interest is saved when they answer yes or no on the call.
          </p>
        </div>
        <button
          type="button"
          onClick={syncLeads}
          disabled={syncing}
          className="rounded-lg bg-pine px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {syncing ? "Syncing…" : "Sync partner leads"}
        </button>
      </div>
      {message ? <p className="mb-4 text-sm text-ink/70">{message}</p> : null}
      <div className="overflow-hidden rounded-xl border border-line bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-paper text-ink/60">
            <tr>
              <th className="px-4 py-2 font-medium">Phone</th>
              <th className="px-4 py-2 font-medium">Doctor</th>
              <th className="px-4 py-2 font-medium">Job</th>
              <th className="px-4 py-2 font-medium">Location</th>
              <th className="px-4 py-2 font-medium">Interested</th>
              <th className="px-4 py-2 font-medium">Campaign</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-t border-line">
                <td className="px-4 py-2">{item.phone_e164}</td>
                <td className="px-4 py-2">{item.doctor_name || "—"}</td>
                <td className="px-4 py-2">
                  <div>{item.job_title || item.job_id || "—"}</div>
                  <div className="text-ink/50">{item.job_facility}</div>
                </td>
                <td className="px-4 py-2">{item.job_location || "—"}</td>
                <td className="px-4 py-2">{item.interested}</td>
                <td className="px-4 py-2">{item.campaign_name}</td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-ink/50" colSpan={6}>
                  No locum calls recorded yet. Sync leads or place a test call on the locum campaign.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
