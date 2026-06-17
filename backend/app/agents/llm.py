import json
from openai import OpenAI
from backend.app.config import settings

class OpenRouterClient:
    def __init__(self):
        self.api_key = settings.AI_PLATFORM_API_KEY
        self.model = settings.AI_PLATFORM_MODEL

        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=settings.AI_PLATFORM_API_BASE,
                timeout=30.0,
            )
            self.is_mock = False
        else:
            self.client = None
            self.is_mock = True
            print("WARNING: AI_PLATFORM_API_KEY not found. Running in local MOCK mode.")

    def _chat(self, messages: list) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
            max_tokens=1000,
        )
        return response.choices[0].message.content

    def run_agent_with_history(self, system_prompt: str, history: list, user_prompt: str) -> str:
        if not self.is_mock and self.client:
            try:
                messages = [{"role": "system", "content": system_prompt}]
                for msg in history:
                    if msg.get("role") in ("user", "assistant"):
                        messages.append({"role": msg["role"], "content": msg["content"]})
                messages.append({"role": "user", "content": user_prompt})
                return self._chat(messages)
            except Exception as e:
                print(f"Error calling VNG Cloud AI Platform API (multi-turn): {e}. Using mock fallback.")
                return self._mock_respond(system_prompt)
        return self._mock_respond(system_prompt)

    def run_agent(self, system_prompt: str, user_prompt: str) -> str:
        if not self.is_mock and self.client:
            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
                return self._chat(messages)
            except Exception as e:
                print(f"Error calling VNG Cloud AI Platform API: {e}. Using mock fallback for this request.")
                return self._mock_respond(system_prompt)
        return self._mock_respond(system_prompt)

    def _mock_respond(self, system_prompt: str) -> str:
        if "extract" in system_prompt.lower() or "extraction" in system_prompt.lower():
            return json.dumps({
                "activity_type": "other",
                "start_time": "18:00",
                "required_players": 2,
                "title": "Activity",
                "location": "Company Premises",
                "missing_fields": []
            })
        if "rejection classifier" in system_prompt.lower():
            return "NOT_REJECTION"
        if "extract the user" in system_prompt.lower() and "4 questions" in system_prompt.lower():
            return "medium,either,either,any"
        return "[Mock mode — set AI_PLATFORM_API_KEY to enable real responses]"

# Single instance client
llm_client = OpenRouterClient()
