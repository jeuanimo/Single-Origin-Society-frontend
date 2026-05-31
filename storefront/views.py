from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Q

from products.models import BrewingGuide, TastingNote
from fundraising.models import FundraisingCampaign
from content.forms import AmbassadorInquiryForm, WholesaleInquiryForm
from content.models import Page, BlogPost
from marketing.models import EmailSubscriber
from shopify_client import service as shopify

from services.background.worker import enqueue
from services.content.notifications import send_inquiry_notification

URL_CART = "storefront:cart"
URL_HOME = "storefront:home"
TEMPLATE_INFO_PAGE = "storefront/info_page.html"
INFO_BODY_FALLBACK = "<p>Content coming soon.</p>"

# Shopify collection handles map to these URL category slugs
COLLECTION_SORT_MAP = {
    "price": ("PRICE", False),
    "-price": ("PRICE", True),
    "name": ("TITLE", False),
    "-name": ("TITLE", True),
    "-created_at": ("CREATED_AT", True),   # products query
    "created_at": ("CREATED_AT", False),   # products query
    "-created": ("CREATED", True),         # collection query
    "created": ("CREATED", False),         # collection query
}

POLICY_FALLBACKS = {
    "shipping": {
        "title": "Shipping Policy",
        "body": "<p>Orders are typically processed within 1–2 business days.</p><p>Complimentary shipping is available on qualifying orders. Delivery windows vary by destination and carrier.</p>",
    },
    "refunds": {
        "title": "Refund Policy",
        "body": "<p>If something is not right, contact us within 14 days of delivery.</p><p>Eligible items may be refunded or replaced according to condition and product type.</p>",
    },
    "privacy": {
        "title": "Privacy Policy",
        "body": "<p>We collect only the information needed to fulfill orders and improve your experience.</p><p>We do not sell personal data to third parties.</p>",
    },
    "terms": {
        "title": "Terms of Service",
        "body": "<p>By using this site, you agree to these terms and all applicable laws.</p><p>Product availability, pricing, and policies may be updated from time to time.</p>",
    },
}

INFO_PAGE_FALLBACKS = {
    "faq": {
        "title": "Frequently Asked Questions",
        "body": "<h2>Orders</h2><p>Most orders ship within 1–2 business days.</p><h2>Freshness</h2><p>All coffee is roasted in small batches for freshness.</p><h2>Support</h2><p>Need help? Contact us and we will respond promptly.</p>",
    },
    "wholesale": {
        "title": "Wholesale",
        "body": "<p>We partner with cafes, hotels, and retailers seeking exceptional coffee and tea.</p><p>Contact us with your business details and projected volume to begin onboarding.</p>",
    },
    "ambassador-program": {
        "title": "Ambassador Program",
        "body": "<p>Join our ambassador community to share the ritual and earn exclusive benefits.</p><p>Applications are reviewed on a rolling basis.</p>",
    },
}


# ── Public storefront ─────────────────────────────────────────────────────────

def home(request):
    featured = shopify.get_products(first=6, query="tag:featured")
    featured_coffee = shopify.get_collection_products("coffee", first=4)
    featured_tea = shopify.get_collection_products("tea", first=4)
    gift_sets = shopify.get_collection_products("gift-sets", first=4)

    campaigns = FundraisingCampaign.objects.filter(status="active")[:2]
    fundraising_feature = campaigns.first()

    tasting_preview = TastingNote.objects.order_by("-created_at")[:3]
    guides_preview = BrewingGuide.objects.filter(is_published=True).order_by("-created_at")[:3]

    now = timezone.now()
    journal_preview = BlogPost.objects.filter(
        Q(status="published") | Q(status="scheduled", published_at__lte=now)
    ).order_by("-published_at", "-created_at")[:3]

    return render(request, "storefront/home.html", {
        "featured_products": featured,
        "featured_coffee": featured_coffee,
        "featured_tea": featured_tea,
        "gift_sets": gift_sets,
        "campaigns": campaigns,
        "fundraising_feature": fundraising_feature,
        "tasting_preview": tasting_preview,
        "guides_preview": guides_preview,
        "journal_preview": journal_preview,
    })


