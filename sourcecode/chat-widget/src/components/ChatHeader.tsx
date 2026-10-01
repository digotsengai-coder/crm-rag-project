import { Sparkles, X } from "lucide-react";
import { widgetUi } from "../widgetStyles";

interface ChatHeaderProps {
  brandName: string;
  logoUrl: string | null;
  onClose: () => void;
}

export default function ChatHeader({
  brandName,
  logoUrl,
  onClose,
}: ChatHeaderProps) {
  return (
    <div className={widgetUi.header}>
      <div className={widgetUi.headerBrand}>
        <div className={widgetUi.headerIcon}>
          {logoUrl ? (
            <img className={widgetUi.headerLogo} src={logoUrl} alt="" />
          ) : (
            <Sparkles size={17} />
          )}
        </div>
        <div>
          <div className={widgetUi.headerTitle}>{brandName}</div>
          <div className={widgetUi.headerStatus}>
            <span className={widgetUi.statusDot} />
            線上服務中
          </div>
        </div>
      </div>
      <button
        type="button"
        className={widgetUi.closeButton}
        aria-label="收合聊天視窗"
        onClick={onClose}
      >
        <X size={18} />
      </button>
    </div>
  );
}
