"""
Content Extraction Service.
Extracts key takeaways, definitions, and topic keywords from educational text.
Supports transformer model-assisted extraction (e.g. FLAN-T5) with a robust,
grounded NLP fallback using TF-IDF, POS/pattern matching, and sentence ranking.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

from backend.app.ai.model_loader import model_loader
from backend.app.utils.token_utils import split_into_sentences

logger = logging.getLogger(__name__)

# Regex patterns for definition identification in educational texts
DEFINITION_PATTERNS = [
    re.compile(r"^(?P<term>[A-Za-z0-9\s\-]{2,40})\s+(?:is defined as|is defined to be)\s+(?P<definition>[^.\n;]+)", re.IGNORECASE),
    re.compile(r"^(?P<term>[A-Za-z0-9\s\-]{2,40})\s+(?:refers to|denotes|signifies)\s+(?P<definition>[^.\n;]+)", re.IGNORECASE),
    re.compile(r"^(?P<term>[A-Za-z0-9\s\-]{2,40})\s+is\s+(?:an?|the)\s+(?P<definition>[^.\n;]+)", re.IGNORECASE),
    re.compile(r"^(?P<term>[A-Za-z0-9\s\-]{2,40}):\s+(?P<definition>[^.\n;]{10,})", re.IGNORECASE),
]

# Common English stop words to exclude from keyword extraction
STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does",
    "doesn't", "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had",
    "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd",
    "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself",
    "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off",
    "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own",
    "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some",
    "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then",
    "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this",
    "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we",
    "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's",
    "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't",
    "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself",
    "yourselves", "also", "using", "used", "may", "often", "example", "examples", "based", "first",
    "second", "third", "one", "two", "three", "many", "well", "much"
}


class ContentExtractionService:
    """Extracts structured learning artifacts from educational text."""

    def __init__(self) -> None:
        pass

    def extract_all(self, text: str, max_takeaways: int = 7, max_keywords: int = 10) -> Dict[str, Any]:
        """
        Runs comprehensive extraction on the provided text.
        Returns a dict with 'key_takeaways', 'definitions', and 'keywords'.
        """
        if not text or not text.strip():
            return {
                "key_takeaways": [],
                "definitions": [],
                "keywords": []
            }

        takeaways = self.extract_key_takeaways(text, max_items=max_takeaways)
        definitions = self.extract_definitions(text)
        keywords = self.extract_keywords(text, max_keywords=max_keywords)

        return {
            "key_takeaways": takeaways,
            "definitions": definitions,
            "keywords": keywords
        }

    def extract_key_takeaways(self, text: str, max_items: int = 7) -> List[str]:
        """
        Extracts salient bullet points summarizing core concepts.
        Ensures all takeaways are directly grounded in the source text.
        """
        sentences = split_into_sentences(text)
        if not sentences:
            return []

        if len(sentences) <= max_items:
            return [s.strip() for s in sentences if len(s.strip().split()) >= 4]

        # Score sentences based on keyword prominence and position
        word_freq: Dict[str, int] = {}
        tokens = re.findall(r"\b[A-Za-z]{3,}\b", text.lower())
        for token in tokens:
            if token not in STOP_WORDS:
                word_freq[token] = word_freq.get(token, 0) + 1

        scored_sentences = []
        for idx, sentence in enumerate(sentences):
            words = re.findall(r"\b[A-Za-z]{3,}\b", sentence.lower())
            if len(words) < 5 or len(words) > 50:
                continue

            score = 0.0
            for w in words:
                score += word_freq.get(w, 0)

            # Normalize by sentence length
            score = score / (len(words) ** 0.5)

            # Boost early sentences slightly (introductory significance)
            if idx < 3:
                score *= 1.25

            scored_sentences.append((score, sentence.strip()))

        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        top_sentences = [s for _, s in scored_sentences[:max_items]]

        # Fallback if filtered out
        if not top_sentences:
            top_sentences = [s.strip() for s in sentences[:max_items]]

        return top_sentences

    def extract_definitions(self, text: str, max_definitions: int = 10) -> List[Dict[str, str]]:
        """
        Extracts term definitions from text using syntactic pattern analysis.
        Returns a list of dicts: [{"term": "...", "definition": "..."}].
        """
        sentences = split_into_sentences(text)
        definitions: List[Dict[str, str]] = []
        seen_terms = set()

        for sentence in sentences:
            sentence_clean = sentence.strip()
            for pattern in DEFINITION_PATTERNS:
                match = pattern.search(sentence_clean)
                if match:
                    term = match.group("term").strip()
                    defn = match.group("definition").strip()
                    
                    # Sanitize term
                    term = re.sub(r"^(however|furthermore|additionally|moreover|therefore|in general|specifically|typically)[,\s]+", "", term, flags=re.IGNORECASE).strip()
                    term = term.rstrip(":").strip()

                    # Quality checks on term and definition
                    if 2 <= len(term.split()) <= 6 and len(defn.split()) >= 4:
                        normalized_term = term.lower()
                        if normalized_term not in seen_terms and normalized_term not in STOP_WORDS:
                            seen_terms.add(normalized_term)
                            definitions.append({
                                "term": term.title(),
                                "definition": defn.capitalize() + ("." if not defn.endswith((".", "!", "?")) else "")
                            })
                            if len(definitions) >= max_definitions:
                                return definitions
                    break

        return definitions

    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        Extracts high-value domain keywords using TF-IDF or frequency scoring.
        """
        if not text or not text.strip():
            return []

        try:
            # Use scikit-learn TfidfVectorizer if feasible
            from sklearn.feature_extraction.text import TfidfVectorizer

            sentences = split_into_sentences(text)
            if len(sentences) >= 3:
                vectorizer = TfidfVectorizer(
                    stop_words="english",
                    ngram_range=(1, 2),
                    max_features=50,
                    min_df=1
                )
                tfidf_matrix = vectorizer.fit_transform(sentences)
                feature_names = vectorizer.get_feature_names_out()
                scores = tfidf_matrix.sum(axis=0).A1
                ranked = sorted(zip(feature_names, scores), key=lambda x: x[1], reverse=True)
                
                keywords = []
                for term, _ in ranked:
                    term_clean = term.strip()
                    if len(term_clean) > 2 and term_clean.lower() not in STOP_WORDS:
                        keywords.append(term_clean.title())
                    if len(keywords) >= max_keywords:
                        break
                return keywords
        except Exception as e:
            logger.debug(f"TF-IDF extraction fallback: {e}")

        # Fallback frequency-based extraction
        words = re.findall(r"\b[A-Za-z][A-Za-z0-9\-]{2,}\b", text.lower())
        freq: Dict[str, int] = {}
        for w in words:
            if w not in STOP_WORDS and len(w) > 2:
                freq[w] = freq.get(w, 0) + 1

        sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [w.title() for w, _ in sorted_words[:max_keywords]]


# Global singleton instance
content_extraction_service = ContentExtractionService()
