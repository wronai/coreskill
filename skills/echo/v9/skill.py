import subprocess
import json
from datetime import datetime, timezone
import re
import time

def get_info():
    return {"name": "echo", "version": "v1", "description": "Echo skill that supports text formatting (bold, uppercase) and reversal (rev: prefix)."}

def health_check():
    return {"status": "ok"}

class EchoSkill:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '')
            if not text:
                return {'success': False, 'message': 'No text provided.'}

            # Check for reversal prefix
            is_reversed = text.startswith('rev:')
            if is_reversed:
                text = text[4:].strip()
            
            processed_text = text
            spoken_text = text

            # Process uppercase - handle nested tags properly
            uppercase_pattern = re.compile(r'\[uppercase\](.*?)\[/uppercase\]', re.IGNORECASE | re.DOTALL)
            while True:
                match = uppercase_pattern.search(processed_text)
                if not match:
                    break
                content = match.group(1)
                processed_text = processed_text[:match.start()] + content.upper() + processed_text[match.end():]
                spoken_text = spoken_text[:match.start()] + content + spoken_text[match.end():]

            # Process bold - handle nested tags properly
            bold_pattern = re.compile(r'\[bold\](.*?)\[/bold\]', re.IGNORECASE | re.DOTALL)
            while True:
                match = bold_pattern.search(processed_text)
                if not match:
                    break
                content = match.group(1)
                processed_text = processed_text[:match.start()] + f"<b>{content}</b>" + processed_text[match.end():]
                spoken_text = spoken_text[:match.start()] + content + spoken_text[match.end():]

            # Apply reversal if needed
            if is_reversed:
                processed_text = processed_text[::-1]
                spoken_text = spoken_text[::-1]

            return {
                'success': True,
                'result': processed_text,
                'spoken': spoken_text,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'skill': get_info()
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}

def execute(params: dict) -> dict:
    skill = EchoSkill()
    return skill.execute(params)

if __name__ == "__main__":
    test_params_1 = {"text": "Hello, this is a [bold]bold[/bold] message."}
    print("Test 1:")
    print(json.dumps(execute(test_params_1), indent=2))

    test_params_2 = {"text": "This is an [uppercase]important[/uppercase] announcement."}
    print("\nTest 2:")
    print(json.dumps(execute(test_params_2), indent=2))

    test_params_3 = {"text": "A [bold]bold[/bold] and [uppercase]UPPERCASE[/uppercase] message."}
    print("\nTest 3:")
    print(json.dumps(execute(test_params_3), indent=2))

    test_params_4 = {"text": "Just a regular message."}
    print("\nTest 4:")
    print(json.dumps(execute(test_params_4), indent=2))

    test_params_5 = {}
    print("\nTest 5 (empty text):")
    print(json.dumps(execute(test_params_5), indent=2))

    test_params_6 = {"text": "[uppercase]ALL CAPS[/uppercase] and [bold]bold[/bold] text."}
    print("\nTest 6:")
    print(json.dumps(execute(test_params_6), indent=2))

    test_params_7 = {"text": "[bold]bold[/bold] and [uppercase]all caps[/uppercase] text."}
    print("\nTest 7:")
    print(json.dumps(execute(test_params_7), indent=2))

    test_params_8 = {"text": "rev:Hello, this is reversed text."}
    print("\nTest 8 (reversed):")
    print(json.dumps(execute(test_params_8), indent=2))

    test_params_9 = {"text": "rev:[uppercase]Reversed uppercase[/uppercase] text."}
    print("\nTest 9 (reversed with formatting):")
    print(json.dumps(execute(test_params_9), indent=2))