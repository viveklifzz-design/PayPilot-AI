'use client';

import { CreditCard, ShieldCheck } from 'lucide-react';
import Link from 'next/link';

export default function CustomersPage() {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 flex-1 space-y-6 w-full">
        <div className="bg-white border border-slate-200 rounded-3xl p-8 shadow-sm space-y-4 text-center">
          <div className="w-12 h-12 bg-sky-50 rounded-2xl flex items-center justify-center text-sky-600 mx-auto">
            <CreditCard className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-black text-slate-900">CUSTOMER RECOVERY PORTAL</h1>
          <p className="text-sm text-slate-500 max-w-md mx-auto">
            Customer authentication, transaction status lookups, and strict ownership security checks.
          </p>

          <div className="pt-4">
            <Link
              href="/customer"
              className="inline-flex items-center space-x-2 px-6 py-3 bg-sky-600 text-white font-bold text-sm rounded-xl hover:bg-sky-700 transition-colors shadow"
            >
              <span>Launch Customer Portal View</span>
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
