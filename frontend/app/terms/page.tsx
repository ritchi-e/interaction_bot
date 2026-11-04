import Link from "next/link";

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-phonwa-snow px-5 py-16 text-phonwa-ink md:px-8">
      <div className="mx-auto max-w-3xl">
        <Link href="/" className="text-sm font-semibold text-phonwa-teal hover:underline">
          ← Phonwa
        </Link>
        <h1 className="mt-6 font-display text-4xl font-bold tracking-tight">Terms of Service</h1>
        <p className="mt-6 text-base leading-relaxed text-phonwa-mute">
          By using Phonwa you agree to use the platform lawfully, obtain required caller consent for voice AI and
          recording where applicable, and keep account credentials secure. Service availability and support levels are
          defined in your order form or enterprise agreement.
        </p>
        <p className="mt-4 text-sm text-phonwa-mute">
          This page is a product placeholder—replace with counsel-approved legal copy before launch.
        </p>
      </div>
    </main>
  );
}
