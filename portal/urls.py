from django.urls import path
from . import views

app_name = "portal"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    # Content hub
    path("content/", views.content_hub, name="content_hub"),
    path("content/pages/", views.content_pages, name="content_pages"),
    path("content/pages/new/", views.content_page_edit, name="content_page_new"),
    path("content/pages/<int:pk>/edit/", views.content_page_edit, name="content_page_edit"),
    path("content/blocks/", views.content_blocks, name="content_blocks"),
    path("content/blocks/new/", views.content_block_edit, name="content_block_new"),
    path("content/blocks/<int:pk>/edit/", views.content_block_edit, name="content_block_edit"),
    path("content/blocks/<int:pk>/delete/", views.content_block_delete, name="content_block_delete"),
    path("content/blog/", views.content_blog, name="content_blog"),
    path("content/blog/new/", views.content_blog_edit, name="content_blog_new"),
    path("content/blog/<int:pk>/edit/", views.content_blog_edit, name="content_blog_edit"),
    path("content/blog/<int:pk>/status/<str:action>/", views.content_blog_status, name="content_blog_status"),
    path("content/guides/", views.content_guides, name="content_guides"),
    path("content/guides/new/", views.content_guide_edit, name="content_guide_new"),
    path("content/guides/<int:pk>/edit/", views.content_guide_edit, name="content_guide_edit"),
    path("content/tasting-notes/", views.content_tasting_notes, name="content_tasting_notes"),
    path("content/tasting-notes/new/", views.content_tasting_note_edit, name="content_tasting_note_new"),
    path("content/tasting-notes/<int:pk>/edit/", views.content_tasting_note_edit, name="content_tasting_note_edit"),
    path("content/journal/", views.content_journal_posts, name="content_journal_posts"),
    path("content/inquiries/wholesale/", views.content_wholesale_inquiries, name="content_wholesale_inquiries"),
    path("content/inquiries/wholesale/<int:pk>/", views.content_wholesale_inquiry_detail, name="content_wholesale_inquiry_detail"),
    path("content/inquiries/ambassadors/", views.content_ambassador_inquiries, name="content_ambassador_inquiries"),
    path("content/inquiries/ambassadors/<int:pk>/", views.content_ambassador_inquiry_detail, name="content_ambassador_inquiry_detail"),
    # Fundraising
    path("fundraising/", views.fundraising_manage, name="fundraising_manage"),
    path("fundraising/new/", views.fundraising_edit, name="fundraising_new"),
    path("fundraising/<int:pk>/edit/", views.fundraising_edit, name="fundraising_edit"),
    path("fundraising/<int:pk>/donations/", views.fundraising_donations, name="fundraising_donations"),
    # Subscribers
    path("subscribers/", views.subscriber_list, name="subscriber_list"),
    # Staff
    path("staff/", views.staff_list, name="staff_list"),
    # Email inbox
    path("email/", views.email_inbox, name="email_inbox"),
    path("email/sent/", views.email_sent, name="email_sent"),
    path("email/sent/<str:uid>/", views.email_sent_detail, name="email_sent_detail"),
    path("email/compose/", views.email_compose, name="email_compose"),
    path("email/drafts/", views.email_draft_list, name="email_draft_list"),
    path("email/drafts/<int:draft_pk>/edit/", views.email_compose, name="email_draft_edit"),
    path("email/drafts/<int:pk>/delete/", views.email_draft_delete, name="email_draft_delete"),
    path("email/<str:uid>/delete/", views.email_delete, name="email_delete"),
    path("email/<str:uid>/mark-unread/", views.email_mark_unread, name="email_mark_unread"),
    path("email/<str:uid>/mark-important/", views.email_mark_important, name="email_mark_important"),
    path("email/<str:uid>/", views.email_detail, name="email_detail"),
]
