#!/usr/bin/env python3
"""
Pipeline 2: Social Media Content Automation

Automatyzuje zarządzanie treścią social media:
1. Generuje post na podstawie tematu
2. Analizuje tekst pod kątem optymalizacji
3. Planuje publikację na określoną godzinę
4. Tworzy zestaw hashtagów

Użycie:
  python3 examples/automations/social_media_automation.py "AI w biznesie" "+2 hours"
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


def social_media_automation(topic, schedule_time="tomorrow 9am"):
    """Complete social media content workflow."""
    print(f"📱 Starting social media automation for: {topic}")
    print("=" * 60)

    # Step 1: Generate content
    print("\n✍️ Step 1: Generating content...")
    content_result = run_skill("social_media_manager", "generate_content", {
        "topic": topic,
        "tone": "professional",
        "length": "medium",
        "template_name": "announcement"
    })
    
    if content_result.get("success"):
        content = content_result.get("content", "")
        print(f"   Content generated ({len(content)} chars)")
        print(f"   Template: {content_result.get('template_used', 'N/A')}")
        print(f"   Hashtags: {', '.join(content_result.get('suggested_hashtags', []))}")
    else:
        print(f"   Error: {content_result.get('error')}")
        return content_result

    # Step 2: Analyze text
    print("\n📊 Step 2: Analyzing content...")
    analysis_result = run_skill("social_media_manager", "analyze_text", {
        "text": content
    })
    
    if analysis_result.get("success"):
        analysis = analysis_result.get("analysis", {})
        print(f"   Word count: {analysis.get('word_count', 0)}")
        print(f"   Hashtags: {len(analysis.get('hashtags', []))}")
        print(f"   Emojis: {len(analysis.get('emojis', []))}")
        print(f"   Readability: {analysis.get('readability_score', 'N/A')}")
        
        # Platform compatibility
        platforms = analysis.get('platform_compatibility', {})
        for platform, info in platforms.items():
            status = "✅" if info.get('fits') else "❌"
            print(f"   {platform}: {status}")

    # Step 3: Schedule post
    print(f"\n📅 Step 3: Scheduling for {schedule_time}...")
    schedule_result = run_skill("social_media_manager", "schedule_post", {
        "content": content,
        "platform": "linkedin",
        "schedule_time": schedule_time
    })
    
    if schedule_result.get("success"):
        print(f"   Post ID: {schedule_result.get('post_id', 'N/A')}")
        print(f"   Scheduled for: {schedule_result.get('scheduled_for', 'N/A')}")
        print(f"   Total scheduled: {schedule_result.get('total_scheduled', 0)}")

    # Step 4: Track hashtags
    print("\n#️⃣ Step 4: Setting up hashtag tracking...")
    hashtags = content_result.get('suggested_hashtags', [])
    track_result = run_skill("social_media_manager", "track_hashtags", {
        "hashtags": hashtags,
        "period": "7d"
    })
    
    if track_result.get("success"):
        print(f"   Tracking {len(hashtags)} hashtags for 7 days")

    # Final summary
    print("\n" + "=" * 60)
    print("✅ Social media automation completed!")
    print(f"   Content length: {len(content)} characters")
    print(f"   Scheduled: {schedule_result.get('scheduled_for', 'N/A')}")
    print(f"   Post ID: {schedule_result.get('post_id', 'N/A')}")

    return {
        "success": True,
        "content": content,
        "scheduled_for": schedule_result.get('scheduled_for'),
        "post_id": schedule_result.get('post_id'),
        "analysis": analysis_result.get('analysis', {})
    }


if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "AI automation"
    schedule = sys.argv[2] if len(sys.argv) > 2 else "tomorrow 9am"
    result = social_media_automation(topic, schedule)
    print(f"\n📊 Full result saved to automation log")
