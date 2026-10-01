import type { ChatResponse, HistoryTurn } from "../api-types";
import type { BotMessage, ChatMessage } from "../types";

export function assertNever(value: never): never {
  throw new Error("不支援的訊息類型");
}

export function toChatMessage(response: ChatResponse): BotMessage {
  switch (response.type) {
    case "text":
      return { role: "bot", type: "text", text: response.text };
    case "product":
      return {
        role: "bot",
        type: "product",
        text: response.text,
        source: response.source,
        sources: response.sources,
      };
    case "order":
      return {
        role: "bot",
        type: "order",
        code: response.code,
        status: response.status,
        eta: response.eta,
        items: response.items,
      };
    default:
      return assertNever(response);
  }
}

export function buildHistory(messages: ChatMessage[]): HistoryTurn[] {
  return messages.flatMap((message): HistoryTurn[] => {
    if (
      message.type === "order" ||
      typeof message.text !== "string" ||
      !message.text.length
    )
      return [];
    return [
      {
        role: message.role === "user" ? "user" : "assistant",
        content: message.text,
      },
    ];
  });
}
