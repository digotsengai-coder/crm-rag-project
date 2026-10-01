import { tw } from "../utils/tw";
import { widgetUi } from "../widgetStyles";

export default function TypingIndicator() {
  return (
    <div className={tw(widgetUi.row, widgetUi.rowBot)}>
      <div className={tw(widgetUi.bubble, widgetUi.bubbleBot, widgetUi.typing)}>
        <span className={widgetUi.dot} />
        <span className={tw(widgetUi.dot, widgetUi.dotSecond)} />
        <span className={tw(widgetUi.dot, widgetUi.dotThird)} />
      </div>
    </div>
  );
}
