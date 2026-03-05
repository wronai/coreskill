#!/usr/bin/env python3
"""
i18n.py — Multilingual keyword and pattern database for all European languages.

Provides language-agnostic intent detection keywords, conversational patterns,
trivial words, and action verbs for ~30 European languages.

The SBERT model (paraphrase-multilingual-MiniLM-L12-v2) already handles
semantic similarity across languages. This module supplements it with
deterministic keyword matching for high-confidence fast paths.

Supported language families:
- Germanic: en, de, nl, sv, no, da, is
- Romance: fr, es, it, pt, ro, ca, gl
- Slavic: pl, cs, sk, uk, ru, bg, hr, sr, sl, be
- Baltic: lt, lv
- Finno-Ugric: fi, et, hu
- Other: el, sq, tr, ga, eu, mt
"""
from typing import Dict, FrozenSet, List, Set, Tuple
import re

# ─── Language codes ──────────────────────────────────────────────────
EUROPEAN_LANGUAGES = (
    "en", "de", "fr", "es", "it", "pt", "nl", "sv", "no", "da",
    "pl", "cs", "sk", "uk", "ru", "bg", "hr", "sr", "sl",
    "ro", "hu", "fi", "et", "lt", "lv", "el", "sq", "tr",
    "ca", "gl", "eu", "ga", "is", "be", "mt",
)

# ─── Diacritics normalization (all European) ─────────────────────────

def normalize_diacritics(text: str) -> str:
    """Normalize European diacritics to ASCII equivalents.
    Uses unicodedata NFD decomposition + special-case handling."""
    import unicodedata
    # NFD decomposition strips most accents
    nfkd = unicodedata.normalize("NFKD", text.lower())
    # Remove combining marks (accents, cedillas, etc.)
    ascii_approx = "".join(
        c for c in nfkd if unicodedata.category(c) != "Mn"
    )
    # Handle special characters that NFD doesn't decompose
    _SPECIAL = str.maketrans({
        "ł": "l", "Ł": "L",
        "đ": "d", "Đ": "D",
        "ð": "d", "Ð": "D",
        "þ": "th", "Þ": "Th",
        "ß": "ss",
        "æ": "ae", "Æ": "AE",
        "œ": "oe", "Œ": "OE",
        "ø": "o", "Ø": "O",
        "ı": "i", "İ": "I",
    })
    return ascii_approx.translate(_SPECIAL)


# ─── TTS keywords (per language) ────────────────────────────────────
TTS_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "en": ("speak", "say", "read aloud", "tell me", "pronounce", "read out"),
    "de": ("sprich", "sag", "vorlesen", "lies vor", "aussprechen", "erzähl"),
    "fr": ("parle", "dis", "lis à voix haute", "prononce", "récite", "dis-moi"),
    "es": ("habla", "di", "lee en voz alta", "pronuncia", "dime", "recita", "háblame"),
    "it": ("parla", "di'", "leggi ad alta voce", "pronuncia", "dimmi", "recita"),
    "pt": ("fala", "diz", "lê em voz alta", "pronuncia", "diz-me", "recita"),
    "nl": ("spreek", "zeg", "lees voor", "vertel", "uitspreek"),
    "sv": ("tala", "säg", "läs högt", "berätta", "uttala"),
    "no": ("snakk", "si", "les høyt", "fortell", "uttal"),
    "da": ("tal", "sig", "læs højt", "fortæl", "udtale"),
    "pl": ("powiedz", "wypowiedz", "przeczytaj", "mów", "odczytaj", "wymów"),
    "cs": ("řekni", "vyslov", "přečti", "mluv", "čti nahlas", "pověz"),
    "sk": ("povedz", "vyslov", "prečítaj", "hovor", "čítaj nahlas"),
    "uk": ("скажи", "вимов", "прочитай", "говори", "озвуч"),
    "ru": ("скажи", "произнеси", "прочитай", "говори", "озвучь"),
    "bg": ("кажи", "произнеси", "прочети", "говори", "озвучи"),
    "hr": ("reci", "izgovori", "pročitaj", "govori", "čitaj naglas"),
    "sr": ("реци", "изговори", "прочитај", "говори", "читај наглас"),
    "sl": ("reci", "izgovori", "preberi", "govori", "preberi naglas"),
    "ro": ("spune", "pronunță", "citește cu voce tare", "vorbește", "citește tare"),
    "hu": ("mondd", "mondd ki", "olvasd fel", "beszélj", "ejts ki"),
    "fi": ("puhu", "sano", "lue ääneen", "kerro", "lausu"),
    "et": ("räägi", "ütle", "loe ette", "lausu", "ütle mulle"),
    "lt": ("sakyk", "ištark", "perskaityk", "kalbėk", "perskaityk garsiai"),
    "lv": ("saki", "izrunā", "lasi skaļi", "runā", "nolasi"),
    "el": ("πες", "μίλα", "διάβασε", "προφέρω", "πες μου"),
    "sq": ("thuaj", "fol", "lexo", "shqipto", "thuaj më"),
    "tr": ("söyle", "konuş", "oku", "seslendir", "telaffuz et"),
    "ca": ("parla", "digues", "llegeix en veu alta", "pronuncia", "digues-me"),
    "gl": ("fala", "di", "le en voz alta", "pronuncia", "dime"),
    "eu": ("esan", "hitz egin", "irakurri ozen", "esan iezadazu"),
    "ga": ("abair", "labhair", "léigh os ard", "inis dom"),
    "is": ("segðu", "talaðu", "lestu upphátt", "segðu mér"),
    "be": ("скажы", "вымаві", "прачытай", "гавары"),
    "mt": ("għid", "tkellem", "aqra b'leħen għoli"),
}

