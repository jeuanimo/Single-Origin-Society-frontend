from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.utils.dateparse import parse_datetime
from django.urls import reverse, NoReverseMatch
import csv

from accounts.decorators import portal_required, manager_required
from portal.imap_client import fetch_inbox, fetch_message, delete_message, mark_unread, toggle_important, IMAPError
from portal.models import EmailDraft
from accounts.models import User
from portal.forms import InquiryAssignForm, InquiryFilterForm, InquiryNoteForm
from products.models import BrewingGuide, TastingNote
from marketing.models import EmailSubscriber
from content.models import (
    AmbassadorInquiry, AmbassadorInquiryNote,
    BlogPost, ContentBlock, Page,
    WholesaleInquiry, WholesaleInquiryNote,
)
from fundraising.models import FundraisingCampaign, Donation

URL_WHOLESALE_DETAIL = "portal:content_wholesale_inquiry_detail"
URL_AMBASSADOR_DETAIL = "portal:content_ambassador_inquiry_detail"
URL_CONTENT_BLOG = "portal:content_blog"
URL_CONTENT_PAGES = "portal:content_pages"


# ── Dashboard ─────────────────────────────────────────────────────────────────

@portal_required
def dashboard(request):
    fundraising_active = FundraisingCampaign.objects.filter(status="active")
    fundraising_goal = fundraising_active.aggregate(s=Sum("goal_amount"))["s"] or 0
    fundraising_raised = fundraising_active.aggregate(s=Sum("raised_amount"))["s"] or 0
    fundraising_percent = int((fundraising_raised / fundraising_goal) * 100) if fundraising_goal else 0

    stats = {
        "blog_posts": BlogPost.objects.filter(status="published").count(),
        "brewing_guides": BrewingGuide.objects.filter(is_published=True).count(),
        "tasting_notes": TastingNote.objects.count(),
        "pages": Page.objects.filter(is_published=True).count(),
        "subscribers": EmailSubscriber.objects.filter(is_active=True).count(),
        "wholesale_inquiries": WholesaleInquiry.objects.count(),
        "ambassador_inquiries": AmbassadorInquiry.objects.count(),
        "fundraising_campaigns": fundraising_active.count(),
        "fundraising_raised": fundraising_raised,
        "fundraising_goal": fundraising_goal,
        "fundraising_percent": fundraising_percent,
    }
    recent_posts = BlogPost.objects.order_by("-updated_at")[:5]
    recent_wholesale = WholesaleInquiry.objects.order_by("-created_at")[:5]
    recent_ambassador = AmbassadorInquiry.objects.order_by("-created_at")[:5]
    return render(request, "portal/dashboard.html", {
        "stats": stats,
        "recent_posts": recent_posts,
        "recent_wholesale": recent_wholesale,
        "recent_ambassador": recent_ambassador,
    })


# ── Content Hub ───────────────────────────────────────────────────────────────

@portal_required
def content_hub(request):
    stats = {
        "pages": Page.objects.count(),
        "guides": BrewingGuide.objects.count(),
        "tasting_notes": TastingNote.objects.count(),
        "journal_posts": BlogPost.objects.count(),
        "wholesale_inquiries": WholesaleInquiry.objects.count(),
        "ambassador_inquiries": AmbassadorInquiry.objects.count(),
    }
    placeholders = ["Homepage sections", "About page content", "Contact page content", "FAQs", "Policy pages"]
    return render(request, "portal/content/hub.html", {"stats": stats, "placeholders": placeholders})


# ── Pages ─────────────────────────────────────────────────────────────────────

@portal_required
def content_pages(request):
    pages = Page.objects.all()
    blog_posts = BlogPost.objects.select_related("author").all()
    return render(request, "portal/content/pages.html", {"pages": pages, "blog_posts": blog_posts})


