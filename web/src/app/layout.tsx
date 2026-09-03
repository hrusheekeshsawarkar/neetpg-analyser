import type { Metadata } from "next";
import { IBM_Plex_Sans, Sora } from "next/font/google";
import "./globals.css";
import { SiteHeader } from "@/components/SiteHeader";
import { DisclaimerBanner, DisclaimerFooter } from "@/components/Disclaimer";

const sora = Sora({
  variable: "--font-sora",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

const ibm = IBM_Plex_Sans({
  variable: "--font-ibm",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const siteUrl =
  process.env.NEXT_PUBLIC_SITE_URL ||
  (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : "http://localhost:3000");

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: "NEET PG Priorities",
  description:
    "High-yield topic priorities, due-for-return watchlists, and similar past questions from 15+ years of memory-based NEET PG / AIPGMEE papers.",
  openGraph: {
    title: "NEET PG Priorities — Next exam topic list",
    description:
      "Must-study and due-for-return topics from ~18k memory-based past questions. Not official NBE papers.",
    images: [{ url: "/api/og/priorities", width: 1200, height: 630 }],
  },
  twitter: {
    card: "summary_large_image",
    images: ["/api/og/priorities"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${sora.variable} ${ibm.variable} antialiased`}>
        <DisclaimerBanner />
        <SiteHeader />
        <main className="mx-auto min-h-[70vh] max-w-6xl px-4 py-8">{children}</main>
        <DisclaimerFooter />
      </body>
    </html>
  );
}