# ─── STT keywords (per language) ────────────────────────────────────
STT_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "en": ("listen", "record", "transcribe", "dictate", "speech to text"),
    "de": ("höre", "aufnehmen", "transkribieren", "diktieren", "zuhören"),
    "fr": ("écoute", "enregistre", "transcrire", "dicte", "reconnaissance vocale"),
    "es": ("escucha", "graba", "transcribe", "dicta", "reconocimiento de voz"),
    "it": ("ascolta", "registra", "trascrivi", "detta", "riconoscimento vocale"),
    "pt": ("ouve", "grava", "transcreve", "dita", "reconhecimento de voz"),
    "nl": ("luister", "opnemen", "transcribeer", "dicteer"),
    "sv": ("lyssna", "spela in", "transkribera", "diktera"),
    "no": ("lytt", "ta opp", "transkriber", "dikter"),
    "da": ("lyt", "optag", "transskriber", "dikter"),
    "pl": ("słuchaj", "nagrywaj", "zapisz co mówię", "transkrybuj", "rozpoznaj mowę"),
    "cs": ("poslouchej", "nahrávej", "přepiš", "diktuj", "rozpoznej řeč"),
    "sk": ("počúvaj", "nahrávaj", "prepíš", "diktuj", "rozpoznaj reč"),
    "uk": ("слухай", "записуй", "транскрибуй", "диктуй", "розпізнай мову"),
    "ru": ("слушай", "записывай", "транскрибируй", "диктуй", "распознай речь"),
    "bg": ("слушай", "записвай", "транскрибирай", "диктувай"),
    "hr": ("slušaj", "snimaj", "transkribiraj", "diktiraj"),
    "sr": ("слушај", "снимај", "транскрибуј", "диктирај"),
    "sl": ("poslušaj", "snemaj", "prepiši", "diktiraj"),
    "ro": ("ascultă", "înregistrează", "transcrie", "dictează"),
    "hu": ("hallgass", "rögzíts", "átírás", "diktálj"),
    "fi": ("kuuntele", "nauhoita", "litteroi", "sanele"),
    "et": ("kuula", "salvesta", "transkribeeri", "dikteeri"),
    "lt": ("klausyk", "įrašyk", "transkribuok", "diktuok"),
    "lv": ("klausies", "ieraksti", "transkribē", "diktē"),
    "el": ("άκου", "ηχογράφησε", "μεταγραφή", "υπαγόρευσε"),
    "sq": ("dëgjo", "regjistro", "transkibo", "dikto"),
    "tr": ("dinle", "kaydet", "yazıya dök", "dikte et"),
    "ca": ("escolta", "enregistra", "transcriu", "dicta"),
    "gl": ("escoita", "grava", "transcribe", "dita"),
    "eu": ("entzun", "grabatu", "transkribatu", "diktatu"),
    "ga": ("éist", "taifead", "tras-scríobh"),
    "is": ("hlustaðu", "taktu upp", "umritaðu"),
    "be": ("слухай", "запісвай", "транскрыбуй", "дыктуй"),
    "mt": ("isma'", "irrekordja", "ittrasskrivi"),
}

# ─── Voice mode keywords ────────────────────────────────────────────
VOICE_MODE_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "en": ("voice mode", "let's talk", "voice conversation", "talk to me"),
    "de": ("sprachmodus", "lass uns reden", "sprachgespräch", "sprich mit mir"),
    "fr": ("mode vocal", "parlons", "conversation vocale", "parle-moi"),
    "es": ("modo voz", "hablemos", "conversación de voz", "hablamos"),
    "it": ("modalità vocale", "parliamo", "conversazione vocale", "parlami"),
    "pt": ("modo voz", "vamos conversar", "conversa por voz", "fala comigo"),
    "nl": ("spraak modus", "laten we praten", "spraakgesprek", "praat met me"),
    "sv": ("röstläge", "låt oss prata", "röstsamtal", "prata med mig"),
    "no": ("stemme modus", "la oss snakke", "stemmesamtale", "snakk med meg"),
    "da": ("stemme tilstand", "lad os tale", "stemmesamtale", "tal med mig"),
    "pl": ("porozmawiajmy głosowo", "pogadajmy głosem", "włącz tryb głosowy", "tryb głosowy"),
    "cs": ("hlasový režim", "pojďme si povídat", "hlasový rozhovor"),
    "sk": ("hlasový režim", "porozprávajme sa", "hlasový rozhovor"),
    "uk": ("голосовий режим", "поговоримо", "голосова розмова"),
    "ru": ("голосовой режим", "давай поговорим", "голосовой разговор"),
    "bg": ("гласов режим", "нека поговорим", "гласов разговор"),
    "hr": ("glasovni način", "razgovarajmo", "glasovni razgovor"),
    "sr": ("гласовни режим", "разговарајмо", "гласовни разговор"),
    "sl": ("glasovni način", "pogovoriva se", "glasovni pogovor"),
    "ro": ("mod vocal", "hai să vorbim", "conversație vocală"),
    "hu": ("hangos mód", "beszélgessünk", "hangbeszélgetés"),
    "fi": ("äänitila", "puhutaan", "äänikeskustelu"),
    "et": ("häälrežiim", "räägime", "häälvestlus"),
    "lt": ("balso režimas", "pakalbėkime", "balso pokalbis"),
    "lv": ("balss režīms", "parunāsimies", "balss saruna"),
    "el": ("φωνητική λειτουργία", "ας μιλήσουμε", "φωνητική συνομιλία"),
    "sq": ("modaliteti i zërit", "le të flasim", "bisedë me zë"),
    "tr": ("sesli mod", "konuşalım", "sesli konuşma"),
    "ca": ("mode de veu", "parlem", "conversa de veu"),
    "gl": ("modo de voz", "falemos", "conversa de voz"),
    "eu": ("ahots modua", "hitz egin dezagun"),
    "ga": ("modh gutha", "labhraímis"),
    "is": ("raddstilling", "tölum saman"),
    "be": ("галасавы рэжым", "пагаворым"),
    "mt": ("modalità tal-vuċi", "ejja nitkellmu"),
}

# ─── Web search keywords ─────────────────────────────────────────────
SEARCH_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "en": ("search", "find online", "look up", "google", "browse"),
    "de": ("suche", "suchen", "finde", "googeln", "nachschlagen", "durchsuchen"),
    "fr": ("cherche", "recherche", "trouve", "googler", "chercher en ligne"),
    "es": ("busca", "buscar", "encuentra", "googlear", "buscar en línea"),
    "it": ("cerca", "ricerca", "trova", "cercare online", "googla"),
    "pt": ("procura", "pesquisa", "encontra", "buscar online", "googlar"),
    "nl": ("zoek", "zoeken", "vind", "googelen", "opzoeken"),
    "sv": ("sök", "leta", "hitta", "googla", "slå upp"),
    "no": ("søk", "finn", "google", "slå opp"),
    "da": ("søg", "find", "google", "slå op"),
    "pl": ("wyszukaj", "szukaj", "znajdź w internecie", "przeszukaj", "google"),
    "cs": ("hledej", "vyhledej", "najdi", "prohledej", "google"),
    "sk": ("hľadaj", "vyhľadaj", "nájdi", "prehľadaj"),
    "uk": ("шукай", "знайди", "пошук", "гугли"),
    "ru": ("ищи", "найди", "поиск", "гугли", "найди в интернете"),
    "bg": ("търси", "намери", "потърси", "гугъл"),
    "hr": ("traži", "pronađi", "pretraži", "guglaj"),
    "sr": ("тражи", "пронађи", "претражи"),
    "sl": ("išči", "najdi", "poišči", "guglaj"),
    "ro": ("caută", "găsește", "cercetează", "google"),
    "hu": ("keress", "keresd meg", "találd meg", "guglizz"),
    "fi": ("etsi", "hae", "googlaa", "löydä"),
    "et": ("otsi", "leia", "googelda"),
    "lt": ("ieškok", "surask", "paieška", "googlink"),
    "lv": ("meklē", "atrodi", "googlē"),
    "el": ("ψάξε", "αναζήτησε", "βρες", "γκούγκλαρε"),
    "sq": ("kërko", "gjej", "kërkim"),
    "tr": ("ara", "bul", "google'la", "araştır"),
    "ca": ("cerca", "busca", "troba", "google"),
    "gl": ("busca", "procura", "atopa", "google"),
    "eu": ("bilatu", "aurkitu"),
    "ga": ("cuardaigh", "aimsigh"),
    "is": ("leitaðu", "finndu", "googlaðu"),
    "be": ("шукай", "знайдзі", "пашук", "гугли"),
    "mt": ("fittex", "sib"),
}

