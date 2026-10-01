import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "Caller",
  description: "Call customers who reply to a WhatsApp campaign.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        <link rel="stylesheet" href="/styles.css" />
        {children}
      </body>
    </html>
  );
}
