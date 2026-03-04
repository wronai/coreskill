"""EmbeddingEngine — sentence-transformers based intent similarity.

Uses paraphrase-multilingual-MiniLM-L12-v2 (~120MB, supports PL+EN).
Falls back to TF-IDF if sentence-transformers not installed.
Ultimate fallback: bag-of-words cosine (zero deps).
"""
import json
from pathlib import Path
from typing import List, Optional

# Import ROOT for config file access
try:
    from ..config import ROOT, get_config_value
except ImportError:
    # Fallback for standalone usage
    ROOT = Path(__file__).resolve().parent.parent.parent.parent
    def get_config_value(k, d=None): return d


# Load intent configuration from system.json
_INTENT_CONFIG = {
    "confidence_threshold": get_config_value("intent.confidence_threshold", 0.78),
    "sbert_threshold": get_config_value("intent.sbert_threshold", 0.70),
    "tfidf_threshold": get_config_value("intent.tfidf_threshold", 0.45),
    "bow_threshold": get_config_value("intent.bow_threshold", 0.35),
    "low_threshold_factor": get_config_value("intent.low_threshold_factor", 0.6),
    "min_threshold": get_config_value("intent.min_threshold", 0.25),
    "similarity_min": get_config_value("intent.similarity_min", 0.3),
    "training_file": get_config_value("intent.training_file", "intent_training.json"),
    "embedding_model": get_config_value("intent.embedding_model", "paraphrase-multilingual-MiniLM-L12-v2"),
    "tfidf_fallback": get_config_value("intent.tfidf_fallback", True),
}


class EmbeddingEngine:
    """
    Sentence-transformers based embedding for intent similarity.
    
    Uses paraphrase-multilingual-MiniLM-L12-v2 (~120MB, supports PL+EN).
    Falls back to TF-IDF if sentence-transformers not installed.
    """

    MODEL_NAME = _INTENT_CONFIG["embedding_model"]
    TFIDF_FALLBACK = _INTENT_CONFIG["tfidf_fallback"]

    def __init__(self, cache_dir: Path = None):
        self._model = None
        self._tfidf = None
        self._mode = None  # "sbert", "tfidf", None
        self._cache_dir = cache_dir or Path.home() / ".evo-engine" / "models"
        self._embeddings_cache = {}  # text -> vector

    @property
    def available(self) -> bool:
        if self._mode is not None:
            return True
        self._try_init()
        return self._mode is not None

    def _try_init(self):
        """Try to initialize in order: sentence-transformers → TF-IDF."""
        if self._mode:
            return

        # Try sentence-transformers
        try:
            from sentence_transformers import SentenceTransformer
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            self._model = SentenceTransformer(
                self.MODEL_NAME,
                cache_folder=str(self._cache_dir)
            )
            self._mode = "sbert"
            return
        except ImportError:
            pass
        except Exception:
            pass

        # Fallback: TF-IDF (stdlib-compatible via sklearn or manual)
        if self.TFIDF_FALLBACK:
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.metrics.pairwise import cosine_similarity
                self._tfidf = {"vectorizer": None, "matrix": None, "fit": False}
                self._mode = "tfidf"
                return
            except ImportError:
                pass

            # Ultimate fallback: bag-of-words cosine (zero deps)
            self._mode = "bow"

    def encode(self, texts: list) -> list:
        """Encode texts to vectors."""
        self._try_init()

        if self._mode == "sbert":
            return self._model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)

        elif self._mode == "tfidf":
            from sklearn.feature_extraction.text import TfidfVectorizer
            if self._tfidf["vectorizer"] is None or not self._tfidf["fit"]:
                self._tfidf["vectorizer"] = TfidfVectorizer(
                    analyzer="char_wb", ngram_range=(2, 5),
                    max_features=8000, sublinear_tf=True,
                    strip_accents="unicode",
                )
            v = self._tfidf["vectorizer"]
            # Normalize Polish diacritics for better matching
            normalized = [self._normalize_pl(t) + " " + t for t in texts]
            if not self._tfidf["fit"]:
                vecs = v.fit_transform(normalized).toarray()
                self._tfidf["fit"] = True
                self._tfidf["matrix"] = vecs
                return vecs
            return v.transform(normalized).toarray()

        elif self._mode == "bow":
            return [self._bow_vector(t) for t in texts]

        return []

    def similarity(self, vec_a, vec_b) -> float:
        """Cosine similarity between two vectors."""
        import numpy as np
        if isinstance(vec_a, dict) and isinstance(vec_b, dict):
            # BOW dict vectors
            keys = set(vec_a) | set(vec_b)
            a = [vec_a.get(k, 0) for k in keys]
            b = [vec_b.get(k, 0) for k in keys]
            vec_a, vec_b = a, b
        a = np.array(vec_a, dtype=float)
        b = np.array(vec_b, dtype=float)
        norm = (np.linalg.norm(a) * np.linalg.norm(b))
        if norm == 0:
            return 0.0
        return float(np.dot(a, b) / norm)

    def _bow_vector(self, text: str) -> dict:
        """Bag-of-character-ngrams (zero-dependency fallback)."""
        text = self._normalize_pl(text.lower())
        ngrams = {}
        for n in (2, 3, 4):
            for i in range(len(text) - n + 1):
                ng = text[i:i+n]
                ngrams[ng] = ngrams.get(ng, 0) + 1
        return ngrams

    @staticmethod
    def _normalize_pl(text: str) -> str:
        """Normalize Polish text: strip diacritics, lowercase."""
        _PL_MAP = str.maketrans(
            "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ",
            "acelnoszzACELNOSZZ"
        )
        return text.lower().translate(_PL_MAP)

    def install_hint(self) -> str:
        """Hint for installing sentence-transformers."""
        return (
            "pip install sentence-transformers  "
            "# ~120MB, multilingual, najlepsza jakość\n"
            "# albo: pip install scikit-learn  "
            "# ~30MB, TF-IDF fallback, dobra jakość"
        )