# ─── Shell / command execution keywords ──────────────────────────────
SHELL_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "en": ("run command", "execute", "run", "terminal", "bash", "shell", "sudo", "apt", "pip install", "docker"),
    "de": ("befehl ausführen", "ausführen", "terminal", "starte"),
    "fr": ("exécute", "lance", "terminal", "commande"),
    "es": ("ejecuta", "lanza", "terminal", "comando"),
    "it": ("esegui", "lancia", "terminale", "comando"),
    "pt": ("execute", "rode", "terminal", "comando"),
    "nl": ("voer uit", "draai", "terminal", "commando"),
    "sv": ("kör", "utför", "terminal", "kommando"),
    "no": ("kjør", "utfør", "terminal", "kommando"),
    "da": ("kør", "udfør", "terminal", "kommando"),
    "pl": ("uruchom", "wykonaj", "terminal", "bash"),
    "cs": ("spusť", "proveď", "terminál", "příkaz"),
    "sk": ("spusti", "vykonaj", "terminál", "príkaz"),
    "uk": ("запусти", "виконай", "термінал", "команда"),
    "ru": ("запусти", "выполни", "терминал", "команда"),
    "bg": ("стартирай", "изпълни", "терминал", "команда"),
    "hr": ("pokreni", "izvrši", "terminal", "naredba"),
    "sr": ("покрени", "изврши", "терминал", "команда"),
    "sl": ("zaženi", "izvedi", "terminal", "ukaz"),
    "ro": ("rulează", "execută", "terminal", "comandă"),
    "hu": ("futtasd", "hajtsd végre", "terminál", "parancs"),
    "fi": ("suorita", "aja", "terminaali", "komento"),
    "et": ("käivita", "teosta", "terminal", "käsk"),
    "lt": ("paleisk", "vykdyk", "terminalas", "komanda"),
    "lv": ("palaid", "izpildi", "terminālis", "komanda"),
    "el": ("εκτέλεσε", "τρέξε", "τερματικό", "εντολή"),
    "sq": ("ekzekuto", "nis", "terminal", "komandë"),
    "tr": ("çalıştır", "yürüt", "terminal", "komut"),
    "ca": ("executa", "llança", "terminal", "comanda"),
    "gl": ("executa", "lanza", "terminal", "comando"),
    "eu": ("exekutatu", "abiarazi", "terminal"),
    "ga": ("rith", "forghníomhaigh", "teirminéal"),
    "is": ("keyrðu", "framkvæmdu", "skipanir"),
    "be": ("запусці", "выканай", "тэрмінал", "каманда"),
    "mt": ("mexxi", "itterminal"),
}

# ─── Create skill keywords ──────────────────────────────────────────
CREATE_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "en": ("create skill", "new skill", "build skill", "make skill", "write program", "build app"),
    "de": ("skill erstellen", "neuer skill", "skill bauen", "programm schreiben", "app bauen"),
    "fr": ("créer skill", "nouveau skill", "construire skill", "écrire programme", "créer application"),
    "es": ("crear skill", "nuevo skill", "construir skill", "escribir programa", "crear aplicación"),
    "it": ("crea skill", "nuovo skill", "costruisci skill", "scrivi programma", "crea applicazione"),
    "pt": ("criar skill", "novo skill", "construir skill", "escrever programa", "criar aplicação"),
    "nl": ("skill maken", "nieuwe skill", "skill bouwen", "programma schrijven"),
    "sv": ("skapa skill", "ny skill", "bygga skill", "skriv program"),
    "no": ("lag skill", "ny skill", "bygg skill", "skriv program"),
    "da": ("opret skill", "ny skill", "byg skill", "skriv program"),
    "pl": ("stwórz", "stwórz skill", "nowy skill", "zbuduj skill", "napisz program", "zbuduj aplikację", "stwórz program", "utwórz"),
    "cs": ("vytvoř skill", "nový skill", "postav skill", "napiš program"),
    "sk": ("vytvor skill", "nový skill", "postav skill", "napíš program"),
    "uk": ("створи скіл", "новий скіл", "побудуй скіл", "напиши програму"),
    "ru": ("создай скилл", "новый скилл", "построй скилл", "напиши программу"),
    "bg": ("създай скил", "нов скил", "построй скил", "напиши програма"),
    "hr": ("stvori skill", "novi skill", "napravi skill", "napiši program"),
    "sr": ("направи скил", "нови скил", "направи програм"),
    "sl": ("ustvari skill", "nov skill", "zgradi skill", "napiši program"),
    "ro": ("creează skill", "skill nou", "construiește skill", "scrie program"),
    "hu": ("készíts skillt", "új skill", "építs skillt", "írj programot"),
    "fi": ("luo taito", "uusi taito", "rakenna taito", "kirjoita ohjelma"),
    "et": ("loo oskus", "uus oskus", "ehita oskus", "kirjuta programm"),
    "lt": ("sukurk skill", "naujas skill", "parašyk programą"),
    "lv": ("izveido skill", "jauns skill", "uzraksti programmu"),
    "el": ("δημιούργησε skill", "νέο skill", "φτιάξε skill", "γράψε πρόγραμμα"),
    "sq": ("krijo skill", "skill i ri", "ndërto skill", "shkruaj program"),
    "tr": ("skill oluştur", "yeni skill", "skill yap", "program yaz"),
    "ca": ("crea skill", "nou skill", "construeix skill", "escriu programa"),
    "gl": ("crea skill", "novo skill", "constrúe skill", "escribe programa"),
    "eu": ("sortu skill", "skill berria"),
    "ga": ("cruthaigh scil", "scil nua"),
    "is": ("búðu til skill", "nýtt skill"),
    "be": ("ствары скіл", "новы скіл", "напішы праграму"),
    "mt": ("oħloq skill", "skill ġdid"),
}

