import type { Metadata, Viewport } from 'next'
import { JetBrains_Mono } from 'next/font/google'
import { GeistPixelGrid } from 'geist/font/pixel'
import { ThemeProvider } from '@/components/theme-provider'

import './globals.css'

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
})

export const metadata: Metadata = {
  title: 'FORGE // Scaffold. Build. Ship. — The zero-config developer CLI',
  description:
    'FORGE is a zero-config command-line tool that scaffolds projects, runs deterministic builds, and ships to any target from a single binary. Read the docs: installation, quick start, guides, CLI reference, examples, and troubleshooting.',
  keywords: [
    'forge cli',
    'developer cli tool',
    'zero config build tool',
    'deterministic builds',
    'deploy cli',
    'project scaffolding',
    'ci cd cli',
    'developer documentation',
    'command line tool',
    'build and deploy',
  ],
  authors: [{ name: 'FORGE' }],
  creator: 'FORGE',
  publisher: 'FORGE',
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    title: 'FORGE // Scaffold. Build. Ship.',
    description:
      'A zero-config developer CLI that scaffolds projects, runs deterministic builds, and ships to any target. Full documentation included.',
    siteName: 'FORGE',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'FORGE // Scaffold. Build. Ship.',
    description:
      'A zero-config developer CLI: scaffold, build deterministically, and deploy to any target from a single binary.',
    creator: '@forge',
  },
  category: 'technology',
}

export const viewport: Viewport = {
  themeColor: '#F2F1EA',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className={`${jetbrainsMono.variable} ${GeistPixelGrid.variable}`} suppressHydrationWarning>
      <body className="font-mono antialiased">
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false} disableTransitionOnChange>
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}
