"use client";

import { FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Button, Card, Input, Label, Textarea } from "@/components/ui";
import { api, type CallRow, type Campaign } from "@/lib/api";

const EMPTY: Campaign = {
  id: "",
  name: "",
  language: "hinglish",
  is_default: false,
  is_active: true,
  dograh_workflow_uuid: "",
  dograh_trigger_uuid: "",
  permission_message: "",
  tts_provider: "",
  tts_voice: "",
  agent_name: "Priya",
  goal: "",
  offer_details: "",
  prices: [],
  faqs: [],
  allowed_topics: [],
  forbidden_topics: [],
  competitors: [],
  handoff_message: "",
  keywords: [],
};

function lines(value: string[]) {
  return value.join("\n");
}

function split(value: string) {
  return value.split("\n").map((item) => item.trim()).filter(Boolean);
}

export default function CampaignEditorPage() {
  const params = useParams<{ id: string }>();
  const [campaign, setCampaign] = useState<Campaign>(EMPTY);
  const [prompt, setPrompt] = useState("");
  const [nodePrompt, setNodePrompt] = useState("");
  const [agent, setAgent] = useState({
    role: "",
    persona: "",
    greeting: "",
    closing_line: "",
    allow_interrupt: true,
    max_call_seconds: 300,
    dograh_workflow_id: null as number | null,
    dograh_workflow_uuid: "",
    publish_error: "",
  });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [testPhone, setTestPhone] = useState("");

  useEffect(() => {
    api<Campaign>(`/api/campaigns/${params.id}/`).then(setCampaign).catch((err) => setError(err.message));
    api<typeof agent>(`/api/campaigns/${params.id}/agent/`).then(setAgent).catch(() => {});
  }, [params.id]);

  async function save(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      const saved = await api<Campaign>(`/api/campaigns/${params.id}/`, {
        method: "PATCH",
        body: JSON.stringify(campaign),
      });
      setCampaign(saved);
      setMessage("Saved. The next call uses this context.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save");
    }
  }

  async function publishAgent() {
    setError("");
    try {
      await api(`/api/campaigns/${params.id}/agent/`, { method: "PUT", body: JSON.stringify(agent) });
      const published = await api<typeof agent>(`/api/campaigns/${params.id}/agent/publish/`, { method: "POST" });
      setAgent(published);
      setMessage("Agent published to Dograh.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not publish");
    }
  }

  async function preview() {
    const result = await api<{ system_prompt: string; dograh_node_prompt: string }>(
      `/api/campaigns/${params.id}/preview-prompt/`,
      { method: "POST" },
    );
    setPrompt(result.system_prompt);
    setNodePrompt(result.dograh_node_prompt);
  }

  async function testCall() {
    setError("");
    try {
      const call = await api<CallRow>(`/api/campaigns/${params.id}/test-call/`, {
        method: "POST",
        body: JSON.stringify({ phone: testPhone }),
      });
      setMessage(`Call is ${call.status}${call.skip_reason ? ` (${call.skip_reason})` : ""}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Test call failed");
    }
  }

  return (
    <form className="space-y-6" onSubmit={save}>
      <div className="flex items-end justify-between gap-4">
        <div className="flex-1">
          <Label>Campaign</Label>
          <Input value={campaign.name} onChange={(e) => setCampaign({ ...campaign, name: e.target.value })} />
        </div>
        <Button type="submit">Save context</Button>
      </div>
      {message && <p className="text-sm text-pine">{message}</p>}
      {error && <p className="text-sm text-red-700">{error}</p>}

      <Card className="grid gap-3 md:grid-cols-2">
        <div>
          <Label>Language</Label>
          <select className="h-10 w-full rounded-md border border-line bg-white px-3 text-sm" value={campaign.language} onChange={(e) => setCampaign({ ...campaign, language: e.target.value as Campaign["language"] })}>
            <option value="hi">Hindi</option>
            <option value="en_in">Indian English</option>
            <option value="hinglish">Hinglish</option>
          </select>
        </div>
        <div>
          <Label>Agent name</Label>
          <Input value={campaign.agent_name} onChange={(e) => setCampaign({ ...campaign, agent_name: e.target.value })} />
        </div>
            <div>
              <Label>Dograh workflow id</Label>
              <Input value={agent.dograh_workflow_uuid || campaign.dograh_workflow_uuid} readOnly />
            </div>
            <div>
              <Label>Permission request shown in WhatsApp</Label>
              <Input value={campaign.permission_message} onChange={(e) => setCampaign({ ...campaign, permission_message: e.target.value })} />
            </div>
        <label className="flex items-center gap-2 text-sm md:col-span-2">
          <input type="checkbox" checked={campaign.is_default} onChange={(e) => setCampaign({ ...campaign, is_default: e.target.checked })} />
          Use this campaign when a reply does not match a button or keyword
        </label>
      </Card>

      <Card className="space-y-3">
        <h2 className="font-serif text-xl">Agent</h2>
        <div className="grid gap-3 md:grid-cols-2">
          <div>
            <Label>Role</Label>
            <Input value={agent.role} onChange={(e) => setAgent({ ...agent, role: e.target.value })} />
          </div>
          <div>
            <Label>Maximum call length (seconds)</Label>
            <Input type="number" value={agent.max_call_seconds} onChange={(e) => setAgent({ ...agent, max_call_seconds: Number(e.target.value) })} />
          </div>
        </div>
        <div>
          <Label>Persona</Label>
          <Textarea value={agent.persona} onChange={(e) => setAgent({ ...agent, persona: e.target.value })} />
        </div>
        <div>
          <Label>Greeting</Label>
          <Textarea value={agent.greeting} onChange={(e) => setAgent({ ...agent, greeting: e.target.value })} />
        </div>
        <div>
          <Label>Closing line</Label>
          <Textarea value={agent.closing_line} onChange={(e) => setAgent({ ...agent, closing_line: e.target.value })} />
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={agent.allow_interrupt} onChange={(e) => setAgent({ ...agent, allow_interrupt: e.target.checked })} />
          Allow the customer to interrupt
        </label>
        <Button type="button" onClick={publishAgent}>Publish to Dograh</Button>
        {agent.publish_error && <p className="text-sm text-red-700">{agent.publish_error}</p>}
      </Card>

      <Card className="space-y-3">
        <h2 className="font-serif text-xl">What the agent is allowed to say</h2>
        <div>
          <Label>Goal of the call</Label>
          <Textarea value={campaign.goal} onChange={(e) => setCampaign({ ...campaign, goal: e.target.value })} />
        </div>
        <div>
          <Label>Offer</Label>
          <Textarea value={campaign.offer_details} onChange={(e) => setCampaign({ ...campaign, offer_details: e.target.value })} />
        </div>
        <div>
          <Label>Prices, one per line as Label | amount</Label>
          <Textarea
            value={campaign.prices.map((price) => `${price.label} | ${price.amount}`).join("\n")}
            onChange={(e) =>
              setCampaign({
                ...campaign,
                prices: split(e.target.value).map((line) => {
                  const [label, amount] = line.split("|");
                  return { label: (label || "").trim(), amount: (amount || "").trim() };
                }),
              })
            }
          />
        </div>
        <div>
          <Label>FAQs, one per line as Question | answer</Label>
          <Textarea
            value={campaign.faqs.map((faq) => `${faq.question} | ${faq.answer}`).join("\n")}
            onChange={(e) =>
              setCampaign({
                ...campaign,
                faqs: split(e.target.value).map((line) => {
                  const [question, answer] = line.split("|");
                  return { question: (question || "").trim(), answer: (answer || "").trim() };
                }),
              })
            }
          />
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <div>
            <Label>Allowed topics, one per line</Label>
            <Textarea value={lines(campaign.allowed_topics)} onChange={(e) => setCampaign({ ...campaign, allowed_topics: split(e.target.value) })} />
          </div>
          <div>
            <Label>Forbidden topics, one per line</Label>
            <Textarea value={lines(campaign.forbidden_topics)} onChange={(e) => setCampaign({ ...campaign, forbidden_topics: split(e.target.value) })} />
          </div>
        </div>
        <div>
          <Label>Competitors the agent must never name, one per line</Label>
          <Textarea value={lines(campaign.competitors)} onChange={(e) => setCampaign({ ...campaign, competitors: split(e.target.value) })} />
        </div>
        <div>
          <Label>Handoff line (said when the answer is not in the facts)</Label>
          <Textarea value={campaign.handoff_message} onChange={(e) => setCampaign({ ...campaign, handoff_message: e.target.value })} />
        </div>
        <div>
          <Label>Keywords that route a reply to this campaign, one per line</Label>
          <Textarea value={lines(campaign.keywords)} onChange={(e) => setCampaign({ ...campaign, keywords: split(e.target.value) })} />
        </div>
      </Card>

      <Card className="space-y-3">
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" onClick={preview}>Preview prompt</Button>
        </div>
        {nodePrompt && (
          <>
            <p className="text-sm text-ink/70">Paste this, and only this, into the Dograh agent node. The facts are added on the server.</p>
            <pre className="whitespace-pre-wrap rounded-md bg-paper p-3 text-sm">{nodePrompt}</pre>
          </>
        )}
        {prompt && <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-md bg-ink p-3 text-xs text-paper">{prompt}</pre>}
        <div className="flex flex-wrap items-end gap-2">
          <div>
            <Label>Call this mobile through Plivo</Label>
            <Input value={testPhone} onChange={(e) => setTestPhone(e.target.value)} placeholder="9876543210" />
          </div>
          <Button type="button" onClick={testCall}>Place test call</Button>
        </div>
      </Card>
    </form>
  );
}