# ─── Evolve / fix keywords ──────────────────────────────────────────
EVOLVE_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "en": ("fix", "repair", "improve", "evolve", "upgrade", "enhance"),
    "de": ("repariere", "verbessere", "behebe", "aktualisiere", "erweitere"),
    "fr": ("répare", "améliore", "corrige", "évolue", "mets à jour"),
    "es": ("repara", "mejora", "arregla", "corrige", "evoluciona"),
    "it": ("ripara", "migliora", "correggi", "evolvi", "aggiorna"),
    "pt": ("repara", "melhora", "corrige", "evolui", "atualiza"),
    "nl": ("repareer", "verbeter", "herstel", "verbeterd", "upgrade"),
    "sv": ("reparera", "förbättra", "fixa", "uppgradera"),
    "no": ("reparer", "forbedre", "fiks", "oppgrader"),
    "da": ("reparer", "forbedre", "fiks", "opgrader"),
    "pl": ("napraw", "popraw", "ulepsz", "ewoluuj", "zaktualizuj"),
    "cs": ("oprav", "vylepši", "zlepši", "aktualizuj"),
    "sk": ("oprav", "vylepši", "zlepši", "aktualizuj"),
    "uk": ("виправ", "покращ", "вдосконал", "оновиш"),
    "ru": ("исправь", "улучши", "почини", "обнови"),
    "bg": ("поправи", "подобри", "оправи", "обнови"),
    "hr": ("popravi", "poboljšaj", "ažuriraj"),
    "sr": ("поправи", "побољшај", "ажурирај"),
    "sl": ("popravi", "izboljšaj", "posodobi"),
    "ro": ("repară", "îmbunătățește", "corectează", "actualizează"),
    "hu": ("javítsd", "fejleszd", "frissítsd", "tökéletesítsd"),
    "fi": ("korjaa", "paranna", "päivitä"),
    "et": ("paranda", "parenda", "uuenda"),
    "lt": ("pataisyk", "pagerink", "atnaujink"),
    "lv": ("salabo", "uzlabo", "atjaunini"),
    "el": ("διόρθωσε", "βελτίωσε", "αναβάθμισε"),
    "sq": ("riparo", "përmirëso", "përditëso"),
    "tr": ("onar", "iyileştir", "düzelt", "güncelle"),
    "ca": ("repara", "millora", "corregeix", "actualitza"),
    "gl": ("repara", "mellora", "corrixe", "actualiza"),
    "eu": ("konpondu", "hobetu"),
    "ga": ("deisigh", "feabhsaigh"),
    "is": ("lagaðu", "bættu", "uppfærðu"),
    "be": ("выправ", "палепшы", "абнаві"),
    "mt": ("sewwi", "tejjeb", "aġġorna"),
}

# ─── Configure keywords ──────────────────────────────────────────────
CONFIGURE_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "en": ("set as default", "change model", "switch to", "use model", "set default", "configure"),
    "de": ("als standard setzen", "modell ändern", "wechsle zu", "verwende modell", "konfiguriere"),
    "fr": ("définir par défaut", "changer le modèle", "passer à", "utiliser le modèle", "configurer"),
    "es": ("establecer por defecto", "cambiar modelo", "cambiar a", "usar modelo", "configurar"),
    "it": ("imposta come predefinito", "cambia modello", "passa a", "usa modello", "configura"),
    "pt": ("definir como padrão", "mudar modelo", "mudar para", "usar modelo", "configurar"),
    "nl": ("als standaard instellen", "model wijzigen", "schakel naar", "gebruik model", "configureer"),
    "sv": ("ställ in som standard", "ändra modell", "byt till", "använd modell", "konfigurera"),
    "no": ("sett som standard", "endre modell", "bytt til", "bruk modell", "konfigurer"),
    "da": ("sæt som standard", "skift model", "skift til", "brug model", "konfigurer"),
    "pl": ("ustaw jako domyślny", "ustaw model", "zmień model", "przełącz na", "użyj modelu", "konfiguruj"),
    "cs": ("nastav jako výchozí", "změň model", "přepni na", "použij model", "konfiguruj"),
    "sk": ("nastav ako predvolený", "zmeň model", "prepni na", "použi model", "konfiguruj"),
    "uk": ("встанови за замовчуванням", "зміни модель", "переключи на", "використовуй модель"),
    "ru": ("установи по умолчанию", "смени модель", "переключи на", "используй модель", "настрой"),
    "bg": ("задай по подразбиране", "смени модел", "превключи на", "използвай модел"),
    "hr": ("postavi kao zadano", "promijeni model", "prebaci na", "koristi model"),
    "sr": ("постави као подразумевано", "промени модел", "пребаци на"),
    "sl": ("nastavi kot privzeto", "spremeni model", "preklopi na"),
    "ro": ("setează implicit", "schimbă modelul", "comută la", "folosește modelul", "configurează"),
    "hu": ("állítsd alapértelmezettnek", "változtasd a modellt", "válts modellt", "használd a modellt"),
    "fi": ("aseta oletukseksi", "vaihda malli", "vaihda malliin", "käytä mallia", "määritä"),
    "et": ("sea vaikimisi", "muuda mudelit", "lülitu", "kasuta mudelit", "seadista"),
    "lt": ("nustatyk kaip numatytąjį", "pakeisk modelį", "perjunk į"),
    "lv": ("iestatīt kā noklusējumu", "mainīt modeli", "pārslēgt uz"),
    "el": ("ορίσε ως προεπιλογή", "άλλαξε μοντέλο", "πήγαινε σε"),
    "sq": ("vendos si parazgjedhje", "ndrysho modelin", "kalo te"),
    "tr": ("varsayılan olarak ayarla", "modeli değiştir", "modele geç", "modeli kullan", "yapılandır"),
    "ca": ("estableix per defecte", "canvia model", "canvia a", "utilitza model", "configura"),
    "gl": ("establecer por defecto", "cambiar modelo", "cambiar a", "usar modelo", "configurar"),
    "eu": ("ezarri lehenetsi", "aldatu eredua"),
    "ga": ("socraigh mar réamhshocrú", "athraigh an múnla"),
    "is": ("settu sem sjálfgefið", "breyttu líkani", "skiptu yfir í"),
    "be": ("усталюй па змаўчанні", "змяні мадэль", "пераключы на"),
    "mt": ("issettja bħala default", "biddel il-mudell"),
}

