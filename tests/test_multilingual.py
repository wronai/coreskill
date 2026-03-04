#!/usr/bin/env python3
"""
Comprehensive multilingual tests for intent classification.

Tests that the SAME command produces the SAME intent across all European languages.
Covers: keyword prefilters, conversational detection, embedding similarity,
skill creation validation, and diacritics normalization.

Languages tested (~30 European):
  Germanic: en, de, nl, sv, no, da, is
  Romance: fr, es, it, pt, ro, ca, gl
  Slavic: pl, cs, sk, uk, ru, bg, hr, sr, sl, be
  Baltic: lt, lv
  Finno-Ugric: fi, et, hu
  Other: el, sq, tr, ga, eu, mt
"""
import sys
import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cores.v1.i18n import (
    EUROPEAN_LANGUAGES,
    normalize_diacritics,
    detect_language,
    match_any_keyword,
    TTS_KEYWORDS, STT_KEYWORDS, VOICE_MODE_KEYWORDS,
    SEARCH_KEYWORDS, SHELL_KEYWORDS, CREATE_KEYWORDS,
    EVOLVE_KEYWORDS, CONFIGURE_KEYWORDS,
    GREETING_PATTERNS, FAREWELL_PATTERNS, THANKS_PATTERNS,
    QUESTION_WORDS, YES_NO_MAYBE, ACTION_VERBS,
    ALL_TTS_KEYWORDS, ALL_STT_KEYWORDS, ALL_VOICE_MODE_KEYWORDS,
    ALL_SEARCH_KEYWORDS, ALL_SHELL_KEYWORDS, ALL_CREATE_KEYWORDS,
    ALL_EVOLVE_KEYWORDS, ALL_CONFIGURE_KEYWORDS,
    ALL_GREETING_PATTERNS, ALL_FAREWELL_PATTERNS,
    ALL_TRIVIAL_WORDS, ALL_ACTION_VERBS,
)
from cores.v1.skill_forge import is_conversational


# ─── Shared intent classifier (loaded once) ─────────────────────────
_SHARED_INTENT = None

def _get_intent():
    global _SHARED_INTENT
    if _SHARED_INTENT is None:
        from cores.v1.intent import SmartIntentClassifier
        _SHARED_INTENT = SmartIntentClassifier(
            state_dir=Path("/tmp/test_multilingual_intent"),
            llm_client=None,
        )
        # Disable local LLM for deterministic embedding-only results
        _SHARED_INTENT._local_llm._model = None
    return _SHARED_INTENT


# ─── Test data: equivalent commands in multiple languages ────────────
# Each entry: (expected_action, expected_skill, {lang: command})

