"use client";

import { Bot, Loader2, Send, Sparkles, User } from "lucide-react";
import { FormEvent, useMemo, useRef, useState } from "react";

import { SectionCard } from "@/components/ui/section-card";
import type { FixtureBetChatResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

type BetChatProps = {
  fixtureId: number;
  fixtureLabel: string;
};

export function BetChat({ fixtureId, fixtureLabel }: BetChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [pending, setPending] = useState(false);
  const [warnings, setWarnings] = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const canSend = question.trim().length > 0 && !pending;
  const statusLabel = useMemo(() => (pending ? "Thinking" : "Ready"), [pending]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || pending) return;

    setQuestion("");
    setPending(true);
    setWarnings([]);
    setMessages((current) => [...current, { role: "user", content: trimmed }]);

    try {
      const response = await fetch("/api/fixture-chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fixtureId, question: trimmed }),
      });

      if (!response.ok) {
        throw new Error("Chat request failed");
      }

      const data = (await response.json()) as FixtureBetChatResponse;
      setMessages((current) => [...current, { role: "assistant", content: data.answer }]);
      setWarnings(data.warnings ?? []);
    } catch {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: "Bet AI chat is unavailable right now. The displayed recommendations and odds are still available.",
        },
      ]);
    } finally {
      setPending(false);
      inputRef.current?.focus();
    }
  }

  return (
    <SectionCard
      title="Ask Bet AI"
      action={
        <span className="inline-flex items-center gap-1">
          {pending ? <Loader2 className="size-3 animate-spin" /> : <Sparkles className="size-3" />}
          {statusLabel}
        </span>
      }
      className="flex min-h-[22rem] min-w-0 flex-col"
    >
      <div className="mb-3 rounded-lg border border-border bg-muted/35 px-3 py-2">
        <div className="flex min-w-0 items-center gap-2">
          <Bot className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          <span className="truncate text-sm font-semibold">{fixtureLabel}</span>
        </div>
        <div className="mt-0.5 text-[11px] text-muted-foreground">Research and education only. Not betting advice. 21+.</div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-2">
        <div className="max-h-[32rem] min-h-[11rem] flex-1 space-y-2 overflow-y-auto pr-1">
          {messages.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border bg-background p-4 text-sm leading-6 text-muted-foreground">
              Bet AI will answer only from this match, model signal, and displayed provider odds.
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={cn(
                  "rounded-lg px-3 py-2 text-sm leading-6",
                  message.role === "user"
                    ? "ml-8 bg-primary text-primary-foreground"
                    : "mr-8 border border-border bg-background text-foreground",
                )}
              >
                <span className="mb-1 flex items-center gap-1.5 text-[11px] font-semibold uppercase opacity-70">
                  {message.role === "user" ? <User className="size-3" aria-hidden="true" /> : <Bot className="size-3" aria-hidden="true" />}
                  {message.role === "user" ? "You" : "Bet AI"}
                </span>
                {message.content.split("\n").map((line, lineIndex) => (
                  <p key={`${index}-${lineIndex}`} className={lineIndex > 0 ? "mt-2" : undefined}>
                    {line}
                  </p>
                ))}
              </div>
            ))
          )}
          {pending ? (
            <div className="mr-8 rounded-lg border border-border bg-background px-3 py-2 text-sm text-muted-foreground">
              Checking the match context...
            </div>
          ) : null}
        </div>

        {warnings.length > 0 ? (
          <div className="space-y-1 rounded-lg border border-border bg-muted/35 p-2 text-[11px] leading-5 text-muted-foreground">
            {warnings.map((warning) => (
              <div key={warning}>{warning}</div>
            ))}
          </div>
        ) : null}

        <form onSubmit={submit} className="flex gap-2">
          <label className="min-w-0 flex-1">
            <span className="sr-only">Question</span>
            <input
              ref={inputRef}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="What is worth watching?"
              className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm outline-none transition-colors placeholder:text-muted-foreground focus-visible:border-muted-foreground"
            />
          </label>
          <button
            type="submit"
            disabled={!canSend}
            className="flex size-10 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
            aria-label="Send question"
          >
            {pending ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
          </button>
        </form>
      </div>
    </SectionCard>
  );
}
