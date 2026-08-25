from typing import Optional

from groq import Groq

from ..core.config import settings


class LLMService:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = "openai/gpt-oss-120b"  # High-quality model for reasoning
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("GROQ_API_KEY not found in environment.")
            self._client = Groq(api_key=self.api_key)
        return self._client

    def generate_response(
        self,
        prompt: str,
        system_prompt: str = "You are an expert security analyst specializing in Nigerian security affairs.",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        json_mode: bool = False,
    ) -> Optional[str]:
        """
        Generic method to generate text responses from the LLM.
        """
        try:
            kwargs = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            completion = self.client.chat.completions.create(**kwargs)
            return completion.choices[0].message.content
        except Exception as e:
            error_str = str(e).lower()
            if "rate_limit" in error_str or "429" in error_str:
                # Re-raise so the ExtractorService can detect it
                raise e
            print(f"[LLM SERVICE ERROR] {e}")
            return None

    def get_travel_advisory(
        self,
        origin: str,
        destination: str,
        risk_score: float,
        states: list,
        distance: float,
    ) -> str:
        """
        Specialized method for generating dynamic travel advisories.
        """
        prompt = f"""
        Generate a concise, professional travel safety advisory for a trip in Nigeria.
        Output format:
        - One short summary sentence (<= 25 words).
        - Then 2 bullet points with short actionable tips (each <= 12 words).

        Origin: {origin}
        Destination: {destination}
        Total Distance: {distance} km
        States to be passed: {", ".join(states)}
        Aggregated Route Risk Score: {risk_score}/100 (Higher is more dangerous)

        The advisory must be direct, non-technical, and never exceed 3 lines total.
        """

        # Ask for a short response and limit tokens
        advisory = self.generate_response(prompt, temperature=0.6, max_tokens=200)
        return (
            advisory
            or "Standard safety precautions apply. Maintain situational awareness."
        )
