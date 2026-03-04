#!/usr/bin/env python3
"""
social_media_manager skill - Manage social media accounts and content.
Supports: post scheduling, content templates, analytics, cross-platform posting.
Uses stdlib + basic HTTP for API interactions.
"""
import json
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timedelta
import re


def get_info():
    return {
        "name": "social_media_manager",
        "version": "v1",
        "description": "Manage social media: schedule posts, content templates, analytics tracking.",
        "capabilities": ["social", "media", "posting", "scheduling", "content"],
        "actions": ["create_post", "schedule_post", "generate_content", "analyze_text", "track_hashtags"]
    }


def health_check():
    return True


class SocialMediaManagerSkill:
    """Social media content management and scheduling."""

    def __init__(self):
        self.config_dir = Path.home() / ".evo_social_media"
        self.config_dir.mkdir(exist_ok=True)
        self.posts_file = self.config_dir / "scheduled_posts.json"
        self.templates_file = self.config_dir / "templates.json"
        self._ensure_defaults()

    def _ensure_defaults(self):
        """Ensure default templates exist."""
        if not self.templates_file.exists():
            default_templates = {
                "announcement": "🎉 Exciting news! {{message}} #announcement",
                "tip": "💡 Pro tip: {{message}} #tips #{{category}}",
                "question": "❓ {{question}} Share your thoughts below! 👇",
                "milestone": "🎯 We reached {{milestone}}! Thanks to everyone who supported us! 🙏",
                "promotion": "🔥 {{offer}} Limited time only! {{link}} #promo #{{category}}"
            }
            with open(self.templates_file, 'w') as f:
                json.dump(default_templates, f, indent=2)

    def _load_posts(self):
        """Load scheduled posts."""
        try:
            if self.posts_file.exists():
                with open(self.posts_file, 'r') as f:
                    return json.load(f)
            return []
        except:
            return []

    def _save_posts(self, posts):
        """Save scheduled posts."""
        try:
            with open(self.posts_file, 'w') as f:
                json.dump(posts, f, indent=2, default=str)
        except Exception as e:
            pass

    def _load_templates(self):
        """Load content templates."""
        try:
            if self.templates_file.exists():
                with open(self.templates_file, 'r') as f:
                    return json.load(f)
            return {}
        except:
            return {}

    def create_post(self, content, platform="generic", hashtags=None, mentions=None):
        """Create a social media post with metadata."""
        try:
            # Validate content length for different platforms
            limits = {
                "twitter": 280,
                "x": 280,
                "linkedin": 3000,
                "facebook": 63206,
                "instagram": 2200,
                "generic": 10000
            }

            platform_lower = platform.lower()
            limit = limits.get(platform_lower, 10000)

            # Generate hashtags if not provided
            if hashtags is None:
                hashtags = self._extract_hashtags(content)

            # Add mentions
            if mentions:
                mention_str = ' '.join(f'@{m}' for m in mentions)
                content = f"{mention_str} {content}"

            # Check length
            is_valid = len(content) <= limit

            post = {
                "content": content,
                "platform": platform,
                "hashtags": hashtags,
                "mentions": mentions or [],
                "length": len(content),
                "limit": limit,
                "within_limit": is_valid,
                "created_at": datetime.now().isoformat()
            }

            return {
                "success": True,
                "post": post,
                "preview": content[:100] + "..." if len(content) > 100 else content
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def schedule_post(self, content, schedule_time, platform="generic", recurring=None):
        """Schedule a post for future publication."""
        try:
            posts = self._load_posts()

            # Parse schedule time
            if isinstance(schedule_time, str):
                try:
                    schedule_dt = datetime.fromisoformat(schedule_time.replace('Z', '+00:00'))
                except:
                    # Try relative time
                    schedule_dt = self._parse_relative_time(schedule_time)
            else:
                schedule_dt = schedule_time

            if schedule_dt is None:
                return {"success": False, "error": "Could not parse schedule time"}

            post = {
                "id": len(posts) + 1,
                "content": content,
                "platform": platform,
                "scheduled_for": schedule_dt.isoformat(),
                "status": "scheduled",
                "recurring": recurring,
                "created_at": datetime.now().isoformat()
            }

            posts.append(post)
            self._save_posts(posts)

            return {
                "success": True,
                "post_id": post["id"],
                "scheduled_for": schedule_dt.isoformat(),
                "platform": platform,
                "total_scheduled": len(posts)
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _parse_relative_time(self, time_str):
        """Parse relative time like '+1 hour', 'tomorrow 9am'."""
        now = datetime.now()
        time_str = time_str.lower().strip()

        if time_str.startswith('+') or time_str.startswith('in '):
            # Relative: +1 hour, in 30 minutes
            match = re.match(r'(?:in\s+)?\+?(\d+)\s*(minute|hour|day|week)s?', time_str)
            if match:
                num = int(match.group(1))
                unit = match.group(2)
                delta = timedelta(**{unit + 's': num})
                return now + delta

        if 'tomorrow' in time_str:
            tomorrow = now + timedelta(days=1)
            # Try to extract time
            time_match = re.search(r'(\d{1,2}):?(\d{2})?\s*(am|pm)?', time_str)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2) or 0)
                if time_match.group(3) == 'pm' and hour != 12:
                    hour += 12
                return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
            return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)

        return None

    def generate_content(self, topic, template_name=None, tone="professional", length="medium"):
        """Generate social media content from template."""
        try:
            templates = self._load_templates()

            if template_name and template_name in templates:
                template = templates[template_name]
            else:
                # Generate based on tone
                tone_templates = {
                    "professional": "Learn about {{topic}}. {{key_points}} Discover more insights.",
                    "casual": "Hey everyone! {{topic}} is something you should check out! {{key_points}} What do you think? 🤔",
                    "excited": "🚀 WOW! {{topic}} is amazing! {{key_points}} Don't miss out! 🔥",
                    "educational": "📚 Understanding {{topic}}: {{key_points}} Save this for later! 💾"
                }
                template = tone_templates.get(tone, tone_templates["professional"])

            # Suggest hashtags based on topic
            suggested_hashtags = self._suggest_hashtags(topic)

            # Generate key points placeholder
            key_points = self._generate_key_points(topic, length)

            content = template.replace("{{topic}}", topic)
            content = content.replace("{{key_points}}", key_points)

            # Add suggested hashtags
            hashtag_str = ' '.join(f'#{tag}' for tag in suggested_hashtags[:5])
            content = f"{content}\n\n{hashtag_str}"

            return {
                "success": True,
                "content": content,
                "template_used": template_name or "auto-generated",
                "tone": tone,
                "suggested_hashtags": suggested_hashtags,
                "length": len(content)
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _generate_key_points(self, topic, length):
        """Generate placeholder key points."""
        points_map = {
            "short": f"Key benefits of {topic}.",
            "medium": f"Key benefits of {topic}: efficiency, quality, and innovation.",
            "long": f"Key benefits of {topic}: 1) Increased efficiency, 2) Better quality, 3) Enhanced innovation, 4) Cost effectiveness, 5) Competitive advantage."
        }
        return points_map.get(length, points_map["medium"])

    def _suggest_hashtags(self, topic):
        """Suggest hashtags based on topic."""
        topic_lower = topic.lower()

        # Common hashtag mappings
        hashtag_map = {
            "tech": ["technology", "innovation", "tech", "digital", "future"],
            "business": ["business", "entrepreneur", "success", "leadership", "growth"],
            "marketing": ["marketing", "digitalmarketing", "socialmedia", "branding", "content"],
            "ai": ["ai", "artificialintelligence", "machinelearning", "tech", "innovation"],
            "design": ["design", "ux", "ui", "creative", "webdesign"],
            "health": ["health", "wellness", "fitness", "lifestyle", "healthy"],
            "education": ["education", "learning", "study", "knowledge", "school"]
        }

        for key, tags in hashtag_map.items():
            if key in topic_lower:
                return tags

        # Generate from topic words
        words = topic_lower.split()[:3]
        return words + ["trending", "viral"]

    def _extract_hashtags(self, text):
        """Extract hashtags from text."""
        return re.findall(r'#\w+', text)

    def analyze_text(self, text):
        """Analyze text for social media optimization."""
        try:
            analysis = {
                "length": len(text),
                "word_count": len(text.split()),
                "character_count": len(text.replace(' ', '')),
                "hashtags": self._extract_hashtags(text),
                "mentions": re.findall(r'@\w+', text),
                "urls": re.findall(r'https?://\S+', text),
                "emojis": re.findall(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', text),
                "readability_score": self._calculate_readability(text)
            }

            # Platform compatibility
            platforms = {}
            for platform, limit in [("twitter", 280), ("linkedin", 3000), ("instagram", 2200)]:
                fits = analysis["length"] <= limit
                platforms[platform] = {
                    "fits": fits,
                    "remaining": limit - analysis["length"] if fits else 0,
                    "over_by": analysis["length"] - limit if not fits else 0
                }

            analysis["platform_compatibility"] = platforms

            return {
                "success": True,
                "analysis": analysis,
                "recommendations": self._generate_recommendations(analysis)
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _calculate_readability(self, text):
        """Simple readability calculation."""
        words = text.split()
        sentences = re.split(r'[.!?]+', text)

        if not words or not sentences:
            return 0

        avg_words_per_sentence = len(words) / len(sentences)

        # Simple score: lower is easier
        if avg_words_per_sentence < 10:
            return "Easy"
        elif avg_words_per_sentence < 20:
            return "Medium"
        else:
            return "Complex"

    def _generate_recommendations(self, analysis):
        """Generate optimization recommendations."""
        recs = []

        if analysis["length"] > 280:
            recs.append("Consider shortening for Twitter/X compatibility")

        if len(analysis["hashtags"]) < 2:
            recs.append("Add more hashtags for better discoverability")
        elif len(analysis["hashtags"]) > 10:
            recs.append("Too many hashtags - consider using 3-5 relevant ones")

        if not analysis["urls"]:
            recs.append("Consider adding a link for more information")

        if len(analysis["emojis"]) < 1:
            recs.append("Add an emoji to increase engagement")

        return recs

    def track_hashtags(self, hashtags, period="7d"):
        """Track hashtag performance (placeholder for analytics)."""
        try:
            # In production, this would use social media APIs
            return {
                "success": True,
                "note": "Hashtag tracking requires API integration",
                "hashtags": hashtags,
                "period": period,
                "suggested_tracking": {
                    "impressions": "Track via platform analytics",
                    "engagement": "Monitor likes, shares, comments",
                    "reach": "Unique accounts reached"
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_scheduled_posts(self, status=None, platform=None):
        """List all scheduled posts."""
        try:
            posts = self._load_posts()

            if status:
                posts = [p for p in posts if p.get("status") == status]
            if platform:
                posts = [p for p in posts if p.get("platform") == platform]

            # Sort by scheduled time
            posts.sort(key=lambda x: x.get("scheduled_for", ""))

            return {
                "success": True,
                "count": len(posts),
                "posts": posts
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        action = input_data.get("action", "create_post")

        if action == "create_post":
            return self.create_post(
                input_data.get("content", ""),
                input_data.get("platform", "generic"),
                input_data.get("hashtags"),
                input_data.get("mentions")
            )
        elif action == "schedule_post":
            return self.schedule_post(
                input_data.get("content", ""),
                input_data.get("schedule_time"),
                input_data.get("platform", "generic"),
                input_data.get("recurring")
            )
        elif action == "generate_content":
            return self.generate_content(
                input_data.get("topic", ""),
                input_data.get("template_name"),
                input_data.get("tone", "professional"),
                input_data.get("length", "medium")
            )
        elif action == "analyze_text":
            return self.analyze_text(input_data.get("text", ""))
        elif action == "track_hashtags":
            return self.track_hashtags(
                input_data.get("hashtags", []),
                input_data.get("period", "7d")
            )
        elif action == "list_scheduled_posts":
            return self.list_scheduled_posts(
                input_data.get("status"),
                input_data.get("platform")
            )
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


def execute(input_data: dict) -> dict:
    return SocialMediaManagerSkill().execute(input_data)


if __name__ == "__main__":
    skill = SocialMediaManagerSkill()
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    print(f"Health: {health_check()}")

    # Test content generation
    print("\nTest generate_content:")
    result = skill.generate_content("AI in business", tone="professional")
    print(json.dumps(result, indent=2))
