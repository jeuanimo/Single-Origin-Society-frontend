"""
High-level Shopify service.

All public methods return Python objects whose attribute names match the
original Django ORM model fields so existing templates need minimal changes.
"""

import logging
from decimal import Decimal, InvalidOperation

from .client import get_client, ShopifyAPIError
from . import queries

logger = logging.getLogger(__name__)


# ── Wrapper objects ──────────────────────────────────────────────────────────

class _Image:
    """Wraps a Shopify image node to expose .url and .altText as attrs."""

    def __init__(self, data: dict):
        self.url = data.get("url", "")
        self.alt_text = data.get("altText") or ""

    def __bool__(self):
        return bool(self.url)


class ShopifyVariant:
    def __init__(self, data: dict):
        self.id = data.get("id", "")
        self.numeric_id = self.id.split("/")[-1] if self.id else ""
        self.title = data.get("title", "")
        self.sku = data.get("sku", "")
        self.available_for_sale = data.get("availableForSale", True)
        qty = data.get("quantityAvailable")
        self.quantity_available = int(qty) if qty is not None else None

        price_data = data.get("price") or {}
        self.price = _parse_decimal(price_data.get("amount", "0"))

        compare = data.get("compareAtPrice") or {}
        self.compare_at_price = _parse_decimal(compare.get("amount")) if compare else None

        self.selected_options = data.get("selectedOptions", [])


class ShopifyProduct:
    """
    Wraps a Shopify product node with attribute names that match the original
    Django Product model so storefront templates work with zero or minimal edits.
    """

    def __init__(self, data: dict):
        self.id = data.get("id", "")
        self.handle = data.get("handle", "")
        self.slug = self.handle  # alias used in a few places
        self.product_type = data.get("productType", "")
        self.tags = data.get("tags", [])

        # Name aliases
        self.title = data.get("title", "")
        self.name = self.title

        # Description (Shopify returns HTML)
        self.description = data.get("descriptionHtml", "")
        self.short_description = _strip_html(self.description)[:300]

        # Images
        fi = data.get("featuredImage")
        self.image = _Image(fi) if fi else None
        raw_images = data.get("images", {}).get("edges", [])
        self._gallery = [_Image(e["node"]) for e in raw_images if e.get("node")]

        # Variants — first variant drives the default price/sku
        variant_edges = data.get("variants", {}).get("edges", [])
        self.variants = [ShopifyVariant(e["node"]) for e in variant_edges if e.get("node")]
        first = self.variants[0] if self.variants else None

        self.price = first.price if first else Decimal("0.00")
        self.compare_price = first.compare_at_price if first else None
        self.sku = first.sku if first else ""

        # The "pk" used in add-to-cart form action is the first variant's numeric ID
        self.pk = first.numeric_id if first else "0"
        self.default_variant_id = first.id if first else ""

        # Stock from first variant
        if first:
            if not first.available_for_sale:
                self.stock_available = 0
            elif first.quantity_available is not None:
                self.stock_available = first.quantity_available
            else:
                self.stock_available = None  # Shopify not tracking
        else:
            self.stock_available = None

        self.is_low_stock = (
            self.stock_available is not None
            and 0 < self.stock_available <= 5
        )

        self.is_active = True
        self.is_featured = "featured" in self.tags

        # Metafields — mapped from Shopify namespace=custom
        mf = {m["key"]: m["value"] for m in (data.get("metafields") or []) if m}
        self.origin = mf.get("origin", "")
        self.blend_info = mf.get("blend_info", "")
        self.roast_level = mf.get("roast_level", "")
        self.flavor_notes = mf.get("flavor_notes", "")
        self.aroma_profile = mf.get("aroma_profile", "")
        self.body_profile = mf.get("body_profile", "")
        self.acidity_profile = mf.get("acidity_profile", "")
        self.finish_profile = mf.get("finish_profile", "")
        self.steeping_notes = mf.get("steeping_notes", "")
        self.ritual_description = mf.get("ritual_description", "")
        self.available_sizes = mf.get("available_sizes", "")
        self.grind_options = mf.get("grind_options", "")
        self.weight = mf.get("weight", "")
        self.meta_title = mf.get("meta_title", "")
        self.meta_description = mf.get("meta_description", "")
        self.og_title = mf.get("og_title", "")
        self.og_description = mf.get("og_description", "")
        self.is_subscription_available = mf.get("subscription_available", "").lower() == "true"

        # Derived type flags from productType or tags
        pt = self.product_type.lower()
        tag_set = {t.lower() for t in self.tags}
        self.is_coffee = pt == "coffee" or "coffee" in tag_set
        self.is_tea = pt == "tea" or "tea" in tag_set

        # Gallery helper matching old template: product.images.exists / product.images.all
        self.images = _GalleryProxy(self._gallery)

        # Tasting notes — Shopify products don't have these; templates do null-check
        self.tasting_notes = _EmptyRelated()

    def get_absolute_url(self) -> str:
        return f"/product/{self.handle}/"

    def __str__(self):
        return self.name