# ─── Conversational / greeting patterns ──────────────────────────────
GREETING_PATTERNS: Dict[str, Tuple[str, ...]] = {
    "en": ("hi", "hello", "hey", "greetings", "good morning", "good evening", "good afternoon"),
    "de": ("hallo", "hi", "guten morgen", "guten tag", "guten abend", "grüß gott", "servus", "moin"),
    "fr": ("salut", "bonjour", "bonsoir", "coucou", "bonne journée"),
    "es": ("hola", "buenos días", "buenas tardes", "buenas noches", "qué tal"),
    "it": ("ciao", "buongiorno", "buonasera", "buona notte", "salve"),
    "pt": ("olá", "oi", "bom dia", "boa tarde", "boa noite"),
    "nl": ("hoi", "hallo", "goedemorgen", "goedemiddag", "goedenavond"),
    "sv": ("hej", "hallå", "god morgon", "god kväll"),
    "no": ("hei", "hallo", "god morgen", "god kveld"),
    "da": ("hej", "godmorgen", "godaften"),
    "pl": ("cześć", "hej", "witaj", "siema", "dzień dobry", "dobry wieczór"),
    "cs": ("ahoj", "dobrý den", "čau", "dobré ráno", "dobrý večer"),
    "sk": ("ahoj", "dobrý deň", "čau", "dobré ráno", "dobrý večer"),
    "uk": ("привіт", "здоров", "доброго ранку", "добрий день", "добрий вечір"),
    "ru": ("привет", "здравствуйте", "доброе утро", "добрый день", "добрый вечер"),
    "bg": ("здравей", "добро утро", "добър ден", "добър вечер"),
    "hr": ("bok", "dobar dan", "dobro jutro", "dobra večer", "zdravo"),
    "sr": ("здраво", "добар дан", "добро јутро", "добро вече"),
    "sl": ("živjo", "dober dan", "dobro jutro", "dober večer"),
    "ro": ("bună", "salut", "bună dimineața", "bună ziua", "bună seara"),
    "hu": ("szia", "helló", "jó reggelt", "jó napot", "jó estét"),
    "fi": ("hei", "moi", "huomenta", "hyvää päivää", "hyvää iltaa"),
    "et": ("tere", "hei", "tere hommikust", "tere õhtust"),
    "lt": ("sveiki", "labas", "labas rytas", "labas vakaras", "sveikas"),
    "lv": ("sveiki", "labdien", "labrīt", "labvakar"),
    "el": ("γεια", "καλημέρα", "καλησπέρα", "γεια σου"),
    "sq": ("përshëndetje", "mirëdita", "mirëmëngjesi", "mirëmbrëma"),
    "tr": ("merhaba", "selam", "günaydın", "iyi akşamlar", "iyi günler"),
    "ca": ("hola", "bon dia", "bona tarda", "bona nit"),
    "gl": ("ola", "bo día", "boa tarde", "boa noite"),
    "eu": ("kaixo", "egun on", "arratsalde on", "gabon"),
    "ga": ("dia duit", "maidin mhaith", "tráthnóna maith"),
    "is": ("halló", "góðan dag", "góða kvöldið"),
    "be": ("прывітанне", "добры дзень", "добрай раніцы"),
    "mt": ("bongu", "il-lejla t-tajba", "merħba"),
}

# ─── Farewell patterns ───────────────────────────────────────────────
FAREWELL_PATTERNS: Dict[str, Tuple[str, ...]] = {
    "en": ("bye", "goodbye", "see you", "later", "take care"),
    "de": ("tschüss", "auf wiedersehen", "bis dann", "bis bald", "mach's gut"),
    "fr": ("au revoir", "salut", "à bientôt", "à plus"),
    "es": ("adiós", "hasta luego", "nos vemos", "chao"),
    "it": ("arrivederci", "ciao", "a presto", "a dopo"),
    "pt": ("tchau", "adeus", "até logo", "até breve"),
    "nl": ("doei", "tot ziens", "tot later"),
    "sv": ("hejdå", "adjö", "vi ses"),
    "no": ("ha det", "adjø", "vi ses"),
    "da": ("farvel", "vi ses", "hej hej"),
    "pl": ("pa", "do widzenia", "na razie", "cześć", "do zobaczenia"),
    "cs": ("sbohem", "na shledanou", "ahoj", "čau"),
    "sk": ("dovidenia", "ahoj", "čau", "zbohom"),
    "uk": ("бувай", "до побачення", "пока"),
    "ru": ("пока", "до свидания", "до встречи"),
    "bg": ("довиждане", "чао", "до скоро"),
    "hr": ("bok", "doviđenja", "vidimo se"),
    "sr": ("ћао", "довиђења", "видимо се"),
    "sl": ("adijo", "nasvidenje", "se vidimo"),
    "ro": ("la revedere", "pa", "pe curând"),
    "hu": ("viszlát", "szia", "viszontlátásra"),
    "fi": ("näkemiin", "hei hei", "moikka"),
    "et": ("nägemist", "head aega"),
    "lt": ("viso gero", "iki", "sudie"),
    "lv": ("ardievu", "uz redzēšanos"),
    "el": ("αντίο", "γεια", "τα λέμε"),
    "sq": ("mirupafshim", "shihemi"),
    "tr": ("hoşça kal", "görüşürüz", "güle güle"),
    "ca": ("adéu", "fins aviat"),
    "gl": ("adeus", "ata logo"),
    "eu": ("agur", "gero arte"),
    "ga": ("slán", "feicfidh mé thú"),
    "is": ("bless", "sjáumst"),
    "be": ("бывай", "да пабачэння"),
    "mt": ("sahha", "narak"),
}

# ─── Thanks / acknowledgment patterns ────────────────────────────────
THANKS_PATTERNS: Dict[str, Tuple[str, ...]] = {
    "en": ("thanks", "thank you", "ok", "okay", "sure", "great", "fine", "got it", "understood"),
    "de": ("danke", "dankeschön", "ok", "gut", "verstanden", "alles klar", "super"),
    "fr": ("merci", "ok", "d'accord", "compris", "bien", "super", "entendu"),
    "es": ("gracias", "ok", "vale", "entendido", "bien", "genial", "perfecto"),
    "it": ("grazie", "ok", "va bene", "capito", "bene", "perfetto"),
    "pt": ("obrigado", "obrigada", "ok", "entendido", "bem", "ótimo"),
    "nl": ("bedankt", "dank je", "ok", "begrepen", "goed", "prima"),
    "sv": ("tack", "ok", "förstått", "bra", "fint"),
    "no": ("takk", "ok", "forstått", "bra", "fint"),
    "da": ("tak", "ok", "forstået", "godt", "fint"),
    "pl": ("dzięki", "dziękuję", "ok", "okej", "dobrze", "super", "fajnie", "rozumiem"),
    "cs": ("díky", "děkuji", "ok", "dobře", "rozumím", "super", "fajn"),
    "sk": ("ďakujem", "ok", "dobre", "rozumiem", "super"),
    "uk": ("дякую", "ок", "добре", "зрозумів", "чудово"),
    "ru": ("спасибо", "ок", "хорошо", "понял", "отлично", "ладно"),
    "bg": ("благодаря", "ок", "добре", "разбрах", "чудесно"),
    "hr": ("hvala", "ok", "dobro", "razumijem", "super"),
    "sr": ("хвала", "ок", "добро", "разумем"),
    "sl": ("hvala", "ok", "dobro", "razumem", "super"),
    "ro": ("mulțumesc", "ok", "bine", "înțeles", "grozav"),
    "hu": ("köszönöm", "ok", "rendben", "értem", "szuper"),
    "fi": ("kiitos", "ok", "selvä", "hyvä", "ymmärsin"),
    "et": ("aitäh", "ok", "selge", "hästi", "sain aru"),
    "lt": ("ačiū", "ok", "gerai", "supratau"),
    "lv": ("paldies", "ok", "labi", "sapratu"),
    "el": ("ευχαριστώ", "εντάξει", "καλά", "κατάλαβα"),
    "sq": ("faleminderit", "ok", "mirë", "kuptova"),
    "tr": ("teşekkürler", "tamam", "anladım", "iyi", "süper"),
    "ca": ("gràcies", "d'acord", "entès", "bé", "genial"),
    "gl": ("grazas", "de acordo", "entendido", "ben"),
    "eu": ("eskerrik asko", "ados", "ondo", "ulertuta"),
    "ga": ("go raibh maith agat", "ok", "maith"),
    "is": ("takk", "ok", "allt í lagi", "flott"),
    "be": ("дзякуй", "ок", "добра", "зразумеў"),
    "mt": ("grazzi", "ok", "tajjeb", "fhimt"),
}

