"""
RAG Engine — Retrieval Augmented Generation ringan untuk dokumen taktik.
Menggunakan TF-IDF (scikit-learn) sebagai retriever, bukan embedding model besar,
supaya tetap ringan & gratis untuk dijalankan di Streamlit Cloud free tier.
"""

import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 80):
    """Pecah dokumen panjang menjadi chunk kecil agar retrieval lebih presisi."""
    text = re.sub(r"\s+", " ", text).strip()
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return [c for c in chunks if len(c.strip()) > 30]


class TacticalKnowledgeBase:
    """Knowledge base sederhana berbasis TF-IDF untuk dokumen referensi taktik."""

    def __init__(self):
        self.chunks = []
        self.sources = []
        self.vectorizer = None
        self.matrix = None

    def add_document(self, text: str, source_name: str):
        new_chunks = chunk_text(text)
        self.chunks.extend(new_chunks)
        self.sources.extend([source_name] * len(new_chunks))
        self._rebuild_index()

    def _rebuild_index(self):
        if not self.chunks:
            return
        self.vectorizer = TfidfVectorizer(
            stop_words=None,  # dokumen bisa campur ID/EN, jadi tidak pakai stopword bawaan
            ngram_range=(1, 2),
            max_features=5000,
        )
        self.matrix = self.vectorizer.fit_transform(self.chunks)

    def is_ready(self) -> bool:
        return self.matrix is not None and len(self.chunks) > 0

    def retrieve(self, query: str, top_k: int = 3):
        """Ambil potongan dokumen paling relevan terhadap query."""
        if not self.is_ready():
            return []
        query_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(query_vec, self.matrix).flatten()
        top_idx = sims.argsort()[::-1][:top_k]
        results = []
        for idx in top_idx:
            if sims[idx] > 0.03:  # ambang batas relevansi minimal
                results.append(
                    {
                        "text": self.chunks[idx],
                        "source": self.sources[idx],
                        "score": float(sims[idx]),
                    }
                )
        return results

    def reset(self):
        self.chunks = []
        self.sources = []
        self.vectorizer = None
        self.matrix = None
