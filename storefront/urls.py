from django.urls import path
from . import views

app_name = "storefront"

urlpatterns = [
    path("", views.home, name="home"),
    # Product browsing — collection handles map to Shopify collection slugs
    path("shop/", views.product_list, name="shop"),
    path("shop/coffee/", views.product_list, {"collection_handle": "coffee"}, name="coffee"),
    path("shop/tea/", views.product_list, {"collection_handle": "tea"}, name="tea"),
    path("shop/accessories/", views.product_list, {"collection_handle": "accessories"}, name="accessories"),
    path("shop/drinkware/", views.product_list, {"collection_handle": "drinkware"}, name="drinkware"),
    path("shop/gift-sets/", views.product_list, {"collection_handle": "gift-sets"}, name="gift_sets"),
    path("product/<slug:handle>/", views.product_detail, name="product_detail"),
    # Content (served from Django DB — unchanged)
    path("brewing-guides/", views.brewing_guides, name="brewing_guides"),
    path("brewing-guides/<slug:slug>/", views.brewing_guide_detail, name="brewing_guide_detail"),
    path("ritual/", views.ritual, name="ritual"),
    path("tasting-notes/", views.tasting_notes, name="tasting_notes"),
    path("fundraising/", views.fundraising_list, name="fundraising"),
    path("fundraising/<slug:slug>/", views.fundraising_detail, name="fundraising_detail"),
    path("ritual-journal/", views.ritual_journal, name="ritual_journal"),
    path("ritual-journal/<slug:slug>/", views.ritual_journal_detail, name="ritual_journal_detail"),
    # Info pages
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("policies/", views.policies, name="policies"),
    path("policies/shipping/", views.policies, {"slug": "shipping"}, name="policy_shipping"),
    path("policies/refunds/", views.policies, {"slug": "refunds"}, name="policy_refunds"),
    path("policies/privacy/", views.policies, {"slug": "privacy"}, name="policy_privacy"),
    path("policies/terms/", views.policies, {"slug": "terms"}, name="policy_terms"),
    path("policies/<slug:slug>/", views.policies, name="policy_page"),
    path("faq/", views.faq, name="faq"),
    path("wholesale/", views.wholesale, name="wholesale"),
    path("ambassador-program/", views.ambassador_program, name="ambassador_program"),
    # Shopify cart — POST-only endpoints
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/", views.cart_add, name="cart_add"),
    path("cart/update/", views.cart_update, name="cart_update"),
    path("cart/remove/", views.cart_remove, name="cart_remove"),
    # Checkout: redirects to Shopify-hosted checkout
    path("checkout/", views.checkout_redirect, name="checkout"),
    # Newsletter
    path("newsletter/subscribe/", views.newsletter_subscribe, name="newsletter_subscribe"),
]
