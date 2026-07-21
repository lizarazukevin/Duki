import type { Metadata } from "next";
import { PRODUCT_NAME } from "@/lib/constants";
import "./globals.css";

export const metadata: Metadata = {
  title: PRODUCT_NAME,
  description: "Mood-aware planning with your rubber duck.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