EQUIVALENT_COMMANDS = {
    "tts": {
        "expected_action": "use",
        "expected_skill": "tts",
        "commands": {
            "en": "speak to me",
            "pl": "powiedz mi",
            "de": "sprich zu mir",
            "fr": "parle-moi",
            "es": "háblame",
            "it": "parlami",
            "pt": "fala comigo",
            "nl": "spreek tegen me",
            "sv": "tala till mig",
            "no": "snakk til meg",
            "da": "tal til mig",
            "cs": "řekni mi",
            "sk": "povedz mi",
            "uk": "скажи мені",
            "ru": "скажи мне",
            "ro": "spune-mi",
            "hu": "mondd el",
            "fi": "puhu minulle",
            "el": "μίλα μου",
            "tr": "söyle bana",
        },
    },
    "stt": {
        "expected_action": "use",
        "expected_skill": "stt",
        "commands": {
            "en": "listen to me",
            "pl": "słuchaj mnie",
            "de": "höre mir zu",
            "fr": "écoute-moi",
            "es": "escúchame",
            "it": "ascoltami",
            "pt": "ouve-me",
            "nl": "luister naar me",
            "cs": "poslouchej mě",
            "uk": "слухай мене",
            "ru": "слушай меня",
            "ro": "ascultă-mă",
            "hu": "hallgass rám",
            "fi": "kuuntele minua",
            "el": "άκου με",
            "tr": "dinle beni",
        },
    },
    "web_search": {
        "expected_action": "use",
        "expected_skill": "web_search",
        "commands": {
            "en": "search for Python tutorials",
            "pl": "wyszukaj tutoriale Python",
            "de": "suche nach Python-Tutorials",
            "fr": "cherche des tutoriels Python",
            "es": "busca tutoriales de Python",
            "it": "cerca tutorial Python",
            "pt": "procura tutoriais Python",
            "nl": "zoek Python tutorials",
            "cs": "hledej Python tutoriály",
            "uk": "шукай підручники Python",
            "ru": "ищи уроки Python",
            "ro": "caută tutoriale Python",
            "hu": "keress Python oktatóanyagokat",
            "fi": "etsi Python oppaita",
            "el": "ψάξε Python tutorials",
            "tr": "Python dersleri ara",
        },
    },
    "shell": {
        "expected_action": "use",
        "expected_skill": "shell",
        "commands": {
            "en": "run command ls -la",
            "pl": "uruchom ls -la",
            "de": "starte den Befehl ls -la",
            "fr": "exécute ls -la",
            "es": "ejecuta ls -la",
            "it": "esegui ls -la",
            "cs": "spusť příkaz ls -la",
            "uk": "запусти команду ls -la",
            "ru": "запусти команду ls -la",
            "tr": "komutu çalıştır ls -la",
        },
    },
    "create": {
        "expected_action": "create",
        "expected_skill": "",
        "commands": {
            "en": "create skill for weather",
            "pl": "stwórz skill do pogody",
            "de": "skill erstellen für Wetter",
            "fr": "créer skill pour la météo",
            "es": "crear skill para el clima",
            "it": "crea skill per il meteo",
            "pt": "criar skill para o tempo",
            "nl": "skill maken voor weer",
            "cs": "vytvoř skill pro počasí",
            "uk": "створи скіл для погоди",
            "ru": "создай скилл для погоды",
            "ro": "creează skill pentru vreme",
            "hu": "készíts skillt az időjáráshoz",
            "fi": "luo taito säähän",
            "el": "δημιούργησε skill για τον καιρό",
            "tr": "hava durumu için skill oluştur",
        },
    },
    "evolve": {
        "expected_action": "evolve",
        "expected_skill": "",
        "commands": {
            "en": "fix the calculator skill",
            "pl": "napraw kalkulator",
            "de": "repariere den Rechner",
            "fr": "répare la calculatrice",
            "es": "repara la calculadora",
            "it": "ripara la calcolatrice",
            "pt": "repara a calculadora",
            "cs": "oprav kalkulačku",
            "uk": "виправ калькулятор",
            "ru": "исправь калькулятор",
            "ro": "repară calculatorul",
            "hu": "javítsd a számológépet",
            "fi": "korjaa laskin",
            "el": "διόρθωσε την αριθμομηχανή",
            "tr": "hesap makinesini onar",
        },
    },
}

# Greetings in all languages (should be conversational / chat)
GREETINGS = {
    "en": "hello",
    "pl": "cześć",
    "de": "hallo",
    "fr": "bonjour",
    "es": "hola",
    "it": "ciao",
    "pt": "olá",
    "nl": "hoi",
    "sv": "hej",
    "no": "hei",
    "da": "godmorgen",
    "cs": "ahoj",
    "sk": "ahoj",
    "uk": "привіт",
    "ru": "привет",
    "bg": "здравей",
    "hr": "bok",
    "sr": "здраво",
    "sl": "živjo",
    "ro": "bună",
    "hu": "szia",
    "fi": "moi",
    "et": "tere",
    "lt": "labas",
    "lv": "sveiki",
    "el": "γεια",
    "sq": "mirëdita",
    "tr": "merhaba",
    "ca": "bon dia",
    "eu": "kaixo",
    "ga": "dia duit",
    "is": "halló",
    "be": "прывітанне",
    "mt": "bongu",
}


# =====================================================================
# Test Classes
# =====================================================================