def product_list(request, collection_handle: str = ""):
    sort_param = request.GET.get("sort", "-created_at")
    q = request.GET.get("q", "").strip()
    collection_filter = request.GET.get("collection", "").strip()

    sort_key, reverse = COLLECTION_SORT_MAP.get(sort_param, ("CREATED_AT", True))

    if collection_filter == "featured":
        products = shopify.get_products(first=48, query="tag:featured", sort_key=sort_key, reverse=reverse)
    elif collection_filter == "new-arrivals":
        products = shopify.get_products(first=48, sort_key="CREATED_AT", reverse=True)
    elif collection_filter == "value-finds":
        products = shopify.get_products(first=48, query="compare_at_price:>0", sort_key=sort_key, reverse=reverse)
    elif collection_handle:
        products = shopify.get_collection_products(collection_handle, first=48, sort_key=sort_key, reverse=reverse)
    else:
        products = shopify.get_products(first=48, sort_key=sort_key, reverse=reverse)

    if q:
        ql = q.lower()
        products = [p for p in products if ql in p.name.lower() or ql in p.description.lower()]

    return render(request, "storefront/product_list.html", {
        "products": products,
        "current_category": collection_handle or "",
        "search_query": q,
        "current_collection": collection_filter,
    })


def product_detail(request, handle: str):
    product = shopify.get_product_by_handle(handle)
    if not product:
        from django.http import Http404
        raise Http404("Product not found.")

    related = shopify.get_collection_products(
        product.product_type.lower() or "all",
        first=5,
    )
    related = [p for p in related if p.handle != handle][:4]

    product_guides = BrewingGuide.objects.filter(is_published=True).order_by("-created_at")[:3]

    return render(request, "storefront/product_detail.html", {
        "product": product,
        "related_products": related,
        "product_guides": product_guides,
        "is_coffee": product.is_coffee,
        "is_tea": product.is_tea,
        "reviews": [],
        "review_count": 0,
        "avg_rating": 0,
        "in_wishlist": False,
    })


# ── Content (Django-served) ───────────────────────────────────────────────────

def brewing_guides(request):
    guides = BrewingGuide.objects.filter(is_published=True)
    q = request.GET.get("q", "").strip()
    guide_type = request.GET.get("guide_type", "")
    level = request.GET.get("level", "")

    if q:
        guides = guides.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(method__icontains=q)
            | Q(tags__icontains=q)
        )
    if guide_type:
        guides = guides.filter(guide_type=guide_type)
    if level:
        guides = guides.filter(audience_level=level)

    beginner_guides = guides.filter(audience_level="beginner")[:6]
    premium_guides = guides.filter(is_premium_featured=True)[:4]
    if not premium_guides:
        premium_guides = guides.filter(audience_level="advanced")[:4]

    guide_type_sections = {
        "pour_over": guides.filter(guide_type="pour_over")[:4],
        "french_press": guides.filter(guide_type="french_press")[:4],
        "espresso_basics": guides.filter(guide_type="espresso_basics")[:4],
        "tea_steeping": guides.filter(guide_type="tea_steeping")[:4],
        "matcha_preparation": guides.filter(guide_type="matcha_preparation")[:4],
    }

    return render(request, "storefront/brewing_guides.html", {
        "guides": guides,
        "beginner_guides": beginner_guides,
        "premium_guides": premium_guides,
        "guide_type_sections": guide_type_sections,
        "search_query": q,
        "current_guide_type": guide_type,
        "current_level": level,
        "guide_type_choices": BrewingGuide.GUIDE_TYPE_CHOICES,
    })


def brewing_guide_detail(request, slug):
    guide = get_object_or_404(BrewingGuide, slug=slug, is_published=True)
    return render(request, "storefront/brewing_guide_detail.html", {"guide": guide})


def ritual(request):
    return render(request, "storefront/ritual.html")


