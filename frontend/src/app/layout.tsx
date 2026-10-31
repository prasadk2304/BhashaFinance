import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BhashaFinance AI | Voice-First Multilingual Assistant",
  description: "Voice-first multilingual journey assistant for Paytm lending and fintech.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased bg-[#F5F7FA] text-[#1B2A41] min-h-screen">
        {children}
      </body>
    </html>
  );
}

