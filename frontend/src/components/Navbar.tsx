'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  BarChart3, 
  CreditCard, 
  ShieldAlert, 
  Layers, 
  Users, 
  ShieldCheck, 
  Activity, 
  Search, 
  Bell, 
  Settings,
  ChevronDown,
  Lock,
  Mic
} from 'lucide-react';
import PayPilotLogo from './PayPilotLogo';
import SettingsModal, { SettingsTab } from './SettingsModal';
import ProfileDropdown from './ProfileDropdown';
import { api, RazorpayHealthStatus, NotificationItem, formatIST } from '@/lib/api';
import { CheckCircle2, AlertTriangle, AlertCircle, Info, ExternalLink, CheckCheck } from 'lucide-react';

export default function Navbar() {
  const pathname = usePathname();
  const [rzpStatus, setRzpStatus] = useState<RazorpayHealthStatus | null>(null);
  const [showMoreMenu, setShowMoreMenu] = useState(false);
  const [globalQuery, setGlobalQuery] = useState('');
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [showNotifMenu, setShowNotifMenu] = useState<boolean>(false);
  const [notifTab, setNotifTab] = useState<'ALL' | 'UNREAD'>('ALL');
  
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [settingsTab, setSettingsTab] = useState<SettingsTab>('GENERAL');
  const [signOutToast, setSignOutToast] = useState(false);

  const handleOpenSettingsTab = (tab: SettingsTab) => {
    setSettingsTab(tab);
    setShowSettingsModal(true);
  };

  const handleSignOut = () => {
    setSignOutToast(true);
    setTimeout(() => setSignOutToast(false), 3000);
  };

  const fetchNotifs = async () => {
    try {
      const [list, uCount] = await Promise.all([
        api.getNotifications({ limit: 20 }).catch(() => []),
        api.getUnreadCount().catch(() => ({ unread_count: 0 }))
      ]);
      setNotifications(list);
      setUnreadCount(uCount.unread_count);
    } catch (e) {
      console.error('Failed to fetch notifications:', e);
    }
  };

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const res = await api.getRazorpayStatus();
        setRzpStatus(res);
        await fetchNotifs();
      } catch (e) {
        setRzpStatus({ configured: true, test_mode: true, webhook_configured: true, status: 'connected' });
      }
    };
    checkStatus();
    const interval = setInterval(checkStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleMarkRead = async (id: string) => {
    try {
      await api.markNotificationRead(id);
      await fetchNotifs();
    } catch (e) {
      console.error('Mark read failed:', e);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await api.markAllNotificationsRead();
      await fetchNotifs();
    } catch (e) {
      console.error('Mark all read failed:', e);
    }
  };

  const mainNavItems = [
    { label: 'Overview', href: '/', icon: BarChart3 },
    { label: 'Transactions', href: '/transactions', icon: CreditCard },
    { label: 'Revenue Risk', href: '/revenue-risk', icon: ShieldAlert },
    { label: 'Recovery Cases', href: '/cases', icon: Layers },
    { label: 'Voice Recovery', href: '/voice', icon: Mic },
    { label: 'Customers', href: '/customers', icon: Users },
  ];

  const moreNavItems = [
    { label: 'Safety & Policy', href: '/safety', icon: ShieldCheck },
    { label: 'Audit Trail', href: '/audit', icon: Lock },
    { label: 'Customer Portal', href: '/customer', icon: Users },
    { label: 'Synthetic Benchmark', href: '/benchmark', icon: Activity, badge: 'SYNTHETIC' },
  ];

  return (
    <header className="bg-slate-900 text-white border-b border-slate-800 sticky top-0 z-50 shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          
          {/* Brand Header */}
          <div className="flex items-center space-x-6">
            <Link href="/" className="flex items-center space-x-2.5 hover:opacity-90 transition-opacity">
              <PayPilotLogo size={28} />
              <span className="font-bold text-lg tracking-tight text-white font-sans">PayPilot AI</span>
            </Link>

            {/* Test Mode Badge */}
            <div className="flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
              <span>TEST</span>
            </div>

            {/* Primary Desktop Nav */}
            <nav className="hidden lg:flex items-center space-x-1">
              {mainNavItems.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-slate-800 text-sky-400 border border-slate-700/80 shadow-sm'
                        : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}

              {/* Dropdown for More */}
              <div className="relative">
                <button
                  onClick={() => setShowMoreMenu(!showMoreMenu)}
                  className="flex items-center space-x-1 px-3 py-1.5 rounded-md text-sm font-medium text-slate-300 hover:bg-slate-800/60 hover:text-white transition-colors"
                >
                  <span>More</span>
                  <ChevronDown className="w-3.5 h-3.5" />
                </button>

                {showMoreMenu && (
                  <div className="absolute left-0 mt-2 w-56 bg-slate-900 border border-slate-800 rounded-lg shadow-xl py-2 z-50">
                    {moreNavItems.map((item) => (
                      <Link
                        key={item.href}
                        href={item.href}
                        onClick={() => setShowMoreMenu(false)}
                        className="flex items-center justify-between px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-white"
                      >
                        <div className="flex items-center space-x-2">
                          <item.icon className="w-4 h-4 text-slate-400" />
                          <span>{item.label}</span>
                        </div>
                        {item.badge && (
                          <span className="text-[10px] bg-slate-800 text-amber-400 px-1.5 py-0.5 rounded border border-amber-500/20 font-mono">
                            SYNTHETIC
                          </span>
                        )}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            </nav>
          </div>

          {/* Right Header Utilities: Search, Notifications, Profile */}
          <div className="flex items-center space-x-3">
            
            {/* Global Search Bar */}
            <div className="relative hidden md:block">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search payment ID, email..."
                value={globalQuery}
                onChange={(e) => setGlobalQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && globalQuery.trim()) {
                    window.location.href = `/transactions?q=${encodeURIComponent(globalQuery.trim())}`;
                  }
                }}
                className="bg-slate-950 border border-slate-800 rounded-md pl-9 pr-4 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 w-56 transition-all"
              />
            </div>

            {/* Notifications Bell & Interactive Center */}
            <div className="relative">
              <button
                onClick={() => setShowNotifMenu(!showNotifMenu)}
                className="p-1.5 text-slate-400 hover:text-white rounded-md hover:bg-slate-800 transition-colors relative"
                title="Notifications"
              >
                <Bell className="w-4 h-4" />
                {unreadCount > 0 && (
                  <span className="absolute -top-0.5 -right-0.5 bg-rose-500 text-white font-mono text-[9px] font-black w-4 h-4 rounded-full flex items-center justify-center border-2 border-slate-900 shadow-sm animate-pulse">
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                )}
              </button>

              {/* Notification Center Dropdown */}
              {showNotifMenu && (
                <div className="absolute right-0 mt-2 w-80 md:w-96 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl z-50 overflow-hidden text-slate-200">
                  {/* Header */}
                  <div className="p-3 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Bell className="w-4 h-4 text-sky-400" />
                      <span className="font-bold text-xs text-white uppercase tracking-wider">Notifications Center</span>
                      {unreadCount > 0 && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                          {unreadCount} UNREAD
                        </span>
                      )}
                    </div>
                    {unreadCount > 0 && (
                      <button
                        onClick={handleMarkAllRead}
                        className="text-[10px] text-sky-400 hover:text-sky-300 font-mono flex items-center space-x-1"
                      >
                        <CheckCheck className="w-3 h-3" />
                        <span>Read All</span>
                      </button>
                    )}
                  </div>

                  {/* Tabs */}
                  <div className="flex border-b border-slate-800 bg-slate-900/60 text-xs font-mono">
                    <button
                      onClick={() => setNotifTab('ALL')}
                      className={`flex-1 py-2 text-center font-bold border-b-2 transition-colors ${
                        notifTab === 'ALL' ? 'border-sky-500 text-sky-400 bg-slate-800/40' : 'border-transparent text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      ALL ({notifications.length})
                    </button>
                    <button
                      onClick={() => setNotifTab('UNREAD')}
                      className={`flex-1 py-2 text-center font-bold border-b-2 transition-colors ${
                        notifTab === 'UNREAD' ? 'border-sky-500 text-sky-400 bg-slate-800/40' : 'border-transparent text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      UNREAD ({unreadCount})
                    </button>
                  </div>

                  {/* Notification Items List */}
                  <div className="max-h-80 overflow-y-auto divide-y divide-slate-800/60">
                    {notifications
                      .filter((n) => (notifTab === 'UNREAD' ? !n.is_read : true))
                      .map((n) => (
                        <div
                          key={n.id}
                          className={`p-3 transition-colors text-xs space-y-1.5 relative ${
                            n.is_read ? 'bg-slate-900/40 opacity-75' : 'bg-slate-800/50'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex items-center space-x-2">
                              <span className={`w-2 h-2 rounded-full shrink-0 ${
                                n.severity === 'SUCCESS' ? 'bg-emerald-400' : n.severity === 'WARNING' ? 'bg-amber-400' : n.severity === 'ERROR' ? 'bg-rose-400' : 'bg-sky-400'
                              }`} />
                              <span className="font-bold text-white leading-tight">{n.title}</span>
                            </div>
                            <span className="text-[10px] text-slate-500 font-mono shrink-0">
                              {formatIST(n.created_at)}
                            </span>
                          </div>

                          <p className="text-slate-300 text-[11px] leading-relaxed pl-4">
                            {n.message}
                          </p>

                          <div className="flex items-center justify-between pt-1 pl-4">
                            {n.action_url ? (
                              <Link
                                href={n.action_url}
                                onClick={() => {
                                  handleMarkRead(n.id);
                                  setShowNotifMenu(false);
                                }}
                                className="text-[10px] font-mono text-sky-400 hover:underline flex items-center space-x-1"
                              >
                                <span>View Case</span>
                                <ExternalLink className="w-3 h-3" />
                              </Link>
                            ) : <span />}

                            {!n.is_read && (
                              <button
                                onClick={() => handleMarkRead(n.id)}
                                className="text-[10px] font-mono text-slate-400 hover:text-slate-200 uppercase"
                              >
                                Mark Read
                              </button>
                            )}
                          </div>
                        </div>
                      ))}

                    {notifications.filter((n) => (notifTab === 'UNREAD' ? !n.is_read : true)).length === 0 && (
                      <div className="p-6 text-center text-xs text-slate-500 font-mono">
                        No notifications found.
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Settings Icon */}
            <button
              onClick={() => handleOpenSettingsTab('GENERAL')}
              className="p-1.5 text-slate-400 hover:text-white rounded-md hover:bg-slate-800 transition-colors"
              title="PayPilot Settings"
            >
              <Settings className="w-4 h-4" />
            </button>

            {/* User Avatar & Profile Dropdown */}
            <div className="relative">
              <button
                onClick={() => setShowProfileMenu(!showProfileMenu)}
                className="w-7 h-7 rounded-full bg-slate-800 text-sky-400 border border-slate-700 hover:border-sky-500 flex items-center justify-center font-bold text-xs transition-colors focus:outline-none"
                title="Account Profile"
              >
                M
              </button>

              <ProfileDropdown
                isOpen={showProfileMenu}
                onClose={() => setShowProfileMenu(false)}
                onOpenSettings={handleOpenSettingsTab}
                onSignOut={handleSignOut}
              />
            </div>

          </div>

        </div>
      </div>

      {/* Global Settings Modal */}
      <SettingsModal
        isOpen={showSettingsModal}
        onClose={() => setShowSettingsModal(false)}
        initialTab={settingsTab}
      />

      {/* Sign Out Notification Toast */}
      {signOutToast && (
        <div className="fixed bottom-4 right-4 z-50 bg-slate-900 border border-slate-700 text-white px-4 py-3 rounded-xl shadow-2xl flex items-center space-x-3 text-xs font-sans animate-fadeIn">
          <div className="w-2 h-2 rounded-full bg-sky-400 animate-pulse" />
          <div>
            <strong className="block font-bold">Signed out of PayPilot Account</strong>
            <span className="text-slate-400">Demo merchant session active on localhost.</span>
          </div>
        </div>
      )}
    </header>
  );
}
