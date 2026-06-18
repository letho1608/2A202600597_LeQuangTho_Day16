import os
import time
from abc import ABC, abstractmethod
from typing import Optional, Tuple
import google.generativeai as genai
from openai import OpenAI
from anthropic import Anthropic
from groq import Groq
import ollama


class LLMProvider(ABC):
    @abstractmethod
    def call(
        self, system_prompt: str, user_prompt: str, json_mode: bool = False
    ) -> Tuple[str, int, float]:
        pass


class GeminiProvider(LLMProvider):
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found")
        genai.configure(api_key=api_key)
        self.model = model_name

    def call(
        self, system_prompt: str, user_prompt: str, json_mode: bool = False
    ) -> Tuple[str, int, float]:
        start = time.time()
        config = {"response_mime_type": "application/json"} if json_mode else {}
        model = genai.GenerativeModel(self.model)
        response = model.generate_content(
            contents=[
                {
                    "role": "user",
                    "parts": [f"System: {system_prompt}\n\nUser: {user_prompt}"],
                }
            ],
            generation_config=config,
        )
        latency = int((time.time() - start) * 1000)
        tokens = (
            response.usage_metadata.total_token_count
            if hasattr(response, "usage_metadata")
            else 0
        )
        return response.text, tokens, latency


class OpenAIProvider(LLMProvider):
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model_name

    def call(
        self, system_prompt: str, user_prompt: str, json_mode: bool = False
    ) -> Tuple[str, int, float]:
        start = time.time()
        response_format = {"type": "json_object"} if json_mode else None
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=response_format,
        )
        latency = int((time.time() - start) * 1000)
        tokens = response.usage.total_tokens
        return response.choices[0].message.content, tokens, latency


class AnthropicProvider(LLMProvider):
    def __init__(self, model_name: str = "claude-3-5-sonnet-20240620"):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = model_name

    def call(
        self, system_prompt: str, user_prompt: str, json_mode: bool = False
    ) -> Tuple[str, int, float]:
        start = time.time()
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        latency = int((time.time() - start) * 1000)
        tokens = response.usage.input_tokens + response.usage.output_tokens
        return response.content[0].text, tokens, latency


class GroqProvider(LLMProvider):
    def __init__(self, model_name: str = "llama-3.1-70b-versatile"):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = model_name

    def call(
        self, system_prompt: str, user_prompt: str, json_mode: bool = False
    ) -> Tuple[str, int, float]:
        start = time.time()
        response_format = {"type": "json_object"} if json_mode else None
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=response_format,
        )
        latency = int((time.time() - start) * 1000)
        tokens = response.usage.total_tokens
        return response.choices[0].message.content, tokens, latency


class OllamaProvider(LLMProvider):
    def __init__(self, model_name: str = "minimax-m3:cloud"):
        self.model = model_name
        # Note: Ollama client connects to http://localhost:11434 by default

    def call(
        self, system_prompt: str, user_prompt: str, json_mode: bool = False
    ) -> Tuple[str, int, float]:
        start = time.time()
        options = {"format": "json"} if json_mode else {}
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = ollama.chat(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    **options,
                )
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Ollama error: {e}. Retrying in {2**attempt}s...")
                    time.sleep(2**attempt)
                else:
                    raise e
                    
        latency = int((time.time() - start) * 1000)
        # Estimate tokens as Ollama doesn't return exact counts in the simple chat response
        # or we could use eval_count + prompt_eval_count if available.
        # It's usually in response['eval_count'] + response['prompt_eval_count']
        eval_count = response.get("eval_count") or 0
        prompt_eval_count = response.get("prompt_eval_count") or 0
        tokens = eval_count + prompt_eval_count
        if tokens == 0:
            tokens = (
                len(system_prompt.split())
                + len(user_prompt.split())
                + len(response["message"]["content"].split())
            )

        return response["message"]["content"], tokens, latency


def get_provider(name: str, model: Optional[str] = None) -> LLMProvider:
    name = name.lower()
    if name == "gemini":
        return GeminiProvider(model or "gemini-1.5-flash")
    elif name == "openai":
        return OpenAIProvider(model or "gpt-4o-mini")
    elif name == "anthropic":
        return AnthropicProvider(model or "claude-3-5-sonnet-20240620")
    elif name == "groq":
        return GroqProvider(model or "llama-3.1-70b-versatile")
    elif name == "ollama":
        return OllamaProvider(model or "minimax-m3:cloud")
    else:
        raise ValueError(f"Unknown provider: {name}")
