import glob
import math
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field

from backend.config import settings


class Chunk(BaseModel):
    id: str
    file_name: str
    category: str  # e.g., "payment_help", "loan_rejection"
    heading: str
    content: str
    embedding: Optional[List[float]] = None


class SearchResult(BaseModel):
    chunk: Chunk
    score: float


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def fallback_dense_embedding(text: str, dim: int = 128) -> List[float]:
    """
    Deterministic hashed frequency vector generator for reliable offline retrieval
    when Ollama nomic-embed-text is not actively running.
    """
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    words = cleaned.split()
    vec = [0.0] * dim

    for w in words:
        h = abs(hash(w))
        idx = h % dim
        sign = 1.0 if (h // dim) % 2 == 0 else -1.0
        vec[idx] += sign * (1.0 + math.log(1.0 + len(w)))

    # Normalize
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


class KnowledgeBaseRAG:
    def __init__(
        self,
        kb_dir: Optional[str] = None,
        ollama_base_url: Optional[str] = None,
        embedding_model: str = "nomic-embed-text",
    ):
        self.kb_dir = kb_dir or str(Path(__file__).resolve().parent / "kb")
        self.ollama_base_url = (ollama_base_url or settings.ollama_base_url).rstrip("/")
        self.embedding_model = embedding_model
        self.chunks: List[Chunk] = []
        self._is_indexed = False

    def chunk_markdown(self, file_path: str) -> List[Chunk]:
        """
        Loads a markdown document and chunks by heading (# or ##).
        """
        p = Path(file_path)
        category = p.stem.lower()
        content = p.read_text(encoding="utf-8")

        lines = content.split("\n")
        chunks: List[Chunk] = []

        current_heading = "General"
        current_lines: List[str] = []
        chunk_idx = 1

        for line in lines:
            line_stripped = line.strip()
            # Match Markdown headings: #, ##, ###
            if line_stripped.startswith("#"):
                # Save previous chunk if it has substantive content
                body = "\n".join(current_lines).strip()
                if body:
                    chunk_id = f"kb-{category}-{chunk_idx}"
                    chunks.append(Chunk(
                        id=chunk_id,
                        file_name=p.name,
                        category=category,
                        heading=current_heading,
                        content=body,
                    ))
                    chunk_idx += 1
                    current_lines = []

                current_heading = line_stripped.lstrip("#").strip()
            else:
                if line_stripped:
                    current_lines.append(line_stripped)

        # Save last chunk
        body = "\n".join(current_lines).strip()
        if body:
            chunk_id = f"kb-{category}-{chunk_idx}"
            chunks.append(Chunk(
                id=chunk_id,
                file_name=p.name,
                category=category,
                heading=current_heading,
                content=body,
            ))

        return chunks

    async def get_embedding(self, text: str) -> List[float]:
        """
        Generates embedding via Ollama nomic-embed-text with graceful fallback.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try Ollama /api/embeddings or /api/embed
                resp = await client.post(
                    f"{self.ollama_base_url}/api/embeddings",
                    json={"model": self.embedding_model, "prompt": text},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    emb = data.get("embedding")
                    if emb and isinstance(emb, list):
                        return emb
        except Exception:
            pass

        # Fallback dense embedding
        return fallback_dense_embedding(text)

    async def load_and_index(self):
        """Loads all markdown files from kb_dir and computes chunk embeddings."""
        md_files = glob.glob(os.path.join(self.kb_dir, "*.md"))
        all_chunks: List[Chunk] = []

        for fpath in md_files:
            chunks = self.chunk_markdown(fpath)
            for c in chunks:
                # Combined text for embedding
                text_to_embed = f"{c.heading}: {c.content}"
                c.embedding = await self.get_embedding(text_to_embed)
                all_chunks.append(c)

        self.chunks = all_chunks
        self._is_indexed = True

    async def search(
        self,
        query: str,
        top_k: int = 3,
        category: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Performs in-memory cosine search and returns top_k chunks.
        """
        if not self._is_indexed:
            await self.load_and_index()

        if not self.chunks:
            return []

        query_vec = await self.get_embedding(query)
        results: List[SearchResult] = []

        for chunk in self.chunks:
            if category and chunk.category != category:
                continue
            if not chunk.embedding:
                chunk.embedding = fallback_dense_embedding(f"{chunk.heading}: {chunk.content}")

            score = cosine_similarity(query_vec, chunk.embedding)
            # Also boost if query words match heading
            q_words = set(re.findall(r"\w+", query.lower()))
            h_words = set(re.findall(r"\w+", chunk.heading.lower()))
            overlap = len(q_words.intersection(h_words))
            boosted_score = score + (overlap * 0.1)

            results.append(SearchResult(chunk=chunk, score=boosted_score))

        # Sort descending by score
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]


rag_service = KnowledgeBaseRAG()

