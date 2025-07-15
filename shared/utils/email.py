import smtplib
from dataclasses import dataclass
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional, Union

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import EmailStr

from shared.core.config import settings
from shared.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class EmailConfig:
    """Email configuration class using dataclass to reduce boilerplate."""

    # SMTP connection details
    smtp_server: str
    smtp_port: int

    # Authentication
    smtp_username: str
    smtp_password: str

    # Email content settings
    from_email: str
    template_dir: str

    # Connection security (combined into a single attribute)
    connection_security: str = "tls"  # Options: "tls", "ssl", "none"

    @property
    def use_tls(self) -> bool:
        """Determine if TLS should be used."""
        return self.connection_security == "tls"

    @property
    def use_ssl(self) -> bool:
        """Determine if SSL should be used."""
        return self.connection_security == "ssl"

    # def __post_init__(self):
    #     """Convert password string to SecretStr if needed."""
    #     if self.smtp_password and not isinstance(self.smtp_password, SecretStr):
    #         self.smtp_password = SecretStr(self.smtp_password)


# Email Utility
class EmailSender:
    def __init__(self, config: EmailConfig):
        self.config = config
        self.env = Environment(
            loader=FileSystemLoader(self.config.template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def _render_template(self, template_file: str, context: Dict[str, Any]) -> str:
        try:
            template = self.env.get_template(template_file)
            return template.render(**context)
        except Exception as e:
            logger.error("Template rendering failed: %s", e)
            return ""

    def _connect_smtp(self) -> Optional[Union[smtplib.SMTP, smtplib.SMTP_SSL]]:
        try:
            if self.config.use_ssl:
                server: Union[smtplib.SMTP, smtplib.SMTP_SSL] = smtplib.SMTP_SSL(
                    self.config.smtp_server, self.config.smtp_port
                )
            else:
                server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
                if self.config.use_tls:
                    server.starttls()
            server.login(
                self.config.smtp_username,
                self.config.smtp_password,
            )
            return server
        except Exception as e:
            logger.error("SMTP connection/login failed: %s", e)
            return None

    def send_email(
        self,
        to: EmailStr,
        subject: str,
        template_file: str,
        context: Dict[str, Any],
    ) -> bool:
        """Send a rendered HTML email to a recipient."""
        server = self._connect_smtp()
        if not server:
            return False

        html = self._render_template(template_file, context)
        if not html:
            return False

        msg = MIMEMultipart()
        msg["From"] = self.config.from_email
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(html, "html"))

        try:
            server.sendmail(self.config.from_email, to, msg.as_string())
            logger.info("Email sent to %s", to)
            return True
        except Exception as e:
            logger.error("Failed to send email: %s", e)
            return False
        finally:
            try:
                server.quit()
            except Exception as e:
                logger.warning("Failed to close SMTP connection: %s", e)


# Configuration from settings
email_config = EmailConfig(
    smtp_server=settings.SMTP_HOST,
    smtp_port=settings.SMTP_PORT,
    smtp_username=settings.SMTP_USER,
    smtp_password=settings.SMTP_PASSWORD,
    from_email=settings.EMAIL_FROM,
    template_dir=settings.EMAIL_TEMPLATES_DIR,
    connection_security="tls",  # Use TLS by default (port 587), use "ssl" for port 465
)

email_sender = EmailSender(email_config)


def send_welcome_email(email: EmailStr, username: str, password: str, logo_url: str) -> None:
    """Send a welcome email to a new user."""
    context = {
        "username": username,
        "email": email,
        "welcome_url": f"{settings.FRONTEND_URL}",
        "password": password,
        "logo_url": logo_url,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject="Welcome to Events2Go!",
        template_file="welcome_email.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send welcome email to %s", email)


def send_user_welcome_email(email: EmailStr, username: str, verification_token: str) -> bool:
    """
    Send a welcome email to a new user with email verification link.

    Args:
        email: User's email address
        username: User's username
        verification_token: Email verification token

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    verification_link = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"

    context = {
        "username": username,
        "email": email,
        "verification_link": verification_link,
        "welcome_url": f"{settings.FRONTEND_URL}",
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject="Welcome to Events2Go - Verify Your Email",
        template_file="welcome_verification.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send welcome email to %s", email)

    return success


def send_password_reset_email(
    email: EmailStr,
    username: str,
    reset_link: str,
    ip_address: Optional[str] = None,
    request_time: Optional[str] = None,
    expiry_hours: int = 24,
) -> bool:
    """Send a password reset email to a user."""
    context = {
        "username": username,
        "email": email,
        "reset_link": reset_link,
        "ip_address": ip_address,
        "request_time": request_time
        or datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "expiry_hours": expiry_hours,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject="Reset Your Events2Go Password",
        template_file="password_reset.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send password reset email to %s", email)

    return success


def send_security_alert_email(
    email: EmailStr,
    username: str,
    alert_type: str,
    activity_time: str,
    ip_address: Optional[str] = None,
    location: Optional[str] = None,
    device_info: Optional[str] = None,
    secure_account_url: Optional[str] = None,
    review_activity_url: Optional[str] = None,
) -> bool:
    """Send a security alert email to a user."""
    context = {
        "username": username,
        "alert_type": alert_type,
        "activity_time": activity_time,
        "ip_address": ip_address,
        "location": location,
        "device_info": device_info,
        "secure_account_url": secure_account_url or f"{settings.FRONTEND_URL}/security",
        "review_activity_url": review_activity_url or f"{settings.FRONTEND_URL}/activity",
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject=f"Security Alert - {alert_type} - Events2Go",
        template_file="security_alert.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send security alert email to %s", email)

    return success


def send_user_verification_email(
    email: EmailStr, username: str, verification_token: str, user_id: str
) -> bool:
    """
    Send a welcome email to a new user with email verification link.

    Args:
        email: User's email address
        username: User's username
        verification_token: Email verification token
        user_id: User's unique identifier

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    verification_link = (
        f"{settings.FRONTEND_URL}/VerifyEmail?email={email}&token={verification_token}"
    )

    context = {
        "username": username,
        "email": email,
        "verification_link": verification_link,
        "welcome_url": f"{settings.FRONTEND_URL}",
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject="Welcome to Events2Go - Verify Your Email",
        template_file="user/email_verification.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send welcome email to %s", email)

    return success
