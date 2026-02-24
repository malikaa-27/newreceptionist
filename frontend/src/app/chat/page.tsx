'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function ChatRedirect() {
  const router = useRouter();
  
  useEffect(() => {
    router.replace('/');
  }, [router]);
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 rounded-full bg-blue-600 flex items-center justify-center animate-pulse">
          <span className="text-white font-bold text-lg">AI</span>
        </div>
        <p className="text-gray-500 text-sm">Redirecting...</p>
      </div>
    </div>
  );
}
