"""
Hospital Information System - Email Notification Helpers
=======================================================

Author: Athul Gopan
Created: 2025
Module: Email Sending and Notification Management

This module provides email utility functions for sending various types of
notifications to hospital staff and patients. All email tasks are implemented
as Celery shared tasks for asynchronous processing.

Email Functions Available:
    - send_doctor_credentials_email(): Sends login credentials to newly created doctor accounts

Features:
    - Asynchronous email sending using Celery
    - Automatic retry on failure (up to 3 attempts with 60-second delay)
    - Configurable email templates
    - Error handling and logging

Configuration Required:
    - EMAIL_BACKEND in settings.py
    - DEFAULT_FROM_EMAIL in settings.py
    - SMTP/Email service credentials
"""

from django.core.mail import send_mail
from django.conf import settings
from celery import shared_task
import logging

# Set up logging for email operations
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_doctor_credentials_email(self, email, first_name, last_name, username, password):
    """
    Send login credentials email to newly created doctor accounts.

    This is a Celery shared task that sends an email containing login credentials
    to doctors when their account is created by an administrator. The task will
    automatically retry up to 3 times (with 60-second intervals) if sending fails.

    Args:
        self: Celery task instance (automatically bound)
        email (str): Recipient's email address
        first_name (str): Doctor's first name
        last_name (str): Doctor's last name
        username (str): Login username for the portal
        password (str): Initial password for the account

    Returns:
        None

    Raises:
        Exception: Re-raises exceptions after max retry attempts are exhausted

    Example:
        # Asynchronous call (recommended for production)
        send_doctor_credentials_email.delay(
            email='doctor@example.com',
            first_name='John',
            last_name='Doe',
            username='jdoe',
            password='TempPass123'
        )

        # Synchronous call (for development/testing)
        send_doctor_credentials_email(
            email='doctor@example.com',
            first_name='John',
            last_name='Doe',
            username='jdoe',
            password='TempPass123'
        )

    Note:
        - This function is currently used for all staff types (doctors, nurses, etc.)
        - TODO: Create specific email templates for different staff roles
    """
    try:
        # Log email sending attempt
        logger.info(f"Attempting to send credentials email to {email}")

        # ====================================================================
        # Email Configuration
        # ====================================================================
        subject = 'Your Doctor Portal Account Credentials'

        # Construct email message body
        message = f"""
        Dear Dr. {first_name or ''} {last_name or ''},

        Your account has been successfully created on our Doctor Portal.

        Here are your login credentials:
        Username: {username}
        Password: {password}

        Please keep this information secure and consider changing your password after first login.

        Best regards,
        Hospital Administration Team
        """

        # ====================================================================
        # Send Email
        # ====================================================================
        send_mail(
            subject=subject,
            message=message.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,  # Raise exception on failure
        )

        # Log successful email delivery
        logger.info(f"Successfully sent credentials email to {email}")

    except Exception as e:
        # Log the error with details
        logger.error(f"Failed to send credentials email to {email}: {str(e)}")

        # Retry the task after 60 seconds
        # This will retry up to max_retries (3) times
        raise self.retry(exc=e, countdown=60)