# ─── Question words (conversational detection) ──────────────────────
QUESTION_WORDS: Dict[str, Tuple[str, ...]] = {
    "en": ("what", "how", "where", "when", "why", "who", "is", "are", "do", "does", "can", "could"),
    "de": ("was", "wie", "wo", "wann", "warum", "wer", "ist", "sind", "kann", "könnte"),
    "fr": ("quoi", "comment", "où", "quand", "pourquoi", "qui", "est-ce"),
    "es": ("qué", "cómo", "dónde", "cuándo", "por qué", "quién"),
    "it": ("cosa", "come", "dove", "quando", "perché", "chi"),
    "pt": ("o que", "como", "onde", "quando", "por que", "quem"),
    "nl": ("wat", "hoe", "waar", "wanneer", "waarom", "wie"),
    "sv": ("vad", "hur", "var", "när", "varför", "vem"),
    "no": ("hva", "hvordan", "hvor", "når", "hvorfor", "hvem"),
    "da": ("hvad", "hvordan", "hvor", "hvornår", "hvorfor", "hvem"),
    "pl": ("co", "jak", "gdzie", "kiedy", "dlaczego", "czy", "kto"),
    "cs": ("co", "jak", "kde", "kdy", "proč", "kdo"),
    "sk": ("čo", "ako", "kde", "kedy", "prečo", "kto"),
    "uk": ("що", "як", "де", "коли", "чому", "хто"),
    "ru": ("что", "как", "где", "когда", "почему", "кто"),
    "bg": ("какво", "как", "къде", "кога", "защо", "кой"),
    "hr": ("što", "kako", "gdje", "kada", "zašto", "tko"),
    "sr": ("шта", "како", "где", "када", "зашто", "ко"),
    "sl": ("kaj", "kako", "kje", "kdaj", "zakaj", "kdo"),
    "ro": ("ce", "cum", "unde", "când", "de ce", "cine"),
    "hu": ("mi", "hogyan", "hol", "mikor", "miért", "ki"),
    "fi": ("mitä", "miten", "missä", "milloin", "miksi", "kuka"),
    "et": ("mis", "kuidas", "kus", "millal", "miks", "kes"),
    "lt": ("kas", "kaip", "kur", "kada", "kodėl"),
    "lv": ("kas", "kā", "kur", "kad", "kāpēc"),
    "el": ("τι", "πώς", "πού", "πότε", "γιατί", "ποιος"),
    "sq": ("çfarë", "si", "ku", "kur", "pse", "kush"),
    "tr": ("ne", "nasıl", "nerede", "ne zaman", "neden", "kim"),
    "ca": ("què", "com", "on", "quan", "per què", "qui"),
    "gl": ("que", "como", "onde", "cando", "por que", "quen"),
    "eu": ("zer", "nola", "non", "noiz", "zergatik", "nor"),
    "ga": ("cad", "conas", "cá", "cathain", "cén fáth", "cé"),
    "is": ("hvað", "hvernig", "hvar", "hvenær", "af hverju", "hver"),
    "be": ("што", "як", "дзе", "калі", "чаму", "хто"),
    "mt": ("x'inhu", "kif", "fejn", "meta", "għaliex", "min"),
}

# ─── Yes/No/Maybe words (trivial responses) ─────────────────────────
YES_NO_MAYBE: Dict[str, Tuple[str, ...]] = {
    "en": ("yes", "no", "maybe", "probably", "perhaps"),
    "de": ("ja", "nein", "vielleicht", "wahrscheinlich"),
    "fr": ("oui", "non", "peut-être", "probablement"),
    "es": ("sí", "no", "quizás", "tal vez", "probablemente"),
    "it": ("sì", "no", "forse", "probabilmente"),
    "pt": ("sim", "não", "talvez", "provavelmente"),
    "nl": ("ja", "nee", "misschien", "waarschijnlijk"),
    "sv": ("ja", "nej", "kanske", "förmodligen"),
    "no": ("ja", "nei", "kanskje", "sannsynligvis"),
    "da": ("ja", "nej", "måske", "sandsynligvis"),
    "pl": ("tak", "nie", "może", "chyba", "pewnie"),
    "cs": ("ano", "ne", "možná", "asi"),
    "sk": ("áno", "nie", "možno", "asi"),
    "uk": ("так", "ні", "може", "напевно"),
    "ru": ("да", "нет", "может", "наверное"),
    "bg": ("да", "не", "може би", "вероятно"),
    "hr": ("da", "ne", "možda", "vjerojatno"),
    "sr": ("да", "не", "можда", "вероватно"),
    "sl": ("da", "ne", "mogoče", "verjetno"),
    "ro": ("da", "nu", "poate", "probabil"),
    "hu": ("igen", "nem", "talán", "valószínűleg"),
    "fi": ("kyllä", "ei", "ehkä", "luultavasti"),
    "et": ("jah", "ei", "võib-olla", "tõenäoliselt"),
    "lt": ("taip", "ne", "gal", "galbūt"),
    "lv": ("jā", "nē", "varbūt", "iespējams"),
    "el": ("ναι", "όχι", "ίσως", "πιθανόν"),
    "sq": ("po", "jo", "ndoshta", "ndofta"),
    "tr": ("evet", "hayır", "belki", "muhtemelen"),
    "ca": ("sí", "no", "potser", "probablement"),
    "gl": ("si", "non", "quizais", "probablemente"),
    "eu": ("bai", "ez", "agian", "ziurrenik"),
    "ga": ("tá", "níl", "b'fhéidir"),
    "is": ("já", "nei", "kannski", "líklega"),
    "be": ("так", "не", "магчыма", "напэўна"),
    "mt": ("iva", "le", "forsi"),
}

