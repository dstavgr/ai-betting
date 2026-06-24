import { NextResponse } from "next/server";

import { askFixtureBetChat } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const payload = (await request.json()) as { fixtureId?: string | number; question?: string };
    const fixtureId = payload.fixtureId;
    const question = typeof payload.question === "string" ? payload.question.trim() : "";

    if (!fixtureId || !question) {
      return NextResponse.json({ error: "fixtureId and question are required" }, { status: 400 });
    }

    const forwardedFor = request.headers.get("x-forwarded-for") || undefined;
    const response = await askFixtureBetChat(fixtureId, question, forwardedFor);
    return NextResponse.json(response);
  } catch {
    return NextResponse.json({ error: "Bet AI chat is unavailable right now" }, { status: 502 });
  }
}
