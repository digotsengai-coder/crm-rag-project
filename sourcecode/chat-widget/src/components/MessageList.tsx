import { Fragment, useEffect, useRef, type ReactNode } from "react";
import type { ChatMessage } from "../types";
import { assertNever } from "../utils/messages";
import { tw } from "../utils/tw";
import { widgetUi } from "../widgetStyles";
import ProductAnswer from "./ProductAnswer";
import OrderCard from "./OrderCard";
import TypingIndicator from "./TypingIndicator";

function Message({ message }: { message: ChatMessage }) {
  switch (message.type) {
    case "text":
      return (
        <div
          className={tw(
            widgetUi.row,
            message.role === "user" ? widgetUi.rowUser : widgetUi.rowBot,
          )}
        >
          <div
            className={tw(
              widgetUi.bubble,
              message.role === "user"
                ? widgetUi.bubbleUser
                : widgetUi.bubbleBot,
            )}
          >
            <p className={widgetUi.bubbleText}>{message.text}</p>
          </div>
        </div>
      );
    case "product":
      return <ProductAnswer text={message.text} sources={message.sources} />;
    case "order":
      return (
        <OrderCard
          code={message.code}
          status={message.status}
          eta={message.eta}
          items={message.items}
        />
      );
    default:
      return assertNever(message);
  }
}
export default function MessageList({
  messages,
  isSending,
  header,
}: {
  messages: ChatMessage[];
  isSending: boolean;
  header?: ReactNode;
}) {
  const listRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (listRef.current)
      listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages, isSending]);
  return (
    <div className={widgetUi.messages} ref={listRef}>
      {messages.map((message, index) => (
        <Fragment key={index}>
          <Message message={message} />
          {index === 0 && header}
        </Fragment>
      ))}
      {isSending && <TypingIndicator />}
    </div>
  );
}
