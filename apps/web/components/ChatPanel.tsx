"use client";

import { MessageCircle } from "lucide-react";

import { BetChat } from "@/components/BetChat";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";

type ChatPanelProps = {
  fixtureId: number;
  fixtureLabel: string;
};

export function ChatPanel({ fixtureId, fixtureLabel }: ChatPanelProps) {
  return (
    <>
      <aside className="hidden lg:sticky lg:top-24 lg:block">
        <BetChat fixtureId={fixtureId} fixtureLabel={fixtureLabel} />
      </aside>

      <div className="lg:hidden">
        <Sheet>
          <SheetTrigger asChild>
            <Button className="fixed bottom-20 right-4 z-40 shadow-lg" size="lg">
              <MessageCircle className="size-4" />
              Ask Bet AI
            </Button>
          </SheetTrigger>
          <SheetContent className="h-dvh max-w-none border-l-0 bg-background p-4">
            <SheetTitle className="sr-only">Ask Bet AI</SheetTitle>
            <div className="h-full overflow-y-auto pt-8">
              <BetChat fixtureId={fixtureId} fixtureLabel={fixtureLabel} />
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </>
  );
}
