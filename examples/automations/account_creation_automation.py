#!/usr/bin/env python3
"""
Pipeline 3: Account Creation Automation

Automatyzuje tworzenie kont internetowych:
1. Generuje bezpieczne hasło
2. Waliduje email i username
3. Tworzy pełne dane konta
4. Zapisuje credentials (hashowane)

Użycie:
  python3 examples/automations/account_creation_automation.py github user@example.com
"""
import sys
import json
import subprocess
from datetime import datetime


def run_skill(skill_name, action, params):
    """Execute a skill via subprocess."""
    input_data = {"action": action, **params}
    cmd = [
        sys.executable, "-c",
        f"""
import sys
sys.path.insert(0, 'skills/{skill_name}/v1')
from skill import execute
result = execute({json.dumps(input_data)})
print(json.dumps(result))
"""
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd='/home/tom/github/wronai/coreskill')
        return json.loads(result.stdout.strip().split('\n')[-1])
    except Exception as e:
        return {"success": False, "error": str(e)}


def account_creation_automation(service, email, platform=None):
    """Complete account creation workflow."""
    print(f"🔐 Starting account creation for: {service}")
    print("=" * 60)

    # Step 1: Validate email
    print("\n📧 Step 1: Validating email...")
    email_result = run_skill("account_creator", "validate_email", {
        "email": email
    })
    
    if email_result.get("is_valid"):
        print(f"   ✅ Email valid: {email}")
        print(f"   Domain: {email_result.get('domain', 'N/A')}")
    else:
        print(f"   ❌ Invalid email: {email}")
        return {"success": False, "error": "Invalid email"}

    # Step 2: Generate secure password
    print("\n🔑 Step 2: Generating secure password...")
    password_result = run_skill("account_creator", "generate_password", {
        "length": 16,
        "include_uppercase": True,
        "include_numbers": True,
        "include_special": True,
        "memorable": False
    })
    
    if password_result.get("success"):
        password = password_result.get("password", "")
        strength = password_result.get("strength", {})
        print(f"   Password generated (length: {len(password)})")
        print(f"   Strength: {strength.get('rating', 'N/A')}")
        print(f"   Score: {strength.get('score', 0)}/8")
    else:
        print(f"   Error: {password_result.get('error')}")
        return password_result

    # Step 3: Validate username for platform
    suggested_username = email.split('@')[0]
    print(f"\n👤 Step 3: Validating username '{suggested_username}'...")
    username_result = run_skill("account_creator", "validate_username", {
        "username": suggested_username,
        "platform": platform or service
    })
    
    if username_result.get("is_valid"):
        print(f"   ✅ Username valid: {suggested_username}")
    else:
        print(f"   ⚠️ Username issues: {', '.join(username_result.get('issues', []))}")
        
        # Generate variations
        print("\n   Generating alternatives...")
        variations_result = run_skill("account_creator", "generate_account_variations", {
            "base_username": suggested_username,
            "count": 5
        })
        
        if variations_result.get("success"):
            variations = variations_result.get("variations', [])
            print(f"   Suggestions: {', '.join(variations[:3])}")

    # Step 4: Create complete account data
    print("\n📋 Step 4: Creating account data package...")
    account_result = run_skill("account_creator", "create_account_data", {
        "service": service,
        "email": email,
        "username": suggested_username,
        "password_options": {
            "length": 16,
            "memorable": False
        }
    })
    
    if account_result.get("success"):
        account_data = account_result.get("account_data', {})
        print(f"   Service: {account_data.get('service')}")
        print(f"   Email: {account_data.get('email')}")
        print(f"   Username: {account_data.get('username')}")
        print(f"   Password strength: {account_data.get('password_strength')}")
        print(f"   Ready to create: {account_result.get('ready_to_create', False)}")

    # Step 5: Store credentials (hashed)
    print("\n💾 Step 5: Storing credentials...")
    store_result = run_skill("account_creator", "store_credentials", {
        "service": service,
        "username": suggested_username,
        "password": password,
        "email": email,
        "notes": f"Created on {datetime.now().isoformat()}"
    })
    
    if store_result.get("success"):
        print(f"   ✅ Credentials stored (hashed)")
        print(f"   Service: {store_result.get('service')}")
        print(f"   Username: {store_result.get('username')}")
        print(f"   ⚠️ {store_result.get('warning', '')}")

    # Final summary
    print("\n" + "=" * 60)
    print("✅ Account creation automation completed!")
    print(f"   Service: {service}")
    print(f"   Email: {email}")
    print(f"   Username: {suggested_username}")
    print(f"   Password: {'*' * len(password)} (length: {len(password)})")
    print(f"   Ready to register: {account_result.get('ready_to_create', False)}")
    
    print("\n⚠️ IMPORTANT: Save the password securely before proceeding!")
    print(f"   Generated password: {password}")

    return {
        "success": True,
        "service": service,
        "email": email,
        "username": suggested_username,
        "password": password,
        "password_length": len(password),
        "ready_to_create": account_result.get('ready_to_create', False)
    }


if __name__ == "__main__":
    service = sys.argv[1] if len(sys.argv) > 1 else "github"
    email = sys.argv[2] if len(sys.argv) > 2 else "user@example.com"
    platform = sys.argv[3] if len(sys.argv) > 3 else None
    
    result = account_creation_automation(service, email, platform)
    
    if result.get("success"):
        print(f"\n📝 Save this information:")
        print(f"   Service: {result['service']}")
        print(f"   Username: {result['username']}")
        print(f"   Password: {result['password']}")
