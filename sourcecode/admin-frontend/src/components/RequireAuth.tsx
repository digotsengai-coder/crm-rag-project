import Button from "antd/es/button";
import Spin from "antd/es/spin";
import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { fullscreenSpinProps } from "../config/spin";
import { tw } from "../utils/tw";

const initializationErrorStyles = {
  container: tw("grid min-h-60 place-items-center p-6 text-center"),
  content: tw("grid max-w-lg gap-3"),
  title: tw("m-0 text-lg text-admin-heading"),
  message: tw("m-0 text-caption text-admin-text-subtle"),
  retryButton: tw("mx-auto w-fit"),
};

export default function RequireAuth({ children }: { children: ReactNode }) {
  const { token, isInitializing, initializationError, retryInitialization } =
    useAuth();
  if (!token) return <Navigate to="/login" replace />;
  if (isInitializing) return <Spin {...fullscreenSpinProps} />;
  if (initializationError)
    return (
      <div className={initializationErrorStyles.container} role="alert">
        <div className={initializationErrorStyles.content}>
          <h1 className={initializationErrorStyles.title}>無法驗證登入狀態</h1>
          <p className={initializationErrorStyles.message}>
            {initializationError}
          </p>
          <Button
            className={initializationErrorStyles.retryButton}
            onClick={retryInitialization}
            type="primary"
          >
            重新嘗試
          </Button>
        </div>
      </div>
    );
  return <>{children}</>;
}