@portal_required
def content_page_edit(request, pk=None):
    page = get_object_or_404(Page, pk=pk) if pk else None
    if request.method == "POST":
        data = request.POST
        obj = page or Page()
        obj.title = data.get("title", "")
        obj.slug = data.get("slug", "").strip() or obj.slug
        obj.body = data.get("body", "")
        obj.meta_title = data.get("meta_title", "")
        obj.meta_description = data.get("meta_description", "")
        obj.image_alt = data.get("image_alt", "").strip()
        if request.FILES.get("image"):
            obj.image = request.FILES["image"]
        elif data.get("clear_image") == "on" and obj.image:
            obj.image.delete(save=False)
            obj.image = None
        obj.is_published = data.get("is_published") == "on"
        obj.save()
        messages.success(request, "Page saved.")
        return redirect(URL_CONTENT_PAGES)
    return render(request, "portal/content/page_edit.html", {"page": page})


# ── Content Blocks ────────────────────────────────────────────────────────────

@portal_required
def content_blocks(request):
    page_filter = request.GET.get("page_key", "")
    blocks = ContentBlock.objects.all()
    if page_filter:
        blocks = blocks.filter(page_key=page_filter)
    blocks = list(blocks)
    for block in blocks:
        block.live_url = _resolve_block_live_url(block)
    return render(request, "portal/content/blocks.html", {
        "blocks": blocks,
        "page_choices": ContentBlock.PAGE_CHOICES,
        "page_filter": page_filter,
    })


@portal_required
def content_block_edit(request, pk=None):
    content_block = get_object_or_404(ContentBlock, pk=pk) if pk else None
    if request.method == "POST":
        data = request.POST
        obj = content_block or ContentBlock()
        obj.page_key = data.get("page_key", "home")
        obj.section_key = data.get("section_key", "").strip()
        obj.label = data.get("label", "").strip()
        obj.body = data.get("body", "")
        obj.image_alt = data.get("image_alt", "").strip()
        obj.is_active = data.get("is_active") == "on"
        obj.sort_order = int(data.get("sort_order") or 0)
        if request.FILES.get("image"):
            obj.image = request.FILES["image"]
        elif data.get("clear_image") == "on" and obj.image:
            obj.image.delete(save=False)
            obj.image = None
        obj.save()
        messages.success(request, "Content block saved.")
        return redirect("portal:content_blocks")
    return render(request, "portal/content/block_edit.html", {
        "content_block": content_block,
        "page_choices": ContentBlock.PAGE_CHOICES,
    })


@portal_required
@require_POST
def content_block_delete(request, pk):
    block = get_object_or_404(ContentBlock, pk=pk)
    block.delete()
    messages.success(request, "Content block deleted.")
    return redirect("portal:content_blocks")


# ── Blog ──────────────────────────────────────────────────────────────────────

@portal_required
def content_blog(request):
    posts = BlogPost.objects.select_related("author").all()
    status = request.GET.get("status", "")
    q = request.GET.get("q", "")
    if status:
        posts = posts.filter(status=status)
    if q:
        posts = posts.filter(Q(title__icontains=q) | Q(excerpt__icontains=q) | Q(tags__icontains=q))
    return render(request, "portal/content/blog.html", {
        "posts": posts,
        "current_status": status,
        "search_query": q,
        "status_choices": BlogPost.STATUS_CHOICES,
    })


@portal_required
def content_blog_edit(request, pk=None):
    post = get_object_or_404(BlogPost, pk=pk) if pk else None
    if request.method == "POST":
        obj = _apply_blog_form_data(post or BlogPost(), request)
        obj.save()
        messages.success(request, "Blog post saved.")
        return redirect(URL_CONTENT_BLOG)
    return render(request, "portal/content/blog_edit.html", {
        "post": post,
        "entry_type_choices": BlogPost.ENTRY_TYPE_CHOICES,
        "status_choices": BlogPost.STATUS_CHOICES,
    })


@portal_required
@require_POST
def content_blog_status(request, pk, action):
    post = get_object_or_404(BlogPost, pk=pk)
    if action == "publish":
        post.status = "published"
        post.published_at = timezone.now()
        post.save(update_fields=["status", "published_at", "is_published", "updated_at"])
        messages.success(request, "Post published.")
    elif action == "unpublish":
        post.status = "unpublished"
        post.save(update_fields=["status", "is_published", "updated_at"])
        messages.success(request, "Post unpublished.")
    return redirect(URL_CONTENT_BLOG)


# ── Brewing Guides ────────────────────────────────────────────────────────────

