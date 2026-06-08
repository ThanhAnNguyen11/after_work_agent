import json
import re
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from backend.app.config import settings

class OpenRouterClient:
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_MODEL
        
        if self.api_key:
            # OpenRouter is OpenAI-compatible
            self.llm = ChatOpenAI(
                openai_api_base=settings.OPENROUTER_API_BASE,
                openai_api_key=self.api_key,
                model_name=self.model,
                temperature=0.2,
                max_tokens=1000,
                timeout=5.0,
                default_headers={
                    "HTTP-Referer": "https://github.com/google/antigravity",
                    "X-Title": "After Work Agent Hackathon"
                }
            )
            self.is_mock = False
        else:
            self.llm = None
            self.is_mock = True
            print("WARNING: OPENROUTER_API_KEY not found. Running in local MOCK mode.")

    def run_agent(self, system_prompt: str, user_prompt: str, expected_format: str = "text") -> str:
        """
        Run LLM with system prompt and user prompt.
        If in mock mode, uses deterministic parsing rules to return realistic responses.
        """
        if not self.is_mock and self.llm:
            try:
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ]
                response = self.llm.invoke(messages)
                return response.content
            except Exception as e:
                print(f"Error calling OpenRouter API: {e}. Falling back to Mock Mode permanently.")
                self.is_mock = True
                # fall through to mock
        
        return self._mock_respond(system_prompt, user_prompt, expected_format)

    def _mock_respond(self, system_prompt: str, user_prompt: str, expected_format: str) -> str:
        """
        Generates realistic responses for each agent in mock mode.
        """
        # 1. Activity Extraction Agent
        if "extract" in system_prompt.lower() or "extraction" in system_prompt.lower():
            # Get the exact text from the prompt (inside single quotes)
            text_to_parse = user_prompt
            match = re.search(r"text: '(.*)'", user_prompt)
            if match:
                text_to_parse = match.group(1)
                
            lowered_text = text_to_parse.lower()
            activity_type = "other"
            if "foot" in lowered_text:
                activity_type = "football"
            elif "gym" in lowered_text:
                activity_type = "gym"
            elif "yoga" in lowered_text:
                activity_type = "yoga"
            elif "board" in lowered_text or "game" in lowered_text:
                activity_type = "board games"
            elif "running" in lowered_text or "run" in lowered_text:
                activity_type = "running"
            elif "zumba" in lowered_text:
                activity_type = "zumba"
            elif "combat" in lowered_text:
                activity_type = "body combat"
            elif "coffee" in lowered_text:
                activity_type = "coffee"
            elif "badminton" in lowered_text:
                activity_type = "badminton"
            elif "ai" in lowered_text or "study" in lowered_text:
                activity_type = "ai"

            # Extract start time
            start_time = "18:00" # Default
            time_match = re.search(r'(\d{1,2})\s*(?:PM|AM|pm|am)', lowered_text)
            if time_match:
                hour = int(time_match.group(1))
                if "pm" in lowered_text and hour < 12:
                    hour += 12
                start_time = f"{hour:02d}:00"
            else:
                time_match_24 = re.search(r'(\d{2}):(\d{2})', lowered_text)
                if time_match_24:
                    start_time = f"{time_match_24.group(1)}:{time_match_24.group(2)}"

            # Extract required participants / players needed
            required_players = 2  # Default
            players_match = re.search(r'(?:need|want|missing)\s*(\d+)', lowered_text, re.IGNORECASE)
            if players_match:
                required_players = int(players_match.group(1))
            else:
                players_match_alt = re.search(r'(\d+)\s*(?:more|players|members|people)', lowered_text, re.IGNORECASE)
                if players_match_alt:
                    required_players = int(players_match_alt.group(1))

            extracted = {
                "activity_type": activity_type,
                "start_time": start_time,
                "required_players": required_players,
                "title": f"{activity_type.capitalize()} Game" if activity_type != "board games" else "Board Game Night",
                "location": "Company Premises"
            }
            return json.dumps(extracted)

        # 2. Discovery Agent (Routine Breaking)
        elif "discovery" in system_prompt.lower():
            if "gym" in user_prompt.lower():
                return "You have attended gym activities consistently. I recommend a social activity to meet new people and break your routine."
            else:
                return "You have been in a consistent routine. Trying something new will expand your horizons."

        # 3. Social Opportunity Agent
        elif "social opportunity" in system_prompt.lower():
            return "This activity includes participants from outside your department (e.g. Data Platform, BIZ), which is a great opportunity to expand your organizational network."

        # 4. Reflection Agent
        elif "reflection" in system_prompt.lower() or "memory" in system_prompt.lower():
            # Extract memory insights
            if "bored" in user_prompt.lower() and "gym" in user_prompt.lower():
                return "The user is bored of going to the gym every day and wants alternative activities."
            elif "football" in user_prompt.lower():
                return "The user loves playing football and likes to join sports."
            return "The user is exploring activities outside their team."

        # 5. Recommendation Agent
        else:
            if "yoga class" in user_prompt.lower() or "try yoga" in user_prompt.lower():
                return (
                    "You should definitely try a Yoga class! It's a wonderful way to build flexibility, relax, and connect with colleagues in a low-pressure environment.\n\n"
                    "We have a **Gym Class: Yoga** session coming up on Monday, Wednesday, and Friday from 12:00 to 13:00 (Location: Upfit VNG Studio Room A) with instructor Ngọc. It's a beginner-friendly class, and since you're interested in health and wellness, it would be a perfect opportunity to try it out!"
                )
            elif "tomorrow" in user_prompt.lower() or "monday" in user_prompt.lower():
                return (
                    "Tonight, there are two interesting opportunities worth exploring:\n\n"
                    "1. **Gym Class: Yoga** from 12:00 to 13:00 (Location: Upfit VNG Studio Room A). It is a great flexibility workout matching your interest in health.\n"
                    "2. **Catan & Avalon Board Game Night** from 18:00 to 20:00 (Location: Pantry Area 2nd Floor). This is a fun board game session hosted by HR."
                )
            elif "bored" in user_prompt.lower() or "routine trap = true" in user_prompt.lower():
                return (
                    "⚡ **UNCOMFORT ZONE PASS ACTIVATED** ⚡\n"
                    "Nguyen, you have attended Gym 5 times in a row! Master level achieved. Tonight, we challenge you to break the loop by exploring other communities:\n\n"
                    "1. **Football Friendly Match 7v7** from 18:00 to 19:00 (Location: Z-Plex Football Field). A casual game with colleagues outside your immediate squad.\n"
                    "2. **AI Sharing: Large Language Models** from 18:30 to 19:30 (Location: Meeting Room 3A). It features participants from Data Platform and Business teams, which is a great chance to learn something new."
                )
            elif "new employee" in user_prompt.lower() or "onboard" in user_prompt.lower() or "minhhoang" in user_prompt.lower():
                return (
                    "Welcome to the team! Based on your profile, here are the recommendations for you:\n\n"
                    "1. **AI Sharing: Large Language Models** from 18:30 to 19:30 (Location: Meeting Room 3A). A great way to connect with the tech community outside PCT.\n"
                    "2. **Gym Class: Running Club** on Wednesday from 18:00 to 19:00 (Location: Office Lobby). A fun, low-pressure way to hang out with members from your division."
                )
            elif "football" in user_prompt.lower():
                return (
                    "Here are the football matches:\n\n"
                    "1. **Football Friendly Match 7v7** from 18:00 to 19:00 (Location: Z-Plex Football Field). Casual friendly match hosted by the TEP squad."
                )
            else:
                # Standard recommendation response
                return (
                    "Tonight, there are three interesting activities worth exploring:\n\n"
                    "1. **Football Friendly Match 7v7** from 18:00 to 19:00 (Location: Z-Plex Football Field). This is a casual game matching your sports interest.\n"
                    "2. **AI Sharing: Large Language Models in Production** from 18:30 to 19:30 (Location: Meeting Room 3A). This features data scientists and engineers sharing production experience.\n"
                    "3. **Gym Class: Yoga** from 18:00 to 19:00 (Location: Upfit VNG Studio Room A). Flexibility session with instructor Ngọc."
                )

# Single instance client
llm_client = OpenRouterClient()
