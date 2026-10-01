export const queryKeys = {
  session: { me: ["session", "me"] as const },
  chatbots: { list: ["chatbots", "list"] as const },
  accounts: {
    platform: ["accounts", "platform"] as const,
    byChatbot: (chatbotId: string) =>
      ["accounts", "chatbot", chatbotId] as const,
  },
  documents: {
    byChatbot: (chatbotId: string) => ["documents", chatbotId] as const,
  },
  summary: {
    byPeriod: (chatbotId: string, startDate: string, endDate: string) =>
      ["summary", chatbotId, startDate, endDate] as const,
  },
  auditLog: {
    byChatbot: (chatbotId: string) => ["audit-log", chatbotId] as const,
  },
  orders: {
    list: ["orders", "list"] as const,
    detail: (orderId: string) => ["orders", "detail", orderId] as const,
  },
};
