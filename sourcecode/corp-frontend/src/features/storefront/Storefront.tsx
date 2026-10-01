import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type FormEvent,
} from "react";
import {
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Minus,
  PackageCheck,
  Plus,
  ShieldCheck,
  ShoppingBag,
  Trash2,
  Truck,
  X,
} from "lucide-react";
import { submitCheckout } from "./orderApi";
import { MOCK_CUSTOMERS } from "./mockCustomers";
import { fetchProductCount, fetchProductPage } from "./productApi";
import type { CheckoutCustomer, Product } from "./types";
import { useCart } from "./useCart";
import { tw } from "../../utils/tw";

const CATEGORY_LABELS: Record<string, string> = {
  all: "全部商品",
};

const PAYMENT_LABELS = {
  Gateway: "線上金流",
  Wallet: "電子錢包",
  CardToCard: "銀行轉帳",
  Cash: "現金付款",
} as const;
const PAYMENT_METHODS = Object.keys(
  PAYMENT_LABELS,
) as CheckoutCustomer["PaymentMethod"][];
const PRODUCT_PAGE_SIZE_OPTIONS = [10, 20, 30, 40, 50] as const;
const DEFAULT_PRODUCT_PAGE_SIZE = 20;

const styles = {
  shell: tw(
    "min-h-full overflow-clip bg-store-canvas font-store text-store-text [&_*]:box-border motion-reduce:[&_*]:scroll-auto motion-reduce:[&_*]:duration-[.01ms] motion-reduce:[&_*]:[animation-iteration-count:1] [&_*::after]:box-border motion-reduce:[&_*::after]:duration-[.01ms] [&_*::before]:box-border motion-reduce:[&_*::before]:duration-[.01ms] [&_:focus-visible]:outline-[3px] [&_:focus-visible]:outline-offset-3 [&_:focus-visible]:outline-brand-primary [&_a]:touch-manipulation [&_a]:text-inherit [&_a]:no-underline [&_button]:touch-manipulation",
  ),
  skipLink: tw(
    "fixed top-2 left-2 z-[1200] translate-y-[-140%] rounded-control bg-store-surface px-4 py-2.5 text-store-dark focus:translate-y-0",
  ),
  header: tw(
    "sticky top-0 z-40 flex min-h-19 items-center justify-between border-b border-store-border bg-white/96 px-[clamp(20px,5vw,76px)] backdrop-blur-[18px] max-[560px]:min-h-16.5 max-[560px]:px-4",
  ),
  brand: tw(
    "inline-flex min-h-11 items-center gap-2.5 font-display text-lg font-bold tracking-[-.02em] max-[560px]:text-base [&_b]:text-brand-primary",
  ),
  brandMark: tw(
    "grid size-10 place-items-center rounded-field bg-brand-primary text-store-surface shadow-[0_6px_16px_rgb(0_102_204/.2)]",
  ),
  cartButton: tw(
    "flex min-h-11.5 cursor-pointer items-center gap-2.25 rounded-card border-0 bg-brand-primary py-0 pr-2.5 pl-4 font-bold text-store-surface shadow-[0_5px_14px_rgb(0_102_204/.18)] transition-[filter,box-shadow] duration-180 hover:shadow-[0_7px_18px_rgb(0_102_204/.25)] hover:brightness-92 max-[560px]:pl-3",
  ),
  cartCount: tw(
    "grid h-7 min-w-7 place-items-center rounded-full bg-brand-accent text-caption tabular-nums",
  ),
  visuallyHiddenMobile: tw(
    "max-[560px]:absolute max-[560px]:size-px max-[560px]:overflow-hidden max-[560px]:[clip:rect(0_0_0_0)]",
  ),
  hero: tw(
    "relative isolate grid min-h-[620px] grid-cols-[minmax(0,1.08fr)_minmax(360px,.92fr)] bg-[linear-gradient(135deg,var(--color-store-canvas)_0%,var(--color-store-canvas-alt)_100%)] px-[clamp(20px,7vw,110px)] py-[clamp(60px,8vw,104px)] before:absolute before:inset-0 before:-z-2 before:bg-[radial-gradient(circle_at_82%_20%,rgb(59_130_246/.12),transparent_34%)] before:content-[''] max-[1120px]:grid-cols-[1fr_.75fr] max-[820px]:min-h-0 max-[820px]:grid-cols-1 max-[820px]:pb-10.5 max-[560px]:px-4.5 max-[560px]:pt-13.5 max-[560px]:pb-8.5",
  ),
  heroCopy: tw("max-w-[760px] self-center max-[820px]:z-2"),
  trustBadge: tw(
    "mb-6 inline-flex items-center gap-2 rounded-full bg-brand-success/10 px-3.5 py-2 text-sm font-bold text-brand-secondary",
  ),
  heroTitle: tw(
    "text-wrap-balance m-0 max-w-[740px] font-display text-[clamp(44px,5.6vw,72px)] leading-[1.08] tracking-[-.04em] max-[560px]:text-[clamp(44px,13vw,62px)] [&_em]:text-brand-primary [&_em]:not-italic",
  ),
  heroDescription: tw(
    "my-7.5 max-w-[590px] text-[clamp(17px,1.5vw,21px)] leading-[1.7] text-store-muted",
  ),
  heroActions: tw("flex flex-wrap gap-3.5"),
  primaryLink: tw(
    "inline-flex min-h-13 cursor-pointer items-center justify-center gap-3 rounded-card bg-brand-primary px-6 font-bold text-store-surface! transition-[filter,background] duration-180 hover:brightness-92",
  ),
  heroArt: tw(
    "relative min-h-[430px] self-center max-[820px]:mt-7.5 max-[820px]:min-h-[350px] max-[560px]:min-h-[280px]",
  ),
  shapeOne: tw(
    "absolute inset-[5%_4%_9%_12%] block rounded-[20px] border border-solid border-store-border bg-[linear-gradient(rgb(30_58_95/.12),rgb(30_58_95/.12)),url('/images/all_product.jpg')] bg-cover bg-center shadow-store before:absolute before:inset-0 before:rounded-[inherit] before:bg-[linear-gradient(to_top,rgb(30_58_95/.35),transparent_45%)] before:content-['']",
  ),
  shapeTwo: tw(
    "absolute top-[8%] right-[2%] block size-29 rounded-[18px] bg-brand-accent opacity-92 max-[560px]:size-23",
  ),
  heroStat: tw(
    "absolute bottom-[2%] left-[6%] z-2 flex items-baseline gap-3.5 rounded-highlight border border-solid border-store-border bg-store-surface px-4.5 py-3.5 text-store-dark shadow-store",
  ),
  heroStatValue: tw(
    "font-display text-[clamp(54px,6vw,76px)] leading-none tracking-[-.06em] text-brand-primary max-[560px]:text-[92px]",
  ),
  heroStatLabel: tw("leading-[1.2] font-extrabold"),
  heroBadge: tw(
    "absolute top-[1%] right-[7%] z-3 grid min-h-19 w-35 place-items-center rounded-highlight border border-solid border-store-border bg-store-surface text-center font-display leading-[1.2] font-bold text-brand-secondary shadow-store max-[560px]:min-h-16 max-[560px]:w-28 max-[560px]:text-label",
  ),
  productsSection: tw(
    "bg-store-surface px-[clamp(20px,5vw,76px)] py-[clamp(64px,8vw,112px)] max-[560px]:rounded-t-[28px] max-[560px]:px-4 max-[560px]:py-15.5",
  ),
  sectionHeading: tw(
    "mx-auto mb-8.5 flex max-w-7xl items-end justify-between gap-8 max-[820px]:flex-col max-[820px]:items-start max-[820px]:gap-3 [&>p]:mb-1.5 [&>p]:max-w-[360px] [&>p]:leading-[1.6] [&>p]:text-store-muted",
  ),
  kicker: tw(
    "mb-5 text-caption font-extrabold tracking-[.14em] text-brand-secondary",
  ),
  sectionTitle: tw(
    "m-0 font-display text-[clamp(34px,4vw,54px)] tracking-[-.035em]",
  ),
  filters: tw(
    "mx-auto mb-9 flex max-w-7xl [scrollbar-width:thin] gap-2.5 overflow-x-auto px-1 pt-1 pb-3",
  ),
  filterButton: tw(
    "min-h-11 shrink-0 cursor-pointer rounded-control border border-solid border-store-border bg-store-surface px-4.5 py-0 font-bold text-store-text transition-[border-color,background,color] duration-180 hover:border-brand-primary",
  ),
  feedback: tw(
    "mx-auto grid min-h-45 max-w-7xl place-items-center content-center gap-3.5 text-center text-store-muted [&_p]:m-0",
  ),
  feedbackError: tw("text-brand-danger"),
  feedbackButton: tw(
    "min-h-11 cursor-pointer rounded-control border border-solid border-current bg-transparent px-4 py-0 font-[inherit] font-extrabold text-inherit",
  ),
  productGrid: tw(
    "mx-auto grid max-w-7xl grid-cols-4 gap-6 max-[1120px]:grid-cols-3 max-[820px]:grid-cols-2 max-[560px]:grid-cols-1 max-[560px]:gap-4.5",
  ),
  productCard: tw(
    "min-w-0 overflow-hidden rounded-card border border-solid border-store-border bg-store-surface shadow-product transition-[box-shadow,transform] duration-220 hover:-translate-y-0.75 hover:shadow-store max-[560px]:block",
  ),
  productImage: tw(
    "relative grid aspect-[256/190] place-items-center border-b border-store-border bg-store-canvas-alt bg-contain bg-center bg-no-repeat max-[560px]:h-auto max-[560px]:border-r-0",
  ),
  productUnavailable: tw("text-sm font-bold text-store-muted"),
  productImageNotice: tw(
    "rounded-lg border border-dashed border-store-border px-3 py-2",
  ),
  productBody: tw(
    "flex min-h-[255px] flex-col p-5 max-[560px]:min-h-[235px] max-[560px]:p-4.5 [&_h3]:mt-3.5 [&_h3]:mb-0.5 [&_h3]:font-display [&_h3]:text-card-title [&_h3]:tracking-[-.02em]",
  ),
  productCategory: tw(
    "self-start rounded-[7px] bg-brand-secondary/10 px-2.25 py-1 text-label font-extrabold text-brand-secondary",
  ),
  productEnglish: tw("m-0 text-xs font-bold text-brand-primary"),
  productCopy: tw(
    "mt-3 mb-5 text-sm leading-[1.55] text-store-muted max-[560px]:text-caption",
  ),
  productFooter: tw(
    "mt-auto flex items-center justify-between gap-2.5 max-[560px]:flex-row",
  ),
  productPrices: tw(
    "flex min-w-0 flex-col items-baseline gap-1 tabular-nums [&_strong]:font-display [&_strong]:text-xl [&_strong]:text-brand-primary [&_strong]:tabular-nums",
  ),
  addButton: tw(
    "inline-flex min-h-11 shrink-0 cursor-pointer items-center gap-1.5 rounded-control border-0 bg-brand-primary px-3.5 py-0 text-caption font-extrabold text-store-surface transition-[filter,transform] duration-180 select-none hover:brightness-92 active:scale-97 disabled:transform-none disabled:cursor-not-allowed disabled:opacity-30 disabled:filter-none max-[560px]:w-auto max-[560px]:justify-center",
  ),
  pagination: tw(
    "mx-auto mt-9 flex max-w-7xl items-center justify-center gap-2 max-[560px]:gap-1.25",
  ),
  paginationButton: tw(
    "inline-grid min-h-10.5 min-w-10.5 cursor-pointer place-items-center rounded-control border border-solid border-store-border bg-store-surface px-2.5 py-0 font-[inherit] font-extrabold text-store-text hover:not-disabled:opacity-80 disabled:cursor-not-allowed disabled:opacity-35 max-[560px]:min-h-9.5 max-[560px]:min-w-9.5 max-[560px]:px-2",
  ),
  paginationActive: tw(
    "border-brand-primary! bg-brand-primary! text-store-surface!",
  ),
  paginationDesktop: tw("contents max-[560px]:hidden"),
  paginationMobile: tw("hidden max-[560px]:contents"),
  paginationEllipsis: tw(
    "inline-grid min-h-10.5 min-w-10.5 place-items-center font-extrabold tracking-[.15em] text-store-muted max-[560px]:min-h-9.5 max-[560px]:min-w-7.5",
  ),
  paginationSelect: tw(
    "min-h-10.5 rounded-control border border-solid border-store-border bg-store-surface px-3 py-0 font-[inherit] font-bold text-store-text",
  ),
  footer: tw(
    "flex items-center justify-between bg-store-dark px-[clamp(20px,5vw,76px)] py-7.5 text-store-surface max-[560px]:flex-col max-[560px]:items-start max-[560px]:gap-1.5 [&_p]:m-0 [&_p]:text-store-border [&_span]:font-display [&_span]:font-extrabold [&_span]:tracking-[.08em]",
  ),
  cartLayer: tw("fixed inset-0 z-[1100]"),
  cartScrim: tw(
    "absolute inset-0 size-full animate-store-fade-in cursor-pointer border-0 bg-store-dark/60 backdrop-blur-[5px] motion-reduce:animate-none",
  ),
  cartDrawer: tw(
    "absolute top-0 right-0 flex h-full w-[min(520px,100%)] animate-store-slide-in flex-col bg-store-surface shadow-drawer motion-reduce:animate-none",
  ),
  cartHead: tw(
    "flex min-h-24 items-center justify-between border-b border-store-border px-6.5 py-5.5 max-[560px]:px-4.5 [&_h2]:m-0 [&_h2]:font-display [&_h2]:text-drawer-title [&_p]:mt-0 [&_p]:mb-1 [&_p]:text-label [&_p]:font-extrabold [&_p]:tracking-[.16em] [&_p]:text-brand-primary",
  ),
  iconButton: tw(
    "grid size-11 cursor-pointer place-items-center rounded-control border-0 bg-store-canvas-alt text-store-text hover:bg-store-border disabled:cursor-not-allowed disabled:opacity-45",
  ),
  cartItems: tw("flex-1 overflow-y-auto px-6.5 py-4 max-[560px]:px-4.5"),
  emptyCart: tw(
    "grid min-h-[420px] place-items-center content-center p-7.5 text-center text-store-muted [&_h3]:mt-0 [&_h3]:mb-2 [&_h3]:font-display [&_h3]:text-store-text [&_p]:mt-0 [&_p]:mb-5 [&_svg]:mb-4.5 [&_svg]:text-brand-primary",
  ),
  textButton: tw(
    "min-h-11 cursor-pointer border-0 bg-transparent font-extrabold text-brand-primary underline underline-offset-4",
  ),
  cartItem: tw(
    "relative grid grid-cols-[112px_1fr_44px] items-center gap-4 border-b border-store-border py-4.5 max-[560px]:grid-cols-[88px_1fr_44px] max-[560px]:gap-3",
  ),
  cartThumb: tw(
    "aspect-[256/190] w-28 rounded-[15px] bg-store-canvas-alt bg-contain bg-center bg-no-repeat max-[560px]:w-22",
  ),
  cartItemInfo: tw(
    "[&_h3]:mt-0 [&_h3]:mb-1 [&_h3]:font-display [&_h3]:text-base [&>span]:font-extrabold [&>span]:text-brand-primary [&>span]:tabular-nums",
  ),
  quantity: tw(
    "mt-3 flex items-center gap-2 [&_button]:size-9 [&_output]:min-w-5.5 [&_output]:text-center [&_output]:font-extrabold [&_output]:tabular-nums",
  ),
  removeButton: tw(
    "grid size-11 cursor-pointer place-items-center rounded-control border-0 bg-transparent text-brand-danger hover:bg-brand-danger/10",
  ),
  cartSummary: tw(
    "border-t border-store-border bg-store-canvas-alt px-6.5 pt-5.5 pb-7 max-[560px]:px-4.5 [&_p]:mt-2 [&_p]:mb-4.5 [&_p]:text-caption [&_p]:text-store-muted [&_strong]:font-display [&_strong]:text-total [&_strong]:tabular-nums [&>div]:flex [&>div]:items-center [&>div]:justify-between",
  ),
  primaryButton: tw(
    "flex min-h-13 w-full cursor-pointer items-center justify-center gap-2.5 rounded-card border-0 bg-brand-primary font-extrabold text-store-surface transition-[filter] duration-180 hover:brightness-92",
  ),
  checkout: tw("flex-1 overflow-y-auto px-6.5 pt-3.5 pb-8 max-[560px]:px-4.5"),
  backButton: tw(
    "mb-2.5 min-h-11 cursor-pointer border-0 bg-transparent font-extrabold text-brand-primary underline underline-offset-4",
  ),
  error: tw(
    "mb-4.5 rounded-lg border-l-4 border-brand-danger bg-brand-danger/8 px-3.75 py-3.25 leading-[1.5] [overflow-wrap:anywhere] text-store-text",
  ),
  formGrid: tw(
    "grid grid-cols-2 gap-4 max-[560px]:grid-cols-1 [&_input]:min-h-11.5 [&_input]:w-full [&_input]:rounded-field [&_input]:border [&_input]:border-solid [&_input]:border-store-border [&_input]:bg-store-surface [&_input]:px-3 [&_input]:py-0 [&_input]:font-[inherit] [&_input]:text-base [&_input]:text-store-text [&_input]:outline-none [&_input:focus]:border-brand-primary [&_input:focus]:shadow-[0_0_0_3px_rgb(59_130_246/.2)] [&_label]:flex [&_label]:min-w-0 [&_label]:flex-col [&_label]:gap-1.75 [&_label]:text-caption [&_label]:font-extrabold [&_label]:text-store-text [&_label_span]:text-brand-danger [&_select]:min-h-11.5 [&_select]:w-full [&_select]:rounded-field [&_select]:border [&_select]:border-solid [&_select]:border-store-border [&_select]:bg-store-surface [&_select]:px-3 [&_select]:py-0 [&_select]:font-[inherit] [&_select]:text-base [&_select]:text-store-text [&_select]:outline-none [&_select:focus]:border-brand-primary [&_select:focus]:shadow-[0_0_0_3px_rgb(59_130_246/.2)]",
  ),
  fieldWide: tw("col-span-full max-[560px]:col-auto"),
  checkoutTotal: tw(
    "mt-6.5 mb-3.5 flex items-center justify-between border-t border-store-border pt-5 [&_strong]:font-display [&_strong]:text-total [&_strong]:tabular-nums",
  ),
  submitButton: tw(
    "flex min-h-13 w-full cursor-pointer items-center justify-center gap-2.5 rounded-card border-0 bg-brand-primary font-extrabold text-store-surface transition-[filter] duration-180 hover:brightness-92 disabled:cursor-wait disabled:opacity-55",
  ),
  checkoutNote: tw("text-center text-xs leading-[1.5] text-store-muted"),
  liveRegion: tw(
    "pointer-events-none fixed right-5.5 bottom-22.5 z-[1200] max-[560px]:right-3 max-[560px]:bottom-20.5",
  ),
  toast: tw(
    "flex max-w-[min(390px,calc(100vw-40px))] animate-store-toast-in items-center gap-2.5 rounded-toast bg-brand-success px-4.5 py-3.5 font-bold text-store-surface shadow-store motion-reduce:animate-none",
  ),
};

