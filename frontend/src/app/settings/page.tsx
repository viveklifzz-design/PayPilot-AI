'use client';

import { useState } from 'react';
import Navbar from '@/components/Navbar';
import SettingsModal, { SettingsTab } from '@/components/SettingsModal';

export default function SettingsPage() {
  const [isOpen, setIsOpen] = useState(true);
  const [activeTab, setActiveTab] = useState<SettingsTab>('GENERAL');

  return (
    <div className="min-h-screen bg-slate-950 text-white flex flex-col font-sans">
      <Navbar />
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
          <h1 className="text-xl font-extrabold tracking-tight">PayPilot Settings</h1>
          <p className="text-xs text-slate-400">Configure merchant identity, AI voice preferences, notifications, security policy gate, and integrations.</p>
          <button
            onClick={() => setIsOpen(true)}
            className="px-4 py-2 bg-sky-500 hover:bg-sky-400 text-white font-bold text-xs rounded-xl transition-colors"
          >
            Open Settings Panel
          </button>
        </div>

        <SettingsModal
          isOpen={isOpen}
          onClose={() => setIsOpen(false)}
          initialTab={activeTab}
        />
      </main>
    </div>
  );
}
