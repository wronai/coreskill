import subprocess
import json
from datetime import datetime, timezone
import re

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
            is_uppercase = False
            is_bold = False

            # Handle uppercase
            uppercase_match = re.search(r'\[uppercase\](.*?)\[/uppercase\]', processed_text, re.IGNORECASE)
            if uppercase_match:
                is_uppercase = True
                content_to_uppercase = uppercase_match.group(1)
                processed_text = processed_text.replace(uppercase_match.group(0), content_to_uppercase.upper())
                spoken_text = spoken_text.replace(uppercase_match.group(0), content_to_uppercase.upper())

            # Handle bold
            bold_match = re.search(r'\[bold\](.*?)\[/bold\]', processed_text, re.IGNORECASE)
            if bold_match:
                is_bold = True
                bold_content = bold_match.group(1)
                processed_text = processed_text.replace(bold_match.group(0), f"<b>{bold_content}</b>")
                # For spoken text, we don't add HTML tags. If it was also uppercased, it's already handled.
                # If only bold, spoken_text remains as is.

            # Ensure spoken_text is derived from the processed_text if no specific formatting was applied to it.
            # This logic needs refinement. The goal is to have spoken_text be the plain text version.
            # If uppercase was applied, spoken_text should reflect that.
            # If bold was applied, spoken_text should be the content without bold tags.

            final_spoken_text = text
            if is_uppercase:
                # Re-extract and uppercase for spoken text to ensure it's clean
                uppercase_match_for_spoken = re.search(r'\[uppercase\](.*?)\[/uppercase\]', text, re.IGNORECASE)
                if uppercase_match_for_spoken:
                    final_spoken_text = final_spoken_text.replace(uppercase_match_for_spoken.group(0), uppercase_match_for_spoken.group(1).upper())

            if is_bold:
                # Remove bold tags for spoken text
                bold_match_for_spoken = re.search(r'\[bold\](.*?)\[/bold\]', final_spoken_text, re.IGNORECASE)
                if bold_match_for_spoken:
                    final_spoken_text = final_spoken_text.replace(bold_match_for_spoken.group(0), bold_match_for_spoken.group(1))

            # If no specific tags were found, processed_text and spoken_text should be the same.
            if not is_uppercase and not is_bold:
                final_spoken_text = processed_text


            return {
                'success': True,
                'result': processed_text,
                'spoken': final_spoken_text,
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
```