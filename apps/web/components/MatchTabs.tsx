"use client";

import type { ReactNode } from "react";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export function MatchTabs({
  overview,
  stats,
  timeline,
}: {
  overview: ReactNode;
  stats: ReactNode;
  timeline: ReactNode;
}) {
  return (
    <Tabs defaultValue="overview">
      <TabsList className="grid w-full grid-cols-3">
        <TabsTrigger value="overview">Overview</TabsTrigger>
        <TabsTrigger value="stats">Stats</TabsTrigger>
        <TabsTrigger value="timeline">Timeline</TabsTrigger>
      </TabsList>
      <TabsContent value="overview" className="space-y-4 pt-2">
        {overview}
      </TabsContent>
      <TabsContent value="stats" className="pt-2">
        {stats}
      </TabsContent>
      <TabsContent value="timeline" className="pt-2">
        {timeline}
      </TabsContent>
    </Tabs>
  );
}
