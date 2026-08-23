import type { Metadata, Viewport } from 'next'
import { GeistPixelGrid } from 'geist/font/pixel'
import { ThemeProvider } from '@/components/theme-provider'
import { BackgroundSnippets } from '@/components/ui/background-snippets'
import './globals.css'

export const metadata: Metadata = {
  title: 'EveryCli — Describe the task. Get the command.',
  description: 'EveryCli is an AI-powered command-line assistant that turns plain-language intent into commands for Git, Docker, and Linux.',
  keywords: ['everycli', 'natural language cli', 'git assistant', 'docker assistant', 'developer documentation'],
  authors: [{ name: 'EveryCli' }],
  creator: 'EveryCli',
  publisher: 'EveryCli',
  openGraph: {
    type: 'website',
    locale: 'en_US',
    title: 'EveryCli — Describe the task. Get the command.',
    description: 'An AI-powered command-line assistant for Git, Docker, and Linux.',
    siteName: 'EveryCli',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'EveryCli — Describe the task. Get the command.',
    description: 'An AI-powered command-line assistant for Git, Docker, and Linux.',
  },
}

export const viewport: Viewport = {
  themeColor: '#0a0908',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={GeistPixelGrid.variable} suppressHydrationWarning>
      <body className="relative min-h-screen font-mono antialiased">
        <BackgroundSnippets />
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false} disableTransitionOnChange>
          <div className="relative z-10">{children}</div>
        </ThemeProvider>
      </body>
    </html>
  )
}
