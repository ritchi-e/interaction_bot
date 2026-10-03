"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { Button, Card, Input, Label } from "@/components/ui";
import { api, rows, type Campaign } from "@/lib/api";

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [name, setName] = useState("");
  const [language, setLanguage] = useState("hi");
  const [error, setError] = useState("");

  function load() {
    api<Campaign[] | { results: Campaign[] }>("/api/campaigns/").then((data) => setCampaigns(rows(data)));
  }

  useEffect(() => {
    load();
  }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api("/api/campaigns/", {
        method: "POST",
        body: JSON.stringify({ name, language, is_default: campaigns.length === 0 }),
      });
      setName("");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the campaign");
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="font-serif text-3xl">Campaigns</h1>
      <Card>
        <form className="flex flex-wrap items-end gap-3" onSubmit={create}>
          <div className="min-w-64 flex-1">
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div>
            <Label>Language</Label>
            <select className="h-10 rounded-md border border-line bg-white px-3 text-sm" value={language} onChange={(e) => setLanguage(e.target.value)}>
              <option value="hi">Hindi</option>
              <option value="en_in">Indian English</option>
            </select>
          </div>
          <Button type="submit">Create</Button>
        </form>
        {error && <p className="mt-2 text-sm text-red-700">{error}</p>}
      </Card>
      <div className="grid gap-3">
        {campaigns.map((campaign) => (
          <Link key={campaign.id} href={`/app/campaigns/${campaign.id}`} className="block">
            <Card className="flex items-center justify-between hover:border-pine">
              <div>
                <p className="font-medium">{campaign.name}</p>
                <p className="text-sm text-ink/60">{campaign.language}{campaign.is_default ? " · default" : ""}</p>
              </div>
              <span className="text-sm text-pine">Edit context</span>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
