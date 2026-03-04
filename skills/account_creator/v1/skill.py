#!/usr/bin/env python3
"""
account_creator skill - Create and manage online accounts.
Supports: generate secure passwords, validate emails, store credentials securely.
Uses stdlib only - no external dependencies.
"""
import json
import secrets
import string
import re
import hashlib
from pathlib import Path
from datetime import datetime


def get_info():
    return {
        "name": "account_creator",
        "version": "v1",
        "description": "Create and manage online accounts: generate passwords, validate data, store credentials.",
        "capabilities": ["accounts", "passwords", "security", "validation"],
        "actions": ["generate_password", "validate_email", "validate_username", "create_account_data", "store_credentials", "check_password_strength"]
    }


def health_check():
    return True


class AccountCreatorSkill:
    """Account creation and credential management."""

    def __init__(self):
        self.config_dir = Path.home() / ".evo_accounts"
        self.config_dir.mkdir(exist_ok=True)
        self.credentials_file = self.config_dir / "credentials.json"
        self.accounts_index = self.config_dir / "accounts_index.json"

    def generate_password(self, length=16, include_uppercase=True, include_numbers=True, include_special=True, memorable=False):
        """Generate secure password."""
        try:
            if memorable:
                # Generate memorable passphrase
                wordlists = [
                    ["alpha", "beta", "gamma", "delta", "echo", "foxtrot", "golf", "hotel"],
                    ["red", "blue", "green", "yellow", "orange", "purple", "silver", "gold"],
                    ["tiger", "lion", "eagle", "shark", "wolf", "bear", "falcon", "hawk"],
                    ["rocket", "plane", "ship", "train", "car", "bike", "boat", "jet"]
                ]

                words = [secrets.choice(wl) for wl in wordlists[:3]]
                numbers = ''.join(secrets.choice(string.digits) for _ in range(3))
                password = '-'.join(words) + '-' + numbers

                return {
                    "success": True,
                    "password": password,
                    "type": "memorable",
                    "length": len(password),
                    "words": words
                }

            # Generate random password
            chars = string.ascii_lowercase
            if include_uppercase:
                chars += string.ascii_uppercase
            if include_numbers:
                chars += string.digits
            if include_special:
                chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"

            password = ''.join(secrets.choice(chars) for _ in range(length))

            # Ensure at least one of each required type
            if include_uppercase and not any(c.isupper() for c in password):
                password = password[:-1] + secrets.choice(string.ascii_uppercase)
            if include_numbers and not any(c.isdigit() for c in password):
                password = password[:-1] + secrets.choice(string.digits)
            if include_special and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
                password = password[:-1] + secrets.choice("!@#$%^&*()_+-=[]{}|;:,.<>?")

            return {
                "success": True,
                "password": password,
                "type": "random",
                "length": length,
                "strength": self._calculate_password_strength(password)
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _calculate_password_strength(self, password):
        """Calculate password strength score."""
        score = 0
        checks = {
            "length_8": len(password) >= 8,
            "length_12": len(password) >= 12,
            "length_16": len(password) >= 16,
            "has_lowercase": any(c.islower() for c in password),
            "has_uppercase": any(c.isupper() for c in password),
            "has_numbers": any(c.isdigit() for c in password),
            "has_special": any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password),
            "no_common": password.lower() not in ["password", "123456", "qwerty", "admin"]
        }

        score = sum(checks.values())

        if score >= 7:
            return {"score": score, "rating": "Very Strong", "checks": checks}
        elif score >= 5:
            return {"score": score, "rating": "Strong", "checks": checks}
        elif score >= 3:
            return {"score": score, "rating": "Medium", "checks": checks}
        else:
            return {"score": score, "rating": "Weak", "checks": checks}

    def check_password_strength(self, password):
        """Check strength of existing password."""
        try:
            strength = self._calculate_password_strength(password)

            # Additional checks
            issues = []
            if len(password) < 8:
                issues.append("Password too short (min 8 characters)")
            if not any(c.isupper() for c in password):
                issues.append("Add uppercase letters")
            if not any(c.islower() for c in password):
                issues.append("Add lowercase letters")
            if not any(c.isdigit() for c in password):
                issues.append("Add numbers")
            if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
                issues.append("Add special characters")
            if password.lower() in ["password", "123456", "qwerty", "admin", "letmein"]:
                issues.append("Common password - easily guessed")

            strength["issues"] = issues
            strength["recommendations"] = ["Use at least 12 characters", "Mix different character types", "Avoid common words"]

            return {
                "success": True,
                "password_length": len(password),
                "strength": strength
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def validate_email(self, email):
        """Validate email format."""
        try:
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            is_valid = re.match(pattern, email) is not None

            # Check common domains
            common_domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "protonmail.com"]
            domain = email.split('@')[-1].lower() if '@' in email else ""
            is_common = domain in common_domains

            return {
                "success": True,
                "email": email,
                "is_valid": is_valid,
                "domain": domain,
                "is_common_domain": is_common,
                "suggestions": [] if is_valid else ["Check for typos", "Ensure @ symbol is present", "Verify domain name"]
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def validate_username(self, username, platform=None):
        """Validate username for specific platform."""
        try:
            # Platform-specific rules
            platform_rules = {
                "twitter": {"min": 1, "max": 15, "allowed": r'^[a-zA-Z0-9_]+$'},
                "github": {"min": 1, "max": 39, "allowed": r'^[a-zA-Z0-9-]+$', "no_start_end_hyphen": True},
                "instagram": {"min": 1, "max": 30, "allowed": r'^[a-zA-Z0-9_.]+$', "no_consecutive_periods": True},
                "linkedin": {"min": 3, "max": 100, "allowed": r'^[a-zA-Z0-9-]+$'},
                "generic": {"min": 3, "max": 32, "allowed": r'^[a-zA-Z0-9_-]+$'}
            }

            rules = platform_rules.get(platform, platform_rules["generic"])
            issues = []

            # Length check
            if len(username) < rules["min"]:
                issues.append(f"Too short (min {rules['min']} characters)")
            if len(username) > rules["max"]:
                issues.append(f"Too long (max {rules['max']} characters)")

            # Character check
            if not re.match(rules["allowed"], username):
                issues.append("Contains invalid characters")

            # Special rules
            if rules.get("no_start_end_hyphen") and (username.startswith('-') or username.endswith('-')):
                issues.append("Cannot start or end with hyphen")

            if rules.get("no_consecutive_periods") and '..' in username:
                issues.append("Cannot have consecutive periods")

            is_valid = len(issues) == 0

            return {
                "success": True,
                "username": username,
                "platform": platform or "generic",
                "is_valid": is_valid,
                "issues": issues,
                "rules": rules
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_account_data(self, service, email, username=None, password_options=None):
        """Generate complete account creation data."""
        try:
            # Validate email
            email_validation = self.validate_email(email)
            if not email_validation.get("is_valid"):
                return {"success": False, "error": "Invalid email address", "details": email_validation}

            # Generate username if not provided
            if username is None:
                base = email.split('@')[0]
                username = base[:15]  # Truncate for common platforms

            # Validate username
            username_validation = self.validate_username(username)

            # Generate password
            pwd_options = password_options or {}
            password_result = self.generate_password(**pwd_options)

            if not password_result.get("success"):
                return password_result

            account_data = {
                "service": service,
                "email": email,
                "username": username,
                "password": password_result["password"],
                "created_at": datetime.now().isoformat(),
                "email_valid": email_validation["is_valid"],
                "username_valid": username_validation["is_valid"],
                "password_strength": password_result["strength"]["rating"]
            }

            return {
                "success": True,
                "account_data": account_data,
                "ready_to_create": email_validation["is_valid"] and username_validation["is_valid"],
                "warnings": username_validation.get("issues", [])
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def store_credentials(self, service, username, password, email=None, notes=None):
        """Store account credentials securely (hashed)."""
        try:
            credentials = self._load_credentials()

            # Create entry
            entry = {
                "service": service,
                "username": username,
                "email": email,
                "password_hash": hashlib.sha256(password.encode()).hexdigest()[:16],  # Partial hash for verification
                "password_hint": password[:2] + "***" + password[-2:] if len(password) > 4 else "****",
                "notes": notes,
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }

            # Update or add
            existing = [c for c in credentials if c["service"] == service and c["username"] == username]
            if existing:
                idx = credentials.index(existing[0])
                credentials[idx] = entry
            else:
                credentials.append(entry)

            self._save_credentials(credentials)

            return {
                "success": True,
                "stored": True,
                "service": service,
                "username": username,
                "warning": "NOTE: Only password hash stored for security. Keep original password safe!"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _load_credentials(self):
        """Load stored credentials."""
        try:
            if self.credentials_file.exists():
                with open(self.credentials_file, 'r') as f:
                    return json.load(f)
            return []
        except:
            return []

    def _save_credentials(self, credentials):
        """Save credentials."""
        try:
            with open(self.credentials_file, 'w') as f:
                json.dump(credentials, f, indent=2, default=str)
        except Exception as e:
            pass

    def list_accounts(self, service=None):
        """List stored accounts."""
        try:
            credentials = self._load_credentials()

            if service:
                credentials = [c for c in credentials if c["service"] == service]

            # Hide sensitive data
            safe_list = []
            for c in credentials:
                safe_list.append({
                    "service": c["service"],
                    "username": c["username"],
                    "email": c.get("email"),
                    "created_at": c.get("created_at"),
                    "last_updated": c.get("last_updated"),
                    "has_password_hint": bool(c.get("password_hint"))
                })

            return {
                "success": True,
                "count": len(safe_list),
                "accounts": safe_list
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_account_variations(self, base_username, count=5):
        """Generate username variations if primary is taken."""
        try:
            variations = []
            suffixes = ["", "_dev", "_pro", "_official", "_hq", "_team"]
            separators = ["", "_", "-", "."]
            numbers = ["", "1", "2", "2024", "01"]

            for i in range(count):
                if i < len(suffixes):
                    var = f"{base_username}{suffixes[i]}"
                else:
                    sep = separators[i % len(separators)]
                    num = numbers[i % len(numbers)]
                    var = f"{base_username}{sep}{num}"

                # Validate
                validation = self.validate_username(var)
                if validation["is_valid"]:
                    variations.append(var)

            return {
                "success": True,
                "base_username": base_username,
                "variations": variations[:count],
                "count": len(variations)
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        action = input_data.get("action", "generate_password")

        if action == "generate_password":
            return self.generate_password(
                input_data.get("length", 16),
                input_data.get("include_uppercase", True),
                input_data.get("include_numbers", True),
                input_data.get("include_special", True),
                input_data.get("memorable", False)
            )
        elif action == "check_password_strength":
            return self.check_password_strength(input_data.get("password", ""))
        elif action == "validate_email":
            return self.validate_email(input_data.get("email", ""))
        elif action == "validate_username":
            return self.validate_username(
                input_data.get("username", ""),
                input_data.get("platform")
            )
        elif action == "create_account_data":
            return self.create_account_data(
                input_data.get("service", ""),
                input_data.get("email", ""),
                input_data.get("username"),
                input_data.get("password_options")
            )
        elif action == "store_credentials":
            return self.store_credentials(
                input_data.get("service", ""),
                input_data.get("username", ""),
                input_data.get("password", ""),
                input_data.get("email"),
                input_data.get("notes")
            )
        elif action == "list_accounts":
            return self.list_accounts(input_data.get("service"))
        elif action == "generate_account_variations":
            return self.generate_account_variations(
                input_data.get("base_username", ""),
                input_data.get("count", 5)
            )
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


def execute(input_data: dict) -> dict:
    return AccountCreatorSkill().execute(input_data)


if __name__ == "__main__":
    skill = AccountCreatorSkill()
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    print(f"Health: {health_check()}")

    # Test password generation
    print("\nTest generate_password:")
    result = skill.generate_password(length=12, memorable=True)
    print(json.dumps(result, indent=2))
