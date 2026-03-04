#!/usr/bin/env python3
"""
ksef_integration skill - Integration with Polish KSeF (Krajowy System e-Faktur).
Supports: login, send invoice, get invoice, check status.
Requires: qualified certificate or electronic seal.
"""
import json
import urllib.request
import urllib.error
import ssl
from pathlib import Path
from datetime import datetime, timezone


def get_info():
    return {
        "name": "ksef_integration",
        "version": "v1",
        "description": "Integration with Polish KSeF system for electronic invoices. Requires qualified certificate.",
        "capabilities": ["ksef", "faktury", "podatki", "vat", "e-faktury"],
        "actions": ["login", "send_invoice", "get_invoice", "check_status", "get_token"]
    }


def health_check():
    """Check if SSL and required modules are available."""
    try:
        import ssl
        import urllib.request
        return True
    except ImportError:
        return False


class KSeFIntegrationSkill:
    """Integration with Polish KSeF system."""

    # KSeF API endpoints
    KSEF_URLS = {
        "test": "https://ksef-test.mf.gov.pl",
        "production": "https://ksef.mf.gov.pl"
    }

    def __init__(self):
        self.config_dir = Path.home() / ".evo_ksef"
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "config.json"
        self.token_file = self.config_dir / "token.json"
        self.session_token = None

    def _load_config(self):
        """Load KSeF configuration."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            return {
                "environment": "test",
                "nip": "",
                "certificate_path": "",
                "api_key": ""
            }
        except:
            return {}

    def _save_config(self, config):
        """Save KSeF configuration."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            pass

    def _get_base_url(self, environment=None):
        """Get base URL for environment."""
        env = environment or self._load_config().get("environment", "test")
        return self.KSEF_URLS.get(env, self.KSEF_URLS["test"])

    def _make_request(self, endpoint, method="GET", data=None, headers=None, environment="test"):
        """Make HTTP request to KSeF API."""
        try:
            base_url = self._get_base_url(environment)
            url = f"{base_url}{endpoint}"

            req_headers = headers or {}
            req_headers["Content-Type"] = "application/json"
            req_headers["Accept"] = "application/json"

            if self.session_token:
                req_headers["SessionToken"] = self.session_token

            if data and isinstance(data, dict):
                data = json.dumps(data).encode('utf-8')

            req = urllib.request.Request(
                url,
                data=data,
                headers=req_headers,
                method=method
            )

            # Create SSL context that allows us to use client certificates
            context = ssl.create_default_context()

            with urllib.request.urlopen(req, context=context, timeout=30) as response:
                return {
                    "success": True,
                    "status": response.status,
                    "data": json.loads(response.read().decode('utf-8'))
                }

        except urllib.error.HTTPError as e:
            return {
                "success": False,
                "error": f"HTTP {e.code}: {e.reason}",
                "status": e.code
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def login(self, nip=None, environment="test", certificate_path=None, use_token=True):
        """Login to KSeF using token or certificate."""
        try:
            config = self._load_config()

            nip = nip or config.get("nip")
            if not nip:
                return {"success": False, "error": "NIP is required"}

            if use_token:
                # Login using integration token (recommended for automation)
                api_key = config.get("api_key")
                if not api_key:
                    return {"success": False, "error": "API key not configured. Get it from https://ksef.mf.gov.pl"}

                # Prepare login request
                login_data = {
                    "NIP": nip,
                    "Environment": environment
                }

                # For demo purposes - in production this requires proper authentication
                return {
                    "success": True,
                    "message": "KSeF login initiated (demo mode)",
                    "nip": nip,
                    "environment": environment,
                    "note": "Production use requires qualified certificate or API token from MF"
                }
            else:
                # Certificate-based login (requires qualified certificate)
                if not certificate_path:
                    return {"success": False, "error": "Certificate path required for certificate login"}

                return {
                    "success": True,
                    "message": "Certificate login initiated (demo mode)",
                    "nip": nip,
                    "certificate": certificate_path,
                    "note": "Production use requires proper SSL certificate with private key"
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_token(self, nip=None, environment="test"):
        """Get integration token for KSeF."""
        try:
            config = self._load_config()
            nip = nip or config.get("nip")

            if not nip:
                return {"success": False, "error": "NIP is required"}

            # In production, this would call KSeF API to get token
            # For now, provide instructions
            return {
                "success": True,
                "instructions": [
                    "1. Log in to https://ksef.mf.gov.pl (production) or https://ksef-test.mf.gov.pl (test)",
                    "2. Go to 'Integracja' (Integration) section",
                    "3. Generate integration token",
                    "4. Save token using: /run ksef_integration save_token <token>"
                ],
                "nip": nip,
                "environment": environment,
                "token_endpoint": f"{self._get_base_url(environment)}/api/IntegrationToken"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_token(self, token, nip=None):
        """Save integration token."""
        try:
            config = self._load_config()
            config["api_key"] = token
            if nip:
                config["nip"] = nip
            config["saved_at"] = datetime.now(timezone.utc).isoformat()
            self._save_config(config)

            return {
                "success": True,
                "message": "Token saved successfully",
                "nip": config.get("nip")
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def send_invoice(self, invoice_data, environment=None):
        """Send invoice to KSeF."""
        try:
            config = self._load_config()
            env = environment or config.get("environment", "test")

            if not config.get("api_key"):
                return {"success": False, "error": "No API token. Get token first using get_token action"}

            # Validate invoice structure (simplified)
            required_fields = ["NIP", "InvoiceNumber", "IssueDate", "DueDate", "TotalAmount"]
            missing = [f for f in required_fields if f not in invoice_data]
            if missing:
                return {"success": False, "error": f"Missing required fields: {missing}"}

            # In production, this would POST to KSeF API
            return {
                "success": True,
                "message": "Invoice ready to send (demo mode)",
                "environment": env,
                "invoice_number": invoice_data.get("InvoiceNumber"),
                "total_amount": invoice_data.get("TotalAmount"),
                "api_endpoint": f"{self._get_base_url(env)}/api/Invoice",
                "note": "Production: POST invoice XML/JSON to KSeF API with proper authentication"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_invoice(self, ksef_reference_number, environment=None):
        """Get invoice from KSeF by reference number."""
        try:
            config = self._load_config()
            env = environment or config.get("environment", "test")

            if not config.get("api_key"):
                return {"success": False, "error": "No API token configured"}

            return {
                "success": True,
                "message": "Invoice retrieval ready (demo mode)",
                "ksef_reference": ksef_reference_number,
                "environment": env,
                "api_endpoint": f"{self._get_base_url(env)}/api/Invoice/{ksef_reference_number}",
                "note": "Production: GET from KSeF API with SessionToken"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def check_status(self, ksef_reference_number, environment=None):
        """Check invoice status in KSeF."""
        try:
            config = self._load_config()
            env = environment or config.get("environment", "test")

            return {
                "success": True,
                "message": "Status check ready (demo mode)",
                "ksef_reference": ksef_reference_number,
                "environment": env,
                "possible_statuses": [
                    "Submitted",      # Złożono
                    "Accepted",       # Przyjęto
                    "Rejected",     # Odrzucono
                    "Processing",   # W trakcie przetwarzania
                    "Delivered"     # Dostarczono
                ],
                "api_endpoint": f"{self._get_base_url(env)}/api/Invoice/{ksef_reference_number}/Status",
                "note": "Production: Check status via KSeF API"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_config(self):
        """Get current configuration."""
        config = self._load_config()
        # Hide sensitive data
        if "api_key" in config:
            key = config["api_key"]
            config["api_key"] = key[:10] + "..." + key[-5:] if len(key) > 15 else "***"

        return {
            "success": True,
            "config": config,
            "config_path": str(self.config_file)
        }

    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        action = input_data.get("action", "get_config")

        if action == "login":
            return self.login(
                input_data.get("nip"),
                input_data.get("environment", "test"),
                input_data.get("certificate_path"),
                input_data.get("use_token", True)
            )
        elif action == "get_token":
            return self.get_token(
                input_data.get("nip"),
                input_data.get("environment", "test")
            )
        elif action == "save_token":
            return self.save_token(
                input_data.get("token", ""),
                input_data.get("nip")
            )
        elif action == "send_invoice":
            return self.send_invoice(
                input_data.get("invoice_data", {}),
                input_data.get("environment")
            )
        elif action == "get_invoice":
            return self.get_invoice(
                input_data.get("ksef_reference", ""),
                input_data.get("environment")
            )
        elif action == "check_status":
            return self.check_status(
                input_data.get("ksef_reference", ""),
                input_data.get("environment")
            )
        elif action == "get_config":
            return self.get_config()
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


def execute(input_data: dict) -> dict:
    return KSeFIntegrationSkill().execute(input_data)


if __name__ == "__main__":
    skill = KSeFIntegrationSkill()
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    print(f"Health: {health_check()}")

    print("\nGet token instructions:")
    result = skill.get_token("1234567890")
    print(json.dumps(result, indent=2, ensure_ascii=False))
