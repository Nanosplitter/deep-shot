import {
  type UIMessage,
  createUIMessageStream,
  createUIMessageStreamResponse,
  generateId,
} from "ai";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

interface NFLResponse {
  response: string;
  code_generated: string | null;
  raw_data: Record<string, unknown> | null;
  attempts: number;
  used_fallback: boolean;
}

interface StreamEvent {
  event: "status" | "complete" | "error";
  step: string;
  message: string;
  attempt?: number;
  data?: NFLResponse;
}

export async function POST(req: Request) {
  const { messages }: { messages: UIMessage[] } = await req.json();

  // Convert messages to the format expected by the backend
  const backendMessages = messages.map((msg) => {
    let content = "";
    if (msg.parts) {
      content = msg.parts
        .map((part) => {
          if (part.type === "text") return part.text;
          return "";
        })
        .filter(Boolean)
        .join("");
    }
    return {
      role: msg.role,
      content,
    };
  });

  try {
    // Use the streaming endpoint
    const backendResponse = await fetch(`${BACKEND_URL}/nfl/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ messages: backendMessages }),
    });

    if (!backendResponse.ok) {
      const errorText = await backendResponse.text();
      return new Response(
        JSON.stringify({ error: `Backend error: ${errorText}` }),
        {
          status: backendResponse.status,
          headers: { "Content-Type": "application/json" },
        },
      );
    }

    const textId = generateId();
    const toolCallId = `nfl_query_${Date.now()}`;
    const reasoningId = generateId();

    const stream = createUIMessageStream({
      execute: async ({ writer }) => {
        const reader = backendResponse.body?.getReader();
        if (!reader) {
          throw new Error("No response body");
        }

        const decoder = new TextDecoder();
        let buffer = "";
        let finalData: NFLResponse | null = null;
        let reasoningStarted = false;
        let currentStatus = "";

        console.log("[route.ts] Starting to read backend stream");

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) {
              console.log("[route.ts] Stream done");
              break;
            }

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
              if (line.startsWith("data: ")) {
                const jsonStr = line.slice(6).trim();
                if (!jsonStr) continue;

                try {
                  const event: StreamEvent = JSON.parse(jsonStr);
                  console.log("[route.ts] Received event:", event);

                  if (event.event === "status") {
                    // Stream status as reasoning parts
                    if (!reasoningStarted) {
                      writer.write({
                        type: "reasoning-start",
                        id: reasoningId,
                      });
                      reasoningStarted = true;
                    }

                    // Add the new status message
                    const statusText = event.message + "\n";
                    currentStatus += statusText;
                    writer.write({
                      type: "reasoning-delta",
                      id: reasoningId,
                      delta: statusText,
                    });
                    console.log("[route.ts] Writing reasoning:", event.message);
                  } else if (event.event === "complete" && event.data) {
                    finalData = event.data;
                  } else if (event.event === "error") {
                    if (event.data) {
                      finalData = event.data;
                    }
                  }
                } catch {
                  // Skip malformed JSON
                }
              }
            }
          }
        } finally {
          reader.releaseLock();
        }

        // End reasoning if we started it
        if (reasoningStarted) {
          writer.write({
            type: "reasoning-end",
            id: reasoningId,
          });
        }

        if (finalData) {
          // Write the final response as text
          writer.write({ type: "text-start", id: textId });
          writer.write({
            type: "text-delta",
            id: textId,
            delta: finalData.response,
          });
          writer.write({ type: "text-end", id: textId });

          // If code was generated, add tool call parts
          if (finalData.code_generated) {
            writer.write({
              type: "tool-input-start",
              toolCallId,
              toolName: "nfl_query",
            });

            writer.write({
              type: "tool-input-available",
              toolCallId,
              toolName: "nfl_query",
              input: {
                code: finalData.code_generated,
                attempts: finalData.attempts,
                used_fallback: finalData.used_fallback,
              },
            });

            writer.write({
              type: "tool-output-available",
              toolCallId,
              output: finalData.raw_data ?? { success: true },
            });
          }
        }
      },
    });

    return createUIMessageStreamResponse({ stream });
  } catch (error) {
    console.error("Error calling backend:", error);
    return new Response(
      JSON.stringify({ error: "Failed to connect to backend" }),
      { status: 500, headers: { "Content-Type": "application/json" } },
    );
  }
}
