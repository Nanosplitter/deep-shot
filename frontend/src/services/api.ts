import type { NFLChatInput, NFLQuery, NFLResponse } from "../types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const TIMEOUT_MS = 120000; // 120 seconds for long-running queries

async function fetchWithTimeout(url: string, options: RequestInit, timeout: number = TIMEOUT_MS): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    return response;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function queryNFL(query: NFLQuery): Promise<NFLResponse> {
  const response = await fetchWithTimeout(`${API_URL}/api/nfl/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(query)
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

export async function chatNFL(input: NFLChatInput): Promise<NFLResponse> {
  const response = await fetchWithTimeout(`${API_URL}/api/nfl/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(input)
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

export async function healthCheck(): Promise<{ status: string }> {
  const response = await fetch(`${API_URL}/health`);

  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }

  return response.json();
}
