import { useEffect, useState } from "react";
import type { ProviderId, ProviderInfo } from "../api-types";
import { fetchProviders } from "../api/chat";

export function useProviders(clientId: string) {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [provider, setProvider] = useState<ProviderId>("google");
  useEffect(() => {
    let active = true;
    void fetchProviders(clientId)
      .then((list) => {
        if (!active) return;
        setProviders(list);
        const configured =
          list.find((entry) => entry.id === "google" && entry.configured) ??
          list.find((entry) => entry.configured);
        if (configured) setProvider(configured.id);
      })
      .catch(() => {
        // 載入失敗時維持既有預設，避免套用不完整的模型清單。
      });
    return () => {
      active = false;
    };
  }, [clientId]);
  return { providers, provider, setProvider };
}
