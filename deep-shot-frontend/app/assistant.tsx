"use client";

import {
  AssistantRuntimeProvider,
  ThreadListPrimitive,
} from "@assistant-ui/react";
import {
  useChatRuntime,
  AssistantChatTransport,
} from "@assistant-ui/react-ai-sdk";
import { Thread } from "@/components/assistant-ui/thread";
import { PlusIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SettingsProvider } from "@/lib/settings-context";
import { SettingsDialog } from "@/components/settings-dialog";

export const Assistant = () => {
  const runtime = useChatRuntime({
    transport: new AssistantChatTransport({
      api: "/api/chat",
    }),
  });

  return (
    <SettingsProvider>
      <AssistantRuntimeProvider runtime={runtime}>
        <div className="flex h-dvh w-full flex-col">
          <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
            <ThreadListPrimitive.New asChild>
              <Button variant="ghost" size="sm" className="gap-2">
                <PlusIcon className="h-4 w-4" />
                New Chat
              </Button>
            </ThreadListPrimitive.New>
            <div className="flex-1 text-center">
              <span className="text-lg font-semibold">Deep Shot</span>
              <span className="ml-2 text-muted-foreground">
                NFL Stats Assistant
              </span>
            </div>
            <SettingsDialog />
          </header>
          <div className="flex-1 overflow-hidden">
            <Thread />
          </div>
        </div>
      </AssistantRuntimeProvider>
    </SettingsProvider>
  );
};
