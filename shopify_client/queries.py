"""
All Shopify Storefront API GraphQL queries and mutations.
Centralised here so views never embed query strings.
"""

# ── Fragments ────────────────────────────────────────────────────────────────

MONEY_FRAGMENT = """
fragment Money on MoneyV2 {
  amount
  currencyCode
}
"""

IMAGE_FRAGMENT = """
fragment Image on Image {
  url
  altText
  width
  height
}
"""

VARIANT_FRAGMENT = """
fragment Variant on ProductVariant {
  id
  title
  sku
  availableForSale
  quantityAvailable
  price { ...Money }
  compareAtPrice { ...Money }
  selectedOptions { name value }
}
"""

PRODUCT_CARD_FRAGMENT = """
fragment ProductCard on Product {
  id
  title
  handle
  productType
  tags
  featuredImage { ...Image }
  priceRange {
    minVariantPrice { ...Money }
  }
  compareAtPriceRange {
    maxVariantPrice { ...Money }
  }
  variants(first: 1) {
    edges { node { ...Variant } }
  }
}
"""

# Coffee/tea-specific metafields requested on every product
PRODUCT_METAFIELDS = """
metafields(identifiers: [
  { namespace: "custom", key: "origin" },
  { namespace: "custom", key: "blend_info" },
  { namespace: "custom", key: "roast_level" },
  { namespace: "custom", key: "flavor_notes" },
  { namespace: "custom", key: "aroma_profile" },
  { namespace: "custom", key: "body_profile" },
  { namespace: "custom", key: "acidity_profile" },
  { namespace: "custom", key: "finish_profile" },
  { namespace: "custom", key: "steeping_notes" },
  { namespace: "custom", key: "ritual_description" },
  { namespace: "custom", key: "available_sizes" },
  { namespace: "custom", key: "grind_options" },
  { namespace: "custom", key: "weight" },
  { namespace: "custom", key: "meta_title" },
  { namespace: "custom", key: "meta_description" },
  { namespace: "custom", key: "og_title" },
  { namespace: "custom", key: "og_description" },
  { namespace: "custom", key: "subscription_available" }
]) {
  key
  value
}
"""

PRODUCT_DETAIL_FRAGMENT = """
fragment ProductDetail on Product {
  id
  title
  handle
  descriptionHtml
  productType
  tags
  featuredImage { ...Image }
  images(first: 8) { edges { node { ...Image } } }
  variants(first: 20) { edges { node { ...Variant } } }
  METAFIELDS_PLACEHOLDER
}
""".replace("METAFIELDS_PLACEHOLDER", PRODUCT_METAFIELDS)

# ── Cart fragment ─────────────────────────────────────────────────────────────

CART_FRAGMENT = """
fragment CartFields on Cart {
  id
  checkoutUrl
  totalQuantity
  cost {
    subtotalAmount { ...Money }
    totalAmount { ...Money }
    totalTaxAmount { ...Money }
  }
  discountCodes { code applicable }
  lines(first: 100) {
    edges {
      node {
        id
        quantity
        cost {
          totalAmount { ...Money }
          amountPerQuantity { ...Money }
        }
        merchandise {
          ... on ProductVariant {
            id
            title
            sku
            price { ...Money }
            compareAtPrice { ...Money }
            product {
              title
              handle
              featuredImage { ...Image }
            }
          }
        }
        attributes { key value }
      }
    }
  }
}
"""

# ── Product queries ───────────────────────────────────────────────────────────

PRODUCTS_QUERY = f"""
{MONEY_FRAGMENT}
{IMAGE_FRAGMENT}
{VARIANT_FRAGMENT}
{PRODUCT_CARD_FRAGMENT}
query Products($first: Int!, $query: String, $sortKey: ProductSortKeys, $reverse: Boolean) {{
  products(first: $first, query: $query, sortKey: $sortKey, reverse: $reverse) {{
    edges {{
      node {{ ...ProductCard }}
    }}
    pageInfo {{ hasNextPage endCursor }}
  }}
}}
"""

PRODUCT_BY_HANDLE_QUERY = f"""
{MONEY_FRAGMENT}
{IMAGE_FRAGMENT}
{VARIANT_FRAGMENT}
{PRODUCT_DETAIL_FRAGMENT}
query ProductByHandle($handle: String!) {{
  product(handle: $handle) {{ ...ProductDetail }}
}}
"""

COLLECTION_PRODUCTS_QUERY = f"""
{MONEY_FRAGMENT}
{IMAGE_FRAGMENT}
{VARIANT_FRAGMENT}
{PRODUCT_CARD_FRAGMENT}
query CollectionProducts($handle: String!, $first: Int!, $sortKey: ProductCollectionSortKeys, $reverse: Boolean) {{
  collection(handle: $handle) {{
    title
    handle
    descriptionHtml
    products(first: $first, sortKey: $sortKey, reverse: $reverse) {{
      edges {{ node {{ ...ProductCard }} }}
      pageInfo {{ hasNextPage endCursor }}
    }}
  }}
}}
"""

COLLECTIONS_QUERY = f"""
{IMAGE_FRAGMENT}
query Collections($first: Int!) {{
  collections(first: $first) {{
    edges {{
      node {{
        id
        title
        handle
        image {{ ...Image }}
      }}
    }}
  }}
}}
"""

# ── Cart mutations ────────────────────────────────────────────────────────────

CART_CREATE_MUTATION = f"""
{MONEY_FRAGMENT}
{IMAGE_FRAGMENT}
{CART_FRAGMENT}
mutation CartCreate($input: CartInput!) {{
  cartCreate(input: $input) {{
    cart {{ ...CartFields }}
    userErrors {{ field message }}
  }}
}}
"""

CART_LINES_ADD_MUTATION = f"""
{MONEY_FRAGMENT}
{IMAGE_FRAGMENT}
{CART_FRAGMENT}
mutation CartLinesAdd($cartId: ID!, $lines: [CartLineInput!]!) {{
  cartLinesAdd(cartId: $cartId, lines: $lines) {{
    cart {{ ...CartFields }}
    userErrors {{ field message }}
  }}
}}
"""

CART_LINES_UPDATE_MUTATION = f"""
{MONEY_FRAGMENT}
{IMAGE_FRAGMENT}
{CART_FRAGMENT}
mutation CartLinesUpdate($cartId: ID!, $lines: [CartLineUpdateInput!]!) {{
  cartLinesUpdate(cartId: $cartId, lines: $lines) {{
    cart {{ ...CartFields }}
    userErrors {{ field message }}
  }}
}}
"""

CART_LINES_REMOVE_MUTATION = f"""
{MONEY_FRAGMENT}
{IMAGE_FRAGMENT}
{CART_FRAGMENT}
mutation CartLinesRemove($cartId: ID!, $lineIds: [ID!]!) {{
  cartLinesRemove(cartId: $cartId, lineIds: $lineIds) {{
    cart {{ ...CartFields }}
    userErrors {{ field message }}
  }}
}}
"""

CART_QUERY = f"""
{MONEY_FRAGMENT}
{IMAGE_FRAGMENT}
{CART_FRAGMENT}
query Cart($cartId: ID!) {{
  cart(id: $cartId) {{ ...CartFields }}
}}
"""
