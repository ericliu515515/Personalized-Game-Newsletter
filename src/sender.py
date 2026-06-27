import os
import smtplib
from email.message import EmailMessage
from html import escape

from dotenv import load_dotenv

from load_settings import USERNAME
from models import ValidatedNewsItem

load_dotenv()

CONSOLE_BADGE_COLORS = {
    "XBOX": "#107c10",
    "Playstations": "#006fcd",
    "Switch and Switch 2": "#e60012",
    "PC": "#111827",
    "SteamDeck and SteamMachine": "#6b7280",
    "not console-specific": "#eab308",
}


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} was not found. Add it to .env first.")
    return value


def send_email(subject: str = "", body: str = "", html_body: str | None = None) -> None:
    smtp_host = required_env("SMTP_HOST")
    smtp_port = int(required_env("SMTP_PORT"))
    smtp_user = required_env("SMTP_USER")
    smtp_password = required_env("SMTP_PASSWORD")
    email_to = required_env("EMAIL_TO")
    email_from = os.getenv("EMAIL_FROM", smtp_user)

    message = EmailMessage()
    message["From"] = email_from
    message["To"] = email_to
    message["Subject"] = subject
    message.set_content(body)

    if html_body:
        message.add_alternative(html_body, subtype="html")

    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as smtp:
            smtp.login(smtp_user, smtp_password)
            smtp.send_message(message)
        return

    with smtplib.SMTP(smtp_host, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(message)


def news_item_to_text(item: ValidatedNewsItem, index: int) -> str:
    console_text = ", ".join(item.consoles)

    return f"""{index}. {item.title}
Source: {item.source_name}
Tag: {item.tag}
Consoles: {console_text}
Summary: {item.summary}
URL: {item.source_url}"""


def console_badge_to_html(console: str) -> str:
    console_text = escape(console)
    background_color = CONSOLE_BADGE_COLORS.get(console, "#6b7280")
    text_color = "#111827" if console == "not console-specific" else "#ffffff"

    return (
        '<span style="display:inline-block; margin:0 8px 8px 0; '
        f"padding:5px 10px; border-radius:4px; background:{background_color}; "
        f"color:{text_color}; font-size:12px; line-height:1.2; font-weight:700; "
        f'text-transform:uppercase;">{console_text}</span>'
    )


def console_badges_to_html(consoles: list[str]) -> str:
    return "".join(console_badge_to_html(console) for console in consoles)


def news_item_to_html(item: ValidatedNewsItem, index: int) -> str:
    title = escape(item.title)
    source_name = escape(item.source_name)
    source_url = escape(item.source_url, quote=True)
    tag = escape(item.tag)
    summary = escape(item.summary)
    console_badges = console_badges_to_html(item.consoles)

    return f"""\
          <div style="margin-bottom:28px;">
            <div style="font-size:13px; line-height:1.4; color:#2563eb; font-weight:700; text-transform:uppercase;">{tag}</div>
            <h2 style="margin:8px 0 10px; font-size:22px; line-height:1.3;">
              <a href="{source_url}" style="color:#111827; text-decoration:none;">{title}</a>
            </h2>
            <div style="margin:0 0 10px; font-size:14px; line-height:1.5; color:#6b7280;">
              {source_name}
            </div>
            <div style="margin:0 0 8px;">
              {console_badges}
            </div>
            <p style="margin:0 0 14px; font-size:16px; line-height:1.6; color:#4b5563;">
              {summary}
            </p>
            <a href="{source_url}" style="color:#2563eb; font-size:15px; font-weight:700; text-decoration:none;">Read article</a>
          </div>"""


def news_count_message(news_item_count: int) -> str:
    if news_item_count == 0:
        return "Sorry, PVN could not find any validated news items today."

    if news_item_count == 1:
        return "Here is today's 1 news."

    return f"Here are today's {news_item_count} news."


def build_news_email(news_items: list[ValidatedNewsItem]) -> tuple[str, str]:
    count_message = news_count_message(len(news_items))
    username = USERNAME
    escaped_username = escape(username)

    text_items = "\n\n".join(
        news_item_to_text(item=item, index=index)
        for index, item in enumerate(news_items, start=1)
    )
    html_items = "\n".join(
        news_item_to_html(item=item, index=index)
        for index, item in enumerate(news_items, start=1)
    )

    text_body = f"""Gaming News Digest

Hi {username},

{count_message}

{text_items}
"""

    html_body = f"""\
<!doctype html>
<html>
  <body style="margin:0; padding:0; background:#f3f4f6; font-family:Arial, Helvetica, sans-serif; color:#24292f;">
    <div style="padding:40px 16px;">
      <div style="max-width:720px; margin:0 auto; text-align:center; padding:16px 0 32px;">
        <div style="font-size:36px; line-height:1.2; font-weight:800; color:#2563eb;">Gaming News Digest</div>
      </div>

      <div style="max-width:720px; margin:0 auto; background:#ffffff; padding:44px 48px; border-radius:8px;">
        <p style="margin:0 0 22px; font-size:20px; line-height:1.5; font-weight:700;">Hi {escaped_username},</p>
        <p style="margin:0 0 28px; font-size:18px; line-height:1.6;">
          {count_message}
        </p>

        <div style="border-top:1px solid #e5e7eb; padding-top:28px;">
{html_items}
        </div>

      </div>
    </div>
  </body>
</html>
"""
    return text_body, html_body


def send_news_email(
    news_items: list[ValidatedNewsItem],
    subject: str | None = None,
) -> None:
    email_subject = subject or os.getenv("EMAIL_SUBJECT", "PVN daily news digest")
    text_body, html_body = build_news_email(news_items)
    send_email(subject=email_subject, body=text_body, html_body=html_body)