class _GalleryProxy:
    """Mimics Django QuerySet .exists() and .all() for the image gallery."""

    def __init__(self, images):
        self._images = images

    def exists(self):
        return bool(self._images)

    def all(self):
        return self._images


class _EmptyRelated:
    """Mimics a Django reverse relation that returns nothing."""

    def exists(self):
        return False

    def all(self):
        return []


class ShopifyCartLine:
    """
    Wraps a Shopify cart line for the cart template.
    Exposes attributes compatible with the old Django session cart items.
    """

    def __init__(self, data: dict):
        self.line_id = data.get("id", "")
        self.quantity = data.get("quantity", 0)

        cost = data.get("cost", {})
        total_amt = cost.get("totalAmount") or {}
        per_unit = cost.get("amountPerQuantity") or {}
        self.line_total = _parse_decimal(total_amt.get("amount", "0"))
        self.unit_price = _parse_decimal(per_unit.get("amount", "0"))

        merch = data.get("merchandise", {})
        self.variant_id = merch.get("id", "")
        self.variant_title = merch.get("title", "")

        prod = merch.get("product", {})
        self.product_title = prod.get("title", "")
        self.product_handle = prod.get("handle", "")
        self.product_url = f"/product/{self.product_handle}/"

        fi = prod.get("featuredImage")
        self.product_image = _Image(fi) if fi else None

        price_data = merch.get("price") or {}
        self.price = _parse_decimal(price_data.get("amount", "0"))

        # Compat shim: templates use item.product.name, item.product.image, etc.
        self.product = _CartProduct(
            title=self.product_title,
            handle=self.product_handle,
            image=self.product_image,
            price=self.price,
            sku=merch.get("sku", ""),
        )


class _CartProduct:
    """Minimal product-like object for use inside cart line items."""

    def __init__(self, title, handle, image, price, sku=""):
        self.name = title
        self.title = title
        self.handle = handle
        self.image = image
        self.price = price
        self.sku = sku
        self.origin = ""  # not available in cart line; omit gracefully

    def get_absolute_url(self):
        return f"/product/{self.handle}/"


class ShopifyCart:
    """
    Wraps the Shopify Cart object returned by cart queries/mutations.
    """

    def __init__(self, data: dict):
        self.id = data.get("id", "")
        self.checkout_url = data.get("checkoutUrl", "")
        self.total_quantity = data.get("totalQuantity", 0)

        cost = data.get("cost", {})
        self.subtotal = _parse_decimal((cost.get("subtotalAmount") or {}).get("amount", "0"))
        self.total = _parse_decimal((cost.get("totalAmount") or {}).get("amount", "0"))
        self.tax = _parse_decimal((cost.get("totalTaxAmount") or {}).get("amount", "0"))

        self.discount_codes = [
            dc["code"] for dc in (data.get("discountCodes") or [])
            if dc.get("applicable")
        ]

        line_edges = data.get("lines", {}).get("edges", [])
        self.lines = [ShopifyCartLine(e["node"]) for e in line_edges if e.get("node")]

    @property
    def items(self):
        return self.lines

    @property
    def item_count(self):
        return self.total_quantity


# ── Service functions ────────────────────────────────────────────────────────

def get_products(
    first: int = 24,
    query: str = "",
    sort_key: str = "CREATED_AT",
    reverse: bool = True,
) -> list[ShopifyProduct]:
    try:
        data = get_client().execute(
            queries.PRODUCTS_QUERY,
            {"first": first, "query": query or None, "sortKey": sort_key, "reverse": reverse},
        )
        return [ShopifyProduct(e["node"]) for e in data.get("products", {}).get("edges", [])]
    except ShopifyAPIError:
        return []


