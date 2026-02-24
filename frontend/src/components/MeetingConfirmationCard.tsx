import { format } from "date-fns";
import { CalendarCheck, Video } from "lucide-react";
import { MeetingDetails } from "@/lib/api";

interface MeetingConfirmationCardProps {
  details: MeetingDetails;
  timezone: string;
}

export function MeetingConfirmationCard({
  details,
  timezone,
}: MeetingConfirmationCardProps) {
  const start = new Date(details.start);
  const end = new Date(details.end);

  return (
    <div className="bg-green-50 border border-green-200 rounded-xl p-4 mt-2 max-w-sm">
      <div className="flex items-center gap-2 mb-3">
        <CalendarCheck className="w-5 h-5 text-green-600" />
        <span className="font-semibold text-green-800">Meeting Scheduled!</span>
      </div>
      <div className="space-y-1 text-sm text-slate-700">
        <p>
          <span className="font-medium">Date: </span>
          {format(start, "EEEE, MMMM d, yyyy")}
        </p>
        <p>
          <span className="font-medium">Time: </span>
          {format(start, "h:mm a")} – {format(end, "h:mm a")}
        </p>
      </div>
      {details.meet_link && (
        <a
          href={details.meet_link}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-3 flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg px-3 py-2 text-sm font-medium transition-colors w-fit"
        >
          <Video className="w-4 h-4" />
          Join Google Meet
        </a>
      )}
    </div>
  );
}
