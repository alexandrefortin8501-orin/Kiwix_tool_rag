import requests
import re
import asyncio
from bs4 import BeautifulSoup as Soup
from urllib.parse import quote
from pydantic import BaseModel, Field
from typing import Callable, Any

# ==========================================
# 1. Nettoyage HTML
# ==========================================
class KiwixCleaner:
    def __init__(self):
        self.useless_tags = [
            "script", "style", "nav", "footer", "header", 
            "aside", "sup", "svg", "button"
        ]

    def clean_html(self, raw_html: str) -> str:
        if not raw_html or "Failed to retrieve" in raw_html:
            return ""

        soup = Soup(raw_html, "html.parser")
        for tag in soup(self.useless_tags):
            tag.decompose()

        text = soup.get_text(separator=" \n ")
        text = re.sub(r"\[\w+\s*.*?\]", "", text)
        text = re.sub(r"http[s]?://\S+", "", text)
        text = text.replace("\xa0", " ").replace("\t", " ")

        lines = [line.strip() for line in text.split("\n")]
        cleaned_lines = [re.sub(r" +", " ", line) for line in lines if line]
        return "\n".join(cleaned_lines)

# ==========================================
# 2. Chunking Intelligent
# ==========================================
class KiwixChunker:
    def __init__(self, max_tokens=400, overlap_lines=2):
        self.max_tokens = max_tokens
        self.overlap_lines = overlap_lines

    def _estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    def chunk_text(self, text: str) -> list[str]:
        lines = text.split("\n")
        chunks = []
        current_chunk_lines = []
        current_tokens = 0

        for line in lines:
            line_tokens = self._estimate_tokens(line)
            if current_tokens + line_tokens > self.max_tokens and current_chunk_lines:
                chunks.append("\n".join(current_chunk_lines))
                overlap = current_chunk_lines[-self.overlap_lines:] if self.overlap_lines > 0 else []
                current_chunk_lines = overlap + [line]
                current_tokens = sum(self._estimate_tokens(l) for l in current_chunk_lines)
            else:
                current_chunk_lines.append(line)
                current_tokens += line_tokens

        if current_chunk_lines:
            chunks.append("\n".join(current_chunk_lines))
        return chunks

# ==========================================
# 3. Intégration Open WebUI
# ==========================================
class Tools:
    class Valves(BaseModel):
        KIWIX_BASE_URL: str = Field(
            default="http://localhost:8080",
            description="L'URL de base de votre serveur Kiwix local."
        )
        DEFAULT_BOOK: str = Field(
            default="wikipedia_en_all_maxi_2026-02",
            description="ID du livre ZIM par défaut à interroger."
        )
        RESULTS_LIMIT: int = Field(
            default=2, description="Nombre d'articles à extraire par requête."
        )
        CHUNK_MAX_TOKENS: int = Field(
            default=500, description="Taille maximale des morceaux (chunks) envoyés au LLM."
        )

    def __init__(self):
        self.valves = self.Valves()
        self.headers = {"User-Agent": "Mozilla/5.0 (RAG-Edge-Client/1.0)"}
        self.cleaner = KiwixCleaner()

    async def search_kiwix(
        self,
        query: str,
        book: str = None,
        __event_emitter__: Callable[[dict], Any] = None,
    ) -> str:
        """
        Recherche des informations dans un serveur Kiwix local.
        :param query: Mots-clés de la recherche.
        :param book: Optionnel. ID du livre ZIM spécifique. Laisser vide pour utiliser la valeur par défaut.
        """
        target_book = book if book else self.valves.DEFAULT_BOOK
        book_clean = target_book.strip().rstrip(".zim")
        safe_query = quote(query)
        kiwix_url = self.valves.KIWIX_BASE_URL.rstrip("/")

        search_url = f"{kiwix_url}/search?books.name={book_clean}&pattern={safe_query}"

        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {"status": "in_progress", "description": f"Recherche de '{query}' dans {book_clean}...", "done": False}
            })

        try:
            response = requests.get(search_url, headers=self.headers, timeout=10)
            response.raise_for_status()
        except Exception as e:
            return f"Erreur de connexion au serveur Kiwix : {e}"

        soup = Soup(response.text, "html.parser")
        results = soup.find_all("li")[:self.valves.RESULTS_LIMIT]

        if not results:
            return "Aucun document trouvé dans la base de données locale."

        final_context = f"Contexte extrait pour la recherche '{query}':\n\n"
        chunker = KiwixChunker(max_tokens=self.valves.CHUNK_MAX_TOKENS, overlap_lines=2)

        for li in results:
            a_tag = li.find("a")
            if not a_tag: continue
            
            title = a_tag.text.strip()
            page_url = f"{kiwix_url}{a_tag['href']}"

            try:
                page_response = requests.get(page_url, headers=self.headers, timeout=10)
                if page_response.status_code == 200:
                    clean_text = self.cleaner.clean_html(page_response.text)
                    chunks = chunker.chunk_text(clean_text)
                    
                    final_context += f"--- DEBUT DOCUMENT : {title} ---\n"
                    for i, chunk in enumerate(chunks[:3]):
                        final_context += f"[Chunk {i+1}]\n{chunk}\n\n"
                    final_context += f"--- FIN DOCUMENT : {title} ---\n\n"
            except Exception:
                continue

        return final_context
