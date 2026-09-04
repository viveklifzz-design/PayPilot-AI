'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  Home, 
  CreditCard, 
  ShieldAlert, 
  Layers, 
  Users, 
  ShieldCheck, 
  Activity, 
  Lock,
  ExternalLink,
  LucideIcon
} from 'lucide-react';

interface SidebarItem {
  label: string;
  href: string;
  icon: LucideIcon;
  badge?: string;
  external?: boolean;
}

interface SidebarSection {
  title: string;
  items: SidebarItem[];
}

export default function Sidebar() {
  const pathname = usePathname();

  const sections: SidebarSection[] = [
    {
      title: 'HOME',
      items: [
        { label: 'Overview', href: '/', icon: Home },
      ]
    },
    {
      title: 'PAYMENTS',
      items: [
        { label: 'Transactions', href: '/transactions', icon: CreditCard },
        { label: 'Orders', href: '/transactions?tab=orders', icon: Layers },
      ]
    },
    {
      title: 'RECOVERY',
      items: [
        { label: 'Revenue Risk', href: '/revenue-risk', icon: ShieldAlert },
        { label: 'Recovery Cases', href: '/cases', icon: Layers },
      ]
    },
    {
      title: 'CUSTOMERS',
      items: [
        { label: 'Customers', href: '/customers', icon: Users },
        { label: 'Customer Portal', href: '/customer', icon: ExternalLink, external: true },
      ]
    },
    {
      title: 'OPERATIONS',
      items: [
        { label: 'Audit Trail', href: '/audit', icon: Lock },
        { label: 'Safety & Policy', href: '/safety', icon: ShieldCheck },
      ]
    },
    {
      title: 'ANALYTICS',
      items: [
        { 
          label: 'Benchmark', 
          href: '/benchmark', 
          icon: Activity, 
          badge: 'SYNTHETIC' 
        },
      ]
    }
  ];

  return (
    <aside className="w-56 bg-white border-r border-slate-200 text-slate-700 min-h-[calc(100vh-3.5rem)] shrink-0 hidden md:block select-none shadow-sm">
      <div className="p-3 space-y-5">
        {sections.map((section, idx) => (
          <div key={idx} className="space-y-1">
            <h3 className="px-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
              {section.title}
            </h3>
            <div className="space-y-0.5 mt-1">
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href) && !item.href.includes('?'));
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center justify-between px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                      isActive
                        ? 'bg-sky-50 text-sky-700 font-bold border border-sky-200/60 shadow-xs'
                        : 'text-slate-600 hover:bg-slate-100/80 hover:text-slate-900'
                    }`}
                  >
                    <div className="flex items-center space-x-2.5">
                      <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-sky-600' : 'text-slate-400'}`} />
                      <span>{item.label}</span>
                    </div>
                    {item.badge && (
                      <span className="text-[9px] font-mono px-1.5 py-0.2 bg-amber-50 text-amber-700 rounded border border-amber-200 font-bold">
                        {item.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Footer Test Mode Status */}
      <div className="p-3 border-t border-slate-100 mt-auto text-[11px] text-slate-500 space-y-1 bg-slate-50/50">
        <div className="flex items-center justify-between font-mono">
          <span className="text-slate-400 font-medium">Environment:</span>
          <span className="text-amber-700 font-bold bg-amber-100/60 px-1.5 py-0.2 rounded border border-amber-200 text-[10px]">TEST</span>
        </div>
        <div className="flex items-center justify-between font-mono">
          <span className="text-slate-400 font-medium">Provider:</span>
          <span className="text-slate-700 font-semibold text-[10px]">Razorpay API</span>
        </div>
      </div>
    </aside>
  );
}
