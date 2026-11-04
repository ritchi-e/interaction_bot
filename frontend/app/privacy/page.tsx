import Link from "next/link";

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-phonwa-snow px-5 py-16 text-phonwa-ink md:px-8">
      <div className="mx-auto max-w-3xl">
        <Link href="/" className="text-sm font-semibold text-phonwa-teal hover:underline">
          ← Phonwa
        </Link>
        <h1 className="mt-6 font-display text-4xl font-bold tracking-tight">Privacy Policy</h1>
        <p id="processing" className="mt-6 scroll-mt-24 text-base leading-relaxed text-phonwa-mute">
          Phonwa processes call audio and related metadata to deliver AI voice agents. We retain recordings and
          transcripts only as needed for the service you configure, apply access controls for enterprise customers, and
          do not sell personal voice data. Contact us for a Data Processing Agreement or deletion requests.
        </p>
        <p className="mt-4 text-sm text-phonwa-mute">
          This page is a product placeholder—replace with counsel-approved legal copy before launch.
        </p>
      </div>
    </main>
  );
}
