export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  toolCalled?: string;
}

export interface TimeSlot {
  start: string;
  end: string;
  duration_minutes: number;
}

export interface MeetingCreated {
  event_id: string;
  meet_link: string | null;
  html_link: string | null;
  start: string;
  end: string;
  attendees: string[];
}

export interface ChatResponse {
  message: string;
  tool_called?: string;
  meeting_created?: MeetingCreated;
}

export interface User {
  id: number;
  email: string;
  name: string;
  timezone: string;
}
