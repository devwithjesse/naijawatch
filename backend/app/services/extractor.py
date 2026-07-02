import json

from .llm import LLMService


class ExtractorService:
    def __init__(self):
        self.llm = LLMService()
        self.model = "llama-3.3-70b-versatile"

    def _preprocess_body(self, text: str, max_chars: int = 1500) -> str:
        """
        Extracts the 'lead' of the article to save tokens.
        """
        if not text:
            return ""
        chunk = text[: max_chars + 200]
        last_dot = chunk.rfind(".", 0, max_chars)
        if last_dot != -1:
            return chunk[: last_dot + 1].strip()
        return chunk[:max_chars].strip()

    def extract_event(self, article_title: str, article_body: str):
        """
        Uses centralized LLMService to extract structured data.
        """
        lean_body = self._preprocess_body(article_body)

        if not lean_body or len(lean_body) < 100:
            return {"status": "irrelevant", "data": None}

        prompt = f"""
        Analyze the following Nigerian news article and extract security incident details.

        ARTICLE TITLE: {article_title}
        ARTICLE BODY: {lean_body}

        EXTRACT the following fields in strict JSON format:
        - event_type: (kidnapping, banditry, armed_robbery, terrorist_attack, communal_clash, assassination, jailbreak, pipeline_vandalism, or other)
        - state: The Nigerian state where it occurred (e.g., Kaduna, Borno, Lagos)
        - location: Specific town, village, or landmark (e.g., Birnin Gwari)
        - killed: Number of people killed (must be an integer, if none specified or vague, return 0)
        - injured: Number of people injured (must be an integer, if none specified or vague, return 0)
        - abducted: Number of people kidnapped/abducted (must be an integer, if none specified or vague, return 0)
        - event_date: Date of the incident (YYYY-MM-DD) if mentioned, otherwise null
        - summary: A concise 1-sentence summary of the event.
        - confidence: Your confidence score (0.0 to 1.0)

        If the article is NOT about a specific security incident in Nigeria, return: {{"irrelevant": true}}

        JSON ONLY. NO PREAMBLE. NO EXPLANATION.
        """

        try:
            # Overriding default model in LLMService for extraction tasks
            self.llm.model = self.model
            response_text = self.llm.generate_response(
                prompt,
                system_prompt="You are a specialized security intelligence analyst focusing on Nigerian conflict data. You output only raw JSON.",
                temperature=0.1,  # Low temperature for factual extraction
                json_mode=True,
            )

            if not response_text:
                return {"status": "failed", "error": "Empty response from LLM"}

            result = json.loads(response_text)

            if result.get("irrelevant"):
                return {"status": "irrelevant", "data": None}

            return {"status": "success", "data": result}

        except Exception as e:
            error_str = str(e).lower()
            if "rate_limit_exceeded" in error_str or "429" in error_str:
                return {"status": "rate_limited", "error": str(e)}

            print(f"Extraction error: {e}")
            return {"status": "failed", "error": str(e)}