class TestI18nModule(unittest.TestCase):
    """Test the i18n module itself."""

    def test_all_languages_have_tts_keywords(self):
        """Every European language should have TTS keywords defined."""
        for lang in EUROPEAN_LANGUAGES:
            self.assertIn(lang, TTS_KEYWORDS,
                          f"Missing TTS keywords for language: {lang}")
            self.assertTrue(len(TTS_KEYWORDS[lang]) > 0,
                            f"Empty TTS keywords for language: {lang}")

    def test_all_languages_have_stt_keywords(self):
        for lang in EUROPEAN_LANGUAGES:
            self.assertIn(lang, STT_KEYWORDS,
                          f"Missing STT keywords for language: {lang}")

    def test_all_languages_have_greeting_patterns(self):
        for lang in EUROPEAN_LANGUAGES:
            self.assertIn(lang, GREETING_PATTERNS,
                          f"Missing greeting patterns for language: {lang}")

    def test_all_languages_have_create_keywords(self):
        for lang in EUROPEAN_LANGUAGES:
            self.assertIn(lang, CREATE_KEYWORDS,
                          f"Missing create keywords for language: {lang}")

    def test_all_languages_have_evolve_keywords(self):
        for lang in EUROPEAN_LANGUAGES:
            self.assertIn(lang, EVOLVE_KEYWORDS,
                          f"Missing evolve keywords for language: {lang}")

    def test_all_languages_have_search_keywords(self):
        for lang in EUROPEAN_LANGUAGES:
            self.assertIn(lang, SEARCH_KEYWORDS,
                          f"Missing search keywords for language: {lang}")

    def test_all_languages_have_question_words(self):
        for lang in EUROPEAN_LANGUAGES:
            self.assertIn(lang, QUESTION_WORDS,
                          f"Missing question words for language: {lang}")

    def test_all_languages_have_yes_no(self):
        for lang in EUROPEAN_LANGUAGES:
            self.assertIn(lang, YES_NO_MAYBE,
                          f"Missing yes/no words for language: {lang}")

    def test_all_languages_have_action_verbs(self):
        for lang in EUROPEAN_LANGUAGES:
            self.assertIn(lang, ACTION_VERBS,
                          f"Missing action verbs for language: {lang}")

    def test_flat_sets_not_empty(self):
        """All flattened keyword sets should be non-empty."""
        self.assertTrue(len(ALL_TTS_KEYWORDS) > 50)
        self.assertTrue(len(ALL_STT_KEYWORDS) > 50)
        self.assertTrue(len(ALL_SEARCH_KEYWORDS) > 50)
        self.assertTrue(len(ALL_CREATE_KEYWORDS) > 50)
        self.assertTrue(len(ALL_EVOLVE_KEYWORDS) > 50)
        self.assertTrue(len(ALL_TRIVIAL_WORDS) > 100)
        self.assertTrue(len(ALL_ACTION_VERBS) > 100)


class TestNormalizeDiacritics(unittest.TestCase):
    """Test diacritics normalization for all European languages."""

    def test_polish(self):
        self.assertEqual(normalize_diacritics("ąćęłńóśźż"), "acelnoszz")

    def test_german(self):
        result = normalize_diacritics("über")
        self.assertEqual(result, "uber")

    def test_french(self):
        self.assertEqual(normalize_diacritics("café"), "cafe")
        self.assertEqual(normalize_diacritics("naïve"), "naive")

    def test_spanish(self):
        self.assertEqual(normalize_diacritics("señor"), "senor")
        self.assertEqual(normalize_diacritics("niño"), "nino")

    def test_czech(self):
        self.assertEqual(normalize_diacritics("příšerně"), "priserne")
        self.assertEqual(normalize_diacritics("žluťoučký"), "zlutoucky")

    def test_romanian(self):
        result = normalize_diacritics("română")
        self.assertIn("roman", result)

    def test_hungarian(self):
        result = normalize_diacritics("ő")
        self.assertEqual(result, "o")

    def test_turkish(self):
        result = normalize_diacritics("güneş")
        self.assertEqual(result, "gunes")

    def test_icelandic(self):
        result = normalize_diacritics("Þór")
        self.assertIn("or", result.lower())

    def test_scandinavian(self):
        result = normalize_diacritics("blåbær")
        self.assertIn("bla", result)

    def test_plain_ascii(self):
        self.assertEqual(normalize_diacritics("hello"), "hello")

    def test_cyrillic_passthrough(self):
        result = normalize_diacritics("привет")
        self.assertEqual(result, "привет")


