import { requestAdminApi } from "./apiClient";

export interface QuestionCategory {
  name: string;
  count: number;
  questions: string[];
}

export interface PeriodSummary {
  start_date: string;
  end_date: string;
  question_count: number;
  categories: QuestionCategory[];
  meaningless_questions: string[];
  needs_merchant_attention: string[];
  mcp_questions: string[];
  summary: string;
}

export async function getPeriodSummary(
  token: string,
  chatbotId: string,
  startDate: string,
  endDate: string,
): Promise<PeriodSummary> {
  const searchParams = new URLSearchParams({
    chatbot_id: chatbotId,
    start_date: startDate,
    end_date: endDate,
  });
  return requestAdminApi<PeriodSummary>(
    `/api/admin/summary?${searchParams.toString()}`,
    { token },
  );
}