@portal_required
def content_guides(request):
    guides = BrewingGuide.objects.all()
    q = request.GET.get("q", "")
    if q:
        guides = guides.filter(Q(title__icontains=q) | Q(method__icontains=q) | Q(tags__icontains=q))
    return render(request, "portal/content/guides.html", {"guides": guides, "search_query": q})


@portal_required
def content_guide_edit(request, pk=None):
    guide = get_object_or_404(BrewingGuide, pk=pk) if pk else None
    if request.method == "POST":
        data = request.POST
        obj = guide or BrewingGuide()
        obj.title = data.get("title", "")
        obj.product_handle = data.get("product_handle", "").strip()
        obj.guide_type = data.get("guide_type", "other")
        obj.audience_level = data.get("audience_level", "beginner")
        obj.tags = data.get("tags", "")
        obj.is_premium_featured = data.get("is_premium_featured") == "on"
        obj.method = data.get("method", "")
        obj.description = data.get("description", "")
        obj.instructions = data.get("instructions", "")
        obj.water_temp = data.get("water_temp", "")
        obj.brew_time = data.get("brew_time", "")
        obj.grind_size = data.get("grind_size", "")
        obj.ratio = data.get("ratio", "")
        obj.is_published = data.get("is_published") == "on"
        if request.FILES.get("image"):
            obj.image = request.FILES["image"]
        obj.save()
        messages.success(request, "Guide saved.")
        return redirect("portal:content_guides")
    return render(request, "portal/content/guide_edit.html", {"guide": guide})


# ── Tasting Notes ─────────────────────────────────────────────────────────────

@portal_required
def content_tasting_notes(request):
    notes = TastingNote.objects.all()
    q = request.GET.get("q", "")
    if q:
        notes = notes.filter(Q(title__icontains=q) | Q(tags__icontains=q) | Q(product_name__icontains=q))
    return render(request, "portal/content/tasting_notes.html", {"notes": notes, "search_query": q})


@portal_required
def content_tasting_note_edit(request, pk=None):
    note = get_object_or_404(TastingNote, pk=pk) if pk else None
    if request.method == "POST":
        data = request.POST
        obj = note or TastingNote()
        obj.product_name = data.get("product_name", "")
        obj.product_handle = data.get("product_handle", "").strip()
        obj.title = data.get("title", "")
        obj.body = data.get("body", "")
        obj.aroma = data.get("aroma", "")
        obj.flavor = data.get("flavor", "")
        obj.finish = data.get("finish", "")
        obj.origin = data.get("origin", "")
        obj.pairings = data.get("pairings", "")
        obj.style_notes = data.get("style_notes", "")
        obj.tags = data.get("tags", "")
        obj.rating = data.get("rating") or 5
        obj.save()
        messages.success(request, "Tasting note saved.")
        return redirect("portal:content_tasting_notes")
    return render(request, "portal/content/tasting_note_edit.html", {"note": note})


# ── Journal Posts ────────────────────────────────────────────────────────────

@portal_required
def content_journal_posts(request):
    posts = BlogPost.objects.all()
    q = request.GET.get("q", "")
    if q:
        posts = posts.filter(Q(title__icontains=q) | Q(tags__icontains=q))
    return render(request, "portal/content/blog.html", {
        "posts": posts,
        "current_status": "",
        "search_query": q,
        "status_choices": BlogPost.STATUS_CHOICES,
    })


# ── Wholesale Inquiries ───────────────────────────────────────────────────────

@portal_required
def content_wholesale_inquiries(request):
    qs = WholesaleInquiry.objects.all()
    q = request.GET.get("q", "")
    from_date = request.GET.get("from_date", "")
    to_date = request.GET.get("to_date", "")
    if q:
        qs = qs.filter(Q(company_name__icontains=q) | Q(name__icontains=q) | Q(email__icontains=q) | Q(location__icontains=q))
    if from_date:
        qs = qs.filter(created_at__date__gte=from_date)
    if to_date:
        qs = qs.filter(created_at__date__lte=to_date)

    if request.GET.get("export") == "csv":
        return _export_inquiry_csv(qs, ["Company", "Contact", "Email", "Phone", "Location", "Volume", "Date"],
                                   lambda i: [i.company_name, i.name, i.email, i.phone, i.location, i.monthly_volume, i.created_at.date()])

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "portal/content/wholesale_inquiries.html", {
        "page_obj": page, "search_query": q, "from_date": from_date, "to_date": to_date,
    })