class TestMatchAnyKeyword(unittest.TestCase):
    """Test multilingual keyword matching."""

    def test_polish_tts(self):
        self.assertTrue(match_any_keyword("powiedz coś", ALL_TTS_KEYWORDS))

    def test_german_tts(self):
        self.assertTrue(match_any_keyword("sprich zu mir", ALL_TTS_KEYWORDS))

    def test_french_tts(self):
        self.assertTrue(match_any_keyword("parle-moi", ALL_TTS_KEYWORDS))

    def test_spanish_stt(self):
        self.assertTrue(match_any_keyword("escucha mi voz", ALL_STT_KEYWORDS))

    def test_italian_search(self):
        self.assertTrue(match_any_keyword("cerca qualcosa", ALL_SEARCH_KEYWORDS))

    def test_russian_create(self):
        self.assertTrue(match_any_keyword("создай скилл", ALL_CREATE_KEYWORDS))

    def test_turkish_evolve(self):
        self.assertTrue(match_any_keyword("hatayı onar", ALL_EVOLVE_KEYWORDS))

    def test_no_match(self):
        self.assertFalse(match_any_keyword("xyz123", ALL_TTS_KEYWORDS))

    def test_case_insensitive(self):
        self.assertTrue(match_any_keyword("SPEAK louder", ALL_TTS_KEYWORDS))


class TestConversationalDetectionMultilingual(unittest.TestCase):
    """Test that greetings are detected as conversational in ALL languages."""

    def test_greetings_all_languages(self):
        """Every greeting in every language should be detected as conversational."""
        for lang, greeting in GREETINGS.items():
            with self.subTest(lang=lang, greeting=greeting):
                result = is_conversational(greeting)
                self.assertTrue(result,
                    f"[{lang}] '{greeting}' should be conversational but wasn't")

    def test_create_not_conversational_multilingual(self):
        """Create commands in any language should NOT be conversational."""
        create_commands = {
            "en": "create skill for weather",
            "pl": "stwórz skill do pogody",
            "de": "skill erstellen für Wetter",
            "fr": "créer skill pour la météo",
            "es": "crear skill para el clima",
            "it": "crea skill per il meteo",
            "ru": "создай скилл для погоды",
            "tr": "skill oluştur",
        }
        for lang, cmd in create_commands.items():
            with self.subTest(lang=lang, cmd=cmd):
                result = is_conversational(cmd)
                self.assertFalse(result,
                    f"[{lang}] '{cmd}' should NOT be conversational but was")

    def test_farewells_conversational(self):
        farewells = {
            "en": "goodbye",
            "pl": "do widzenia",
            "de": "tschüss",
            "fr": "au revoir",
            "es": "adiós",
            "it": "arrivederci",
            "ru": "до свидания",
            "tr": "hoşça kal",
        }
        for lang, farewell in farewells.items():
            with self.subTest(lang=lang, farewell=farewell):
                self.assertTrue(is_conversational(farewell),
                    f"[{lang}] '{farewell}' should be conversational")

    def test_thanks_conversational(self):
        thanks = {
            "en": "thank you",
            "pl": "dziękuję",
            "de": "danke",
            "fr": "merci",
            "es": "gracias",
            "it": "grazie",
            "ru": "спасибо",
            "tr": "teşekkürler",
            "hu": "köszönöm",
            "fi": "kiitos",
        }
        for lang, word in thanks.items():
            with self.subTest(lang=lang, word=word):
                self.assertTrue(is_conversational(word),
                    f"[{lang}] '{word}' should be conversational")

    def test_action_verbs_not_conversational(self):
        """Short action commands should NOT be conversational."""
        actions = {
            "en": "calculate 5+5",
            "pl": "policz 5+5",
            "de": "berechne 5+5",
            "fr": "calcule 5+5",
            "es": "calcula 5+5",
            "ru": "посчитай 5+5",
        }
        for lang, cmd in actions.items():
            with self.subTest(lang=lang, cmd=cmd):
                self.assertFalse(is_conversational(cmd),
                    f"[{lang}] '{cmd}' should NOT be conversational")


