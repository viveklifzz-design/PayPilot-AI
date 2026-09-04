import type { Metadata } from 'next';
import './globals.css';
import Navbar from '@/components/Navbar';
import Sidebar from '@/components/Sidebar';

export const metadata: Metadata = {
  title: 'PayPilot AI — Autonomous Revenue Recovery Platform',
  description: 'Enterprise AI Revenue Recovery and Payment Failure Intelligence Platform',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-slate-50 text-slate-900 antialiased font-sans min-h-screen flex flex-col selection:bg-sky-100 selection:text-sky-900">
        <Navbar />
        <div className="flex flex-1">
          <Sidebar />
          <main className="flex-1 bg-slate-50 min-h-[calc(100vh-3.5rem)]">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