def tasting_notes(request):
    notes = TastingNote.objects.all()
    q = request.GET.get("q", "").strip()
    tag = request.GET.get("tag", "").strip().lower()

    if q:
        notes = notes.filter(
            Q(title__icontains=q)
            | Q(body__icontains=q)
            | Q(aroma__icontains=q)
            | Q(flavor__icontains=q)
            | Q(finish__icontains=q)
            | Q(origin__icontains=q)
            | Q(pairings__icontains=q)
            | Q(tags__icontains=q)
        )
    if tag:
        notes = notes.filter(tags__icontains=tag)

    notes = list(notes.order_by("-created_at")[:80])
    for note in notes:
        note.tag_list = _split_tags(note.tags)

    all_tags = set()
    for tag_str in TastingNote.objects.exclude(tags="").values_list("tags", flat=True):
        all_tags.update(_split_tags(tag_str))

    return render(request, "storefront/tasting_notes.html", {
        "notes": notes,
        "search_query": q,
        "current_tag": tag,
        "all_tags": sorted(all_tags),
    })


def fundraising_list(request):
    campaigns = FundraisingCampaign.objects.filter(status="active")
    return render(request, "storefront/fundraising.html", {"campaigns": campaigns})


def fundraising_detail(request, slug):
    campaign = get_object_or_404(FundraisingCampaign, slug=slug)
    return render(request, "storefront/fundraising_detail.html", {"campaign": campaign})


def ritual_journal(request):
    now = timezone.now()
    posts = BlogPost.objects.filter(
        Q(status="published") | Q(status="scheduled", published_at__lte=now)
    ).order_by("-published_at", "-created_at")

    q = request.GET.get("q", "").strip()
    entry_type = request.GET.get("entry_type", "").strip()
    tag = request.GET.get("tag", "").strip().lower()

    if q:
        posts = posts.filter(
            Q(title__icontains=q)
            | Q(excerpt__icontains=q)
            | Q(body__icontains=q)
            | Q(tags__icontains=q)
        )
    if entry_type:
        posts = posts.filter(entry_type=entry_type)
    if tag:
        posts = posts.filter(tags__icontains=tag)

    all_tags = set()
    for tag_string in BlogPost.objects.exclude(tags="").values_list("tags", flat=True):
        all_tags.update(_split_tags(tag_string))

    featured_post = posts.first()
    remaining_posts = posts[1:15] if featured_post else posts[:15]

    return render(request, "storefront/ritual_journal.html", {
        "featured_post": featured_post,
        "posts": remaining_posts,
        "search_query": q,
        "current_entry_type": entry_type,
        "current_tag": tag,
        "entry_type_choices": BlogPost.ENTRY_TYPE_CHOICES,
        "all_tags": sorted(all_tags),
    })


def ritual_journal_detail(request, slug):
    now = timezone.now()
    post = get_object_or_404(BlogPost, slug=slug)
    is_visible = post.status == "published" or (
        post.status == "scheduled" and post.published_at and post.published_at <= now
    )
    if not is_visible:
        return redirect("storefront:ritual_journal")

    related_posts = BlogPost.objects.filter(
        Q(status="published") | Q(status="scheduled", published_at__lte=now)
    ).exclude(pk=post.pk).order_by("-published_at")[:3]

    return render(request, "storefront/ritual_journal_detail.html", {
        "post": post,
        "related_posts": related_posts,
        "post_tags": _split_tags(post.tags),
    })


def about(request):
    page = Page.objects.filter(slug="about").first()
    return render(request, "storefront/about.html", {
        "page": page,
        "page_visual_alt": _page_image_alt(page, "About page visual"),
    })


