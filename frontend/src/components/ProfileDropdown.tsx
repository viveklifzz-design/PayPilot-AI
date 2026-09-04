'use client';

import { 
  User, 
  Building2, 
  Mic, 
  Bell, 
  ShieldCheck, 
  Palette, 
  Cpu, 
  LogOut,
  ChevronRight,
  Sparkles
} from 'lucide-react';
import { SettingsTab } from './SettingsModal';

interface ProfileDropdownProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenSettings: (tab: SettingsTab) => void;
  onSignOut: () => void;
}

export default function ProfileDropdown({ isOpen, onClose, onOpenSettings, onSignOut }: ProfileDropdownProps) {
  if (!isOpen) return null;

  const menuItems: { label: string; icon: any; tab: SettingsTab; badge?: string }[] = [
    { label: 'Profile', icon: User, tab: 'GENERAL' },
    { label: 'Account', icon: Building2, tab: 'GENERAL' },
    { label: 'Voice Assistant', icon: Mic, tab: 'VOICE', badge: 'AI' },
    { label: 'Notifications', icon: Bell, tab: 'NOTIFICATIONS' },
    { label: 'Security', icon: ShieldCheck, tab: 'SECURITY' },
    { label: 'Appearance', icon: Palette, tab: 'APPEARANCE' },
    { label: 'Integrations', icon: Cpu, tab: 'INTEGRATIONS' },
  ];

  return (
    <>
      {/* Invisible Overlay to close on outside click */}
      <div 
        className="fixed inset-0 z-40" 
        onClick={onClose} 
      />

      {/* Popover Dropdown */}
      <div className="absolute right-0 mt-2 w-64 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl z-50 overflow-hidden font-sans text-slate-100 animate-fadeIn">
        
        {/* Merchant Info Header */}
        <div className="p-4 bg-slate-950 border-b border-slate-800 space-y-1">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-sky-500 to-indigo-600 text-white font-black text-sm flex items-center justify-center border border-slate-700 shadow-sm shrink-0">
              M
            </div>
            <div className="overflow-hidden">
              <h4 className="font-extrabold text-xs text-white truncate">Main Merchant Account</h4>
              <p className="text-[11px] text-slate-400 font-mono truncate">merchant@paypilot.ai</p>
            </div>
          </div>

          <div className="pt-2 flex items-center justify-between text-[10px] font-mono text-slate-400">
            <span>Status: <strong className="text-emerald-400">ACTIVE</strong></span>
            <span>ID: <strong className="text-slate-300">mch_prod_01</strong></span>
          </div>
        </div>

        {/* Navigation Items */}
        <div className="py-2 space-y-0.5">
          {menuItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.label}
                onClick={() => {
                  onOpenSettings(item.tab);
                  onClose();
                }}
                className="w-full flex items-center justify-between px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800 hover:text-white transition-colors group"
              >
                <div className="flex items-center space-x-2.5">
                  <Icon className="w-4 h-4 text-slate-400 group-hover:text-sky-400 transition-colors" />
                  <span>{item.label}</span>
                </div>

                <div className="flex items-center space-x-1.5">
                  {item.badge && (
                    <span className="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                      {item.badge}
                    </span>
                  )}
                  <ChevronRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-slate-400" />
                </div>
              </button>
            );
          })}
        </div>

        {/* Footer: Sign Out */}
        <div className="p-2 bg-slate-950/80 border-t border-slate-800/80">
          <button
            onClick={() => {
              onSignOut();
              onClose();
            }}
            className="w-full flex items-center space-x-2.5 px-3 py-2 rounded-xl text-xs font-bold text-rose-400 hover:bg-rose-500/10 transition-colors"
          >
            <LogOut className="w-4 h-4 text-rose-400" />
            <span>Sign Out</span>
          </button>
        </div>

      </div>
    </>
  );
}
