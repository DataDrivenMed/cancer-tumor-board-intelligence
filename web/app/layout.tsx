import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Cancer Tumor Board Intelligence",
  description:
    "A governed clinical decision-support workspace for multidisciplinary cancer case review.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
