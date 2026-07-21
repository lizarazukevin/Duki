import type { Metadata } from "next";
import "@fontsource-variable/mona-sans/standard.css";
import { PRODUCT_NAME } from "@/lib/constants";
import "./globals.css";

export const metadata: Metadata = {
  title: `${PRODUCT_NAME} — Plan around your actual energy`,
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