class TestKeywordPrefilterMultilingual(unittest.TestCase):
    """Test that keyword prefilter catches commands in all languages."""

    @classmethod
    def setUpClass(cls):
        cls.classifier = _get_intent()

    def _classify(self, msg):
        return self.classifier.classify(msg, skills=["tts", "stt", "web_search", "shell", "echo"])

    def test_tts_keywords_per_language(self):
        """TTS keywords should be recognized in every language."""
        tts_cmds = EQUIVALENT_COMMANDS["tts"]["commands"]
        for lang, cmd in tts_cmds.items():
            with self.subTest(lang=lang, cmd=cmd):
                result = self._classify(cmd)
                self.assertEqual(result.action, "use",
                    f"[{lang}] '{cmd}' → action={result.action}, expected 'use'")
                self.assertEqual(result.skill, "tts",
                    f"[{lang}] '{cmd}' → skill={result.skill}, expected 'tts'")

    def test_stt_keywords_per_language(self):
        """STT keywords should be recognized in every language."""
        stt_cmds = EQUIVALENT_COMMANDS["stt"]["commands"]
        for lang, cmd in stt_cmds.items():
            with self.subTest(lang=lang, cmd=cmd):
                result = self._classify(cmd)
                self.assertEqual(result.action, "use",
                    f"[{lang}] '{cmd}' → action={result.action}, expected 'use'")
                self.assertEqual(result.skill, "stt",
                    f"[{lang}] '{cmd}' → skill={result.skill}, expected 'stt'")

    def test_search_keywords_per_language(self):
        """Web search keywords should be recognized in every language."""
        search_cmds = EQUIVALENT_COMMANDS["web_search"]["commands"]
        for lang, cmd in search_cmds.items():
            with self.subTest(lang=lang, cmd=cmd):
                result = self._classify(cmd)
                self.assertEqual(result.action, "use",
                    f"[{lang}] '{cmd}' → action={result.action}, expected 'use'")
                self.assertEqual(result.skill, "web_search",
                    f"[{lang}] '{cmd}' → skill={result.skill}, expected 'web_search'")

    def test_shell_keywords_per_language(self):
        """Shell keywords should be recognized in every language."""
        shell_cmds = EQUIVALENT_COMMANDS["shell"]["commands"]
        for lang, cmd in shell_cmds.items():
            with self.subTest(lang=lang, cmd=cmd):
                result = self._classify(cmd)
                self.assertEqual(result.action, "use",
                    f"[{lang}] '{cmd}' → action={result.action}, expected 'use'")
                self.assertEqual(result.skill, "shell",
                    f"[{lang}] '{cmd}' → skill={result.skill}, expected 'shell'")

    def test_create_keywords_per_language(self):
        """Create keywords should be recognized in every language."""
        create_cmds = EQUIVALENT_COMMANDS["create"]["commands"]
        for lang, cmd in create_cmds.items():
            with self.subTest(lang=lang, cmd=cmd):
                result = self._classify(cmd)
                self.assertEqual(result.action, "create",
                    f"[{lang}] '{cmd}' → action={result.action}, expected 'create'")

    def test_evolve_keywords_per_language(self):
        """Evolve/fix keywords should be recognized in every language."""
        evolve_cmds = EQUIVALENT_COMMANDS["evolve"]["commands"]
        for lang, cmd in evolve_cmds.items():
            with self.subTest(lang=lang, cmd=cmd):
                result = self._classify(cmd)
                self.assertEqual(result.action, "evolve",
                    f"[{lang}] '{cmd}' → action={result.action}, expected 'evolve'")


class TestCrossLanguageConsistency(unittest.TestCase):
    """Verify that the SAME command in different languages produces the SAME intent."""

    @classmethod
    def setUpClass(cls):
        cls.classifier = _get_intent()

    def test_all_equivalent_commands_same_action(self):
        """For each command group, all languages should produce the same action."""
        for group_name, group in EQUIVALENT_COMMANDS.items():
            expected_action = group["expected_action"]
            commands = group["commands"]
            results = {}
            for lang, cmd in commands.items():
                result = self.classifier.classify(
                    cmd, skills=["tts", "stt", "web_search", "shell", "echo"])
                results[lang] = result.action

            # All should match expected action
            for lang, action in results.items():
                with self.subTest(group=group_name, lang=lang):
                    self.assertEqual(action, expected_action,
                        f"[{group_name}][{lang}] '{commands[lang]}' → "
                        f"action={action}, expected '{expected_action}'. "
                        f"All results: {results}")

    def test_all_equivalent_commands_same_skill(self):
        """For each command group, all languages should produce the same skill."""
        for group_name, group in EQUIVALENT_COMMANDS.items():
            expected_skill = group["expected_skill"]
            if not expected_skill:
                continue  # Skip groups where skill is empty (create, evolve)
            commands = group["commands"]
            for lang, cmd in commands.items():
                with self.subTest(group=group_name, lang=lang):
                    result = self.classifier.classify(
                        cmd, skills=["tts", "stt", "web_search", "shell", "echo"])
                    self.assertEqual(result.skill, expected_skill,
                        f"[{group_name}][{lang}] '{cmd}' → "
                        f"skill={result.skill}, expected '{expected_skill}'")


