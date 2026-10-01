import type { SourceRef } from "./api-types";

export type BotMessage =
  | { role: "bot"; type: "text"; text: string }
  | {
      role: "bot";
      type: "product";
      text: string;
      source: string | null;
      sources: SourceRef[] | null;
    }
  | {
      role: "bot";
      type: "order";
      code: string;
      status: number;
      eta: string;
      items: string;
    };

export type ChatMessage =
  { role: "user"; type: "text"; text: string } | BotMessage;