def get_collection_products(
    handle: str,
    first: int = 24,
    sort_key: str = "CREATED_AT",
    reverse: bool = True,
) -> list[ShopifyProduct]:
    try:
        data = get_client().execute(
            queries.COLLECTION_PRODUCTS_QUERY,
            {"handle": handle, "first": first, "sortKey": sort_key, "reverse": reverse},
        )
        coll = data.get("collection") or {}
        return [ShopifyProduct(e["node"]) for e in coll.get("products", {}).get("edges", [])]
    except ShopifyAPIError:
        return []


def get_product_by_handle(handle: str) -> ShopifyProduct | None:
    try:
        data = get_client().execute(
            queries.PRODUCT_BY_HANDLE_QUERY,
            {"handle": handle},
        )
        raw = data.get("product")
        return ShopifyProduct(raw) if raw else None
    except ShopifyAPIError:
        return None


def get_collections(first: int = 20) -> list[dict]:
    try:
        data = get_client().execute(queries.COLLECTIONS_QUERY, {"first": first})
        return [e["node"] for e in data.get("collections", {}).get("edges", [])]
    except ShopifyAPIError:
        return []


# ── Cart service ─────────────────────────────────────────────────────────────

def cart_create(variant_id: str, quantity: int = 1) -> ShopifyCart | None:
    try:
        data = get_client().execute(
            queries.CART_CREATE_MUTATION,
            {"input": {"lines": [{"merchandiseId": variant_id, "quantity": quantity}]}},
        )
        result = data.get("cartCreate", {})
        _raise_user_errors(result)
        return ShopifyCart(result["cart"]) if result.get("cart") else None
    except ShopifyAPIError as exc:
        logger.error("cartCreate failed: %s", exc)
        return None


def cart_lines_add(cart_id: str, variant_id: str, quantity: int = 1) -> ShopifyCart | None:
    try:
        data = get_client().execute(
            queries.CART_LINES_ADD_MUTATION,
            {"cartId": cart_id, "lines": [{"merchandiseId": variant_id, "quantity": quantity}]},
        )
        result = data.get("cartLinesAdd", {})
        _raise_user_errors(result)
        return ShopifyCart(result["cart"]) if result.get("cart") else None
    except ShopifyAPIError as exc:
        logger.error("cartLinesAdd failed: %s", exc)
        return None


def cart_lines_update(cart_id: str, line_id: str, quantity: int) -> ShopifyCart | None:
    try:
        data = get_client().execute(
            queries.CART_LINES_UPDATE_MUTATION,
            {"cartId": cart_id, "lines": [{"id": line_id, "quantity": quantity}]},
        )
        result = data.get("cartLinesUpdate", {})
        _raise_user_errors(result)
        return ShopifyCart(result["cart"]) if result.get("cart") else None
    except ShopifyAPIError as exc:
        logger.error("cartLinesUpdate failed: %s", exc)
        return None


def cart_lines_remove(cart_id: str, line_id: str) -> ShopifyCart | None:
    try:
        data = get_client().execute(
            queries.CART_LINES_REMOVE_MUTATION,
            {"cartId": cart_id, "lineIds": [line_id]},
        )
        result = data.get("cartLinesRemove", {})
        _raise_user_errors(result)
        return ShopifyCart(result["cart"]) if result.get("cart") else None
    except ShopifyAPIError as exc:
        logger.error("cartLinesRemove failed: %s", exc)
        return None


def get_cart(cart_id: str) -> ShopifyCart | None:
    try:
        data = get_client().execute(queries.CART_QUERY, {"cartId": cart_id})
        raw = data.get("cart")
        return ShopifyCart(raw) if raw else None
    except ShopifyAPIError as exc:
        logger.error("cart query failed: %s", exc)
        return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _raise_user_errors(result: dict):
    errors = result.get("userErrors", [])
    if errors:
        msg = "; ".join(e.get("message", "Cart error") for e in errors)
        raise ShopifyAPIError(msg)


def _parse_decimal(value) -> Decimal:
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        return Decimal("0.00")


def _strip_html(html: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", html or "").strip()