function getProductImageStyle(imageUrl: string): CSSProperties {
  return imageUrl ? { backgroundImage: `url("${imageUrl}")` } : {};
}

function isPurchasableProduct(product: Product): boolean {
  return (
    Boolean(product.imageUrl) &&
    product.originalPrice !== null &&
    product.realPrice !== null
  );
}

function getPaginationItems(
  currentPage: number,
  totalPages: number,
): Array<number | "start-ellipsis" | "end-ellipsis"> {
  if (totalPages <= 7)
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  if (currentPage <= 4) return [1, 2, 3, 4, 5, "end-ellipsis", totalPages];
  if (currentPage >= totalPages - 3)
    return [
      1,
      "start-ellipsis",
      totalPages - 4,
      totalPages - 3,
      totalPages - 2,
      totalPages - 1,
      totalPages,
    ];
  return [
    1,
    "start-ellipsis",
    currentPage - 1,
    currentPage,
    currentPage + 1,
    "end-ellipsis",
    totalPages,
  ];
}

function getMobilePageNumbers(
  currentPage: number,
  totalPages: number,
): number[] {
  const startPage = Math.max(1, Math.min(currentPage - 1, totalPages - 2));
  return Array.from(
    { length: Math.min(3, totalPages) },
    (_, index) => startPage + index,
  );
}

