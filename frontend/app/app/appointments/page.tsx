"use client";

import { useEffect, useState } from "react";
import { api, rows, type AppointmentRow } from "@/lib/api";

export default function AppointmentsPage() {
  const [items, setItems] = useState<AppointmentRow[]>([]);

  useEffect(() => {
    api<AppointmentRow[] | { results: AppointmentRow[] }>("/api/appointments/").then((data) => setItems(rows(data)));
  }, []);

  return (
    <div>
      <h1 className="font-serif text-3xl">Appointments</h1>
      <p className="mb-4 text-sm text-ink/70">Bookings saved from calls. A row appears here after the slot is stored.</p>
      <div className="overflow-hidden rounded-xl border border-line bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-paper text-ink/60">
            <tr>
              <th className="px-4 py-2 font-medium">Name</th>
              <th className="px-4 py-2 font-medium">Date</th>
              <th className="px-4 py-2 font-medium">Time</th>
              <th className="px-4 py-2 font-medium">Campaign</th>
              <th className="px-4 py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-t border-line">
                <td className="px-4 py-2">{item.caller_name}</td>
                <td className="px-4 py-2">{item.appointment_date}</td>
                <td className="px-4 py-2">{item.appointment_time.slice(0, 5)}</td>
                <td className="px-4 py-2">{item.campaign_name}</td>
                <td className="px-4 py-2">{item.status}</td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-ink/50" colSpan={5}>No appointments yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