@portal_required
def content_wholesale_inquiry_detail(request, pk):
    inquiry = get_object_or_404(WholesaleInquiry.objects.select_related("assigned_to", "reviewed_by"), pk=pk)
    assign_form = InquiryAssignForm(prefix="assign", initial={"assigned_to": inquiry.assigned_to})
    note_form = InquiryNoteForm(prefix="note")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "mark_reviewed":
            inquiry.reviewed_by = request.user
            inquiry.reviewed_at = timezone.now()
            inquiry.save(update_fields=["reviewed_by", "reviewed_at"])
            messages.success(request, "Inquiry marked as reviewed.")
            return redirect(URL_WHOLESALE_DETAIL, pk=pk)
        if action == "assign":
            assign_form = InquiryAssignForm(request.POST, prefix="assign")
            if assign_form.is_valid():
                inquiry.assigned_to = assign_form.cleaned_data["assigned_to"]
                inquiry.save(update_fields=["assigned_to"])
                messages.success(request, "Owner assignment updated.")
                return redirect(URL_WHOLESALE_DETAIL, pk=pk)
        if action == "add_note":
            note_form = InquiryNoteForm(request.POST, prefix="note")
            if note_form.is_valid():
                WholesaleInquiryNote.objects.create(inquiry=inquiry, author=request.user, body=note_form.cleaned_data["note"])
                messages.success(request, "Internal note added.")
                return redirect(URL_WHOLESALE_DETAIL, pk=pk)

    notes = inquiry.internal_notes.select_related("author").all()
    return render(request, "portal/content/wholesale_inquiry_detail.html", {
        "inquiry": inquiry, "assign_form": assign_form, "note_form": note_form, "notes": notes,
    })


# ── Ambassador Inquiries ──────────────────────────────────────────────────────

@portal_required
def content_ambassador_inquiries(request):
    qs = AmbassadorInquiry.objects.all()
    q = request.GET.get("q", "")
    platform = request.GET.get("platform", "")
    from_date = request.GET.get("from_date", "")
    to_date = request.GET.get("to_date", "")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(social_handle__icontains=q) | Q(city__icontains=q))
    if platform:
        qs = qs.filter(primary_platform__icontains=platform)
    if from_date:
        qs = qs.filter(created_at__date__gte=from_date)
    if to_date:
        qs = qs.filter(created_at__date__lte=to_date)

    if request.GET.get("export") == "csv":
        return _export_inquiry_csv(qs, ["Name", "Email", "Handle", "Platform", "Audience", "City", "Date"],
                                   lambda i: [i.name, i.email, i.social_handle, i.primary_platform, i.audience_size, i.city, i.created_at.date()])

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "portal/content/ambassador_inquiries.html", {
        "page_obj": page, "search_query": q, "platform_query": platform, "from_date": from_date, "to_date": to_date,
    })


@portal_required
def content_ambassador_inquiry_detail(request, pk):
    inquiry = get_object_or_404(AmbassadorInquiry.objects.select_related("assigned_to", "reviewed_by"), pk=pk)
    assign_form = InquiryAssignForm(prefix="assign", initial={"assigned_to": inquiry.assigned_to})
    note_form = InquiryNoteForm(prefix="note")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "mark_reviewed":
            inquiry.reviewed_by = request.user
            inquiry.reviewed_at = timezone.now()
            inquiry.save(update_fields=["reviewed_by", "reviewed_at"])
            messages.success(request, "Inquiry marked as reviewed.")
            return redirect(URL_AMBASSADOR_DETAIL, pk=pk)
        if action == "assign":
            assign_form = InquiryAssignForm(request.POST, prefix="assign")
            if assign_form.is_valid():
                inquiry.assigned_to = assign_form.cleaned_data["assigned_to"]
                inquiry.save(update_fields=["assigned_to"])
                messages.success(request, "Owner assignment updated.")
                return redirect(URL_AMBASSADOR_DETAIL, pk=pk)
        if action == "add_note":
            note_form = InquiryNoteForm(request.POST, prefix="note")
            if note_form.is_valid():
                AmbassadorInquiryNote.objects.create(inquiry=inquiry, author=request.user, body=note_form.cleaned_data["note"])
                messages.success(request, "Internal note added.")
                return redirect(URL_AMBASSADOR_DETAIL, pk=pk)

    notes = inquiry.internal_notes.select_related("author").all()
    return render(request, "portal/content/ambassador_inquiry_detail.html", {
        "inquiry": inquiry, "assign_form": assign_form, "note_form": note_form, "notes": notes,
    })


