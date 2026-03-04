"""Intent classification training data and utilities.

Multilingual training examples covering all European languages.
The SBERT model (paraphrase-multilingual-MiniLM-L12-v2) handles
cross-lingual semantic similarity natively.
"""
from typing import List, Tuple

# Default training examples — ALL European languages
# Format: (user_message, action, skill_or_goal)
DEFAULT_TRAINING: List[Tuple[str, str, str]] = [
    # ── Chat / conversation ──────────────────────────────────────────
    # English
    ("hi", "chat", ""),
    ("hello", "chat", ""),
    ("how are you", "chat", ""),
    ("what's up", "chat", ""),
    # Polish
    ("cześć", "chat", ""),
    ("hej", "chat", ""),
    ("jak się masz", "chat", ""),
    ("co słychać", "chat", ""),
    ("dzień dobry", "chat", ""),
    # German
    ("hallo", "chat", ""),
    ("guten morgen", "chat", ""),
    ("wie geht es dir", "chat", ""),
    # French
    ("salut", "chat", ""),
    ("bonjour", "chat", ""),
    ("comment ça va", "chat", ""),
    # Spanish
    ("hola", "chat", ""),
    ("buenos días", "chat", ""),
    ("cómo estás", "chat", ""),
    # Italian
    ("ciao", "chat", ""),
    ("buongiorno", "chat", ""),
    ("come stai", "chat", ""),
    # Portuguese
    ("olá", "chat", ""),
    ("bom dia", "chat", ""),
    ("como vai", "chat", ""),
    # Dutch
    ("hoi", "chat", ""),
    ("goedemorgen", "chat", ""),
    ("hoe gaat het", "chat", ""),
    # Swedish
    ("hej", "chat", ""),
    ("god morgon", "chat", ""),
    ("hur mår du", "chat", ""),
    # Norwegian
    ("hei", "chat", ""),
    ("god morgen", "chat", ""),
    ("hvordan har du det", "chat", ""),
    # Danish
    ("godmorgen", "chat", ""),
    ("hvordan går det", "chat", ""),
    # Czech
    ("ahoj", "chat", ""),
    ("dobrý den", "chat", ""),
    ("jak se máš", "chat", ""),
    # Slovak
    ("dobrý deň", "chat", ""),
    ("ako sa máš", "chat", ""),
    # Ukrainian
    ("привіт", "chat", ""),
    ("добрий день", "chat", ""),
    ("як справи", "chat", ""),
    # Russian
    ("привет", "chat", ""),
    ("здравствуйте", "chat", ""),
    ("как дела", "chat", ""),
    # Bulgarian
    ("здравей", "chat", ""),
    ("добро утро", "chat", ""),
    ("как си", "chat", ""),
    # Croatian
    ("bok", "chat", ""),
    ("dobar dan", "chat", ""),
    ("kako si", "chat", ""),
    # Serbian
    ("здраво", "chat", ""),
    ("добар дан", "chat", ""),
    # Slovenian
    ("živjo", "chat", ""),
    ("dober dan", "chat", ""),
    ("kako si", "chat", ""),
    # Romanian
    ("bună", "chat", ""),
    ("bună ziua", "chat", ""),
    ("ce faci", "chat", ""),
    # Hungarian
    ("szia", "chat", ""),
    ("jó napot", "chat", ""),
    ("hogy vagy", "chat", ""),
    # Finnish
    ("moi", "chat", ""),
    ("huomenta", "chat", ""),
    ("mitä kuuluu", "chat", ""),
    # Estonian
    ("tere", "chat", ""),
    ("kuidas läheb", "chat", ""),
    # Lithuanian
    ("labas", "chat", ""),
    ("kaip sekasi", "chat", ""),
    # Latvian
    ("sveiki", "chat", ""),
    ("kā iet", "chat", ""),
    # Greek
    ("γεια", "chat", ""),
    ("καλημέρα", "chat", ""),
    ("τι κάνεις", "chat", ""),
    # Albanian
    ("përshëndetje", "chat", ""),
    ("mirëdita", "chat", ""),
    # Turkish
    ("merhaba", "chat", ""),
    ("günaydın", "chat", ""),
    ("nasılsın", "chat", ""),
    # Catalan
    ("bon dia", "chat", ""),
    ("com estàs", "chat", ""),
    # Basque
    ("kaixo", "chat", ""),
    ("egun on", "chat", ""),
    # Irish
    ("dia duit", "chat", ""),
    # Icelandic
    ("halló", "chat", ""),
    ("góðan dag", "chat", ""),
    # Belarusian
    ("прывітанне", "chat", ""),
    ("добры дзень", "chat", ""),
    # Maltese
    ("bongu", "chat", ""),
    ("merħba", "chat", ""),

    # ── TTS / voice output ───────────────────────────────────────────
    # English
    ("speak", "use", "tts"),
    ("say", "use", "tts"),
    ("read aloud", "use", "tts"),
    # Polish
    ("powiedz", "use", "tts"),
    ("wypowiedz", "use", "tts"),
    ("przeczytaj", "use", "tts"),
    ("mów do mnie", "use", "tts"),
    ("odczytaj", "use", "tts"),
    # German
    ("sprich", "use", "tts"),
    ("lies vor", "use", "tts"),
    ("sag mir", "use", "tts"),
    # French
    ("parle", "use", "tts"),
    ("lis à voix haute", "use", "tts"),
    ("dis-moi", "use", "tts"),
    # Spanish
    ("habla", "use", "tts"),
    ("lee en voz alta", "use", "tts"),
    ("dime", "use", "tts"),
    # Italian
    ("parla", "use", "tts"),
    ("leggi ad alta voce", "use", "tts"),
    ("dimmi", "use", "tts"),
    # Portuguese
    ("fala", "use", "tts"),
    ("lê em voz alta", "use", "tts"),
    # Dutch
    ("spreek", "use", "tts"),
    ("lees voor", "use", "tts"),
    # Swedish
    ("tala", "use", "tts"),
    ("läs högt", "use", "tts"),
    # Norwegian
    ("snakk", "use", "tts"),
    ("les høyt", "use", "tts"),
    # Czech
    ("řekni", "use", "tts"),
    ("čti nahlas", "use", "tts"),
    # Slovak
    ("povedz", "use", "tts"),
    ("čítaj nahlas", "use", "tts"),
    # Ukrainian
    ("скажи", "use", "tts"),
    ("прочитай вголос", "use", "tts"),
    # Russian
    ("скажи", "use", "tts"),
    ("прочитай вслух", "use", "tts"),
    ("произнеси", "use", "tts"),
    # Romanian
    ("spune", "use", "tts"),
    ("citește cu voce tare", "use", "tts"),
    # Hungarian
    ("mondd", "use", "tts"),
    ("olvasd fel", "use", "tts"),
    # Finnish
    ("puhu", "use", "tts"),
    ("lue ääneen", "use", "tts"),
    # Greek
    ("μίλα", "use", "tts"),
    ("διάβασε", "use", "tts"),
    # Turkish
    ("söyle", "use", "tts"),
    ("seslendir", "use", "tts"),

    # ── STT / voice input ────────────────────────────────────────────
    # English
    ("listen", "use", "stt"),
    ("record", "use", "stt"),
    ("transcribe", "use", "stt"),
    # Polish
    ("słuchaj", "use", "stt"),
    ("nagrywaj", "use", "stt"),
    ("zapisz co mówię", "use", "stt"),
    ("rozpoznaj mowę", "use", "stt"),
    ("transkrybuj", "use", "stt"),
    # German
    ("höre zu", "use", "stt"),
    ("aufnehmen", "use", "stt"),
    ("transkribieren", "use", "stt"),
    # French
    ("écoute", "use", "stt"),
    ("enregistre", "use", "stt"),
    ("transcrire", "use", "stt"),
    # Spanish
    ("escucha", "use", "stt"),
    ("graba", "use", "stt"),
    ("transcribe", "use", "stt"),
    # Italian
    ("ascolta", "use", "stt"),
    ("registra", "use", "stt"),
    ("trascrivi", "use", "stt"),
    # Portuguese
    ("ouve", "use", "stt"),
    ("grava", "use", "stt"),
    # Dutch
    ("luister", "use", "stt"),
    ("opnemen", "use", "stt"),
    # Czech
    ("poslouchej", "use", "stt"),
    ("nahrávej", "use", "stt"),
    # Ukrainian
    ("слухай", "use", "stt"),
    ("записуй", "use", "stt"),
    # Russian
    ("слушай", "use", "stt"),
    ("записывай", "use", "stt"),
    # Romanian
    ("ascultă", "use", "stt"),
    ("înregistrează", "use", "stt"),
    # Hungarian
    ("hallgass", "use", "stt"),
    ("rögzíts", "use", "stt"),
    # Finnish
    ("kuuntele", "use", "stt"),
    ("nauhoita", "use", "stt"),
    # Greek
    ("άκου", "use", "stt"),
    ("ηχογράφησε", "use", "stt"),
    # Turkish
    ("dinle", "use", "stt"),
    ("kaydet", "use", "stt"),

    # ── Voice mode (TTS + STT conversation) ──────────────────────────
    # English
    ("voice mode", "use", "stt"),
    ("let's talk", "use", "stt"),
    ("voice conversation", "use", "stt"),
    # Polish
    ("porozmawiajmy głosowo", "use", "stt"),
    ("pogadajmy głosem", "use", "stt"),
    ("włącz tryb głosowy", "use", "stt"),
    # German
    ("sprachmodus", "use", "stt"),
    ("lass uns reden", "use", "stt"),
    # French
    ("mode vocal", "use", "stt"),
    ("parlons", "use", "stt"),
    # Spanish
    ("modo voz", "use", "stt"),
    ("hablemos", "use", "stt"),
    # Italian
    ("modalità vocale", "use", "stt"),
    ("parliamo", "use", "stt"),
    # Portuguese
    ("modo voz", "use", "stt"),
    ("vamos conversar", "use", "stt"),
    # Russian
    ("голосовой режим", "use", "stt"),
    ("давай поговорим", "use", "stt"),
    # Turkish
    ("sesli mod", "use", "stt"),
    ("konuşalım", "use", "stt"),

    # ── Web search ───────────────────────────────────────────────────
    # English
    ("search", "use", "web_search"),
    ("find online", "use", "web_search"),
    ("look up", "use", "web_search"),
    ("google", "use", "web_search"),
    # Polish
    ("wyszukaj", "use", "web_search"),
    ("szukaj", "use", "web_search"),
    ("znajdź w internecie", "use", "web_search"),
    ("przeszukaj web", "use", "web_search"),
    ("daj mi linki", "use", "web_search"),
    # German
    ("suche", "use", "web_search"),
    ("finde", "use", "web_search"),
    ("nachschlagen", "use", "web_search"),
    # French
    ("cherche", "use", "web_search"),
    ("recherche", "use", "web_search"),
    # Spanish
    ("busca", "use", "web_search"),
    ("buscar en línea", "use", "web_search"),
    # Italian
    ("cerca", "use", "web_search"),
    ("ricerca", "use", "web_search"),
    # Portuguese
    ("procura", "use", "web_search"),
    ("pesquisa", "use", "web_search"),
    # Dutch
    ("zoek", "use", "web_search"),
    ("opzoeken", "use", "web_search"),
    # Czech
    ("hledej", "use", "web_search"),
    ("vyhledej", "use", "web_search"),
    # Ukrainian
    ("шукай", "use", "web_search"),
    ("знайди", "use", "web_search"),
    # Russian
    ("ищи", "use", "web_search"),
    ("найди в интернете", "use", "web_search"),
    # Romanian
    ("caută", "use", "web_search"),
    ("găsește", "use", "web_search"),
    # Hungarian
    ("keress", "use", "web_search"),
    ("keresd meg", "use", "web_search"),
    # Finnish
    ("etsi", "use", "web_search"),
    ("hae", "use", "web_search"),
    # Greek
    ("ψάξε", "use", "web_search"),
    ("αναζήτησε", "use", "web_search"),
    # Turkish
    ("ara", "use", "web_search"),
    ("araştır", "use", "web_search"),

    # ── DevOps ───────────────────────────────────────────────────────
    ("deploy", "use", "devops"),
    ("wdrożenie", "use", "devops"),
    ("status systemu", "use", "devops"),
    ("restart usługi", "use", "devops"),
    ("check service", "use", "devops"),
    ("Dienst neustarten", "use", "devops"),
    ("état du service", "use", "devops"),
    ("stato del servizio", "use", "devops"),

    # ── Git ops ──────────────────────────────────────────────────────
    ("commit", "use", "git_ops"),
    ("push", "use", "git_ops"),
    ("pull", "use", "git_ops"),
    ("status gita", "use", "git_ops"),
    ("zacommituj", "use", "git_ops"),
    ("wypchnij", "use", "git_ops"),
    ("ściągnij zmiany", "use", "git_ops"),

    # ── Deps / dependencies ──────────────────────────────────────────
    ("zainstaluj", "use", "deps"),
    ("doinstaluj", "use", "deps"),
    ("dodaj paczkę", "use", "deps"),
    ("install", "use", "deps"),
    ("requirements", "use", "deps"),
    ("dependencies", "use", "deps"),
    ("installiere", "use", "deps"),
    ("installe", "use", "deps"),
    ("instala", "use", "deps"),

    # ── Skill evolution ──────────────────────────────────────────────
    # English
    ("fix", "evolve", ""),
    ("repair", "evolve", ""),
    ("improve", "evolve", ""),
    # Polish
    ("napraw", "evolve", ""),
    ("popraw", "evolve", ""),
    ("ulepsz", "evolve", ""),
    # German
    ("repariere", "evolve", ""),
    ("verbessere", "evolve", ""),
    # French
    ("répare", "evolve", ""),
    ("améliore", "evolve", ""),
    # Spanish
    ("repara", "evolve", ""),
    ("mejora", "evolve", ""),
    # Italian
    ("ripara", "evolve", ""),
    ("migliora", "evolve", ""),
    # Portuguese
    ("repara", "evolve", ""),
    ("melhora", "evolve", ""),
    # Czech
    ("oprav", "evolve", ""),
    ("vylepši", "evolve", ""),
    # Ukrainian
    ("виправ", "evolve", ""),
    ("покращ", "evolve", ""),
    # Russian
    ("исправь", "evolve", ""),
    ("улучши", "evolve", ""),
    # Romanian
    ("repară", "evolve", ""),
    ("îmbunătățește", "evolve", ""),
    # Hungarian
    ("javítsd", "evolve", ""),
    ("fejleszd", "evolve", ""),
    # Finnish
    ("korjaa", "evolve", ""),
    ("paranna", "evolve", ""),
    # Greek
    ("διόρθωσε", "evolve", ""),
    ("βελτίωσε", "evolve", ""),
    # Turkish
    ("onar", "evolve", ""),
    ("iyileştir", "evolve", ""),
    ("düzelt", "evolve", ""),

    # ── Skill creation ───────────────────────────────────────────────
    # English
    ("create skill", "create", ""),
    ("new skill", "create", ""),
    ("build skill", "create", ""),
    ("write program", "create", ""),
    ("build application", "create", ""),
    # Polish
    ("stwórz skill", "create", ""),
    ("nowy skill", "create", ""),
    ("zbuduj", "create", ""),
    ("utwórz", "create", ""),
    ("napisz program", "create", ""),
    ("zbuduj aplikację", "create", ""),
    ("stwórz program", "create", ""),
    ("napisz kod", "create", ""),
    ("zbuduj system", "create", ""),
    ("utwórz aplikację", "create", ""),
    # German
    ("skill erstellen", "create", ""),
    ("neuer skill", "create", ""),
    ("programm schreiben", "create", ""),
    # French
    ("créer skill", "create", ""),
    ("nouveau skill", "create", ""),
    ("écrire programme", "create", ""),
    # Spanish
    ("crear skill", "create", ""),
    ("nuevo skill", "create", ""),
    ("escribir programa", "create", ""),
    # Italian
    ("crea skill", "create", ""),
    ("nuovo skill", "create", ""),
    ("scrivi programma", "create", ""),
    # Portuguese
    ("criar skill", "create", ""),
    ("novo skill", "create", ""),
    # Dutch
    ("skill maken", "create", ""),
    ("nieuwe skill", "create", ""),
    # Czech
    ("vytvoř skill", "create", ""),
    ("nový skill", "create", ""),
    # Ukrainian
    ("створи скіл", "create", ""),
    ("новий скіл", "create", ""),
    ("напиши програму", "create", ""),
    # Russian
    ("создай скилл", "create", ""),
    ("новый скилл", "create", ""),
    ("напиши программу", "create", ""),
    # Romanian
    ("creează skill", "create", ""),
    ("skill nou", "create", ""),
    # Hungarian
    ("készíts skillt", "create", ""),
    ("új skill", "create", ""),
    # Finnish
    ("luo taito", "create", ""),
    ("uusi taito", "create", ""),
    # Greek
    ("δημιούργησε skill", "create", ""),
    ("φτιάξε skill", "create", ""),
    # Turkish
    ("skill oluştur", "create", ""),
    ("yeni skill", "create", ""),
    ("program yaz", "create", ""),

    # ── Echo (test skill) ────────────────────────────────────────────
    ("echo", "use", "echo"),
    ("test echo", "use", "echo"),
    ("przetestuj echo", "use", "echo"),
    ("ping", "use", "echo"),

    # ── Shell / bash ─────────────────────────────────────────────────
    # English
    ("run command", "use", "shell"),
    ("execute", "use", "shell"),
    ("bash", "use", "shell"),
    ("terminal", "use", "shell"),
    # Polish
    ("uruchom", "use", "shell"),
    ("wykonaj", "use", "shell"),
    # German
    ("befehl ausführen", "use", "shell"),
    ("starte", "use", "shell"),
    # French
    ("exécute", "use", "shell"),
    ("lance la commande", "use", "shell"),
    # Spanish
    ("ejecuta", "use", "shell"),
    ("comando", "use", "shell"),
    # Italian
    ("esegui", "use", "shell"),
    ("lancia", "use", "shell"),
    # Czech
    ("spusť příkaz", "use", "shell"),
    # Ukrainian
    ("запусти команду", "use", "shell"),
    # Russian
    ("запусти команду", "use", "shell"),
    ("выполни команду", "use", "shell"),
    # Turkish
    ("komutu çalıştır", "use", "shell"),

    # ── Network info ─────────────────────────────────────────────────
    ("jaki mam adres ip", "use", "network_info"),
    ("pokaż mac", "use", "network_info"),
    ("jaki numer ip", "use", "network_info"),
    ("adres mac urządzenia", "use", "network_info"),
    ("pokaż ip i mac", "use", "network_info"),
    ("show my ip address", "use", "network_info"),
    ("zeige meine IP-Adresse", "use", "network_info"),
    ("montre mon adresse IP", "use", "network_info"),
    ("muestra mi dirección IP", "use", "network_info"),

    # ── Time ─────────────────────────────────────────────────────────
    # Polish
    ("która jest godzina", "use", "time"),
    ("jaki mamy czas", "use", "time"),
    ("podaj datę", "use", "time"),
    ("ile jest godzin", "use", "time"),
    ("pokaż czas", "use", "time"),
    # English
    ("what time is it", "use", "time"),
    ("current time", "use", "time"),
    # German
    ("wie spät ist es", "use", "time"),
    ("aktuelle Uhrzeit", "use", "time"),
    # French
    ("quelle heure est-il", "use", "time"),
    # Spanish
    ("qué hora es", "use", "time"),
    # Russian
    ("который час", "use", "time"),
    # Turkish
    ("saat kaç", "use", "time"),

    # ── Configure / settings ─────────────────────────────────────────
    # English
    ("set as default", "configure", "llm"),
    ("change model", "configure", "llm"),
    ("switch to model", "configure", "llm"),
    ("use model", "configure", "llm"),
    ("set default LLM", "configure", "llm"),
    ("settings", "configure", ""),
    ("configure", "configure", ""),
    # Polish
    ("ustaw jako domyślny", "configure", "llm"),
    ("ustaw model", "configure", "llm"),
    ("zmień model", "configure", "llm"),
    ("zmień domyślny LLM", "configure", "llm"),
    ("ustaw domyślny model", "configure", "llm"),
    ("przełącz na model", "configure", "llm"),
    ("użyj modelu", "configure", "llm"),
    ("model LLM", "configure", "llm"),
    ("zmień ustawienia", "configure", ""),
    ("konfiguracja", "configure", ""),
    ("ustawienia", "configure", ""),
    # German
    ("als standard setzen", "configure", "llm"),
    ("modell ändern", "configure", "llm"),
    ("wechsle zu", "configure", "llm"),
    ("konfiguriere", "configure", ""),
    ("Einstellungen", "configure", ""),
    # French
    ("changer le modèle", "configure", "llm"),
    ("définir par défaut", "configure", "llm"),
    ("configurer", "configure", ""),
    ("paramètres", "configure", ""),
    # Spanish
    ("cambiar modelo", "configure", "llm"),
    ("establecer por defecto", "configure", "llm"),
    ("configurar", "configure", ""),
    ("ajustes", "configure", ""),
    # Italian
    ("cambia modello", "configure", "llm"),
    ("imposta come predefinito", "configure", "llm"),
    ("configura", "configure", ""),
    # Russian
    ("смени модель", "configure", "llm"),
    ("установи по умолчанию", "configure", "llm"),
    ("настройки", "configure", ""),
    # Turkish
    ("modeli değiştir", "configure", "llm"),
    ("varsayılan olarak ayarla", "configure", "llm"),
    ("ayarlar", "configure", ""),
]
