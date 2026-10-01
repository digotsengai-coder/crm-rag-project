import Alert from "antd/es/alert";
import Card from "antd/es/card";
import DatePicker from "antd/es/date-picker";
import Empty from "antd/es/empty";
import Tag from "antd/es/tag";
import Table from "antd/es/table";
import Typography from "antd/es/typography";
import { Pie } from "@ant-design/plots";
import type { ColumnsType } from "antd/es/table";
import dayjs, { type Dayjs } from "dayjs";
import type { ReactNode } from "react";
import { useState } from "react";
import { Navigate } from "react-router-dom";
import AdminPageLayout from "../components/AdminPageLayout";
import CardLoading from "../components/CardLoading";
import ChatbotSettingsTabs from "../components/ChatbotSettingsTabs";
import { useAuth } from "../auth/AuthContext";
import type { PeriodSummary } from "../api/summary";
import { useSummaryQuery } from "../hooks/useAdminQueries";
import { ui } from "../uiStyles";

const { Paragraph, Text } = Typography;

function getUtcToday() {
  return dayjs(new Date().toISOString().slice(0, 10));
}

// 後端限制區間最多 31 日（含起訖）；預設帶入最近 7 天。
const MAX_RANGE_DAYS = 31;

function getDefaultRange(): [Dayjs, Dayjs] {
  const today = getUtcToday();
  return [today.subtract(6, "day"), today];
}

interface ChartItem {
  key: string;
  label: string;
  questions: string[];
  count: number;
}

interface ChartDatum {
  key: string;
  label: string;
  value: number;
}

// 分類統計：常見主題各一區，其後固定為 MCP、需商家關注、無意義訊息。
function buildChartItems(data: PeriodSummary): ChartItem[] {
  const topics = [...data.categories]
    .sort((a, b) => b.count - a.count)
    .map((category) => ({
      key: `topic:${category.name}`,
      label: category.name,
      questions: category.questions ?? [],
      count: category.count,
    }));
  const groups = [
    {
      key: "mcp",
      label: "MCP 訊息",
      questions: data.mcp_questions ?? [],
    },
    {
      key: "attention",
      label: "需商家關注",
      questions: data.needs_merchant_attention,
    },
    {
      key: "meaningless",
      label: "無意義訊息",
      questions: data.meaningless_questions,
    },
  ].map((group) => ({ ...group, count: group.questions.length }));
  return [...topics, ...groups];
}

function SummaryBarChart({ items }: { items: ChartItem[] }) {
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const selected = items.find((item) => item.key === selectedKey);
  const chartData: ChartDatum[] = items.map(({ key, label, count }) => ({
    key,
    label,
    value: count,
  }));

  return (
    <div className={ui.summaryChartLayout}>
      <div className={ui.summaryChart}>
        <Pie
          aria-label="提問分類圓餅圖"
          data={chartData}
          angleField="value"
          colorField="label"
          autoFit
          className={ui.summaryPieChart}
          height={300}
          innerRadius={0.62}
          legend={{ position: "bottom" }}
          tooltip={{ items: [{ field: "value", name: "提問數" }] }}
          interaction={{
            elementSelect: { single: true },
            legendFilter: false,
          }}
          state={{
            selected: { lineWidth: 0, strokeOpacity: 0 },
            unselected: { lineWidth: 0, strokeOpacity: 0 },
          }}
          style={{
            fillOpacity: (datum: ChartDatum) =>
              !selectedKey || datum.key === selectedKey ? 1 : 0.28,
            lineWidth: 0,
            strokeOpacity: 0,
          }}
          onReady={(plot) => {
            plot.chart.on(
              "element:select",
              (event: { data?: { data?: unknown } }) => {
                const eventData = event.data?.data;
                const datum = (
                  Array.isArray(eventData) ? eventData[0] : eventData
                ) as ChartDatum | undefined;
                if (datum?.key) setSelectedKey(datum.key);
              },
            );
            plot.chart.on("element:unselect", () => setSelectedKey(null));
          }}
        />
      </div>
      <section aria-live="polite" className={ui.summaryChartDetails}>
        {selected ? (
          <>
            <div className={ui.summaryChartDetailsHeading}>
              <Text strong>{selected.label}</Text>
              <Tag color="blue">{selected.count} 則提問</Tag>
            </div>
            <MessageList items={selected.questions} />
          </>
        ) : (
          <Text type="secondary">點選圖表區塊，查看分類明細</Text>
        )}
      </section>
    </div>
  );
}

