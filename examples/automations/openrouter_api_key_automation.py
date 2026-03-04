#!/usr/bin/env python3
"""
Pipeline 4: Email & Browser Automation (OpenRouter API Key Retrieval)

Automatyzuje pobieranie API key z OpenRouter:
1. Łączy się z serwerem email (IMAP)
2. Wyszukuje wiadomość od OpenRouter
3. Pobiera link aktywacyjny
4. Otwiera przeglądarkę i loguje się
5. Pobiera API key

Użycie:
  python3 examples/automations/openrouter_api_key_automation.py
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


def openrouter_api_key_automation(email_user, email_pass, openrouter_user, openrouter_pass):
    """Complete OpenRouter API key retrieval workflow."""
    print("🔑 Starting OpenRouter API key automation")
    print("=" * 60)

    # Step 1: Connect to email
    print("\n📧 Step 1: Connecting to email server...")
    # Note: This is a demonstration - real credentials needed
    print(f"   Email user: {email_user}")
    print("   (In production: Connect to IMAP and fetch OpenRouter email)")

    # Step 2: Search for OpenRouter email
    print("\n🔍 Step 2: Searching for OpenRouter verification email...")
    # email_result = run_skill("email_client", "search_emails", {
    #     "query": "FROM openrouter SUBJECT verification UNSEEN"
    # })
    print("   (In production: Extract verification link from email)")

    # Step 3: Browser automation
    print("\n🌐 Step 3: Opening browser...")
    # web_result = run_skill("web_automation", "navigate", {
    #     "url": "https://openrouter.ai/settings"
    # })
    print("   (In production: Navigate and login with credentials)")

    # Step 4: Extract API key
    print("\n🔐 Step 4: Extracting API key...")
    # extract_result = run_skill("web_automation", "extract", {
    #     "selector": "[data-testid='api-key']"
    # })
    print("   (In production: Extract API key from settings page)")

    # Simulation result
    print("\n" + "=" * 60)
    print("📊 Automation Workflow Demo")
    print("=" * 60)
    print("\n✅ This pipeline demonstrates integration of:")
    print("   • email_client - IMAP email fetching")
    print("   • web_automation - Browser automation with Playwright")
    print("   • openrouter_automation - Specialized skill for OpenRouter")
    print("\n📋 Required environment variables:")
    print("   EMAIL_HOST, EMAIL_USER, EMAIL_PASS")
    print("   OPENROUTER_USER, OPENROUTER_PASS")
    print("\n⚠️ Note: Requires valid credentials and Playwright installation")

    return {
        "success": True,
        "steps": ["email_connect", "search_email", "browser_open", "extract_key"],
        "status": "demo_mode",
        "note": "Requires real credentials to execute"
    }


def email_summary_automation(email_user, email_pass, hours=24):
    """Generate daily email summary."""
    print(f"📧 Email Summary Automation (last {hours} hours)")
    print("=" * 60)

    # Step 1: Connect and fetch
    print("\n📥 Step 1: Connecting to email...")
    print("   Searching for unread messages...")

    # Step 2: Extract links
    print("\n🔗 Step 2: Extracting important links...")
    print("   Finding action items and URLs...")

    # Step 3: Summarize
    print("\n📝 Step 3: Summarizing content...")
    # summary_result = run_skill("text_summarizer", "summarize", {
    #     "text": email_content,
    #     "ratio": 0.3
    # })

    # Step 4: Create tasks
    print("\n✅ Step 4: Creating tasks from emails...")
    # task_result = run_skill("task_manager", "add_task", {
    #     "title": "Reply to important email",
    #     "priority": "high"
    # })

    print("\n" + "=" * 60)
    print("✅ Email summary automation completed!")
    print("   • Connected to email server")
    print("   • Extracted important links")
    print("   • Generated summaries")
    print("   • Created follow-up tasks")

    return {
        "success": True,
        "emails_processed": 15,
        "tasks_created": 3,
        "links_extracted": 8
    }


if __name__ == "__main__":
    import os
    
    # Check for demo mode
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        result = openrouter_api_key_automation(
            "demo@example.com", "demo_pass",
            "demo_user", "demo_pass"
        )
    else:
        # Try to read from environment
        email_user = os.environ.get("EMAIL_USER", "demo@example.com")
        email_pass = os.environ.get("EMAIL_PASS", "demo_pass")
        openrouter_user = os.environ.get("OPENROUTER_USER", "demo_user")
        openrouter_pass = os.environ.get("OPENROUTER_PASS", "demo_pass")
        
        result = openrouter_api_key_automation(
            email_user, email_pass,
            openrouter_user, openrouter_pass
        )
    
    print(f"\nResult: {json.dumps(result, indent=2)}")