# ─── Action verbs (for short-query detection) ────────────────────────
ACTION_VERBS: Dict[str, Tuple[str, ...]] = {
    "en": ("calculate", "run", "execute", "scan", "search", "install", "find", "check", "test", "deploy", "build", "create"),
    "de": ("berechne", "starte", "führe aus", "suche", "installiere", "finde", "prüfe", "teste", "baue", "erstelle"),
    "fr": ("calcule", "lance", "exécute", "cherche", "installe", "trouve", "vérifie", "teste", "construis", "crée"),
    "es": ("calcula", "ejecuta", "busca", "instala", "encuentra", "verifica", "prueba", "construye", "crea"),
    "it": ("calcola", "esegui", "cerca", "installa", "trova", "verifica", "testa", "costruisci", "crea"),
    "pt": ("calcula", "executa", "procura", "instala", "encontra", "verifica", "testa", "constrói", "cria"),
    "nl": ("bereken", "draai", "zoek", "installeer", "vind", "controleer", "test", "bouw", "maak"),
    "sv": ("beräkna", "kör", "sök", "installera", "hitta", "kontrollera", "testa", "bygg", "skapa"),
    "no": ("beregn", "kjør", "søk", "installer", "finn", "sjekk", "test", "bygg", "lag"),
    "da": ("beregn", "kør", "søg", "installer", "find", "tjek", "test", "byg", "opret"),
    "pl": ("policz", "oblicz", "uruchom", "wykonaj", "skanuj", "szukaj", "zainstaluj", "znajdź", "sprawdź", "testuj", "zbuduj", "stwórz"),
    "cs": ("spočítej", "spusť", "proveď", "hledej", "instaluj", "najdi", "zkontroluj", "testuj", "postav", "vytvoř"),
    "sk": ("spočítaj", "spusti", "vykonaj", "hľadaj", "inštaluj", "nájdi", "skontroluj", "testuj", "postav", "vytvor"),
    "uk": ("порахуй", "запусти", "виконай", "шукай", "встанови", "знайди", "перевір", "протестуй", "побудуй", "створи"),
    "ru": ("посчитай", "запусти", "выполни", "ищи", "установи", "найди", "проверь", "протестируй", "построй", "создай"),
    "bg": ("изчисли", "стартирай", "изпълни", "търси", "инсталирай", "намери", "провери", "тествай", "построй", "създай"),
    "hr": ("izračunaj", "pokreni", "izvrši", "traži", "instaliraj", "pronađi", "provjeri", "testiraj", "izgradi", "stvori"),
    "sr": ("израчунај", "покрени", "изврши", "тражи", "инсталирај", "пронађи", "провери"),
    "sl": ("izračunaj", "zaženi", "izvedi", "išči", "namesti", "najdi", "preveri", "testiraj", "zgradi", "ustvari"),
    "ro": ("calculează", "rulează", "execută", "caută", "instalează", "găsește", "verifică", "testează", "construiește", "creează"),
    "hu": ("számold", "futtasd", "hajtsd végre", "keress", "telepítsd", "találd", "ellenőrizd", "teszteld", "építsd", "készítsd"),
    "fi": ("laske", "suorita", "aja", "etsi", "asenna", "löydä", "tarkista", "testaa", "rakenna", "luo"),
    "et": ("arvuta", "käivita", "teosta", "otsi", "installi", "leia", "kontrolli", "testi", "ehita", "loo"),
    "lt": ("apskaičiuok", "paleisk", "vykdyk", "ieškok", "instaliuok", "surask", "patikrink", "testuok", "statyk", "sukurk"),
    "lv": ("aprēķini", "palaid", "izpildi", "meklē", "instalē", "atrodi", "pārbaudi", "testē", "būvē", "izveido"),
    "el": ("υπολόγισε", "εκτέλεσε", "τρέξε", "ψάξε", "εγκατάστησε", "βρες", "έλεγξε", "δοκίμασε", "χτίσε", "δημιούργησε"),
    "sq": ("llogarit", "ekzekuto", "nis", "kërko", "instalo", "gjej", "kontrollo", "testo", "ndërto", "krijo"),
    "tr": ("hesapla", "çalıştır", "yürüt", "ara", "kur", "bul", "kontrol et", "test et", "inşa et", "oluştur"),
    "ca": ("calcula", "executa", "cerca", "instal·la", "troba", "verifica", "prova", "construeix", "crea"),
    "gl": ("calcula", "executa", "busca", "instala", "atopa", "verifica", "proba", "constrúe", "crea"),
    "eu": ("kalkulatu", "exekutatu", "bilatu", "instalatu", "aurkitu", "egiaztatu", "probatu", "eraiki", "sortu"),
    "ga": ("ríomh", "rith", "cuardaigh", "suiteáil", "aimsigh", "seiceáil", "tástáil", "tóg", "cruthaigh"),
    "is": ("reiknaðu", "keyrðu", "leitaðu", "settu upp", "finndu", "athugaðu", "prófaðu", "byggðu", "búðu til"),
    "be": ("палічы", "запусці", "выканай", "шукай", "ўстанаві", "знайдзі", "праверь", "пратэстуй", "пабудуй", "ствары"),
    "mt": ("ikkalkula", "mexxi", "fittex", "installa", "sib", "iċċekkja", "ittestja", "ibni", "oħloq"),
}


# ─── Flattened helpers (for fast keyword lookup) ─────────────────────

def _flatten(d: Dict[str, Tuple[str, ...]]) -> FrozenSet[str]:
    """Flatten all language keywords into a single set."""
    result = set()
    for keywords in d.values():
        result.update(keywords)
    return frozenset(result)


# Pre-computed flat sets for fast `any(kw in text)` checks
ALL_TTS_KEYWORDS = _flatten(TTS_KEYWORDS)
ALL_STT_KEYWORDS = _flatten(STT_KEYWORDS)
ALL_VOICE_MODE_KEYWORDS = _flatten(VOICE_MODE_KEYWORDS)
ALL_SEARCH_KEYWORDS = _flatten(SEARCH_KEYWORDS)
ALL_SHELL_KEYWORDS = _flatten(SHELL_KEYWORDS)
ALL_CREATE_KEYWORDS = _flatten(CREATE_KEYWORDS)
ALL_EVOLVE_KEYWORDS = _flatten(EVOLVE_KEYWORDS)
ALL_CONFIGURE_KEYWORDS = _flatten(CONFIGURE_KEYWORDS)
ALL_GREETING_PATTERNS = _flatten(GREETING_PATTERNS)
ALL_FAREWELL_PATTERNS = _flatten(FAREWELL_PATTERNS)
ALL_THANKS_PATTERNS = _flatten(THANKS_PATTERNS)
ALL_QUESTION_WORDS = _flatten(QUESTION_WORDS)
ALL_YES_NO_MAYBE = _flatten(YES_NO_MAYBE)
ALL_ACTION_VERBS = _flatten(ACTION_VERBS)