class TestDetectLanguage(unittest.TestCase):
    """Test basic language detection."""

    def test_polish(self):
        self.assertEqual(detect_language("cześć, jak się masz?"), "pl")

    def test_russian(self):
        self.assertEqual(detect_language("привет, как дела?"), "ru")

    def test_ukrainian(self):
        self.assertEqual(detect_language("привіт, як справи?"), "uk")

    def test_greek(self):
        self.assertEqual(detect_language("γεια σου, τι κάνεις;"), "el")

    def test_czech(self):
        self.assertEqual(detect_language("jak se máš, příteli?"), "cs")

    def test_romanian(self):
        self.assertEqual(detect_language("ce faci, prietenul meu? România e frumoasă"), "ro")
        
    def test_turkish(self):
        self.assertEqual(detect_language("nasılsın, arkadaşım?"), "tr")

    def test_english_plain(self):
        self.assertEqual(detect_language("hello, how are you?"), "en")

    def test_spanish(self):
        self.assertEqual(detect_language("¿cómo estás, amigo?"), "es")

    def test_german(self):
        self.assertEqual(detect_language("Wie geht es dir? Das ist schön und gemütlich."), "de")


class TestTrivialWordsMultilingual(unittest.TestCase):
    """Test that trivial (greeting) words are filtered across languages."""

    def test_trivial_greetings(self):
        """Single-word greetings should be in trivial set."""
        trivial_greetings = [
            "hej", "hallo", "ciao", "moi", "tere", "labas",
            "sveiki", "bok", "szia", "merhaba", "kaixo",
        ]
        for word in trivial_greetings:
            with self.subTest(word=word):
                self.assertIn(word, ALL_TRIVIAL_WORDS,
                    f"'{word}' should be in ALL_TRIVIAL_WORDS")

    def test_yes_no_all_languages(self):
        """Yes/no words should be in trivial set."""
        yes_no = [
            "yes", "no", "tak", "nie", "ja", "nein", "oui", "non",
            "sí", "sì", "da", "ne", "igen", "nem", "evet", "hayır",
        ]
        for word in yes_no:
            with self.subTest(word=word):
                self.assertIn(word, ALL_TRIVIAL_WORDS,
                    f"'{word}' should be in ALL_TRIVIAL_WORDS")


class TestSkillCreationMultilingual(unittest.TestCase):
    """Test that skill creation commands work across languages via SkillForge."""

    def test_conversational_blocks_creation_all_langs(self):
        """Greetings in any language should block skill creation (→ chat)."""
        from cores.v1.skill_forge import SkillForge
        forge = SkillForge()
        skills = {"echo": ["v1"], "shell": ["v1"]}

        for lang, greeting in GREETINGS.items():
            with self.subTest(lang=lang, greeting=greeting):
                should, reason = forge.should_create(greeting, skills)
                self.assertFalse(should,
                    f"[{lang}] '{greeting}' should NOT trigger creation, "
                    f"but got should_create=True")
                self.assertEqual(reason, "chat",
                    f"[{lang}] '{greeting}' reason should be 'chat', got '{reason}'")

    def test_create_commands_allow_creation(self):
        """Create commands in any language should allow skill creation."""
        from cores.v1.skill_forge import SkillForge
        forge = SkillForge()
        skills = {"echo": ["v1"]}

        create_cmds = {
            "en": "create skill for PDF parsing",
            "pl": "stwórz skill do parsowania PDF",
            "de": "skill erstellen für PDF-Parsing",
            "fr": "créer skill pour parser des PDF",
            "es": "crear skill para parsear PDF",
            "it": "crea skill per il parsing PDF",
            "ru": "создай скилл для парсинга PDF",
            "tr": "PDF ayrıştırma için skill oluştur",
        }
        for lang, cmd in create_cmds.items():
            with self.subTest(lang=lang, cmd=cmd):
                should, reason = forge.should_create(cmd, skills)
                self.assertTrue(should,
                    f"[{lang}] '{cmd}' should trigger creation, "
                    f"but got should_create=False, reason='{reason}'")


