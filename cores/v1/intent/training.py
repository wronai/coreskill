"""Intent classification training data and utilities."""
from typing import List, Tuple

# Default training examples (Polish + English)
# Format: (user_message, action, skill_or_goal)
DEFAULT_TRAINING: List[Tuple[str, str, str]] = [
    # Chat / conversation
    ("cześć", "chat", ""),
    ("hej", "chat", ""),
    ("jak się masz", "chat", ""),
    ("co słychać", "chat", ""),
    ("dzień dobry", "chat", ""),
    ("hi", "chat", ""),
    ("hello", "chat", ""),
    ("how are you", "chat", ""),
    
    # TTS / voice output
    ("powiedz", "use", "tts"),
    ("wypowiedz", "use", "tts"),
    ("przeczytaj", "use", "tts"),
    ("mów do mnie", "use", "tts"),
    ("odczytaj", "use", "tts"),
    ("speak", "use", "tts"),
    ("say", "use", "tts"),
    ("read aloud", "use", "tts"),
    
    # STT / voice input
    ("słuchaj", "use", "stt"),
    ("nagrywaj", "use", "stt"),
    ("zapisz co mówię", "use", "stt"),
    ("rozpoznaj mowę", "use", "stt"),
    ("transkrybuj", "use", "stt"),
    ("listen", "use", "stt"),
    ("record", "use", "stt"),
    ("transcribe", "use", "stt"),
    
    # Voice mode (TTS + STT conversation)
    ("porozmawiajmy głosowo", "use", "stt"),
    ("pogadajmy głosem", "use", "stt"),
    ("włącz tryb głosowy", "use", "stt"),
    ("rozmawiajmy głosowo", "use", "stt"),
    ("voice mode", "use", "stt"),
    ("let's talk", "use", "stt"),
    ("voice conversation", "use", "stt"),
    
    # Web search
    ("wyszukaj", "use", "web_search"),
    ("szukaj", "use", "web_search"),
    ("znajdź w internecie", "use", "web_search"),
    ("przeszukaj web", "use", "web_search"),
    ("daj mi linki", "use", "web_search"),
    ("google", "use", "web_search"),
    ("search", "use", "web_search"),
    ("find online", "use", "web_search"),
    ("look up", "use", "web_search"),
    
    # DevOps
    ("deploy", "use", "devops"),
    ("wdrożenie", "use", "devops"),
    ("status systemu", "use", "devops"),
    ("restart usługi", "use", "devops"),
    ("przebuduj", "use", "devops"),
    ("check service", "use", "devops"),
    
    # Git ops
    ("commit", "use", "git_ops"),
    ("push", "use", "git_ops"),
    ("pull", "use", "git_ops"),
    ("status gita", "use", "git_ops"),
    ("zacommituj", "use", "git_ops"),
    ("wypchnij", "use", "git_ops"),
    ("ściągnij zmiany", "use", "git_ops"),
    
    # Deps / dependencies
    ("zainstaluj", "use", "deps"),
    ("doinstaluj", "use", "deps"),
    ("dodaj paczkę", "use", "deps"),
    ("install", "use", "deps"),
    ("requirements", "use", "deps"),
    ("dependencies", "use", "deps"),
    
    # Skill evolution
    ("napraw", "evolve", ""),
    ("popraw", "evolve", ""),
    ("ulepsz", "evolve", ""),
    ("fix", "evolve", ""),
    ("repair", "evolve", ""),
    ("improve", "evolve", ""),
    
    # Skill creation
    ("stwórz skill", "create", ""),
    ("nowy skill", "create", ""),
    ("zbuduj", "create", ""),
    ("utwórz", "create", ""),
    ("create skill", "create", ""),
    ("new skill", "create", ""),
    ("build skill", "create", ""),
    # Program/app creation
    ("napisz program", "create", ""),
    ("zbuduj aplikację", "create", ""),
    ("stwórz program", "create", ""),
    ("napisz kod", "create", ""),
    ("zbuduj system", "create", ""),
    ("utwórz aplikację", "create", ""),
    
    # Echo (test skill)
    ("echo", "use", "echo"),
    ("test echo", "use", "echo"),
    ("przetestuj echo", "use", "echo"),
    ("ping", "use", "echo"),
    
    # Shell / bash
    ("uruchom", "use", "shell"),
    ("wykonaj", "use", "shell"),
    ("bash", "use", "shell"),
    ("command", "use", "shell"),
    ("terminal", "use", "shell"),
    ("run command", "use", "shell"),
    ("execute", "use", "shell"),
    
    # Network info
    ("jaki mam adres ip", "use", "network_info"),
    ("pokaż mac", "use", "network_info"),
    ("jaki numer ip", "use", "network_info"),
    ("adres mac urządzenia", "use", "network_info"),
    ("pokaż ip i mac", "use", "network_info"),
    
    # Time
    ("która jest godzina", "use", "time"),
    ("jaki mamy czas", "use", "time"),
    ("podaj datę", "use", "time"),
    ("ile jest godzin", "use", "time"),
    ("pokaż czas", "use", "time"),
]
