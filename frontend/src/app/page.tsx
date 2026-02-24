'use client';

import { useEffect, useState } from 'react';
import { getCurrentUser, logout } from '@/lib/api';
import { User } from '@/lib/types';
import LoginButton from '@/components/LoginButton';
import Chat from '@/components/Chat';

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCurrentUser().then((u) => {
      setUser(u);
      setLoading(false);
    });
  }, []);

  const handleLogout = async () => {
    await logout();
    setUser(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-blue-600 flex items-center justify-center animate-pulse">
            <span className="text-white font-bold text-lg">AI</span>
          </div>
          <p className="text-gray-500 text-sm">Loading...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-3xl shadow-xl p-10 max-w-md w-full text-center">
          <div className="w-16 h-16 rounded-full bg-blue-600 flex items-center justify-center mx-auto mb-6">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">AI Scheduling Agent</h1>
          <p className="text-gray-500 mb-8 leading-relaxed">
            Schedule meetings effortlessly with your AI assistant. Connect your Google Calendar to get started.
          </p>
          <div className="flex justify-center mb-6">
            <LoginButton />
          </div>
          <div className="grid grid-cols-3 gap-4 mt-8 text-center">
            {[
              { icon: '🗓️', label: 'Smart Scheduling' },
              { icon: '🤖', label: 'AI Powered' },
              { icon: '🔗', label: 'Google Meet' },
            ].map((feature) => (
              <div key={feature.label} className="flex flex-col items-center gap-1">
                <span className="text-2xl">{feature.icon}</span>
                <span className="text-xs text-gray-500">{feature.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      {/* Top nav */}
      <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
            <span className="text-white font-bold text-sm">AI</span>
          </div>
          <span className="font-semibold text-gray-800">Scheduling Agent</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">{user.name}</span>
          <button
            onClick={handleLogout}
            className="text-sm text-gray-500 hover:text-gray-700 px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors"
          >
            Sign out
          </button>
        </div>
      </nav>

      {/* Chat */}
      <div className="flex-1 max-w-3xl mx-auto w-full flex flex-col" style={{ height: 'calc(100vh - 60px)' }}>
        <Chat userEmail={user.email} userName={user.name} />
      </div>
    </div>
  );
}
