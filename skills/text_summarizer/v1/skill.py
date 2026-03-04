#!/usr/bin/env python3
"""
text_summarizer skill - Summarize long texts using extractive summarization.
Uses stdlib only - no external dependencies.
"""
import re
import json
from collections import Counter


def get_info():
    return {
        "name": "text_summarizer",
        "version": "v1",
        "description": "Summarize long texts using extractive methods. Works with any language.",
        "capabilities": ["summarization", "text", "nlp"],
        "actions": ["summarize", "extract_keywords", "get_stats"]
    }


def health_check():
    return True


class TextSummarizerSkill:
    """Text summarization using extractive methods (stdlib only)."""

    def _tokenize_sentences(self, text):
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _tokenize_words(self, text):
        """Extract words from text."""
        # Find word tokens (alphanumeric)
        words = re.findall(r'\b[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]+\b', text.lower())
        return words

    def _score_sentences(self, sentences, word_freq):
        """Score sentences based on word frequency."""
        scores = {}
        for i, sentence in enumerate(sentences):
            words = self._tokenize_words(sentence)
            if not words:
                scores[i] = 0
                continue
            # Score is average word frequency
            score = sum(word_freq.get(word, 0) for word in words) / len(words)
            scores[i] = score
        return scores

    def summarize(self, text, ratio=0.2, max_sentences=5):
        """Create extractive summary of text."""
        try:
            if not text or not isinstance(text, str):
                return {"success": False, "error": "No text provided"}

            # Clean text
            text = text.strip()
            if len(text) < 100:
                return {
                    "success": True,
                    "summary": text,
                    "original_length": len(text),
                    "summary_length": len(text),
                    "compression_ratio": 1.0,
                    "note": "Text too short to summarize"
                }

            # Tokenize
            sentences = self._tokenize_sentences(text)
            if len(sentences) <= 2:
                return {
                    "success": True,
                    "summary": text,
                    "original_length": len(text),
                    "summary_length": len(text),
                    "compression_ratio": 1.0,
                    "note": "Too few sentences to summarize"
                }

            # Calculate word frequencies
            words = self._tokenize_words(text)
            if not words:
                return {"success": False, "error": "Could not extract words from text"}

            # Remove common stop words
            stop_words = {
                'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
                'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
                'through', 'during', 'before', 'after', 'above', 'below',
                'between', 'under', 'and', 'but', 'or', 'yet', 'so', 'if',
                'because', 'although', 'though', 'while', 'where', 'when',
                'that', 'which', 'who', 'whom', 'whose', 'what', 'this',
                'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we',
                'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your',
                'his', 'its', 'our', 'their', 'and', 'or', 'but', 'in',
                'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from',
                'as', 'into', 'through', 'during', 'before', 'after'
            }

            # Filter words and count frequencies
            filtered_words = [w for w in words if w not in stop_words and len(w) > 2]
            word_freq = Counter(filtered_words)

            # Score sentences
            scores = self._score_sentences(sentences, word_freq)

            # Select top sentences
            num_summary_sentences = max(1, min(max_sentences, int(len(sentences) * ratio)))
            top_indices = sorted(scores.keys(), key=lambda i: scores[i], reverse=True)[:num_summary_sentences]

            # Sort by original position to maintain flow
            top_indices.sort()

            # Build summary
            summary_sentences = [sentences[i] for i in top_indices]
            summary = ' '.join(summary_sentences)

            return {
                "success": True,
                "summary": summary,
                "original_length": len(text),
                "summary_length": len(summary),
                "original_sentences": len(sentences),
                "summary_sentences": len(summary_sentences),
                "compression_ratio": round(len(summary) / len(text), 2),
                "method": "extractive_frequency"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def extract_keywords(self, text, top_n=10):
        """Extract most important keywords from text."""
        try:
            if not text or not isinstance(text, str):
                return {"success": False, "error": "No text provided"}

            words = self._tokenize_words(text)
            if not words:
                return {"success": False, "error": "Could not extract words"}

            # Stop words
            stop_words = {
                'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                'would', 'could', 'should', 'may', 'might', 'must', 'to',
                'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as',
                'and', 'or', 'but', 'this', 'that', 'these', 'those',
                'it', 'its', 'they', 'them', 'their', 'we', 'our', 'us',
                'i', 'me', 'my', 'mine', 'you', 'your', 'yours'
            }

            # Filter and count
            filtered = [w.lower() for w in words if w.lower() not in stop_words and len(w) > 3]
            word_freq = Counter(filtered)

            # Get top keywords
            keywords = word_freq.most_common(top_n)

            return {
                "success": True,
                "keywords": [{"word": w, "count": c} for w, c in keywords],
                "total_words": len(words),
                "unique_words": len(set(words))
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_stats(self, text):
        """Get text statistics."""
        try:
            if not text or not isinstance(text, str):
                return {"success": False, "error": "No text provided"}

            sentences = self._tokenize_sentences(text)
            words = self._tokenize_words(text)

            # Count characters (excluding whitespace)
            chars_no_space = len(re.sub(r'\s', '', text))

            return {
                "success": True,
                "characters": len(text),
                "characters_no_spaces": chars_no_space,
                "words": len(words),
                "sentences": len(sentences),
                "avg_word_length": round(sum(len(w) for w in words) / len(words), 1) if words else 0,
                "avg_sentence_length": round(len(words) / len(sentences), 1) if sentences else 0
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        action = input_data.get("action", "summarize")

        if action == "summarize":
            return self.summarize(
                input_data.get("text", ""),
                input_data.get("ratio", 0.2),
                input_data.get("max_sentences", 5)
            )
        elif action == "extract_keywords":
            return self.extract_keywords(
                input_data.get("text", ""),
                input_data.get("top_n", 10)
            )
        elif action == "get_stats":
            return self.get_stats(input_data.get("text", ""))
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


def execute(input_data: dict) -> dict:
    return TextSummarizerSkill().execute(input_data)


if __name__ == "__main__":
    skill = TextSummarizerSkill()
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    print(f"Health: {health_check()}")

    # Test
    test_text = """
    Artificial intelligence (AI) is intelligence demonstrated by machines, in contrast to the natural intelligence displayed by humans and animals. Leading AI textbooks define the field as the study of "intelligent agents": any device that perceives its environment and takes actions that maximize its chance of successfully achieving its goals. Colloquially, the term "artificial intelligence" is often used to describe machines that mimic "cognitive" functions that humans associate with the human mind, such as "learning" and "problem solving".

    As machines become increasingly capable, tasks considered to require "intelligence" are often removed from the definition of AI, a phenomenon known as the AI effect. A quip in Tesler's Theorem says "AI is whatever hasn't been done yet." For instance, optical character recognition is frequently excluded from things considered to be AI, having become a routine technology. Modern machine capabilities generally classified as AI include successfully understanding human speech, competing at the highest level in strategic game systems, autonomously operating cars, intelligent routing in content delivery networks, and military simulations.
    """

    print("\nSummarize:")
    result = skill.summarize(test_text, ratio=0.3)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    print("\nKeywords:")
    result = skill.extract_keywords(test_text, top_n=5)
    print(json.dumps(result, indent=2, ensure_ascii=False))
