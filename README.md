# Single Origin Society — Shopify-Backed Custom Storefront

**Stack:** Django 6.0 · Python 3.12 · PostgreSQL · Shopify Storefront API

This is the custom frontend for Single Origin Society. Django renders all templates and proxies product/cart/checkout data through the **Shopify Storefront API** — Shopify is the commerce backend. The Django server never exposes Shopify credentials to the browser.

---

## Architecture

```
Browser ──► Django (templates, sessions, content DB)
                │
                ├── Shopify Storefront API  (products, cart, checkout)
                └── PostgreSQL DB           (blog, brewing guides, tasting notes,
                                             fundraising campaigns, email subscribers,
                                             inquiry forms, CMS pages)
```

**What Shopify owns:**
Products · Variants · Collections · Inventory · Pricing · Discounts · Cart · Checkout · Payments · Taxes · Shipping · Orders · Customer accounts · Fulfillment

**What Django owns:**
Blog (Ritual Journal) · Brewing guides · Tasting notes · Fundraising campaigns · CMS pages · Email subscriber list · Wholesale/ambassador inquiry forms · Content blocks

---

## Shopify Setup

### 1. Create a Shopify store

Set up your store at [shopify.com](https://www.shopify.com).

### 2. Create a Storefront API access token

1. In Shopify Admin → **Apps** → **Develop apps** → **Create an app**
2. Name it `SOS Storefront Frontend`
3. Under **Configuration → Storefront API access scopes**, enable:
   - `unauthenticated_read_product_listings`
   - `unauthenticated_read_collection_listings`
   - `unauthenticated_write_checkouts`
   - `unauthenticated_read_checkouts`
   - `unauthenticated_write_customers`
   - `unauthenticated_read_customer_tags`
4. Install the app and copy the **Storefront API access token**

> ⚠️ The Storefront Access Token has **read-only public scope**. It is safe to use server-side in environment variables but should **never** be returned in HTML, API responses, or browser JS.

### 3. Set up collections in Shopify Admin

Create these collections (handles must match exactly):

| Collection title | Handle |
|---|---|
| Coffee | `coffee` |
| Tea | `tea` |
| Accessories | `accessories` |
| Drinkware | `drinkware` |
| Gift Sets | `gift-sets` |

### 4. Set up product metafields

Add these metafield definitions in Shopify Admin → **Settings → Custom data → Products**:

| Namespace | Key | Type | Purpose |
|---|---|---|---|
| `custom` | `origin` | Single-line text | Country/region of origin |
| `custom` | `blend_info` | Single-line text | Blend description |
| `custom` | `roast_level` | Single-line text | Roast level label |
| `custom` | `flavor_notes` | Single-line text | Flavor notes |
| `custom` | `aroma_profile` | Single-line text | Aroma descriptor |
| `custom` | `body_profile` | Single-line text | Body descriptor |
| `custom` | `acidity_profile` | Single-line text | Acidity descriptor |
| `custom` | `finish_profile` | Single-line text | Finish descriptor |
| `custom` | `steeping_notes` | Multi-line text | Tea steeping instructions |
| `custom` | `ritual_description` | Multi-line text | Ritual copy for product page |
| `custom` | `available_sizes` | Single-line text | e.g. "250g, 500g, 1kg" |
| `custom` | `grind_options` | Single-line text | e.g. "Whole Bean, Pour Over, Espresso" |
| `custom` | `weight` | Single-line text | Package weight |
| `custom` | `meta_title` | Single-line text | SEO title override |
| `custom` | `meta_description` | Single-line text | SEO description override |
| `custom` | `og_title` | Single-line text | Open Graph title override |
| `custom` | `og_description` | Single-line text | Open Graph description override |
| `custom` | `subscription_available` | Single-line text | `true` to show subscription copy |

### 5. Import products

Use the Shopify CSV importer (Admin → **Products → Import**) or the bulk GraphQL import. When importing:

- `Title` → product name
- `Body (HTML)` → product description
- `Variant Price` → price
- `Variant Compare At Price` → compare/was price
- `Variant SKU` → SKU
- `Image Src` → product images
- `Tags` → include `featured` for featured products; use collection assignment for categories
- Metafields → use the Shopify CSV metafield column format: `Metafield: custom.origin [single_line_text_field]`

---

## Local Development

### Prerequisites

- Python 3.12+
- PostgreSQL
- A Shopify store with a Storefront API token

### Setup

```bash
git clone https://github.com/jeuanimo/Single-Origin-Society-frontend.git
cd Single-Origin-Society-frontend

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — fill in SHOPIFY_STORE_DOMAIN, SHOPIFY_STOREFRONT_ACCESS_TOKEN, and DB values

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit `http://127.0.0.1:8000` — product pages will pull live data from Shopify.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | Yes | Django secret key |
| `DJANGO_DEBUG` | No | `True` in dev, `False` in production |
| `DJANGO_ALLOWED_HOSTS` | Yes | Comma-separated allowed hostnames |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Yes (prod) | Comma-separated trusted origins with `https://` |
| `DB_NAME` | Yes | PostgreSQL database name |
| `DB_USER` | Yes | PostgreSQL user |
| `DB_PASSWORD` | Yes | PostgreSQL password |
| `DB_HOST` | Yes | PostgreSQL host |
| `DB_PORT` | No | Default `5432` |
| `SHOPIFY_STORE_DOMAIN` | **Yes** | e.g. `your-store.myshopify.com` |
| `SHOPIFY_STOREFRONT_ACCESS_TOKEN` | **Yes** | Storefront API token (server-side only) |
| `SHOPIFY_API_VERSION` | No | Default `2025-04` |
| `SENDGRID_API_KEY` | No | For transactional email in production |

---

## Deployment (Render)

1. Connect the GitHub repo to Render
2. Use the `render.yaml` configuration — it sets up the web service and PostgreSQL database automatically
3. Add the Shopify environment variables in Render's **Environment** tab (they are marked `sync: false` in `render.yaml` for security)
4. Deploy — Render runs `migrate` and `collectstatic` automatically on each deploy

---

## What Shopify Now Handles

| Feature | Where |
|---|---|
| Product catalog | Shopify Admin → Products |
| Collections / categories | Shopify Admin → Collections |
| Inventory tracking | Shopify Admin → Inventory |
| Pricing & compare prices | Shopify Admin → Products → Variants |
| Cart | Shopify Storefront API (cart ID stored in Django session) |
| Checkout | Shopify hosted checkout (`checkoutUrl` redirect) |
| Payments | Shopify Payments / your configured gateway |
| Tax calculation | Shopify Tax |
| Shipping rates | Shopify Admin → Settings → Shipping |
| Discount codes | Shopify Admin → Discounts |
| Orders | Shopify Admin → Orders |
| Customer accounts | Shopify (new customer accounts) |
| Order history | Shopify customer account portal |
| Fulfillment | Shopify Admin → Orders (or integrated 3PL) |
| Returns/refunds | Shopify Admin → Orders |
| Analytics | Shopify Analytics |
| Marketing emails | Shopify Email or Klaviyo |
| Product reviews | Shopify Product Reviews app or Judge.me |
| Customer support | Shopify Inbox, Gorgias, or Zendesk |

---

## Fundraising

Fundraising campaigns and their public pages are managed in the Django CMS (Admin → Fundraising). Sales attribution to campaigns is tracked via `FundraisingSale` records that store the Shopify order ID. To build a full fundraising team dashboard, see `fundraising/models.py` — the `FundraisingSale` model is wired to accept Shopify order IDs.

For teams/organizations needing a self-service dashboard, the recommended path is:
- **Simple:** Use Shopify discount codes per team + `FundraisingSale` records
- **Advanced:** Build a lightweight Shopify app using the Admin API (server-side) to pull order attribution data

---

## Backend Replacement Matrix

| Old Django App | Replaced By |
|---|---|
| `products/` (Product, Category, Variant) | Shopify Products + Collections |
| `cart/` | Shopify Storefront API cart |
| `checkout/` + Stripe | Shopify hosted checkout |
| `orders/` | Shopify Orders |
| `inventory/` | Shopify Inventory |
| `purchasing/` | Shopify supply chain / manual |
| `finance/` | Shopify Analytics + Xero/QuickBooks |
| `reporting/` | Shopify Analytics |
| `crm/` | Shopify Customers + tags |
| `shipping/` | Shopify Shipping |
| `portal/` | Shopify Admin |
| `reviews/` | Shopify reviews app |
| `support/` | Shopify Inbox / Gorgias |
| `customers/` (wishlist, addresses) | Shopify customer accounts |
| `marketing/` (coupons) | Shopify Discounts |
| `business_config/` | Django settings + env vars |
| `accounts/` (portal roles/permissions) | Shopify Staff accounts |

---

## Testing Checklist

- [ ] Homepage loads — featured products pulled from Shopify
- [ ] `/shop/` loads all products
- [ ] `/shop/coffee/` loads coffee collection
- [ ] `/product/<handle>/` loads product detail with correct price, images, and metafields
- [ ] "Add to Cart" creates a Shopify cart (cart ID stored in session)
- [ ] Cart page displays Shopify cart lines with correct quantities and totals
- [ ] Cart update (quantity change) reflects in Shopify cart
- [ ] Cart remove deletes line from Shopify cart
- [ ] "Proceed to Checkout" redirects to Shopify hosted checkout URL
- [ ] Newsletter subscribe creates an EmailSubscriber record
- [ ] Brewing guides and tasting notes pages load from Django DB
- [ ] Blog / Ritual Journal loads from Django DB
- [ ] Fundraising campaign pages load correctly
- [ ] Wholesale inquiry form submits successfully
- [ ] Ambassador inquiry form submits successfully
- [ ] Django admin accessible at `/admin/` for content management
- [ ] No Shopify tokens visible in page source, API responses, or browser JS
- [ ] `DJANGO_DEBUG=False` does not expose a debug page on errors
