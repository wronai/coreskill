#!/usr/bin/env python3
"""
OpenRouter API Test Skill - Validates OpenRouter API key
Usage: execute({"action": "test", "api_key": "sk-or-v1-..."})
"""
import json
import os
import subprocess
import sys
import time

class OpenRouterAPITestSkill:
    """Test OpenRouter API connectivity and validate API key."""
    
    def __init__(self):
        self.name = "openrouter_api_test"
        self.version = "v1"
    
    def get_info(self):
        return {
            "name": self.name,
            "version": self.version,
            "description": "Test OpenRouter API connectivity and validate API key",
            "actions": ["test", "validate", "ping"]
        }
    
    def execute(self, params: dict) -> dict:
        """
        Execute API test.
        
        Args:
            params: {
                "action": "test" | "validate" | "ping",
                "api_key": "sk-or-v1-..." (optional, uses env if not provided),
                "model": "openrouter/meta-llama/llama-3.3-70b-instruct:free" (optional)
            }
        """
        action = params.get("action", "test")
        api_key = params.get("api_key") or os.environ.get("OPENROUTER_API_KEY")
        model = params.get("model", "openrouter/meta-llama/llama-3.3-70b-instruct:free")
        
        if not api_key:
            return {
                "success": False,
                "error": "No API key provided. Set OPENROUTER_API_KEY env var or pass api_key param.",
                "suggestion": "Get key from https://openrouter.ai/keys"
            }
        
        if action == "test":
            return self._test_api(api_key, model)
        elif action == "validate":
            return self._validate_key(api_key)
        elif action == "ping":
            return self._ping_openrouter(api_key)
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }
    
    def _test_api(self, api_key: str, model: str) -> dict:
        """Test API with a simple completion call."""
        try:
            # Try to use litellm if available
            import litellm
            litellm.set_verbose = False
            
            start = time.time()
            response = litellm.completion(
                model=model,
                messages=[{"role": "user", "content": "Say 'OK' and nothing else."}],
                api_key=api_key,
                timeout=15,
                max_tokens=10
            )
            elapsed = time.time() - start
            
            content = response.choices[0].message.content if response.choices else ""
            
            return {
                "success": True,
                "model_used": model,
                "response_time_ms": round(elapsed * 1000, 2),
                "response": content.strip(),
                "api_key_valid": True,
                "api_key_prefix": api_key[:8] + "..." if len(api_key) > 12 else api_key
            }
            
        except Exception as e:
            error_str = str(e)
            
            # Check for specific errors
            if "401" in error_str or "authentication" in error_str.lower():
                return {
                    "success": False,
                    "error": "API key invalid or expired",
                    "error_type": "authentication",
                    "suggestion": "Check your key at https://openrouter.ai/keys"
                }
            elif "429" in error_str or "rate limit" in error_str.lower():
                return {
                    "success": False,
                    "error": "Rate limit exceeded",
                    "error_type": "rate_limit",
                    "suggestion": "Wait a moment and try again"
                }
            elif "402" in error_str or "insufficient" in error_str.lower():
                return {
                    "success": False,
                    "error": "Insufficient credits",
                    "error_type": "payment",
                    "suggestion": "Add credits at https://openrouter.ai/credits"
                }
            else:
                return {
                    "success": False,
                    "error": error_str,
                    "error_type": "unknown"
                }
    
    def _validate_key(self, api_key: str) -> dict:
        """Validate key format without making API call."""
        # OpenRouter keys start with "sk-or-v1-"
        if not api_key.startswith("sk-or-"):
            return {
                "success": False,
                "error": "Invalid API key format",
                "error_type": "format",
                "suggestion": "OpenRouter keys start with 'sk-or-v1-'"
            }
        
        if len(api_key) < 20:
            return {
                "success": False,
                "error": "API key too short",
                "error_type": "format"
            }
        
        return {
            "success": True,
            "valid_format": True,
            "key_prefix": api_key[:12] + "..."
        }
    
    def _ping_openrouter(self, api_key: str) -> dict:
        """Ping OpenRouter API endpoint."""
        try:
            import urllib.request
            import urllib.error
            
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/auth/key",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            start = time.time()
            with urllib.request.urlopen(req, timeout=10) as response:
                elapsed = time.time() - start
                data = json.loads(response.read().decode())
                
                return {
                    "success": True,
                    "ping_ms": round(elapsed * 1000, 2),
                    "status_code": response.status,
                    "data": data
                }
                
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return {
                    "success": False,
                    "error": "API key invalid",
                    "error_type": "authentication",
                    "status_code": 401
                }
            return {
                "success": False,
                "error": f"HTTP error: {e.code}",
                "status_code": e.code
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": "connection"
            }


def execute(params: dict) -> dict:
    """Entry point for skill execution."""
    skill = OpenRouterAPITestSkill()
    return skill.execute(params)


def get_info():
    """Return skill metadata."""
    return OpenRouterAPITestSkill().get_info()


if __name__ == "__main__":
    # Test the skill
    print("Testing OpenRouter API Skill...")
    
    # Test 1: Validate format
    result = execute({"action": "validate", "api_key": "sk-or-v1-invalid"})
    print(f"Validate test: {result}")
    
    # Test 2: Test with env key if available
    if os.environ.get("OPENROUTER_API_KEY"):
        result = execute({"action": "test"})
        print(f"API test: {result}")
    else:
        print("No OPENROUTER_API_KEY set, skipping API test")


def health_check():
    return True

