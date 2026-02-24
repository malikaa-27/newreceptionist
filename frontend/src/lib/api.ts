import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
});

export interface User {
  id: string;
  email: string;
  name: string;
  timezone: string;
  created_at: string;
}

export interface TimeSlot {
  start: string;
  end: string;
}

export interface MeetingDetails {
  event_id: string;
  meet_link: string;
  start: string;
  end: string;
}

export interface AgentResponse {
  message: string;
  session_id: string;
  tool_calls: Array<{ name: string; result: Record<string, unknown> }> | null;
  meeting_confirmed: boolean;
  meeting_details: MeetingDetails | null;
}

export async function getMe(): Promise<User> {
  const { data } = await api.get<User>("/auth/me");
  return data;
}

export async function sendMessage(
  sessionId: string,
  message: string,
  timezone: string
): Promise<AgentResponse> {
  const { data } = await api.post<AgentResponse>("/agent/chat", {
    session_id: sessionId,
    message,
    timezone,
  });
  return data;
}

export async function logout(): Promise<void> {
  await api.post("/auth/logout");
}
