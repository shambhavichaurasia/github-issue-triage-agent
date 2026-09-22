"""Load settings from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    groq_api_key: str | None
    gemini_api_key: str | None
    github_token: str | None
    groq_model: str
    gemini_model: str

    def require_github_token(self) -> str:
        if not self.github_token:
            raise ValueError(
                "GITHUB_TOKEN is missing. Copy .env.example to .env and add a GitHub PAT."
            )
        return self.github_token

    def require_llm_key(self) -> tuple[str, str, str]:
        provider = self.llm_provider.lower().strip()
        if provider == "groq":
            if not self.groq_api_key:
                raise ValueError("GROQ_API_KEY is missing in .env")
            return provider, self.groq_api_key, self.groq_model
        if provider == "gemini":
            if not self.gemini_api_key:
                raise ValueError("GEMINI_API_KEY is missing in .env")
            return provider, self.gemini_api_key, self.gemini_model
        raise ValueError("LLM_PROVIDER must be 'groq' or 'gemini'")


def get_settings() -> Settings:
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "groq"),
        groq_api_key=os.getenv("GROQ_API_KEY") or None,
        gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
        github_token=os.getenv("GITHUB_TOKEN") or None,
        groq_model=os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
    )
