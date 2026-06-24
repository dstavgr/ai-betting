import { NextResponse } from "next/server";

import { getFixtureNews } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const fixtureId = searchParams.get("fixtureId");

    if (!fixtureId) {
      return NextResponse.json({ error: "fixtureId is required" }, { status: 400 });
    }

    const response = await getFixtureNews(fixtureId);
    return NextResponse.json(response);
  } catch {
    return NextResponse.json({ error: "Fixture news is unavailable right now" }, { status: 502 });
  }
}
