"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Send, LogOut, CalendarClock } from "lucide-react";
import { format } from "date-fns";
import {
  getMe,
  sendMessage,
  logout,
  type User,
  type MeetingDetails,
  type TimeSlot,
} from "@/lib/api";
import { MeetingConfirmationCard } from "@/components/MeetingConfirmationCard";
import { TimeSlotButtons } from "@/components/TimeSlotButtons";
import { TypingIndicator } from "@/components/TypingIndicator";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  meetingDetails?: MeetingDetails;
  proposedSlots?: TimeSlot[];
}

export default function ChatPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string>("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

  useEffect(() => {
    getMe()
      .then((u) => {
        setUser(u);
        setMessages([
          {
            id: "welcome",
            role: "assistant",
            content: `Hi ${u.name.split(" ")[0]}! 👋 I'm your AI scheduling assistant. Tell me who you'd like to meet with and when, and I'll check everyone's availability and set it up for you.`,
            timestamp: new Date(),
          },
        ]);
      })
      .catch(() => router.push("/"));
  }, [router]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSend = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return;
      setError(null);

      const userMsg: Message = {
        // crypto.randomUUID() requires HTTPS in production (secure context).
        id: crypto.randomUUID(),
        role: "user",
        content: text,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setIsLoading(true);

      try {
        const response = await sendMessage(sessionId, text, timezone);
        if (response.session_id && !sessionId) {
          setSessionId(response.session_id);
        }

        const assistantMsg: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.message,
          timestamp: new Date(),
          meetingDetails: response.meeting_details ?? undefined,
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch {
        setError("Something went wrong. Please try again.");
      } finally {
        setIsLoading(false);
        inputRef.current?.focus();
      }
    },
    [sessionId, isLoading, timezone]
  );

  const handleSlotSelect = useCallback(
    (slot: TimeSlot) => {
      const start = new Date(slot.start);
      const end = new Date(slot.end);
      const text = `I'll take ${format(start, "EEEE, MMMM d")} from ${format(start, "h:mm a")} to ${format(end, "h:mm a")}.`;
      handleSend(text);
    },
    [handleSend]
  );

  const handleLogout = async () => {
    await logout();
    router.push("/");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend(input);
    }
  };

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <div className="bg-indigo-100 rounded-full p-2">
            <CalendarClock className="w-5 h-5 text-indigo-600" />
          </div>
          <div>
            <h1 className="font-semibold text-slate-800 text-sm leading-none">
              AI Scheduling Agent
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">{user.email}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-1.5 text-slate-500 hover:text-slate-700 text-sm transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Logout
        </button>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-1">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} mb-4`}>
            {msg.role === "assistant" && (
              <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-xs font-bold text-indigo-600 shrink-0 mr-2 mt-0.5">
                AI
              </div>
            )}
            <div className="max-w-[75%]">
              <div
                className={
                  msg.role === "user"
                    ? "bg-indigo-600 text-white rounded-2xl rounded-br-sm px-4 py-3 shadow-sm"
                    : "bg-white border border-slate-200 text-slate-800 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm"
                }
              >
                <p className="text-sm whitespace-pre-wrap leading-relaxed">
                  {msg.content}
                </p>
              </div>
              {msg.meetingDetails && (
                <MeetingConfirmationCard
                  details={msg.meetingDetails}
                  timezone={timezone}
                />
              )}
              {msg.proposedSlots && msg.proposedSlots.length > 0 && (
                <TimeSlotButtons
                  slots={msg.proposedSlots}
                  onSelect={handleSlotSelect}
                />
              )}
              <p className="text-xs text-slate-400 mt-1 px-1">
                {format(msg.timestamp, "h:mm a")}
              </p>
            </div>
          </div>
        ))}
        {isLoading && <TypingIndicator />}
        <div ref={messagesEndRef} />
      </div>

      {/* Error banner */}
      {error && (
        <div className="mx-4 mb-2 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-2">
          {error}
        </div>
      )}

      {/* Input */}
      <div className="bg-white border-t border-slate-200 px-4 py-3">
        <div className="flex items-end gap-2 max-w-3xl mx-auto">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message… (Enter to send, Shift+Enter for new line)"
            rows={1}
            className="flex-1 resize-none rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent max-h-32 overflow-y-auto"
            style={{ minHeight: "48px" }}
          />
          <button
            onClick={() => handleSend(input)}
            disabled={!input.trim() || isLoading}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white rounded-xl p-3 transition-colors shrink-0"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
