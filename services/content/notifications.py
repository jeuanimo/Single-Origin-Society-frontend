from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string


def send_inquiry_notification(subject, message, recipient_email=None):
    """
    Send an inquiry notification email.
    
    Args:
        subject: Email subject line
        message: Plain text email body
        recipient_email: Email address to send to (defaults to DEFAULT_FROM_EMAIL)
    """
    if not recipient_email:
        recipient_email = getattr(settings, "DEFAULT_FROM_EMAIL", "") or "noreply@singleoriginsociety.com"
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient_email],
        fail_silently=False,
    )


def send_order_confirmation(order):
    """Send order confirmation email to customer."""
    subject = f"Order Confirmation #{order.order_number}"
    message = f"""
    Thank you for your order!
    
    Order Number: {order.order_number}
    Total: ${order.total}
    
    We'll send you tracking information as soon as your order ships.
    
    Best regards,
    Single Origin Society
    """
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.user.email],
        fail_silently=False,
    )


def send_password_reset(user, reset_link):
    """Send password reset email."""
    subject = "Reset Your Single Origin Society Password"
    message = f"""
    Hi {user.get_full_name() or user.email},
    
    Click the link below to reset your password:
    {reset_link}
    
    This link expires in 24 hours.
    
    If you didn't request this, you can safely ignore this email.
    
    Best regards,
    Single Origin Society Team
    """
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_welcome_email(user):
    """Send welcome email to new customer."""
    subject = "Welcome to Single Origin Society"
    message = f"""
    Welcome {user.get_full_name() or user.email}!
    
    We're excited to have you join our community of coffee enthusiasts.
    
    Explore our collections, read brewing guides, and discover single-origin beans sourced directly from farmers.
    
    Happy brewing!
    
    Best regards,
    Single Origin Society Team
    """
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_support_ticket_confirmation(ticket):
    """Send support ticket confirmation to customer."""
    subject = f"Support Ticket #{ticket.ticket_number} Received"
    message = f"""
    Thank you for contacting Single Origin Society support.
    
    Ticket Number: {ticket.ticket_number}
    Category: {ticket.get_category_display()}
    Subject: {ticket.subject}
    
    We've received your message and will respond as soon as possible.
    
    Best regards,
    Single Origin Society Support Team
    """
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[ticket.email],
        fail_silently=False,
    )


def send_wholesale_inquiry_confirmation(inquiry):
    """Send confirmation to wholesale inquirer."""
    subject = "Wholesale Inquiry Received"
    message = f"""
    Thank you for your wholesale inquiry.
    
    Business Name: {inquiry.business_name}
    Contact: {inquiry.contact_email}
    
    Our wholesale team will review your inquiry and reach out within 2-3 business days.
    
    Best regards,
    Single Origin Society Team
    """
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[inquiry.contact_email],
        fail_silently=False,
    )


def send_ambassador_inquiry_confirmation(inquiry):
    """Send confirmation to ambassador program applicant."""
    subject = "Ambassador Program Application Received"
    message = f"""
    Thank you for applying to the Single Origin Society Ambassador Program.
    
    Name: {inquiry.name}
    Email: {inquiry.email}
    
    We review applications regularly and will follow up within 5-7 business days.
    
    Best regards,
    Single Origin Society Team
    """
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[inquiry.email],
        fail_silently=False,
    )
