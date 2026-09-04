'use client';

import { useState, useEffect } from 'react';
import { 
  X, 
  Building2, 
  Mic, 
  Bell, 
  ShieldCheck, 
  Cpu, 
  Palette, 
  Check, 
  RefreshCw, 
  Trash2, 
  Lock, 
  Key,
  Globe,
  Sliders,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';

export type SettingsTab = 'GENERAL' | 'VOICE' | 'NOTIFICATIONS' | 'SECURITY' | 'INTEGRATIONS' | 'APPEARANCE';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialTab?: SettingsTab;
}

export interface PayPilotSettings {
  // General
  merchantName: string;
  email: string;
  phone: string;
  timezone: string;
  currency: string;

  // Voice Assistant
  voiceEnabled: boolean;
  femaleVoicePreference: boolean;
  language: 'AUTO' | 'ENGLISH' | 'HINDI' | 'HINGLISH';
  speechSpeed: number;
  responseStyle: 'PROFESSIONAL' | 'FRIENDLY' | 'CONCISE';
  autoSpeakResponse: boolean;

  // Notifications
  failedPaymentAlerts: boolean;
  paymentReceivedAlerts: boolean;
  paymentRecoveredAlerts: boolean;
  overdueInvoiceAlerts: boolean;
  b2bReceivableAlerts: boolean;
  highRiskAlerts: boolean;
  humanEscalationAlerts: boolean;

  // Security
  sessionTimeout: string;
  confirmFinancialActions: boolean;
  humanApprovalHighRisk: boolean;

  // Appearance
  theme: 'DARK' | 'LIGHT' | 'SYSTEM';
  density: 'COMPACT' | 'COMFORTABLE';
  animations: boolean;
  refreshInterval: string;
}

const DEFAULT_SETTINGS: PayPilotSettings = {
  merchantName: 'Main Merchant Account',
  email: 'merchant@paypilot.ai',
  phone: '+91 98765 43210',
  timezone: 'Asia/Kolkata (IST)',
  currency: 'INR (₹)',

  voiceEnabled: true,
  femaleVoicePreference: true,
  language: 'AUTO',
  speechSpeed: 0.92,
  responseStyle: 'PROFESSIONAL',
  autoSpeakResponse: true,

  failedPaymentAlerts: true,
  paymentReceivedAlerts: true,
  paymentRecoveredAlerts: true,
  overdueInvoiceAlerts: true,
  b2bReceivableAlerts: true,
  highRiskAlerts: true,
  humanEscalationAlerts: true,

  sessionTimeout: '30m',
  confirmFinancialActions: true,
  humanApprovalHighRisk: true,

  theme: 'DARK',
  density: 'COMFORTABLE',
  animations: true,
  refreshInterval: '15s',
};

const STORAGE_KEY = 'paypilot_settings';

