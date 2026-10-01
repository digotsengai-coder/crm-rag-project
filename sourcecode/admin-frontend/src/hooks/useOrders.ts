import { useOrdersQuery } from "./useAdminQueries";

export function useOrders() {
  const query = useOrdersQuery();
  return {
    orders: query.data?.orders ?? [],
    isLoading: query.isLoading,
    error: query.error?.message ?? null,
    reload: () => void query.refetch(),
  };
}
