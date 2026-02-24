'use client';

import { Message } from '@/lib/types';
import { format } from 'date-fns';

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold mr-2 flex-shrink-0 mt-1">
          AI
        </div>
      )}
      <div className={`max-w-[75%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        <div
          className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
            isUser
              ? 'bg-blue-600 text-white rounded-br-sm'
              : 'bg-white text-gray-800 shadow-sm border border-gray-100 rounded-bl-sm'
          }`}
        >
          {message.content}
        </div>
        <span className="text-xs text-gray-400 mt-1 px-1">
          {format(new Date(message.timestamp), 'h:mm a')}
        </span>
      </div>
      {isUser && (
        <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-600 text-sm font-bold ml-2 flex-shrink-0 mt-1">
          U
        </div>
      )}
    </div>
  );
}