class TestEmbeddingSimilarityMultilingual(unittest.TestCase):
    """Test that the SBERT model handles cross-lingual similarity."""

    @classmethod
    def setUpClass(cls):
        from cores.v1.intent import EmbeddingEngine
        cls.embedder = EmbeddingEngine()
        if not cls.embedder.available:
            raise unittest.SkipTest("EmbeddingEngine not available")

    def test_same_meaning_different_languages_higher_similarity(self):
        """Semantically equivalent phrases across languages should have
        higher similarity than unrelated phrases."""
        # "search for information" in different languages
        search_phrases = [
            "search for information",
            "szukaj informacji",
            "suche nach Informationen",
            "cherche des informations",
            "busca información",
            "cerca informazioni",
        ]
        # Unrelated phrase
        unrelated = "the weather is nice today"

        search_vecs = self.embedder.encode(search_phrases)
        unrelated_vec = self.embedder.encode([unrelated])[0]

        # Cross-lingual similarity between search phrases
        import numpy as np
        for i in range(1, len(search_vecs)):
            sim_related = self.embedder.similarity(search_vecs[0], search_vecs[i])
            sim_unrelated = self.embedder.similarity(search_vecs[0], unrelated_vec)
            with self.subTest(phrase=search_phrases[i]):
                self.assertGreater(sim_related, sim_unrelated,
                    f"'{search_phrases[i]}' should be more similar to "
                    f"'{search_phrases[0]}' than to '{unrelated}'. "
                    f"Got sim_related={sim_related:.3f} vs sim_unrelated={sim_unrelated:.3f}")

    def test_create_skill_cross_lingual(self):
        """'Create skill' phrases in different languages should cluster together."""
        create_phrases = [
            "create a new skill",
            "stwórz nowy skill",
            "erstelle einen neuen Skill",
            "créer un nouveau skill",
            "crear un nuevo skill",
            "создай новый скилл",
        ]
        chat_phrases = [
            "how are you today",
            "what is the meaning of life",
        ]

        create_vecs = self.embedder.encode(create_phrases)
        chat_vecs = self.embedder.encode(chat_phrases)

        # Average within-group similarity should be higher than between-group
        within_sims = []
        for i in range(len(create_vecs)):
            for j in range(i + 1, len(create_vecs)):
                within_sims.append(
                    self.embedder.similarity(create_vecs[i], create_vecs[j]))

        between_sims = []
        for cv in create_vecs:
            for chv in chat_vecs:
                between_sims.append(self.embedder.similarity(cv, chv))

        import numpy as np
        avg_within = np.mean(within_sims)
        avg_between = np.mean(between_sims)
        self.assertGreater(avg_within, avg_between,
            f"Within-group similarity ({avg_within:.3f}) should be greater "
            f"than between-group ({avg_between:.3f})")


class TestLanguageCoverage(unittest.TestCase):
    """Verify that all 35 European languages have adequate keyword coverage."""

    def test_minimum_keywords_per_language(self):
        """Each language should have at least 2 keywords per intent category."""
        categories = {
            "TTS": TTS_KEYWORDS,
            "STT": STT_KEYWORDS,
            "Search": SEARCH_KEYWORDS,
            "Shell": SHELL_KEYWORDS,
            "Create": CREATE_KEYWORDS,
            "Evolve": EVOLVE_KEYWORDS,
            "Greetings": GREETING_PATTERNS,
        }
        for cat_name, cat_data in categories.items():
            for lang in EUROPEAN_LANGUAGES:
                with self.subTest(category=cat_name, lang=lang):
                    self.assertIn(lang, cat_data,
                        f"Language '{lang}' missing from {cat_name}")
                    self.assertGreaterEqual(len(cat_data[lang]), 2,
                        f"Language '{lang}' has <2 keywords in {cat_name}: "
                        f"{cat_data[lang]}")

    def test_total_language_count(self):
        """Should support at least 30 European languages."""
        self.assertGreaterEqual(len(EUROPEAN_LANGUAGES), 30)


if __name__ == "__main__":
    unittest.main(verbosity=2)