# Trivial words — greetings + yes/no across all languages (for stage 0 filter)
ALL_TRIVIAL_WORDS: FrozenSet[str] = frozenset(
    set(w for tup in GREETING_PATTERNS.values() for w in tup if " " not in w)
    | set(w for tup in YES_NO_MAYBE.values() for w in tup)
    | set(w for tup in FAREWELL_PATTERNS.values() for w in tup if " " not in w)
    | {"ok", "hm", "ee", "hmm", "eee", "aha", "wow", "ej", "yo", "elo",
       "o", "a", "i", "no"}
)

# All conversational patterns combined (for SkillForge)
ALL_CONVERSATIONAL_GREETINGS = _flatten(GREETING_PATTERNS)
ALL_CONVERSATIONAL_FAREWELLS = _flatten(FAREWELL_PATTERNS)
ALL_CONVERSATIONAL_THANKS = _flatten(THANKS_PATTERNS)

# Create keywords flattened (for conversational override)
ALL_CREATE_KW_FLAT = _flatten(CREATE_KEYWORDS)


def match_any_keyword(text: str, keyword_set: FrozenSet[str]) -> bool:
    """Check if any keyword from the set appears in the text (case-insensitive).

    For keywords ≤ 3 chars, requires word-boundary matching to prevent
    false positives across languages (e.g., "di" matching inside "dinle").
    Also checks diacritics-normalized text for cross-lingual matching
    (e.g., "háblame" matching keyword "habla").
    """
    text_lower = text.lower()
    text_norm = normalize_diacritics(text_lower)
    words = set(text_lower.split())
    words_norm = set(text_norm.split())

    for kw in keyword_set:
        if len(kw) <= 3:
            # Short keywords: exact word match only (avoid "di" in "dinle")
            if kw in words or kw in words_norm:
                return True
        else:
            # Longer keywords: substring match
            if kw in text_lower or kw in text_norm:
                return True
            # Also normalize the keyword itself (e.g., "háblame" → "hablame")
            kw_norm = normalize_diacritics(kw)
            if kw_norm != kw and (kw_norm in text_lower or kw_norm in text_norm):
                return True
    return False


# ─── Lookup tables for detect_language() — CC reduction ─────────────────

_UNICODE_RANGES: Dict[str, Tuple[int, int]] = {
    # Non-Latin scripts (dominant = immediate classification)
    "cyrillic": (0x0400, 0x04FF),
    "cyrillic_ext": (0x0500, 0x052F),
    "greek": (0x0370, 0x03FF),
    "greek_ext": (0x1F00, 0x1FFF),
    "cjk": (0x4E00, 0x9FFF),  # Common Han
    "cjk_ext": (0x3400, 0x4DBF),
    "arabic": (0x0600, 0x06FF),
    "hebrew": (0x0590, 0x05FF),
    "devanagari": (0x0900, 0x097F),
    "armenian": (0x0530, 0x058F),
    "georgian": (0x10A0, 0x10FF),
    "latin_ext": (0x0100, 0x024F),  # Extended Latin (catch-all)
}

_SCRIPT_TO_LANG: Dict[str, str] = {
    "cyrillic": "ru",  # Default Cyrillic (refined by distinctive chars)
    "cyrillic_ext": "ru",
    "greek": "el",
    "greek_ext": "el",
    "cjk": "zh",
    "cjk_ext": "zh",
    "arabic": "ar",
    "hebrew": "he",
    "devanagari": "hi",
    "armenian": "hy",
    "georgian": "ka",
}

# Distinctive characters per language (for disambiguating Latin/Cyrillic)
_DISTINCTIVE_CHARS: Dict[str, FrozenSet[str]] = {
    # Cyrillic refinements
    "uk": frozenset("іїєґ"),
    "be": frozenset("ўі"),
    "bg": frozenset("ъ"),
    "sr": frozenset("ђљњћџ"),
    
    # Latin-script languages
    "pl": frozenset("ąęłćźżń"),
    "cs": frozenset("ěřůď"),
    "sk": frozenset("ľĺŕ"),
    "ro": frozenset("șțăâî"),
    "hu": frozenset("őű"),
    "tr": frozenset("ığşç"),
    "is": frozenset("ðþ"),
    "de": frozenset("ßäöü"),
    "sv": frozenset("åäö"),
    "no": frozenset("åøæ"),
    "da": frozenset("åøæ"),
    "fr": frozenset("çéèêëàù"),
    "es": frozenset("ñ¿¡"),
    "pt": frozenset("ãõçáéíóú"),
    "it": frozenset("àèéìòù"),
}

_DISTINCTIVE_WORDS: Dict[str, Tuple[str, ...]] = {
    "ro": ("faci", "prietenul", "cum", "să", "și", "pentru", "din", "multumesc", "buna", "că", "şi"),
    "de": ("der", "die", "das", "ein", "eine", "und", "ist", "wie"),
    "fr": ("le", "la", "les", "un", "une", "et", "est", "pour", "ce"),
    "es": ("el", "la", "los", "las", "un", "una", "es", "está", "qué"),
    "it": ("il", "la", "gli", "un", "una", "è", "sono", "per"),
    "pl": ("jest", "nie", "tak", "co", "jak", "dla", "tego"),
    "nl": ("de", "het", "een", "en", "is", "voor"),
    "pt": ("o", "a", "os", "as", "um", "uma", "é", "para"),
}


def _detect_by_script(text: str) -> str:
    """Phase 1: Detect language by dominant Unicode script. Returns lang code or ''."""
    script_counts: Dict[str, int] = {}
    for char in text:
        cp = ord(char)
        for script, (start, end) in _UNICODE_RANGES.items():
            if start <= cp <= end:
                script_counts[script] = script_counts.get(script, 0) + 1
                break
    if not script_counts:
        return ""
    dominant = max(script_counts, key=lambda k: script_counts[k])
    if script_counts[dominant] > len(text) * 0.1:
        return _SCRIPT_TO_LANG.get(dominant, "")
    return ""


def _score_by_chars_and_keywords(text: str) -> str:
    """Phase 2+3: Score Latin-script languages by distinctive chars + keywords. Returns lang code or ''."""
    tl = text.lower()
    char_set = set(tl)
    scores: Dict[str, int] = {}
    for lang, chars in _DISTINCTIVE_CHARS.items():
        match_count = len(char_set.intersection(chars))
        if match_count > 0:
            distinctiveness = 10 // len(chars)
            scores[lang] = match_count * distinctiveness
    words = set(tl.split())
    for lang, keywords in _DISTINCTIVE_WORDS.items():
        if any(kw in words for kw in keywords):
            scores[lang] = scores.get(lang, 0) + 5
    if scores:
        return max(scores, key=lambda k: scores[k])
    return ""


def detect_language(text: str) -> str:
    """Fast language detection using Unicode script analysis + distinctive char scoring.
    
    Returns ISO 639-1 code. Uses lookup tables for O(1) character classification
    instead of chained if/elif.
    """
    if not text or not text.strip():
        return "en"
    return _detect_by_script(text) or _score_by_chars_and_keywords(text) or "en"
