import subprocess
import json
from datetime import datetime, timezone
import re
import time

def get_info():
    return {"name": "echo", "version": "v1", "description": "Echo skill that supports text formatting (bold, uppercase)."}

def health_check():
    return {"status": "ok"}

class EchoSkill:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '')
            if not text:
                return {'success': False, 'message': 'No text provided.'}

            processed_text = text
            spoken_text = text

            # Handle uppercase
            if "[uppercase]" in processed_text.lower():
                processed_text = processed_text.replace("[uppercase]", "").strip()
                spoken_text = processed_text.upper()
                processed_text = f"<b>{processed_text.upper()}</b>"

            # Handle bold
            bold_match = re.search(r'\[bold\](.*?)\[/bold\]', processed_text, re.IGNORECASE)
            if bold_match:
                bold_content = bold_match.group(1)
                processed_text = processed_text.replace(bold_match.group(0), f"<b>{bold_content}</b>")
                # For TTS, we might want to speak bold content normally or with emphasis if espeak supports it.
                # For simplicity, we'll keep spoken_text as is unless it was also uppercased.

            # If no specific formatting was applied, ensure spoken_text is derived from processed_text
            if "[uppercase]" not in text.lower() and not bold_match:
                 spoken_text = processed_text


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