function ProductCard({
  product,
  onAdd,
}: {
  product: Product;
  onAdd: (product: Product) => void;
}) {
  const isPurchasable = isPurchasableProduct(product);
  return (
    <article className={styles.productCard}>
      <div
        className={tw(
          styles.productImage,
          !product.imageUrl && styles.productUnavailable,
        )}
        style={getProductImageStyle(product.imageUrl)}
        role="img"
        aria-label={`${product.productNameZH}商品圖片`}
      >
        {!product.imageUrl && (
          <span className={styles.productImageNotice}>圖片未提供</span>
        )}
      </div>
      <div className={styles.productBody}>
        <span className={styles.productCategory}>
          {CATEGORY_LABELS[product.category] ?? product.category}
        </span>
        <h3>{product.productNameZH}</h3>
        <p className={styles.productEnglish}>{product.productNameEN}</p>
        <p className={styles.productCopy}>{product.descriptionShort}</p>
        <div className={styles.productFooter}>
          {product.originalPrice !== null && product.realPrice !== null && (
            <div
              className={styles.productPrices}
              aria-label={`${product.productNameZH}價格`}
            >
              <strong>${product.realPrice.toLocaleString("en-US")}</strong>
            </div>
          )}
          <button
            className={styles.addButton}
            type="button"
            onClick={() => onAdd(product)}
            disabled={!isPurchasable}
          >
            <Plus size={18} aria-hidden="true" />
            加入購物車
          </button>
        </div>
      </div>
    </article>
  );
}

