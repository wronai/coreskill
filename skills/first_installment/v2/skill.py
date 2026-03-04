import subprocess
import re
import urllib.request
import json


def get_info() -> dict:
    return {
        'name': 'first_installment',
        'version': 'v1',
        'description': 'Skill to handle queries about first installment (pierwsza rata)'
    }


def health_check() -> dict:
    try:
        # Check if espeak is available (for TTS if needed)
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


class FirstInstallmentSkill:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').strip().lower()
            
            # Check if the query is about "pierwsza rata"
            if 'pierwsza rata' in text or 'pierwsza rata' in text.replace(' ', ''):
                # Try to get general info about first installment
                try:
                    # Use espeak to generate speech if needed
                    subprocess.run(['espeak', 'Pierwsza rata to zazwyczaj wpłata początkowa przy kupnie towaru lub usługi na raty.'], timeout=5)
                except Exception:
                    pass  # Ignore TTS errors
                
                # Provide a helpful response
                response_text = (
                    "Pierwsza rata to zazwyczaj wpłata początkowa przy kupnie towaru lub usługi na raty. "
                    "Wiele firm oferuje możliwość zapłaty pierwszej raty w wysokości od 10% do 30% wartości całości. "
                    "Warto sprawdzić warunki oferty, w tym oprocentowanie i opłaty dodatkowe."
                )
                
                return {
                    'success': True,
                    'text': response_text,
                    'spoken': response_text,
                    'data': {
                        'first_installment_info': response_text
                    }
                }
            else:
                # Not a match for this skill
                return {
                    'success': False,
                    'text': 'Not applicable',
                    'spoken': 'Not applicable',
                    'data': {}
                }
        
        except Exception as e:
            return {
                'success': False,
                'text': f'Błąd przetwarzania: {str(e)}',
                'spoken': f'Błąd przetwarzania: {str(e)}',
                'data': {'error': str(e)}
            }


# Module-level execute function
def execute(params: dict) -> dict:
    skill = FirstInstallmentSkill()
    return skill.execute(params)


if __name__ == '__main__':
    # Test the skill
    test_params = {'text': 'pierwsza rata'}
    result = execute(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))