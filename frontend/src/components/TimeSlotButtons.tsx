'use client';

import { TimeSlot } from '@/lib/types';
import { format, parseISO } from 'date-fns';

interface TimeSlotButtonsProps {
  slots: TimeSlot[];
  onSelect: (slot: TimeSlot) => void;
  userTimezone?: string;
}

function formatSlotTime(isoString: string): string {
  try {
    const date = parseISO(isoString);
    return format(date, "EEE, MMM d 'at' h:mm a");
  } catch {
    return isoString;
  }
}

export default function TimeSlotButtons({ slots, onSelect, userTimezone }: TimeSlotButtonsProps) {
  if (!slots || slots.length === 0) return null;

  return (
    <div className="flex flex-col gap-2 mt-3">
      <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">Available time slots:</p>
      {slots.slice(0, 3).map((slot, idx) => (
        <button
          key={idx}
          onClick={() => onSelect(slot)}
          className="flex items-center justify-between px-4 py-3 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-xl text-left transition-colors duration-150 group"
        >
          <div>
            <div className="text-sm font-medium text-blue-700">
              {formatSlotTime(slot.start)}
            </div>
            <div className="text-xs text-blue-500">
              {slot.duration_minutes} minutes
            </div>
          </div>
          <svg
            className="w-5 h-5 text-blue-400 group-hover:text-blue-600 transition-colors"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      ))}
    </div>
  );
}