# ── Fundraising ───────────────────────────────────────────────────────────────

@portal_required
def fundraising_manage(request):
    campaigns = FundraisingCampaign.objects.all()
    stats = {
        "active": campaigns.filter(status="active").count(),
        "draft": campaigns.filter(status="draft").count(),
        "total_goal": campaigns.aggregate(s=Sum("goal_amount"))["s"] or 0,
        "total_raised": campaigns.aggregate(s=Sum("raised_amount"))["s"] or 0,
    }
    return render(request, "portal/fundraising/list.html", {"campaigns": campaigns, "stats": stats, "placeholders": []})


@portal_required
def fundraising_edit(request, pk=None):
    campaign = get_object_or_404(FundraisingCampaign, pk=pk) if pk else None
    if request.method == "POST":
        data = request.POST
        obj = campaign or FundraisingCampaign()
        obj.title = data.get("title", "")
        obj.description = data.get("description", "")
        obj.story = data.get("story", "")
        obj.goal_amount = data.get("goal_amount", 0)
        obj.raised_amount = data.get("raised_amount", 0) or 0
        obj.beneficiary = data.get("beneficiary", "")
        obj.status = data.get("status", "draft")
        obj.start_date = data.get("start_date") or None
        obj.end_date = data.get("end_date") or None
        if request.FILES.get("image"):
            obj.image = request.FILES["image"]
        obj.save()
        messages.success(request, "Campaign saved.")
        return redirect("portal:fundraising_manage")
    return render(request, "portal/fundraising/edit.html", {"campaign": campaign})


@portal_required
def fundraising_donations(request, pk):
    campaign = get_object_or_404(FundraisingCampaign, pk=pk)
    donations = campaign.donations.all()
    return render(request, "portal/fundraising/donations.html", {"campaign": campaign, "donations": donations})


# ── Email Subscribers ─────────────────────────────────────────────────────────

@portal_required
def subscriber_list(request):
    subs = EmailSubscriber.objects.all()
    q = request.GET.get("q", "")
    if q:
        subs = subs.filter(Q(email__icontains=q) | Q(source__icontains=q))
    paginator = Paginator(subs, 50)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "portal/marketing/subscribers.html", {"page_obj": page, "search_query": q})


# ── Email Inbox ───────────────────────────────────────────────────────────────

@portal_required
def email_inbox(request):
    try:
        emails = fetch_inbox(limit=50)
        error = None
    except IMAPError as e:
        emails = []
        error = str(e)
    return render(request, "portal/email/inbox.html", {"emails": emails, "error": error})


@portal_required
@require_POST
def email_mark_important(request, uid):
    flagged = request.POST.get("flagged") == "1"
    try:
        toggle_important(uid, flagged)
        label = "marked as important" if flagged else "unmarked"
        messages.success(request, f"Message {label}.")
    except IMAPError as e:
        messages.error(request, f"Could not update flag: {e}")
    return redirect("portal:email_detail", uid=uid)


@portal_required
@require_POST
def email_mark_unread(request, uid):
    try:
        mark_unread(uid)
        messages.success(request, "Message marked as unread.")
    except IMAPError as e:
        messages.error(request, f"Could not mark as unread: {e}")
    return redirect("portal:email_inbox")


@portal_required
@require_POST
def email_delete(request, uid):
    try:
        delete_message(uid)
        messages.success(request, "Message deleted.")
    except IMAPError as e:
        messages.error(request, f"Could not delete message: {e}")
    return redirect("portal:email_inbox")


@portal_required
def email_compose(request, draft_pk=None):
    draft = get_object_or_404(EmailDraft, pk=draft_pk, created_by=request.user) if draft_pk else None

    if request.method == "POST":
        data = _parse_compose_form(request.POST)
        if request.POST.get("action") == "send" and data["to"]:
            return _send_compose(request, data, draft)
        return _save_draft(request, data, draft)

    return render(request, "portal/email/compose.html", {"draft": draft})


