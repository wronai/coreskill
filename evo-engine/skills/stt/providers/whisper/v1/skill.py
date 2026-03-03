# Placeholder for stt/whisper provider
# TODO: implement by running /evolve stt --provider whisper

def get_info():
    return {'name': 'stt', 'provider': 'whisper', 'version': 'v1', 'status': 'placeholder'}

def health_check():
    return False  # not implemented yet

class WhisperSkill:
    def execute(self, input_data):
        return {'error': 'Provider whisper not yet implemented'}
