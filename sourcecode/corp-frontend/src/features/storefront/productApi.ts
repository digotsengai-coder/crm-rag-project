import type { Product, ProductListResponse } from "./types";

const PRODUCT_API_BASE_URL =
  import.meta.env.VITE_API_CORP_URL || "http://localhost:8001";

interface ProductApiItem {
  ProductID: string;
  ProductNameZH: string;
  ProductNameEN: string;
  Category: string;
  Description: string;
  DescriptionShort: string;
  ImageUrl?: string;
  OriginalPrice?: string | number | null;
  RealPrice?: string | number | null;
  id: string;
}

interface ProductApiResponse {
  pidx: number;
  pno: number;
  count: number;
  products: ProductApiItem[];
}

interface ProductCountApiResponse {
  count: number;
}

export class ProductCatalogError extends Error {}

function toPrice(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  const normalizedValue = typeof value === "string" ? value.trim() : value;
  if (normalizedValue === "") return null;
  const price =
    typeof normalizedValue === "number"
      ? normalizedValue
      : Number(normalizedValue);
  return Number.isFinite(price) && price >= 0 ? price : null;
}

function toStorefrontProduct(product: ProductApiItem): Product | null {
  const productId = Number(product.ProductID);
  if (!Number.isSafeInteger(productId)) {
    // 購物車與訂單需要數字 ProductID；略過單筆異常資料，避免其餘商品整頁無法瀏覽。
    return null;
  }

  return {
    productID: productId,
    productNameEN: product.ProductNameEN,
    productNameZH: product.ProductNameZH,
    category: product.Category,
    originalPrice: toPrice(product.OriginalPrice),
    realPrice: toPrice(product.RealPrice),
    descriptionShort: product.DescriptionShort || product.Description,
    imageUrl: product.ImageUrl?.trim() ?? "",
  };
}

export async function fetchProductPage(
  page: number,
  pageSize: number,
  signal?: AbortSignal,
): Promise<ProductListResponse> {
  const response = await fetch(
    `${PRODUCT_API_BASE_URL}/api/v1/Product?pidx=${page}&pno=${pageSize}`,
    { signal },
  );

  if (!response.ok) {
    throw new ProductCatalogError(
      `商品列表載入失敗（${response.status}）。請稍後重試。`,
    );
  }

  const payload = (await response.json()) as ProductApiResponse;
  const products = payload.products.flatMap((product) => {
    const storefrontProduct = toStorefrontProduct(product);
    return storefrontProduct === null ? [] : [storefrontProduct];
  });

  return {
    pidx: payload.pidx,
    pno: payload.pno,
    count: products.length,
    products,
  };
}

export async function fetchProductCount(signal?: AbortSignal): Promise<number> {
  const response = await fetch(`${PRODUCT_API_BASE_URL}/api/v1/Product/count`, {
    signal,
  });

  if (!response.ok) {
    throw new ProductCatalogError(
      `商品總數載入失敗（${response.status}）。請稍後重試。`,
    );
  }

  const payload = (await response.json()) as ProductCountApiResponse;
  if (!Number.isSafeInteger(payload.count) || payload.count < 0) {
    throw new ProductCatalogError("商品總數資料格式錯誤。請稍後重試。");
  }

  return payload.count;
}
