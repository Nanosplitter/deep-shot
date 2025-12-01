import {
  type UIMessage,
  createUIMessageStream,
  createUIMessageStreamResponse,
} from "ai";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

interface NFLResponse {
  response: string;
  code_generated: string | null;
  raw_data: Record<string, unknown> | null;
  attempts: number;
  used_fallback: boolean;
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
    const backendResponse = await fetch(`${BACKEND_URL}/nfl/chat`, {
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

    const data: NFLResponse = await backendResponse.json();

    // Use AI SDK v5's createUIMessageStream for proper SSE format
    const textId = `text_${Date.now()}`;
    const toolCallId = `nfl_query_${Date.now()}`;

    const stream = createUIMessageStream({
      execute: async ({ writer }) => {
        // Write text content using start/delta/end pattern
        writer.write({ type: "text-start", id: textId });
        writer.write({ type: "text-delta", id: textId, delta: data.response });
        writer.write({ type: "text-end", id: textId });

        // If code was generated, add tool call parts
        if (data.code_generated) {
          // Tool input start
          writer.write({
            type: "tool-input-start",
            toolCallId,
            toolName: "nfl_query",
          });

          // Tool input available (with full args)
          writer.write({
            type: "tool-input-available",
            toolCallId,
            toolName: "nfl_query",
            input: {
              code: data.code_generated,
              attempts: data.attempts,
              used_fallback: data.used_fallback,
            },
          });

          // Tool output available (result)
          writer.write({
            type: "tool-output-available",
            toolCallId,
            output: data.raw_data ?? { success: true },
          });
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