def _parse_compose_form(post):
    return {
        "to": post.get("to", "").strip(),
        "cc": post.get("cc", "").strip(),
        "subject": post.get("subject", "").strip(),
        "body": post.get("body", ""),
    }


def _send_compose(request, data, draft):
    from django.core.mail import EmailMessage as DjangoEmail
    DjangoEmail(
        subject=data["subject"],
        body=data["body"],
        from_email=None,
        to=[t.strip() for t in data["to"].split(",") if t.strip()],
        cc=[c.strip() for c in data["cc"].split(",") if c.strip()] if data["cc"] else [],
    ).send()
    if draft:
        draft.delete()
    messages.success(request, f"Email sent to {data['to']}.")
    return redirect("portal:email_inbox")


def _save_draft(request, data, draft):
    if draft:
        for field, value in data.items():
            setattr(draft, field, value)
        draft.save()
    else:
        draft = EmailDraft.objects.create(**data, created_by=request.user)
    messages.success(request, "Draft saved.")
    return redirect("portal:email_draft_edit", pk=draft.pk)


@portal_required
def email_draft_list(request):
    drafts = EmailDraft.objects.filter(created_by=request.user)
    return render(request, "portal/email/drafts.html", {"drafts": drafts})


@portal_required
@require_POST
def email_draft_delete(request, pk):
    draft = get_object_or_404(EmailDraft, pk=pk, created_by=request.user)
    draft.delete()
    messages.success(request, "Draft deleted.")
    return redirect("portal:email_draft_list")


@portal_required
def email_detail(request, uid):
    try:
        message = fetch_message(uid)
        error = None
    except IMAPError as e:
        message = None
        error = str(e)
    return render(request, "portal/email/detail.html", {"message": message, "error": error})


# ── Staff ─────────────────────────────────────────────────────────────────────

@manager_required
def staff_list(request):
    staff = User.objects.filter(is_staff=True).order_by("first_name", "last_name", "username")
    return render(request, "portal/staff/list.html", {"staff_members": staff})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _apply_blog_form_data(obj, request):
    data = request.POST
    obj.title = data.get("title", "")
    obj.entry_type = data.get("entry_type", "slow_living")
    obj.tags = data.get("tags", "")
    obj.excerpt = data.get("excerpt", "")
    obj.body = data.get("body", "")
    obj.status = data.get("status", "draft")
    obj.author = request.user
    published_at = _parse_portal_datetime(data.get("published_at", ""))
    if published_at is not None:
        obj.published_at = published_at
    elif obj.status in ["draft", "unpublished"]:
        obj.published_at = None
    if obj.status == "published" and not obj.published_at:
        obj.published_at = timezone.now()
    if request.FILES.get("image"):
        obj.image = request.FILES["image"]
    return obj


def _parse_portal_datetime(raw_value):
    value = (raw_value or "").strip()
    if not value:
        return None
    parsed = parse_datetime(value)
    if parsed is None:
        return None
    return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed


def _resolve_block_live_url(block):
    policy_map = {
        "shipping": "storefront:policy_shipping",
        "refunds": "storefront:policy_refunds",
        "privacy": "storefront:policy_privacy",
        "terms": "storefront:policy_terms",
    }
    try:
        if block.page_key == "home":
            return reverse("storefront:home")
        if block.page_key == "about":
            return reverse("storefront:about")
        if block.page_key == "contact":
            return reverse("storefront:contact")
        if block.page_key == "policies":
            return reverse(policy_map.get(block.section_key, "storefront:policy_shipping"))
        if block.page_key == "brewing_guides":
            return reverse("storefront:brewing_guides")
        if block.page_key == "ritual":
            return reverse("storefront:ritual")
        if block.page_key == "shop":
            return reverse("storefront:shop")
    except NoReverseMatch:
        pass
    return ""


def _export_inquiry_csv(qs, headers, row_fn):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="inquiries.csv"'
    writer = csv.writer(response)
    writer.writerow(headers)
    for item in qs:
        writer.writerow(row_fn(item))
    return response
