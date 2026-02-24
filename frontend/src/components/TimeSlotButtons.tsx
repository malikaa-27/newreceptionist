import { format } from "date-fns";
import { TimeSlot } from "@/lib/api";

interface TimeSlotButtonsProps {
  slots: TimeSlot[];
  onSelect: (slot: TimeSlot) => void;
}

export function TimeSlotButtons({ slots, onSelect }: TimeSlotButtonsProps) {
  return (
    <div className="flex flex-col gap-2 mt-2">
      {slots.slice(0, 3).map((slot, i) => {
        const start = new Date(slot.start);
        const end = new Date(slot.end);
        return (
          <button
            key={i}
            onClick={() => onSelect(slot)}
            className="flex items-center justify-between bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-lg px-4 py-2.5 text-sm text-indigo-800 font-medium transition-colors w-full text-left"
          >
            <span>{format(start, "EEE, MMM d")}</span>
            <span className="text-indigo-600">
              {format(start, "h:mm a")} – {format(end, "h:mm a")}
            </span>
          </button>
        );
      })}
    </div>
  );
}