def contact(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        sender_email = request.POST.get("email", "").strip()
        subject = request.POST.get("subject", "").strip() or "Contact Form Enquiry"
        message_body = request.POST.get("message", "").strip()

        if sender_email and message_body:
            from django.core.mail import EmailMessage
            from django.conf import settings
            try:
                EmailMessage(
                    subject=f"Contact: {subject}",
                    body=f"From: {first_name} {last_name} <{sender_email}>\n\n{message_body}",
                    from_email=None,
                    to=[settings.ORDER_NOTIFICATION_EMAIL],
                    reply_to=[sender_email],
                ).send()
            except Exception:
                pass

        messages.success(request, "Thank you for your message. We'll be in touch.")
        return redirect("storefront:contact")
    return render(request, "storefront/contact.html")


def policies(request, slug="shipping"):
    page = Page.objects.filter(slug=slug).first()
    fallback = POLICY_FALLBACKS.get(slug, {})
    return render(request, "storefront/policies.html", {
        "page": page,
        "page_visual_alt": _page_image_alt(page, "Policy page visual"),
        "policy_slug": slug,
        "policy_title": fallback.get("title", "Policies"),
        "policy_body": fallback.get("body", "<p>Policy content coming soon.</p>"),
    })


def faq(request):
    return _info_page(request, "faq")


def wholesale(request):
    page, fallback = _get_page_with_fallback("wholesale", INFO_PAGE_FALLBACKS)
    if request.method == "POST":
        form = WholesaleInquiryForm(request.POST)
        if form.is_valid():
            inquiry = form.save()
            enqueue(
                send_inquiry_notification,
                "New wholesale inquiry",
                f"Wholesale inquiry from {inquiry.name} ({inquiry.email}) for {inquiry.company_name}.",
            )
            messages.success(request, "Thank you. Our wholesale team will contact you shortly.")
            return redirect("storefront:wholesale")
    else:
        form = WholesaleInquiryForm()

    return render(request, TEMPLATE_INFO_PAGE, {
        "page": page,
        "title": page.title if page else fallback.get("title", "Wholesale"),
        "body": page.body if page else fallback.get("body", INFO_BODY_FALLBACK),
        "inquiry_form": form,
        "inquiry_heading": "Wholesale Inquiry",
        "inquiry_submit_label": "Send Wholesale Inquiry",
    })


def ambassador_program(request):
    page, fallback = _get_page_with_fallback("ambassador-program", INFO_PAGE_FALLBACKS)
    if request.method == "POST":
        form = AmbassadorInquiryForm(request.POST)
        if form.is_valid():
            inquiry = form.save()
            enqueue(
                send_inquiry_notification,
                "New ambassador inquiry",
                f"Ambassador inquiry from {inquiry.name} ({inquiry.email}) on {inquiry.primary_platform}.",
            )
            messages.success(request, "Thanks for applying. We review ambassador requests weekly.")
            return redirect("storefront:ambassador_program")
    else:
        form = AmbassadorInquiryForm()

    return render(request, TEMPLATE_INFO_PAGE, {
        "page": page,
        "title": page.title if page else fallback.get("title", "Ambassador Program"),
        "body": page.body if page else fallback.get("body", INFO_BODY_FALLBACK),
        "inquiry_form": form,
        "inquiry_heading": "Ambassador Inquiry",
        "inquiry_submit_label": "Submit Ambassador Application",
    })


# ── Shopify Cart ──────────────────────────────────────────────────────────────

def _get_shopify_cart_id(request) -> str:
    return request.session.get("shopify_cart_id", "")


def _save_cart_to_session(request, cart):
    request.session["shopify_cart_id"] = cart.id
    request.session["shopify_cart_count"] = cart.total_quantity
    request.session.modified = True


def cart_view(request):
    cart_id = _get_shopify_cart_id(request)
    cart = shopify.get_cart(cart_id) if cart_id else None

    return render(request, "storefront/cart.html", {
        "cart": cart,
        "items": cart.lines if cart else [],
        "subtotal": cart.subtotal if cart else 0,
        "checkout_url": cart.checkout_url if cart else "",
    })


@require_POST
def cart_add(request):
    variant_id = request.POST.get("variant_id", "").strip()
    try:
        quantity = max(1, int(request.POST.get("quantity", 1)))
    except (ValueError, TypeError):
        quantity = 1

    if not variant_id:
        messages.error(request, "Invalid product selection.")
        return redirect(URL_CART)

    cart_id = _get_shopify_cart_id(request)

    if cart_id:
        cart = shopify.cart_lines_add(cart_id, variant_id, quantity)
    else:
        cart = shopify.cart_create(variant_id, quantity)

    if cart:
        _save_cart_to_session(request, cart)
        messages.success(request, "Added to cart.")
    else:
        messages.error(request, "Could not add item to cart. Please try again.")

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or URL_CART
    return redirect(next_url)


@require_POST
def cart_update(request):
    line_id = request.POST.get("line_id", "").strip()
    try:
        quantity = int(request.POST.get("quantity", 0))
    except (ValueError, TypeError):
        quantity = 0

    cart_id = _get_shopify_cart_id(request)
    if not cart_id or not line_id:
        return redirect(URL_CART)

    if quantity <= 0:
        cart = shopify.cart_lines_remove(cart_id, line_id)
    else:
        cart = shopify.cart_lines_update(cart_id, line_id, quantity)

    if cart:
        _save_cart_to_session(request, cart)

    return redirect(URL_CART)


@require_POST
def cart_remove(request):
    line_id = request.POST.get("line_id", "").strip()
    cart_id = _get_shopify_cart_id(request)

    if cart_id and line_id:
        cart = shopify.cart_lines_remove(cart_id, line_id)
        if cart:
            _save_cart_to_session(request, cart)

    return redirect(URL_CART)


def checkout_redirect(request):
    """Redirect the customer to Shopify-hosted checkout."""
    cart_id = _get_shopify_cart_id(request)
    if not cart_id:
        return redirect(URL_CART)

    cart = shopify.get_cart(cart_id)
    if not cart or not cart.checkout_url:
        messages.error(request, "Unable to proceed to checkout. Please try again.")
        return redirect(URL_CART)

    return redirect(cart.checkout_url)


# ── Newsletter ────────────────────────────────────────────────────────────────

@require_POST
def newsletter_subscribe(request):
    email = request.POST.get("email", "").strip()
    if not email:
        return redirect(URL_HOME)

    defaults = _newsletter_tracking_defaults(request)
    subscriber, created = EmailSubscriber.objects.get_or_create(email=email, defaults=defaults)
    if not created:
        _update_subscriber_tracking(subscriber, defaults)

    messages.success(request, "Thank you for subscribing.")
    return redirect(URL_HOME)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _info_page(request, slug):
    page = Page.objects.filter(slug=slug).first()
    fallback = INFO_PAGE_FALLBACKS.get(slug, {})
    return render(request, TEMPLATE_INFO_PAGE, {
        "page": page,
        "page_visual_alt": _page_image_alt(page, "Page visual"),
        "title": page.title if page else fallback.get("title", "Information"),
        "body": page.body if page else fallback.get("body", INFO_BODY_FALLBACK),
    })


def _get_page_with_fallback(slug, fallback_map):
    page = Page.objects.filter(slug=slug).first()
    return page, fallback_map.get(slug, {})


def _page_image_alt(page, fallback):
    if not page:
        return fallback
    return (page.image_alt or "").strip() or fallback


def _newsletter_tracking_defaults(request):
    source_raw = request.POST.get("source") or request.META.get("HTTP_REFERER", "direct")
    return {
        "source": source_raw[:100],
        "referral_code": (request.POST.get("ref") or request.session.get("tracking_ref", ""))[:80],
        "utm_source": (request.POST.get("utm_source") or request.session.get("tracking_utm_source", ""))[:120],
        "utm_medium": (request.POST.get("utm_medium") or request.session.get("tracking_utm_medium", ""))[:120],
        "utm_campaign": (request.POST.get("utm_campaign") or request.session.get("tracking_utm_campaign", ""))[:120],
        "landing_path": (request.POST.get("landing_path") or request.session.get("tracking_landing_path", request.path))[:255],
    }


def _update_subscriber_tracking(subscriber, defaults):
    changed = False
    for field, value in defaults.items():
        if value and getattr(subscriber, field) != value:
            setattr(subscriber, field, value)
            changed = True
    if changed:
        subscriber.save()


def _split_tags(value):
    return [part.strip().lower() for part in value.split(",") if part.strip()]
