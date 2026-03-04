#!/usr/bin/env python3
"""
email_client skill - Email IMAP/SMTP operations.
Supports: read emails, search, send, extract links from messages.
"""
import json
import re
import email
from email.header import decode_header
from datetime import datetime, timezone


def get_info():
    return {
        "name": "email_client",
        "version": "v1",
        "description": "Email client using IMAP/SMTP. Read, search, send emails, extract links.",
        "capabilities": ["email", "imap", "smtp", "messaging"],
        "actions": ["connect", "list_folders", "search", "read", "send", "extract_links", "get_unread"]
    }


def health_check():
    try:
        import imaplib
        import smtplib
        return True
    except ImportError:
        return False


class EmailClientSkill:
    """Email client for IMAP/SMTP operations."""

    def __init__(self):
        self.imap_conn = None
        self.smtp_conn = None
        self.connected = False

    def connect(self, server, username, password, port=None, use_ssl=True, protocol="imap"):
        """Connect to email server."""
        try:
            import imaplib
            import smtplib
            import ssl

            if protocol.lower() == "imap":
                if port is None:
                    port = 993 if use_ssl else 143

                if use_ssl:
                    self.imap_conn = imaplib.IMAP4_SSL(server, port)
                else:
                    self.imap_conn = imaplib.IMAP4(server, port)

                self.imap_conn.login(username, password)
                self.connected = True

                return {
                    "success": True,
                    "protocol": "IMAP",
                    "server": server,
                    "username": username,
                    "folders": self._list_folders()
                }

            elif protocol.lower() == "smtp":
                if port is None:
                    port = 587

                self.smtp_conn = smtplib.SMTP(server, port)
                self.smtp_conn.starttls()
                self.smtp_conn.login(username, password)

                return {
                    "success": True,
                    "protocol": "SMTP",
                    "server": server,
                    "username": username
                }

            else:
                return {"success": False, "error": f"Unknown protocol: {protocol}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _list_folders(self):
        """List IMAP folders."""
        try:
            if not self.imap_conn:
                return []
            status, folders = self.imap_conn.list()
            if status == "OK":
                return [f.decode().split(' "/" ')[-1].strip('"') for f in folders]
            return []
        except:
            return []

    def list_folders(self):
        """List email folders."""
        try:
            folders = self._list_folders()
            return {
                "success": True,
                "folders": folders,
                "count": len(folders)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search(self, folder="INBOX", criteria="ALL", limit=10):
        """Search emails in folder."""
        try:
            if not self.imap_conn:
                return {"success": False, "error": "Not connected to IMAP"}

            self.imap_conn.select(folder)
            status, messages = self.imap_conn.search(None, criteria)

            if status != "OK":
                return {"success": False, "error": "Search failed"}

            msg_ids = messages[0].split()
            results = []

            for msg_id in msg_ids[-limit:]:  # Get last N messages
                status, msg_data = self.imap_conn.fetch(msg_id, "(RFC822.HEADER)")
                if status == "OK":
                    raw_header = msg_data[0][1]
                    header = email.message_from_bytes(raw_header)

                    results.append({
                        "id": msg_id.decode(),
                        "subject": self._decode_header(header.get("Subject", "")),
                        "from": self._decode_header(header.get("From", "")),
                        "date": header.get("Date", ""),
                        "size": len(raw_header)
                    })

            return {
                "success": True,
                "folder": folder,
                "criteria": criteria,
                "count": len(results),
                "messages": results
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_unread(self, folder="INBOX", limit=10):
        """Get unread messages."""
        return self.search(folder, "UNSEEN", limit)

    def read(self, msg_id, folder="INBOX"):
        """Read full email message."""
        try:
            if not self.imap_conn:
                return {"success": False, "error": "Not connected to IMAP"}

            self.imap_conn.select(folder)
            status, msg_data = self.imap_conn.fetch(msg_id, "(RFC822)")

            if status != "OK":
                return {"success": False, "error": f"Could not fetch message {msg_id}"}

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Extract body
            body = ""
            html_body = ""

            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))

                    if "attachment" not in content_disposition:
                        if content_type == "text/plain":
                            body = self._get_text(part)
                        elif content_type == "text/html":
                            html_body = self._get_text(part)
            else:
                body = self._get_text(msg)
                if msg.get_content_type() == "text/html":
                    html_body = body
                    body = ""

            return {
                "success": True,
                "id": msg_id,
                "subject": self._decode_header(msg.get("Subject", "")),
                "from": self._decode_header(msg.get("From", "")),
                "to": self._decode_header(msg.get("To", "")),
                "date": msg.get("Date", ""),
                "body": body,
                "html_body": html_body,
                "headers": dict(msg.items())
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def extract_links(self, text):
        """Extract all URLs from text."""
        try:
            # URL regex pattern
            url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?'
            urls = re.findall(url_pattern, text)

            # Remove duplicates while preserving order
            seen = set()
            unique_urls = []
            for url in urls:
                if url not in seen:
                    seen.add(url)
                    unique_urls.append(url)

            return {
                "success": True,
                "urls": unique_urls,
                "count": len(unique_urls)
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def send(self, to, subject, body, from_addr=None):
        """Send email via SMTP."""
        try:
            if not self.smtp_conn:
                return {"success": False, "error": "Not connected to SMTP"}

            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart()
            msg["From"] = from_addr or self.username
            msg["To"] = to
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "plain"))

            self.smtp_conn.sendmail(
                from_addr or self.username,
                [to],
                msg.as_string()
            )

            return {
                "success": True,
                "to": to,
                "subject": subject
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _decode_header(self, header):
        """Decode email header."""
        try:
            decoded_parts = decode_header(header)
            result = ""
            for part, charset in decoded_parts:
                if isinstance(part, bytes):
                    result += part.decode(charset or "utf-8", errors="replace")
                else:
                    result += part
            return result
        except:
            return header

    def _get_text(self, part):
        """Extract text from email part."""
        try:
            payload = part.get_payload(decode=True)
            charset = part.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
        except:
            return ""

    def disconnect(self):
        """Disconnect from servers."""
        try:
            if self.imap_conn:
                self.imap_conn.close()
                self.imap_conn.logout()
            if self.smtp_conn:
                self.smtp_conn.quit()
            return {"success": True, "message": "Disconnected"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        action = input_data.get("action", "connect")

        if action == "connect":
            return self.connect(
                input_data.get("server", ""),
                input_data.get("username", ""),
                input_data.get("password", ""),
                input_data.get("port"),
                input_data.get("use_ssl", True),
                input_data.get("protocol", "imap")
            )
        elif action == "list_folders":
            return self.list_folders()
        elif action == "search":
            return self.search(
                input_data.get("folder", "INBOX"),
                input_data.get("criteria", "ALL"),
                input_data.get("limit", 10)
            )
        elif action == "get_unread":
            return self.get_unread(
                input_data.get("folder", "INBOX"),
                input_data.get("limit", 10)
            )
        elif action == "read":
            return self.read(
                input_data.get("msg_id", ""),
                input_data.get("folder", "INBOX")
            )
        elif action == "extract_links":
            return self.extract_links(input_data.get("text", ""))
        elif action == "send":
            return self.send(
                input_data.get("to", ""),
                input_data.get("subject", ""),
                input_data.get("body", ""),
                input_data.get("from")
            )
        elif action == "disconnect":
            return self.disconnect()
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


def execute(input_data: dict) -> dict:
    return EmailClientSkill().execute(input_data)


if __name__ == "__main__":
    skill = EmailClientSkill()
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    print(f"Health: {health_check()}")

    # Test link extraction
    test_text = """
    Welcome! Click here to verify: https://example.com/verify?token=abc123
    Or visit our site: http://openrouter.ai/keys
    """
    print("\nExtract links:")
    print(json.dumps(skill.extract_links(test_text), indent=2))
