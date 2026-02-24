'use client';

import { MeetingCreated } from '@/lib/types';
import { format, parseISO } from 'date-fns';

interface MeetingConfirmationProps {
  meeting: MeetingCreated;
}

export default function MeetingConfirmation({ meeting }: MeetingConfirmationProps) {
  const startDate = parseISO(meeting.start);
  const endDate = parseISO(meeting.end);

  return (
    <div className="bg-green-50 border border-green-200 rounded-2xl p-4 mt-4 max-w-sm">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center">
          <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <span className="font-semibold text-green-800">Meeting Scheduled!</span>
      </div>
      
      <div className="space-y-2 text-sm">
        <div className="flex items-start gap-2">
          <svg className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <div>
            <div className="font-medium text-gray-800">
              {format(startDate, 'EEEE, MMMM d, yyyy')}
            </div>
            <div className="text-gray-600">
              {format(startDate, 'h:mm a')} – {format(endDate, 'h:mm a')}
            </div>
          </div>
        </div>
        
        <div className="flex items-start gap-2">
          <svg className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <div className="text-gray-600">
            {meeting.attendees.join(', ')}
          </div>
        </div>
        
        {meeting.meet_link && (
          <div className="flex items-start gap-2">
            <svg className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.069A1 1 0 0121 8.882v6.236a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            <a
              href={meeting.meet_link}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-700 underline break-all"
            >
              Join Google Meet
            </a>
          </div>
        )}
      </div>
      
      <div className="mt-3 pt-3 border-t border-green-200 flex gap-2">
        {meeting.html_link && (
          <a
            href={meeting.html_link}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 text-center text-xs text-blue-600 hover:text-blue-700 font-medium"
          >
            View in Calendar
          </a>
        )}
      </div>
    </div>
  );
}
