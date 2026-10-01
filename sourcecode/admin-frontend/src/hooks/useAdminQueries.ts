import { useMutation, useQuery } from "@tanstack/react-query";
import { listAccounts } from "../api/accounts";
import { listAuditLog } from "../api/auditLog";
import {
  createChatbot,
  deleteChatbot,
  listChatbots,
  updateChatbot,
} from "../api/chatbots";
import { fetchDocuments } from "../api/documents";
import { getOrders, getOrder } from "../api/orders";
import { queryKeys } from "../api/queryKeys";
import { getPeriodSummary } from "../api/summary";
import { getMe } from "../api/auth";
import { queryClient } from "../queryClient";
import type { ChatbotInfo } from "../types/auth";

export function useMeQuery(token: string | null) {
  return useQuery({
    queryKey: queryKeys.session.me,
    queryFn: () => getMe(token!),
    enabled: Boolean(token),
  });
}

export function useChatbotsQuery(token: string | null) {
  return useQuery({
    queryKey: queryKeys.chatbots.list,
    queryFn: () => listChatbots(token!),
    enabled: Boolean(token),
  });
}

export function useAccountsQuery(token: string | null, chatbotId?: string) {
  return useQuery({
    queryKey: chatbotId
      ? queryKeys.accounts.byChatbot(chatbotId)
      : queryKeys.accounts.platform,
    queryFn: () => listAccounts(token!, chatbotId),
    enabled: Boolean(token),
  });
}

export function useDocumentsQuery(
  token: string | null,
  chatbotId: string | null,
) {
  return useQuery({
    queryKey: queryKeys.documents.byChatbot(chatbotId ?? ""),
    queryFn: () => fetchDocuments(token!, chatbotId!),
    enabled: Boolean(token && chatbotId),
  });
}

export function useSummaryQuery(
  token: string | null,
  chatbotId: string | null,
  startDate: string,
  endDate: string,
) {
  return useQuery({
    queryKey: queryKeys.summary.byPeriod(chatbotId ?? "", startDate, endDate),
    queryFn: () => getPeriodSummary(token!, chatbotId!, startDate, endDate),
    enabled: Boolean(token && chatbotId),
  });
}

export function useAuditLogQuery(
  token: string | null,
  chatbotId: string | null,
) {
  return useQuery({
    queryKey: queryKeys.auditLog.byChatbot(chatbotId ?? ""),
    queryFn: () => listAuditLog(token!, chatbotId!),
    enabled: Boolean(token && chatbotId),
  });
}

export function useOrdersQuery() {
  return useQuery({
    queryKey: queryKeys.orders.list,
    queryFn: ({ signal }) => getOrders(signal),
  });
}

export function useOrderQuery(orderId: string) {
  return useQuery({
    queryKey: queryKeys.orders.detail(orderId),
    queryFn: ({ signal }) => getOrder(orderId, signal),
    enabled: Boolean(orderId),
  });
}

function replaceChatbot(updated: ChatbotInfo) {
  queryClient.setQueryData<ChatbotInfo[]>(queryKeys.chatbots.list, (current) =>
    current?.map((item) => (item.id === updated.id ? updated : item)),
  );
}

export function useCreateChatbotMutation(token: string) {
  return useMutation({
    mutationFn: (params: Parameters<typeof createChatbot>[1]) =>
      createChatbot(token, params),
    onSuccess: (created) => {
      queryClient.setQueryData<ChatbotInfo[]>(
        queryKeys.chatbots.list,
        (current) => [...(current ?? []), created],
      );
    },
  });
}

export function useUpdateChatbotMutation(token: string) {
  return useMutation({
    mutationFn: ({
      chatbotId,
      params,
    }: {
      chatbotId: string;
      params: Parameters<typeof updateChatbot>[2];
    }) => updateChatbot(token, chatbotId, params),
    onSuccess: (updated) => {
      replaceChatbot(updated);
      queryClient.invalidateQueries({
        queryKey: queryKeys.auditLog.byChatbot(updated.id),
      });
    },
  });
}

export function useDeleteChatbotMutation(token: string) {
  return useMutation({
    mutationFn: (chatbotId: string) => deleteChatbot(token, chatbotId),
    onSuccess: (_, chatbotId) => {
      queryClient.setQueryData<ChatbotInfo[]>(
        queryKeys.chatbots.list,
        (current) => current?.filter((item) => item.id !== chatbotId),
      );
      queryClient.removeQueries({
        queryKey: ["accounts", "chatbot", chatbotId],
      });
      queryClient.removeQueries({ queryKey: ["documents", chatbotId] });
      queryClient.removeQueries({ queryKey: ["audit-log", chatbotId] });
      queryClient.removeQueries({ queryKey: ["summary", chatbotId] });
    },
  });
}
