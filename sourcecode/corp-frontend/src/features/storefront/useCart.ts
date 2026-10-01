import { useCallback, useEffect, useMemo, useState } from "react";
import type { CartItem, Product } from "./types";

const STORAGE_KEY = "crm-squad-store-cart";

interface StoredCartItem {
  product: Product;
  quantity: number;
}

function isCompleteProduct(product: unknown): product is Product {
  if (!product || typeof product !== "object") return false;
  const candidate = product as Partial<Product>;
  return (
    Number.isSafeInteger(candidate.productID) &&
    typeof candidate.imageUrl === "string" &&
    candidate.imageUrl.length > 0 &&
    typeof candidate.originalPrice === "number" &&
    Number.isFinite(candidate.originalPrice) &&
    typeof candidate.realPrice === "number" &&
    Number.isFinite(candidate.realPrice)
  );
}

function loadCart(): CartItem[] {
  try {
    const rawValue = localStorage.getItem(STORAGE_KEY);
    if (!rawValue) return [];
    const storedItems = JSON.parse(rawValue) as StoredCartItem[];
    if (!Array.isArray(storedItems)) return [];
    return storedItems.flatMap((storedItem) => {
      if (
        !storedItem ||
        typeof storedItem !== "object" ||
        !isCompleteProduct(storedItem.product) ||
        !Number.isInteger(storedItem.quantity) ||
        storedItem.quantity < 1
      )
        return [];
      return [
        {
          product: storedItem.product,
          quantity: Math.min(storedItem.quantity, 99),
        },
      ];
    });
  } catch {
    return [];
  }
}

export function useCart() {
  const [items, setItems] = useState<CartItem[]>(loadCart);

  useEffect(() => {
    const storedItems: StoredCartItem[] = items.map(
      ({ product, quantity }) => ({
        product,
        quantity,
      }),
    );
    localStorage.setItem(STORAGE_KEY, JSON.stringify(storedItems));
  }, [items]);

  const addItem = useCallback((product: Product) => {
    setItems((currentItems) => {
      const existingItem = currentItems.find(
        (item) => item.product.productID === product.productID,
      );
      if (!existingItem) return [...currentItems, { product, quantity: 1 }];
      return currentItems.map((item) =>
        item.product.productID === product.productID
          ? { ...item, quantity: Math.min(item.quantity + 1, 99) }
          : item,
      );
    });
  }, []);

  const updateQuantity = useCallback((productId: number, quantity: number) => {
    setItems((currentItems) =>
      quantity < 1
        ? currentItems.filter((item) => item.product.productID !== productId)
        : currentItems.map((item) =>
            item.product.productID === productId
              ? { ...item, quantity: Math.min(quantity, 99) }
              : item,
          ),
    );
  }, []);

  const clearCart = useCallback(() => setItems([]), []);
  const itemCount = useMemo(
    () => items.reduce((total, item) => total + item.quantity, 0),
    [items],
  );
  const total = useMemo(
    () =>
      items.reduce(
        (sum, item) => sum + (item.product.realPrice ?? 0) * item.quantity,
        0,
      ),
    [items],
  );

  return { items, addItem, updateQuantity, clearCart, itemCount, total };
}
