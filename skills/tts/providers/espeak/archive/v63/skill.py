import subprocess

class TestSkill:
    def execute(self, params: dict) -> dict:
        try:
            # Use espeak for TTS
            text_to_speak = "mowmy glosowo"
            subprocess.run(['espeak', text_to_speak], check=True)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

def get_info():
    return {"name": "test"}

def health_check():
    return True

if __name__ == "__main__":
    skill = TestSkill()
    result = skill.execute({})
    print(result)