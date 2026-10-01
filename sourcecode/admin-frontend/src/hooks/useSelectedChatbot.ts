import { useAuth } from "../auth/AuthContext";
import { useChatbotsQuery } from "./useAdminQueries";

export function useSelectedChatbot() {
  const { token, selectedChatbotId, selectChatbot } = useAuth();
  const chatbotsQuery = useChatbotsQuery(token);
  const chatbot = chatbotsQuery.data?.find(
    (item) => item.id === selectedChatbotId,
  );

  return {
    ...chatbotsQuery,
    chatbot,
    selectedChatbotId,
    selectChatbot,
  };
}
