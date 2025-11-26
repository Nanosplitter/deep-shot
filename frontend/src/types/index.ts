// TypeScript interfaces matching backend schemas

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface NFLQuery {
  input: string;
}

export interface NFLChatInput {
  messages: ChatMessage[];
}

export interface NFLResponse {
  response: string;
  code_generated: string | null;
  raw_data: Record<string, unknown> | null;
  attempts: number;
}
