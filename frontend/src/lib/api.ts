import axios from 'axios';
import { ChatResponse, User } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

export async function getCurrentUser(): Promise<User | null> {
  try {
    const response = await apiClient.get('/api/auth/me');
    return response.data;
  } catch {
    return null;
  }
}

export async function sendChatMessage(
  messages: Array<{ role: string; content: string }>
): Promise<ChatResponse> {
  const response = await apiClient.post('/api/agent/chat', { messages });
  return response.data;
}

export function getLoginUrl(): string {
  return `${API_BASE}/api/auth/login`;
}

export async function logout(): Promise<void> {
  await apiClient.post('/api/auth/logout');
}