export default function SettingsModal({ isOpen, onClose, initialTab = 'GENERAL' }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<SettingsTab>(initialTab);
  const [settings, setSettings] = useState<PayPilotSettings>(DEFAULT_SETTINGS);
  const [savedToast, setSavedToast] = useState(false);
  const [clearedHistoryToast, setClearedHistoryToast] = useState(false);

  useEffect(() => {
    if (initialTab) setActiveTab(initialTab);
  }, [initialTab]);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        try {
          setSettings({ ...DEFAULT_SETTINGS, ...JSON.parse(stored) });
        } catch (e) {
          console.error('Failed to parse settings:', e);
        }
      }
    }
  }, [isOpen]);

  const updateSetting = <K extends keyof PayPilotSettings>(key: K, value: PayPilotSettings[K]) => {
    const updated = { ...settings, [key]: value };
    setSettings(updated);
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    }
    showSavedNotification();
  };

  const showSavedNotification = () => {
    setSavedToast(true);
    setTimeout(() => setSavedToast(false), 2000);
  };

  const handleClearHistory = () => {
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('paypilot_voice_session');
    }
    setClearedHistoryToast(true);
    setTimeout(() => setClearedHistoryToast(false), 2500);
  };

  if (!isOpen) return null;

  const tabs = [
    { id: 'GENERAL' as SettingsTab, label: 'General', icon: Building2 },
    { id: 'VOICE' as SettingsTab, label: 'Voice Assistant', icon: Mic },
    { id: 'NOTIFICATIONS' as SettingsTab, label: 'Notifications', icon: Bell },
    { id: 'SECURITY' as SettingsTab, label: 'Security', icon: ShieldCheck },
    { id: 'INTEGRATIONS' as SettingsTab, label: 'Integrations', icon: Cpu },
    { id: 'APPEARANCE' as SettingsTab, label: 'Appearance', icon: Palette },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden text-slate-100 font-sans">
        
        {/* Modal Header */}
        <div className="px-6 py-4 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/30 text-sky-400 flex items-center justify-center font-bold">
              <Sliders className="w-4 h-4" />
            </div>
            <div>
              <h2 className="font-extrabold text-base text-white tracking-tight">PayPilot Settings & Preferences</h2>
              <p className="text-xs text-slate-400">Configure business profiles, AI voice behavior, security and notifications</p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {savedToast && (
              <span className="text-xs text-emerald-400 font-mono flex items-center space-x-1 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-full animate-pulse">
                <Check className="w-3.5 h-3.5" />
                <span>Saved to localStorage</span>
              </span>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body: Sidebar Tabs + Content */}
        <div className="flex-1 flex overflow-hidden">
          
          {/* Tab Sidebar */}
          <div className="w-56 bg-slate-950/60 border-r border-slate-800/80 p-3 space-y-1 shrink-0 overflow-y-auto">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center space-x-2.5 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                    isActive
                      ? 'bg-slate-800 text-sky-400 border border-slate-700 shadow-sm'
                      : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-sky-400' : 'text-slate-500'}`} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Tab Content Panel */}
          <div className="flex-1 p-6 overflow-y-auto space-y-6 bg-slate-900/40">
            
            {/* GENERAL TAB */}
            {activeTab === 'GENERAL' && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-sm font-extrabold text-white uppercase tracking-wider font-mono">Business & Account Information</h3>
                  <p className="text-xs text-slate-400">Manage merchant identity and region settings</p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-slate-300">Merchant / Business Name</label>
                    <input
                      type="text"
                      value={settings.merchantName}
                      onChange={(e) => updateSetting('merchantName', e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-sky-500"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-slate-300">Business Email Address</label>
                    <input
                      type="email"
                      value={settings.email}
                      onChange={(e) => updateSetting('email', e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-sky-500"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-slate-300">Contact Phone Number</label>
                    <input
                      type="text"
                      value={settings.phone}
                      onChange={(e) => updateSetting('phone', e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-sky-500"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-slate-300">Display Timezone</label>
                    <select
                      value={settings.timezone}
                      onChange={(e) => updateSetting('timezone', e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-sky-500 font-mono"
                    >
                      <option value="Asia/Kolkata (IST)">Asia/Kolkata (IST)</option>
                      <option value="UTC">UTC (Coordinated Universal Time)</option>
                      <option value="America/New_York (EST)">America/New_York (EST)</option>
                    </select>
                  </div>

                  <div className="space-y-1.5 sm:col-span-2">
                    <label className="text-xs font-bold text-slate-300">Default Currency</label>
                    <select
                      value={settings.currency}
                      onChange={(e) => updateSetting('currency', e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-sky-500 font-mono"
                    >
                      <option value="INR (₹)">INR (Indian Rupee - ₹)</option>
                      <option value="USD ($)">USD (US Dollar - $)</option>
                      <option value="EUR (€)">EUR (Euro - €)</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* VOICE ASSISTANT TAB */}
            {activeTab === 'VOICE' && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-sm font-extrabold text-white uppercase tracking-wider font-mono">Voice Assistant Hardening & Preferences</h3>
                  <p className="text-xs text-slate-400">Configure PayPilot conversational AI voice persona, speed, and language</p>
                </div>

                <div className="space-y-4">
                  {/* Enable Voice Toggle */}
                  <div className="flex items-center justify-between p-3.5 bg-slate-950 border border-slate-800 rounded-xl">
                    <div>
                      <span className="font-bold text-xs text-white block">Enable Voice Assistant</span>
                      <span className="text-[11px] text-slate-400">Activate web speech synthesis and voice calls</span>
                    </div>
                    <button
                      onClick={() => updateSetting('voiceEnabled', !settings.voiceEnabled)}
                      className={`w-11 h-6 rounded-full transition-colors relative ${settings.voiceEnabled ? 'bg-purple-600' : 'bg-slate-800'}`}
                    >
                      <span className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${settings.voiceEnabled ? 'left-6' : 'left-1'}`} />
                    </button>
                  </div>

                  {/* Female Voice Preference */}
                  <div className="flex items-center justify-between p-3.5 bg-slate-950 border border-slate-800 rounded-xl">
                    <div>
                      <span className="font-bold text-xs text-white block">Female Voice Preference</span>
                      <span className="text-[11px] text-slate-400">Prefer genuine female TTS voices (e.g. Heera, Veena, Zira)</span>
                    </div>
                    <button
                      onClick={() => updateSetting('femaleVoicePreference', !settings.femaleVoicePreference)}
                      className={`w-11 h-6 rounded-full transition-colors relative ${settings.femaleVoicePreference ? 'bg-purple-600' : 'bg-slate-800'}`}
                    >
                      <span className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${settings.femaleVoicePreference ? 'left-6' : 'left-1'}`} />
                    </button>
                  </div>

                  {/* Language */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-slate-300">Conversation Language</label>
                    <select
                      value={settings.language}
                      onChange={(e) => updateSetting('language', e.target.value as any)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-purple-500 font-mono"
                    >
                      <option value="AUTO">Auto Detect (Multilingual)</option>
                      <option value="HINGLISH">Hinglish (Hindi + English)</option>
                      <option value="ENGLISH">English (Indian Accent)</option>
                      <option value="HINDI">Hindi (हिन्दी)</option>
                    </select>
                  </div>

                  {/* Speech Speed */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-slate-300">Speech Speed Rate ({settings.speechSpeed}x)</label>
                    <input
                      type="range"
                      min="0.75"
                      max="1.25"
                      step="0.05"
                      value={settings.speechSpeed}
                      onChange={(e) => updateSetting('speechSpeed', parseFloat(e.target.value))}
                      className="w-full accent-purple-500 bg-slate-950 rounded-lg cursor-pointer"
                    />
                  </div>

                  {/* Response Style */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-slate-300">Response Style</label>
                    <div className="grid grid-cols-3 gap-2">
                      {(['PROFESSIONAL', 'FRIENDLY', 'CONCISE'] as const).map((style) => (
                        <button
                          key={style}
                          onClick={() => updateSetting('responseStyle', style)}
                          className={`py-2 rounded-xl text-xs font-mono font-bold border transition-colors ${
                            settings.responseStyle === style
                              ? 'bg-purple-600/20 text-purple-300 border-purple-500/50'
                              : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-white'
                          }`}
                        >
                          {style}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Auto Speak Toggle */}
                  <div className="flex items-center justify-between p-3.5 bg-slate-950 border border-slate-800 rounded-xl">
                    <div>
                      <span className="font-bold text-xs text-white block">Auto-Speak Responses</span>
                      <span className="text-[11px] text-slate-400">Automatically pronounce Gemini text responses in browser</span>
                    </div>
                    <button
                      onClick={() => updateSetting('autoSpeakResponse', !settings.autoSpeakResponse)}
                      className={`w-11 h-6 rounded-full transition-colors relative ${settings.autoSpeakResponse ? 'bg-purple-600' : 'bg-slate-800'}`}
                    >
                      <span className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${settings.autoSpeakResponse ? 'left-6' : 'left-1'}`} />
                    </button>
                  </div>

                  {/* Clear History */}
                  <div className="pt-2 flex items-center justify-between border-t border-slate-800">
                    <div>
                      <span className="font-bold text-xs text-slate-300 block">Conversation History</span>
                      <span className="text-[11px] text-slate-400">Reset local session speech transcript memory</span>
                    </div>
                    <button
                      onClick={handleClearHistory}
                      className="px-3.5 py-1.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 text-xs font-mono font-bold rounded-xl transition-colors flex items-center space-x-1.5"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>{clearedHistoryToast ? 'Cleared!' : 'Clear History'}</span>
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* NOTIFICATIONS TAB */}
            {activeTab === 'NOTIFICATIONS' && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-sm font-extrabold text-white uppercase tracking-wider font-mono">Notification & Alert Rules</h3>
                  <p className="text-xs text-slate-400">Select which events trigger instant merchant notification center alerts</p>
                </div>

                <div className="space-y-2">
                  {[
                    { key: 'failedPaymentAlerts', label: 'Failed Payment Alerts', desc: 'Notify on new payment gateway declines' },
                    { key: 'paymentReceivedAlerts', label: 'Payment Received Alerts', desc: 'Notify when payment is successfully captured' },
                    { key: 'paymentRecoveredAlerts', label: 'Payment Recovered Alerts', desc: 'Notify when PayPilot AI recovers a failed transaction' },
                    { key: 'overdueInvoiceAlerts', label: 'Overdue Invoice Alerts', desc: 'Notify when B2B receivable crosses due date' },
                    { key: 'b2bReceivableAlerts', label: 'B2B Receivable Alerts', desc: 'Notify on promise-to-pay registrations & status changes' },
                    { key: 'highRiskAlerts', label: 'High-Risk Transaction Alerts', desc: 'Notify when transaction risk score exceeds threshold' },
                    { key: 'humanEscalationAlerts', label: 'Human Escalation Alerts', desc: 'Notify when case is escalated to human operator' },
                  ].map((item) => (
                    <div key={item.key} className="flex items-center justify-between p-3.5 bg-slate-950 border border-slate-800 rounded-xl">
                      <div>
                        <span className="font-bold text-xs text-white block">{item.label}</span>
                        <span className="text-[11px] text-slate-400">{item.desc}</span>
                      </div>
                      <button
                        onClick={() => updateSetting(item.key as any, !settings[item.key as keyof PayPilotSettings])}
                        className={`w-11 h-6 rounded-full transition-colors relative ${settings[item.key as keyof PayPilotSettings] ? 'bg-sky-500' : 'bg-slate-800'}`}
                      >
                        <span className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${settings[item.key as keyof PayPilotSettings] ? 'left-6' : 'left-1'}`} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* SECURITY TAB */}
            {activeTab === 'SECURITY' && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-sm font-extrabold text-white uppercase tracking-wider font-mono">Security & Policy Gate Settings</h3>
                  <p className="text-xs text-slate-400">Manage session rules, financial action confirmation, and security audit status</p>
                </div>

                <div className="space-y-4">
                  {/* Session Timeout */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-slate-300">Session Timeout</label>
                    <select
                      value={settings.sessionTimeout}
                      onChange={(e) => updateSetting('sessionTimeout', e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-sky-500 font-mono"
                    >
                      <option value="15m">15 Minutes</option>
                      <option value="30m">30 Minutes</option>
                      <option value="1h">1 Hour</option>
                      <option value="NEVER">Never Timeout</option>
                    </select>
                  </div>

                  {/* Confirm Financial Actions */}
                  <div className="flex items-center justify-between p-3.5 bg-slate-950 border border-slate-800 rounded-xl">
                    <div>
                      <span className="font-bold text-xs text-white block">Confirmation Before Financial Actions</span>
                      <span className="text-[11px] text-slate-400">Require policy gate check before link resend or mandate retry</span>
                    </div>
                    <button
                      onClick={() => updateSetting('confirmFinancialActions', !settings.confirmFinancialActions)}
                      className={`w-11 h-6 rounded-full transition-colors relative ${settings.confirmFinancialActions ? 'bg-sky-500' : 'bg-slate-800'}`}
                    >
                      <span className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${settings.confirmFinancialActions ? 'left-6' : 'left-1'}`} />
                    </button>
                  </div>

                  {/* Human Approval High Risk */}
                  <div className="flex items-center justify-between p-3.5 bg-slate-950 border border-slate-800 rounded-xl">
                    <div>
                      <span className="font-bold text-xs text-white block">Human Approval for High-Risk Actions</span>
                      <span className="text-[11px] text-slate-400">Escalate cases with high risk score to operator dashboard</span>
                    </div>
                    <button
                      onClick={() => updateSetting('humanApprovalHighRisk', !settings.humanApprovalHighRisk)}
                      className={`w-11 h-6 rounded-full transition-colors relative ${settings.humanApprovalHighRisk ? 'bg-sky-500' : 'bg-slate-800'}`}
                    >
                      <span className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${settings.humanApprovalHighRisk ? 'left-6' : 'left-1'}`} />
                    </button>
                  </div>

                  {/* Status Badges */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                    <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Lock className="w-4 h-4 text-emerald-400" />
                        <span className="text-xs font-bold text-slate-200">Audit Logging Status</span>
                      </div>
                      <span className="text-[10px] font-mono font-bold bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20">
                        ACTIVE & VERIFIED
                      </span>
                    </div>

                    <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Key className="w-4 h-4 text-sky-400" />
                        <span className="text-xs font-bold text-slate-200">API Key Connection Status</span>
                      </div>
                      <span className="text-[10px] font-mono font-bold bg-sky-500/10 text-sky-400 px-2 py-0.5 rounded border border-sky-500/20">
                        SECURE & CONNECTED
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* INTEGRATIONS TAB */}
            {activeTab === 'INTEGRATIONS' && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-sm font-extrabold text-white uppercase tracking-wider font-mono">Provider Integrations & Gateway Status</h3>
                  <p className="text-xs text-slate-400">View real-time connection status for Razorpay, Gemini AI, WhatsApp and Email</p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  
                  {/* Razorpay */}
                  <div className="p-4 bg-slate-950 border border-slate-800 rounded-2xl space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="font-extrabold text-xs text-white uppercase font-mono tracking-wider">Razorpay Gateway</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center space-x-1">
                        <CheckCircle2 className="w-3 h-3" />
                        <span>CONNECTED</span>
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400">Test keys configured. Payment links and webhook events verified.</p>
                    <div className="text-[10px] font-mono text-slate-500">Mode: Test Sandbox | Secret: Hidden</div>
                  </div>

                  {/* Gemini AI */}
                  <div className="p-4 bg-slate-950 border border-slate-800 rounded-2xl space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="font-extrabold text-xs text-white uppercase font-mono tracking-wider">Gemini AI (google.genai)</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-500/10 text-purple-400 border border-purple-500/20 flex items-center space-x-1">
                        <CheckCircle2 className="w-3 h-3" />
                        <span>ACTIVE</span>
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400">Server-side v1beta Client with 17 read-only PayPilot tools enabled.</p>
                    <div className="text-[10px] font-mono text-purple-400">API Key: Secured in Server ENV</div>
                  </div>

                  {/* WhatsApp */}
                  <div className="p-4 bg-slate-950 border border-slate-800 rounded-2xl space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="font-extrabold text-xs text-white uppercase font-mono tracking-wider">WhatsApp Business API</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-sky-500/10 text-sky-400 border border-sky-500/20">
                        CONFIGURED
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400">Automated payment recovery message dispatch via Meta Graph API.</p>
                    <div className="text-[10px] font-mono text-slate-500">Template ID: paypilot_recovery_v1</div>
                  </div>

                  {/* Email */}
                  <div className="p-4 bg-slate-950 border border-slate-800 rounded-2xl space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="font-extrabold text-xs text-white uppercase font-mono tracking-wider">Email Dispatch Engine</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        ACTIVE
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400">Transactional invoice reminders and payment receipts.</p>
                    <div className="text-[10px] font-mono text-slate-500">Sender: notifications@paypilot.ai</div>
                  </div>
                </div>
              </div>
            )}

            {/* APPEARANCE TAB */}
            {activeTab === 'APPEARANCE' && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-sm font-extrabold text-white uppercase tracking-wider font-mono">Theme & Dashboard Appearance</h3>
                  <p className="text-xs text-slate-400">Customize UI theme density, animations, and auto-refresh intervals</p>
                </div>

                <div className="space-y-4">
                  {/* Theme */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-slate-300">Interface Theme</label>
                    <div className="grid grid-cols-3 gap-3">
                      {[
                        { id: 'DARK', label: 'Dark SaaS (Default)' },
                        { id: 'LIGHT', label: 'Light Mode' },
                        { id: 'SYSTEM', label: 'System Default' }
                      ].map((t) => (
                        <button
                          key={t.id}
                          onClick={() => updateSetting('theme', t.id as any)}
                          className={`p-3 rounded-xl text-xs font-bold border text-center transition-colors ${
                            settings.theme === t.id
                              ? 'bg-sky-500/20 text-sky-400 border-sky-500/50'
                              : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-white'
                          }`}
                        >
                          {t.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Density */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-slate-300">Layout Density</label>
                    <div className="grid grid-cols-2 gap-3">
                      {[
                        { id: 'COMFORTABLE', label: 'Comfortable (Standard)' },
                        { id: 'COMPACT', label: 'Compact (High Information Density)' }
                      ].map((d) => (
                        <button
                          key={d.id}
                          onClick={() => updateSetting('density', d.id as any)}
                          className={`p-3 rounded-xl text-xs font-bold border text-center transition-colors ${
                            settings.density === d.id
                              ? 'bg-sky-500/20 text-sky-400 border-sky-500/50'
                              : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-white'
                          }`}
                        >
                          {d.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Animations Toggle */}
                  <div className="flex items-center justify-between p-3.5 bg-slate-950 border border-slate-800 rounded-xl">
                    <div>
                      <span className="font-bold text-xs text-white block">UI Animations & Transitions</span>
                      <span className="text-[11px] text-slate-400">Enable smooth micro-animations and pulse effects</span>
                    </div>
                    <button
                      onClick={() => updateSetting('animations', !settings.animations)}
                      className={`w-11 h-6 rounded-full transition-colors relative ${settings.animations ? 'bg-sky-500' : 'bg-slate-800'}`}
                    >
                      <span className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${settings.animations ? 'left-6' : 'left-1'}`} />
                    </button>
                  </div>

                  {/* Refresh Interval */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-slate-300">Dashboard Refresh Interval</label>
                    <select
                      value={settings.refreshInterval}
                      onChange={(e) => updateSetting('refreshInterval', e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-sky-500 font-mono"
                    >
                      <option value="5s">Every 5 Seconds</option>
                      <option value="15s">Every 15 Seconds (Default)</option>
                      <option value="30s">Every 30 Seconds</option>
                      <option value="60s">Every 60 Seconds</option>
                      <option value="MANUAL">Manual Refresh Only</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

          </div>

        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 bg-slate-950 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400 font-mono">
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>PayPilot AI v1.0.0 — All settings saved locally</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-white font-bold rounded-xl transition-colors"
          >
            Done
          </button>
        </div>

      </div>
    </div>
  );
}