interface SummaryTableRow {
  key: string;
  label: string;
  content: ReactNode;
}

const summaryColumns: ColumnsType<SummaryTableRow> = [
  {
    title: "摘要欄位",
    dataIndex: "label",
    key: "label",
    width: 100,
  },
  {
    title: "內容",
    dataIndex: "content",
    key: "content",
  },
];

function MessageList({ items }: { items: string[] }) {
  if (items.length === 0) return <Text type="secondary">無</Text>;
  return (
    <ul className={ui.summaryTableList}>
      {items.map((item, index) => (
        <li key={`${item}-${index}`}>{item}</li>
      ))}
    </ul>
  );
}

/**
 * 客服摘要：指定週期內的提問主題摘要。
 * 依 AuthContext.selectedChatbotId 過濾，跟 RAG 頁面一樣的模式——切換公司時這裡也要
 * 重新拉取，只看得到目前選定公司的顧客提問內容。
 */
export default function SummaryPage() {
  const { token, selectedChatbotId } = useAuth();
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs]>(getDefaultRange);
  const summaryQuery = useSummaryQuery(
    token,
    selectedChatbotId,
    dateRange[0].format("YYYY-MM-DD"),
    dateRange[1].format("YYYY-MM-DD"),
  );
  const { data } = summaryQuery;

  if (!selectedChatbotId) return <Navigate to="/chatbots" replace />;

  const summaryRows: SummaryTableRow[] = data
    ? [
        {
          key: "question_count",
          label: "提問數",
          content: <Tag color="blue">{data.question_count} 則提問</Tag>,
        },
        {
          key: "summary",
          label: "摘要",
          content: (
            <Paragraph className={ui.summaryTableParagraph}>
              {data.summary}
            </Paragraph>
          ),
        },
        {
          key: "chart",
          label: "分類統計",
          content: (
            <SummaryBarChart
              key={`${data.start_date}_${data.end_date}`}
              items={buildChartItems(data)}
            />
          ),
        },
      ]
    : [];

  return (
    <AdminPageLayout
      title="客服摘要"
      description="查看指定期間（最多一個月）內使用者向聊天機器人提問的主題摘要。"
    >
      <ChatbotSettingsTabs />
      <Card className={ui.settingsCard}>
        <div className={ui.summaryPeriodControl}>
          <Text type="secondary">摘要期間（最多 31 日）</Text>
          <DatePicker.RangePicker
            aria-label="客服摘要期間"
            allowClear={false}
            disabled={summaryQuery.isFetching}
            disabledDate={(current, info) => {
              if (current.isAfter(getUtcToday(), "day")) return true;
              // 選了起日或迄日後，另一端限制在 31 日內。
              const anchor = info.from;
              return (
                !!anchor &&
                Math.abs(current.diff(anchor, "day")) >= MAX_RANGE_DAYS
              );
            }}
            format="YYYY-MM-DD"
            value={dateRange}
            onChange={(dates) => {
              if (dates?.[0] && dates[1]) setDateRange([dates[0], dates[1]]);
            }}
          />
        </div>
        {summaryQuery.isLoading ? (
          <CardLoading label="客服摘要讀取中" />
        ) : summaryQuery.error ? (
          <Alert type="error" showIcon message={summaryQuery.error.message} />
        ) : data ? (
          data.question_count === 0 ? (
            <Empty description="這個期間沒有使用者提問紀錄" />
          ) : (
            <Table<SummaryTableRow>
              aria-label="客服摘要資料表"
              className={ui.summaryTable}
              columns={summaryColumns}
              dataSource={summaryRows}
              pagination={false}
              rowKey="key"
              size="small"
              tableLayout="fixed"
            />
          )
        ) : null}
      </Card>
    </AdminPageLayout>
  );
}
