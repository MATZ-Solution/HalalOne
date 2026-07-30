import type { Metadata } from "next";
import {
  Geist,
  Geist_Mono,
  Roboto,
  Inter,
  Space_Grotesk,
  Manrope,
  DM_Sans,
  Raleway,
  Plus_Jakarta_Sans,
} from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const roboto = Roboto({
  variable: "--font-roboto",
  subsets: ["latin"],
  weight: ["400", "500", "700"],
});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
});

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
});

const dmSans = DM_Sans({
  variable: "--font-dm-sans",
  subsets: ["latin"],
});

const raleway = Raleway({
  variable: "--font-raleway",
  subsets: ["latin"],
});

const plusJakartaSans = Plus_Jakarta_Sans({
  variable: "--font-plus-jakarta-sans",
  subsets: ["latin"],
});

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL), // makes image paths absolute
  title: 'HalalOne — Every halal answer, one platform',
  description: "Verify products, decode ingredients, and search the global halal repository with AI that cites its sources.",
  openGraph: {
    type: 'website',
    url: SITE_URL,
    siteName: 'HalalOne',
    title: 'HalalOne — Every halal answer, one platform',
    description: "Verify products, decode ingredients, and search the global halal repository with AI that cites its sources.",
    images: [{ url: '/og-rounded.png', width: 1200, height: 630, alt: 'HalalOne' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'HalalOne — Every halal answer, one platform',
    description: "Verify products, decode ingredients, and search the global halal repository.",
    images: ['/og-rounded.png'],
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${roboto.variable} ${inter.variable} ${spaceGrotesk.variable} ${manrope.variable} ${dmSans.variable} ${raleway.variable} ${plusJakartaSans.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
