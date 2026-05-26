"""
Thin HTTP client for the Shopify Storefront API.

Never import this module in templates or anywhere that runs client-side.
The Storefront Access Token is server-side only.
"""

import json
import logging
import urllib.request
import urllib.error
from django.conf import settings

logger = logging.getLogger(__name__)


class ShopifyAPIError(Exception):
    pass


class ShopifyStorefrontClient:
    """Executes GraphQL queries against the Shopify Storefront API."""

    def __init__(self):
        domain = settings.SHOPIFY_STORE_DOMAIN
        version = settings.SHOPIFY_API_VERSION
        self._url = f"https://{domain}/api/{version}/graphql.json"
        self._token = settings.SHOPIFY_STOREFRONT_ACCESS_TOKEN

    def execute(self, query: str, variables: dict | None = None) -> dict:
        payload = json.dumps(
            {"query": query, "variables": variables or {}}
        ).encode("utf-8")

        req = urllib.request.Request(
            self._url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Storefront-Access-Token": self._token,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            logger.error("Shopify Storefront API unreachable: %s", exc)
            raise ShopifyAPIError("Unable to reach Shopify.") from exc

        if "errors" in body:
            msg = body["errors"][0].get("message", "Unknown Shopify error")
            logger.error("Shopify GraphQL error: %s", body["errors"])
            raise ShopifyAPIError(msg)

        return body.get("data", {})


_client: ShopifyStorefrontClient | None = None


def get_client() -> ShopifyStorefrontClient:
    global _client
    if _client is None:
        _client = ShopifyStorefrontClient()
    return _client
