"use client";

import { FormEvent, useEffect, useState } from "react";
import { Button, Card, Input, Label, Textarea } from "@/components/ui";
import { api } from "@/lib/api";

const STEPS = ["Business", "WhatsApp", "Calling", "Voice"] as const;

export default function OnboardingPage() {
  const [step, setStep] = useState(0);
  const [message, setMessage] = useState("");
  const [profile, setProfile] = useState({ display_name: "", description: "", industry: "" });
  const [whatsapp, setWhatsapp] = useState({
    waba_id: "",
    phone_number_id: "",
    verify_token: "",
    access_token: "",
    app_secret: "",
    webhook_path: "",
    access_token_masked: "",
  });
  const [calling, setCalling] = useState({
    business_number_e164: "",
    calling_enabled: false,
    sip_enabled: false,
    asterisk_endpoint: "",
    permission_message: "",
    is_ready: false,
  });
  const [providers, setProviders] = useState<Record<string, unknown>>({});

  useEffect(() => {
    api<typeof profile>("/api/settings/profile/").then(setProfile).catch(() => {});
    api<typeof whatsapp>("/api/settings/whatsapp/").then(setWhatsapp).catch(() => {});
    api<typeof calling>("/api/settings/whatsapp-calling/").then(setCalling).catch(() => {});
    api<Record<string, unknown>>("/api/settings/providers/").then(setProviders).catch(() => {});
  }, []);

  async function save(path: string, body: unknown) {
    setMessage("");
    await api(path, { method: "PUT", body: JSON.stringify(body) });
    setMessage("Saved.");
  }

  return (
    <div className="space-y-6">
      <h1 className="font-serif text-3xl">Connect the business</h1>
      <div className="flex gap-2 text-sm">
        {STEPS.map((label, index) => (
          <button
            key={label}
            type="button"
            onClick={() => setStep(index)}
            className={index === step ? "rounded-full bg-pine px-3 py-1 text-white" : "rounded-full bg-white px-3 py-1"}
          >
            {index + 1}. {label}
          </button>
        ))}
      </div>
      {message && <p className="text-sm text-pine">{message}</p>}

      {step === 0 && (
        <Card>
          <form
            className="space-y-3"
            onSubmit={(event: FormEvent) => {
              event.preventDefault();
              save("/api/settings/profile/", profile).then(() => setStep(1));
            }}
          >
            <div>
              <Label>Name customers will hear</Label>
              <Input value={profile.display_name} onChange={(e) => setProfile({ ...profile, display_name: e.target.value })} />
            </div>
            <div>
              <Label>Industry</Label>
              <Input value={profile.industry} onChange={(e) => setProfile({ ...profile, industry: e.target.value })} />
            </div>
            <div>
              <Label>What the business does</Label>
              <Textarea value={profile.description} onChange={(e) => setProfile({ ...profile, description: e.target.value })} />
            </div>
            <Button type="submit">Save and continue</Button>
          </form>
        </Card>
      )}

      {step === 1 && (
        <Card>
          <p className="mb-3 text-sm text-ink/70">
            In Meta, set the callback URL to your public host followed by <code>{whatsapp.webhook_path}</code>.
            Use the verify token below.
          </p>
          <form
            className="space-y-3"
            onSubmit={(event: FormEvent) => {
              event.preventDefault();
              save("/api/settings/whatsapp/", {
                waba_id: whatsapp.waba_id,
                phone_number_id: whatsapp.phone_number_id,
                verify_token: whatsapp.verify_token,
                access_token: whatsapp.access_token,
                app_secret: whatsapp.app_secret,
              }).then(() => setStep(2));
            }}
          >
            <div>
              <Label>WhatsApp Business account id</Label>
              <Input value={whatsapp.waba_id} onChange={(e) => setWhatsapp({ ...whatsapp, waba_id: e.target.value })} />
            </div>
            <div>
              <Label>Phone number id</Label>
              <Input value={whatsapp.phone_number_id} onChange={(e) => setWhatsapp({ ...whatsapp, phone_number_id: e.target.value })} />
            </div>
            <div>
              <Label>Verify token</Label>
              <Input value={whatsapp.verify_token} onChange={(e) => setWhatsapp({ ...whatsapp, verify_token: e.target.value })} />
            </div>
            <div>
              <Label>Access token {whatsapp.access_token_masked ? `(saved ${whatsapp.access_token_masked})` : ""}</Label>
              <Input type="password" value={whatsapp.access_token} onChange={(e) => setWhatsapp({ ...whatsapp, access_token: e.target.value })} placeholder="Leave blank to keep the saved token" />
            </div>
            <div>
              <Label>App secret</Label>
              <Input type="password" value={whatsapp.app_secret} onChange={(e) => setWhatsapp({ ...whatsapp, app_secret: e.target.value })} placeholder="Leave blank to keep the saved secret" />
            </div>
            <Button type="submit">Save and continue</Button>
          </form>
        </Card>
      )}

      {step === 2 && (
        <Card>
          <p className="mb-3 text-sm text-ink/70">
            Calls stay on WhatsApp. The customer has to tap Allow before the agent rings them. Meta only enables this on a
            Cloud API number whose daily messaging limit is at least 2,000 unique people.
          </p>
          <p className="mb-3 text-sm">
            Status: {calling.calling_enabled ? "calling on" : "calling off"}, {calling.sip_enabled ? "SIP on" : "SIP off"}
            {calling.is_ready ? ", ready" : ""}. Endpoint {calling.asterisk_endpoint || "—"}.
          </p>
          <form
            className="space-y-3"
            onSubmit={async (event: FormEvent) => {
              event.preventDefault();
              setMessage("");
              try {
                await save("/api/settings/whatsapp-calling/", {
                  business_number_e164: calling.business_number_e164,
                  permission_message: calling.permission_message,
                });
                const enabled = await api<typeof calling>("/api/settings/whatsapp-calling/enable/", {
                  method: "POST",
                  body: JSON.stringify({ business_number_e164: calling.business_number_e164 }),
                });
                setCalling(enabled);
                setMessage("WhatsApp calling enabled.");
                setStep(3);
              } catch (err) {
                setMessage(err instanceof Error ? err.message : "Could not enable calling");
              }
            }}
          >
            <div>
              <Label>WhatsApp business number</Label>
              <Input value={calling.business_number_e164} onChange={(e) => setCalling({ ...calling, business_number_e164: e.target.value })} placeholder="+919876543210" />
            </div>
            <div>
              <Label>Default permission message</Label>
              <Textarea value={calling.permission_message} onChange={(e) => setCalling({ ...calling, permission_message: e.target.value })} />
            </div>
            <Button type="submit">Enable WhatsApp calling</Button>
          </form>
        </Card>
      )}

      {step === 3 && (
        <Card className="space-y-4">
          <form
            className="space-y-3"
            onSubmit={(event: FormEvent) => {
              event.preventDefault();
              save("/api/settings/providers/", {
                tts_provider: providers.tts_provider || "sarvam",
                tts_voice: providers.tts_voice || "anushka",
                deepgram_api_key: providers.deepgram_api_key || "",
                sarvam_api_key: providers.sarvam_api_key || "",
                rumik_api_key: providers.rumik_api_key || "",
                cartesia_api_key: providers.cartesia_api_key || "",
                elevenlabs_api_key: providers.elevenlabs_api_key || "",
                dograh_api_key: providers.dograh_api_key || "",
              });
            }}
          >
            <div>
              <Label>Default voice</Label>
              <select
                className="h-10 w-full rounded-md border border-line bg-white px-3 text-sm"
                value={String(providers.tts_provider || "sarvam")}
                onChange={(e) => setProviders({ ...providers, tts_provider: e.target.value })}
              >
                <option value="sarvam">Sarvam Bulbul</option>
                <option value="rumik">Rumik</option>
                <option value="cartesia">Cartesia</option>
                <option value="elevenlabs">ElevenLabs</option>
              </select>
            </div>
            <div>
              <Label>Voice name</Label>
              <Input value={String(providers.tts_voice || "")} onChange={(e) => setProviders({ ...providers, tts_voice: e.target.value })} />
            </div>
            <div>
              <Label>Deepgram key (optional, otherwise the platform key is used)</Label>
              <Input type="password" value={String(providers.deepgram_api_key || "")} onChange={(e) => setProviders({ ...providers, deepgram_api_key: e.target.value })} />
            </div>
            <div>
              <Label>Voice provider key</Label>
              <Input type="password" value={String(providers.sarvam_api_key || "")} onChange={(e) => setProviders({ ...providers, sarvam_api_key: e.target.value })} />
            </div>
            <div>
              <Label>Dograh API key for this business</Label>
              <Input type="password" value={String(providers.dograh_api_key || "")} onChange={(e) => setProviders({ ...providers, dograh_api_key: e.target.value })} />
            </div>
            <Button type="submit">Save voice keys</Button>
          </form>
          <pre className="overflow-auto rounded-md bg-ink p-3 text-xs text-paper">
            {JSON.stringify(providers.dograh_configuration || {}, null, 2)}
          </pre>
          <p className="text-sm text-ink/70">Paste this into Dograh under model configuration. The language model URL is the context guard.</p>
        </Card>
      )}
    </div>
  );
}