export default function Storefront() {
  const [activeCategory, setActiveCategory] = useState("all");
  const [isCartOpen, setIsCartOpen] = useState(false);
  const [isCheckoutOpen, setIsCheckoutOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [selectedCustomerId, setSelectedCustomerId] = useState(() =>
    String(MOCK_CUSTOMERS[0].CustomerID),
  );
  const [selectedPaymentMethod, setSelectedPaymentMethod] =
    useState<CheckoutCustomer["PaymentMethod"]>("Gateway");
  const [products, setProducts] = useState<Product[]>([]);
  const [isProductsLoading, setIsProductsLoading] = useState(true);
  const [productsError, setProductsError] = useState("");
  const [productRequestVersion, setProductRequestVersion] = useState(0);
  const [currentProductPage, setCurrentProductPage] = useState(1);
  const [productPageSize, setProductPageSize] = useState(
    DEFAULT_PRODUCT_PAGE_SIZE,
  );
  const [currentProductPageCount, setCurrentProductPageCount] = useState(0);
  const [totalProductCount, setTotalProductCount] = useState<number | null>(
    null,
  );
  const statusMessageTimerRef = useRef<number | null>(null);
  const { items, addItem, updateQuantity, clearCart, itemCount, total } =
    useCart();

  const categories = useMemo(
    () => ["all", ...new Set(products.map((product) => product.category))],
    [products],
  );
  const visibleProducts = useMemo(
    () =>
      activeCategory === "all"
        ? products
        : products.filter((product) => product.category === activeCategory),
    [activeCategory, products],
  );
  const totalProductPages =
    totalProductCount === null
      ? 0
      : Math.ceil(totalProductCount / productPageSize);
  const paginationItems = useMemo(
    () => getPaginationItems(currentProductPage, totalProductPages),
    [currentProductPage, totalProductPages],
  );
  const mobilePageNumbers = useMemo(
    () => getMobilePageNumbers(currentProductPage, totalProductPages),
    [currentProductPage, totalProductPages],
  );
  const selectedCustomer = useMemo(
    () =>
      MOCK_CUSTOMERS.find(
        (customer) => String(customer.CustomerID) === selectedCustomerId,
      ) ?? MOCK_CUSTOMERS[0],
    [selectedCustomerId],
  );

  useEffect(() => {
    if (!isCartOpen) setIsCheckoutOpen(false);
  }, [isCartOpen]);

  useEffect(() => {
    const controller = new AbortController();
    setIsProductsLoading(true);
    setProductsError("");

    const productPageRequest = fetchProductPage(
      currentProductPage,
      productPageSize,
      controller.signal,
    );
    const productCountRequest =
      totalProductCount === null
        ? fetchProductCount(controller.signal)
        : Promise.resolve(null);

    Promise.all([productPageRequest, productCountRequest])
      .then(([response, productCount]) => {
        setProducts(response.products);
        setCurrentProductPageCount(response.count);
        if (productCount !== null) setTotalProductCount(productCount);
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError")
          return;
        setProductsError(
          error instanceof Error ? error.message : "商品列表載入失敗。",
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsProductsLoading(false);
      });

    return () => controller.abort();
  }, [currentProductPage, productPageSize, productRequestVersion]);

  useEffect(
    () => () => {
      if (statusMessageTimerRef.current !== null)
        window.clearTimeout(statusMessageTimerRef.current);
    },
    [],
  );

  useEffect(() => {
    if (!isCartOpen) return undefined;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !isSubmitting) setIsCartOpen(false);
    };
    document.body.classList.add("overflow-hidden");
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.classList.remove("overflow-hidden");
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isCartOpen, isSubmitting]);

  function showStatusMessage(message: string) {
    if (statusMessageTimerRef.current !== null)
      window.clearTimeout(statusMessageTimerRef.current);
    setStatusMessage(message);
    statusMessageTimerRef.current = window.setTimeout(() => {
      setStatusMessage("");
      statusMessageTimerRef.current = null;
    }, 3000);
  }

  function handleAdd(product: Product) {
    if (!isPurchasableProduct(product)) return;
    addItem(product);
    showStatusMessage(`已將${product.productNameZH}加入購物車`);
  }

  function handleProductPageSizeChange(pageSize: number) {
    setProductPageSize(pageSize);
    setCurrentProductPage(1);
  }

  function openCheckout() {
    const randomCustomer =
      MOCK_CUSTOMERS[Math.floor(Math.random() * MOCK_CUSTOMERS.length)];
    const randomPaymentMethod =
      PAYMENT_METHODS[Math.floor(Math.random() * PAYMENT_METHODS.length)];
    setSelectedCustomerId(String(randomCustomer.CustomerID));
    setSelectedPaymentMethod(randomPaymentMethod);
    setErrorMessage("");
    setIsCheckoutOpen(true);
  }

  async function handleCheckout(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!items.length || isSubmitting) return;
    const formData = new FormData(event.currentTarget);
    const customer: CheckoutCustomer = {
      CustomerID: Number(formData.get("CustomerID")),
      Age: Number(formData.get("Age")),
      City: String(formData.get("City") || ""),
      SignupDate: String(formData.get("SignupDate") || ""),
      CustomerSegment: String(
        formData.get("CustomerSegment"),
      ) as CheckoutCustomer["CustomerSegment"],
      PhoneNumber: String(formData.get("PhoneNumber") || ""),
      PaymentMethod: String(
        formData.get("PaymentMethod"),
      ) as CheckoutCustomer["PaymentMethod"],
    };
    setErrorMessage("");
    setIsSubmitting(true);

    try {
      await submitCheckout(customer, items);
      clearCart();
      setIsCheckoutOpen(false);
      setIsCartOpen(false);
      showStatusMessage("訂單已送出");
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "訂單送出失敗。",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className={styles.shell}>
      <a className={styles.skipLink} href="#products">
        跳至商品列表
      </a>
      <header className={styles.header}>
        <a className={styles.brand} href="#top" aria-label="CRM Select 首頁">
          <span className={styles.brandMark}>
            <Check size={20} aria-hidden="true" />
          </span>
          <span>
            CRM <b>SELECT</b>
          </span>
        </a>
        {/* <nav aria-label="主要導覽">
          <a href="#products">新品選物</a>
        </nav> */}
        <button
          className={styles.cartButton}
          type="button"
          onClick={() => setIsCartOpen(true)}
          aria-label={`開啟購物車，共 ${itemCount} 件商品`}
        >
          <ShoppingBag size={21} aria-hidden="true" />
          <span className={styles.visuallyHiddenMobile}>購物車</span>
          <b className={styles.cartCount} aria-hidden="true">
            {itemCount}
          </b>
        </button>
      </header>

      <main id="top">
        <section className={styles.hero} aria-labelledby="store-title">
          <div className={styles.heroCopy}>
            <p className={styles.trustBadge}>
              <CheckCircle2 size={18} aria-hidden="true" /> 商品選購
            </p>
            <h1 className={styles.heroTitle} id="store-title">
              日常用品
              <br />
              <em>一次選齊</em>
            </h1>
            <p className={styles.heroDescription}>
              瀏覽各類商品，加入購物車後即可結帳。
            </p>
            <div className={styles.heroActions}>
              <a className={styles.primaryLink} href="#products">
                瀏覽商品 <ArrowRight size={20} aria-hidden="true" />
              </a>
            </div>
          </div>
          <div className={styles.heroArt} aria-hidden="true">
            <span className={styles.shapeOne} />
            <span className={styles.shapeTwo} />
            <div className={styles.heroStat}>
              <b className={styles.heroStatValue}>{totalProductCount ?? "—"}</b>
              <span className={styles.heroStatLabel}>件生活選物</span>
            </div>
            <div className={styles.heroBadge}>
              GOOD CHOICE
              <br />
              GOOD DAY
            </div>
          </div>
        </section>

        <section
          className={styles.productsSection}
          id="products"
          aria-labelledby="products-title"
        >
          <div className={styles.sectionHeading}>
            <div>
              <p className={styles.kicker}>SHOP THE COLLECTION</p>
              <h2 className={styles.sectionTitle} id="products-title">
                全部商品
              </h2>
            </div>
            <p aria-live="polite">
              本頁顯示 {currentProductPageCount}{" "}
              筆商品，可查看價格並加入購物車。
            </p>
          </div>
          <div className={styles.filters} aria-label="商品分類">
            {categories.map((category) => (
              <button
                key={category}
                type="button"
                className={tw(
                  styles.filterButton,
                  activeCategory === category &&
                    "border-brand-primary bg-brand-primary text-store-surface",
                )}
                aria-pressed={activeCategory === category}
                onClick={() => setActiveCategory(category)}
              >
                {CATEGORY_LABELS[category] ?? category}
              </button>
            ))}
          </div>
          {isProductsLoading ? (
            <div className={styles.feedback} role="status">
              正在載入商品…
            </div>
          ) : productsError ? (
            <div
              className={tw(styles.feedback, styles.feedbackError)}
              role="alert"
            >
              <p>{productsError}</p>
              <button
                className={styles.feedbackButton}
                type="button"
                onClick={() =>
                  setProductRequestVersion((version) => version + 1)
                }
              >
                重新載入
              </button>
            </div>
          ) : (
            <>
              <div className={styles.productGrid}>
                {visibleProducts.map((product) => (
                  <ProductCard
                    key={product.productID}
                    product={product}
                    onAdd={handleAdd}
                  />
                ))}
              </div>
              {!visibleProducts.length && (
                <div className={styles.feedback}>此分類目前沒有商品。</div>
              )}
              {!!totalProductPages && (
                <nav className={styles.pagination} aria-label="商品分頁">
                  <button
                    className={styles.paginationButton}
                    type="button"
                    aria-label="上一頁"
                    disabled={currentProductPage === 1}
                    onClick={() => setCurrentProductPage((page) => page - 1)}
                  >
                    <ChevronLeft size={18} aria-hidden="true" />
                  </button>
                  <span className={styles.paginationDesktop}>
                    {paginationItems.map((item) =>
                      typeof item === "number" ? (
                        <button
                          key={item}
                          type="button"
                          className={tw(
                            styles.paginationButton,
                            item === currentProductPage &&
                              styles.paginationActive,
                          )}
                          aria-current={
                            item === currentProductPage ? "page" : undefined
                          }
                          onClick={() => setCurrentProductPage(item)}
                        >
                          {item}
                        </button>
                      ) : (
                        <span
                          className={styles.paginationEllipsis}
                          key={item}
                          aria-hidden="true"
                        >
                          •••
                        </span>
                      ),
                    )}
                  </span>
                  <span className={styles.paginationMobile}>
                    {mobilePageNumbers.map((page) => (
                      <button
                        key={page}
                        type="button"
                        className={tw(
                          styles.paginationButton,
                          page === currentProductPage &&
                            styles.paginationActive,
                        )}
                        aria-current={
                          page === currentProductPage ? "page" : undefined
                        }
                        onClick={() => setCurrentProductPage(page)}
                      >
                        {page}
                      </button>
                    ))}
                  </span>
                  <button
                    className={styles.paginationButton}
                    type="button"
                    aria-label="下一頁"
                    disabled={currentProductPage === totalProductPages}
                    onClick={() => setCurrentProductPage((page) => page + 1)}
                  >
                    <ChevronRight size={18} aria-hidden="true" />
                  </button>
                  <label htmlFor="product-page-size">
                    <select
                      className={styles.paginationSelect}
                      id="product-page-size"
                      value={productPageSize}
                      onChange={(event) =>
                        handleProductPageSizeChange(Number(event.target.value))
                      }
                    >
                      {PRODUCT_PAGE_SIZE_OPTIONS.map((pageSize) => (
                        <option key={pageSize} value={pageSize}>
                          {pageSize} / 頁
                        </option>
                      ))}
                    </select>
                  </label>
                </nav>
              )}
            </>
          )}
        </section>
      </main>

      <footer className={styles.footer}>
        <span>CRM SELECT</span>
        <p>Good tools. Better days.</p>
      </footer>

      {isCartOpen && (
        <div className={styles.cartLayer}>
          <button
            className={styles.cartScrim}
            type="button"
            onClick={() => !isSubmitting && setIsCartOpen(false)}
            aria-label="關閉購物車"
          />
          <aside
            className={styles.cartDrawer}
            role="dialog"
            aria-modal="true"
            aria-labelledby="cart-title"
          >
            <div className={styles.cartHead}>
              <div>
                <p>{isCheckoutOpen ? "CHECKOUT" : "YOUR PICKS"}</p>
                <h2 id="cart-title">
                  {isCheckoutOpen ? "填寫訂購資料" : `購物車・${itemCount} 件`}
                </h2>
              </div>
              <button
                className={styles.iconButton}
                type="button"
                onClick={() => setIsCartOpen(false)}
                disabled={isSubmitting}
                aria-label="關閉購物車"
              >
                <X aria-hidden="true" />
              </button>
            </div>

            {!isCheckoutOpen ? (
              <>
                <div className={styles.cartItems}>
                  {!items.length && (
                    <div className={styles.emptyCart}>
                      <ShoppingBag size={40} aria-hidden="true" />
                      <h3>購物車尚無商品</h3>
                      <p>請先瀏覽商品並加入購物車。</p>
                      <button
                        className={styles.textButton}
                        type="button"
                        onClick={() => setIsCartOpen(false)}
                      >
                        繼續購物
                      </button>
                    </div>
                  )}
                  {items.map(({ product, quantity }) => (
                    <article
                      className={styles.cartItem}
                      key={product.productID}
                    >
                      <div
                        className={styles.cartThumb}
                        style={getProductImageStyle(product.imageUrl)}
                        role="img"
                        aria-label={product.productNameZH}
                      />
                      <div className={styles.cartItemInfo}>
                        <h3>{product.productNameZH}</h3>
                        <span>
                          ${(product.realPrice ?? 0).toLocaleString("en-US")}
                        </span>
                        <div className={styles.quantity}>
                          <button
                            className={styles.iconButton}
                            type="button"
                            onClick={() =>
                              updateQuantity(product.productID, quantity - 1)
                            }
                            aria-label={`減少${product.productNameZH}數量`}
                          >
                            <Minus size={16} />
                          </button>
                          <output aria-label={`${product.productNameZH}數量`}>
                            {quantity}
                          </output>
                          <button
                            className={styles.iconButton}
                            type="button"
                            onClick={() =>
                              updateQuantity(product.productID, quantity + 1)
                            }
                            aria-label={`增加${product.productNameZH}數量`}
                          >
                            <Plus size={16} />
                          </button>
                        </div>
                      </div>
                      <button
                        className={styles.removeButton}
                        type="button"
                        onClick={() => updateQuantity(product.productID, 0)}
                        aria-label={`移除${product.productNameZH}`}
                      >
                        <Trash2 size={18} />
                      </button>
                    </article>
                  ))}
                </div>
                {!!items.length && (
                  <div className={styles.cartSummary}>
                    <div>
                      <span>商品小計</span>
                      <strong>${total.toLocaleString("en-US")}</strong>
                    </div>
                    <p>運費與實際付款金額請於結帳頁確認。</p>
                    <button
                      className={styles.primaryButton}
                      type="button"
                      onClick={openCheckout}
                    >
                      前往結帳 <ArrowRight size={19} aria-hidden="true" />
                    </button>
                  </div>
                )}
              </>
            ) : (
              <form className={styles.checkout} onSubmit={handleCheckout}>
                <button
                  className={styles.backButton}
                  type="button"
                  onClick={() => setIsCheckoutOpen(false)}
                  disabled={isSubmitting}
                >
                  返回購物車
                </button>
                {errorMessage && (
                  <div className={styles.error} role="alert">
                    {errorMessage}
                  </div>
                )}
                <div className={styles.formGrid}>
                  <label>
                    顧客編號<span>*</span>
                    <input
                      name="CustomerID"
                      type="number"
                      value={selectedCustomer.CustomerID}
                      readOnly
                      required
                      inputMode="numeric"
                    />
                  </label>
                  <label>
                    年齡<span>*</span>
                    <input
                      name="Age"
                      type="number"
                      value={selectedCustomer.Age}
                      readOnly
                      required
                      inputMode="numeric"
                    />
                  </label>
                  <label className={styles.fieldWide}>
                    城市<span>*</span>
                    <input
                      name="City"
                      type="text"
                      value={selectedCustomer.City}
                      readOnly
                      required
                      autoComplete="address-level2"
                    />
                  </label>
                  <label>
                    註冊日期<span>*</span>
                    <input
                      name="SignupDate"
                      type="date"
                      value={selectedCustomer.SignupDate}
                      readOnly
                      required
                    />
                  </label>
                  <label>
                    顧客分群<span>*</span>
                    <select name="CustomerSegment" defaultValue="New" required>
                      <option value="New">New</option>
                      <option value="Regular">Regular</option>
                      <option value="VIP">VIP</option>
                    </select>
                  </label>
                  <label className={styles.fieldWide}>
                    聯絡電話<span>*</span>
                    <input
                      name="PhoneNumber"
                      type="tel"
                      value={selectedCustomer.PhoneNumber}
                      readOnly
                      required
                      autoComplete="tel"
                    />
                  </label>
                  <label className={styles.fieldWide}>
                    付款方式<span>*</span>
                    <select
                      name="PaymentMethod"
                      value={selectedPaymentMethod}
                      onChange={(event) =>
                        setSelectedPaymentMethod(
                          event.target
                            .value as CheckoutCustomer["PaymentMethod"],
                        )
                      }
                      required
                    >
                      {Object.entries(PAYMENT_LABELS).map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}（{value}）
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                <div className={styles.checkoutTotal}>
                  <span>訂單總額</span>
                  <strong>${total.toLocaleString("en-US")}</strong>
                </div>
                <button
                  className={styles.submitButton}
                  type="submit"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? "正在送出訂單…" : "送出訂單"}
                </button>
                <p className={styles.checkoutNote}>
                  送出後將建立訂單；若送出失敗，購物車商品會保留。
                </p>
              </form>
            )}
          </aside>
        </div>
      )}

      <div className={styles.liveRegion} aria-live="polite" aria-atomic="true">
        {statusMessage && (
          <div className={styles.toast}>
            <CheckCircle2 size={19} aria-hidden="true" />
            {statusMessage}
          </div>
        )}
      </div>
    </div>
  );
}
