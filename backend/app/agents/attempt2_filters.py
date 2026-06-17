import re
from typing import Dict
from backend.app.agents.llm import llm_client


def parse_attempt2_answers(message: str) -> Dict[str, str]:
    """
    Parses the user's answers to the 4 filter questions.
    Uses heuristics first, LLM fallback for ambiguous answers.
    Returns dict with keys: energy, social, environment, time.
    Missing answers default to neutral values.
    """
    lowered = message.lower()

    # Energy
    energy = "medium"
    if any(k in lowered for k in [
        "high energy", "lots of energy", "energized", "pumped",
        "vận động mạnh", "năng động", "cường độ cao", "mạnh mẽ", "sweaty",
    ]):
        energy = "high"
    elif any(k in lowered for k in [
        "low energy", "low", "tired", "exhausted", "drained",
        "mệt", "nhẹ nhàng", "thư giãn", "nhẹ", "không vận động nhiều", "thoải mái",
    ]):
        energy = "low"
    elif "medium" in lowered or "vừa phải" in lowered:
        energy = "medium"

    # Social
    social = "either"
    if any(k in lowered for k in [
        "group", "people", "with others", "social", "together",
        "nhóm", "đông người", "gặp bạn", "cùng bạn", "cùng mọi người",
    ]):
        social = "group"
    elif any(k in lowered for k in [
        "solo", "alone", "by myself", "on my own",
        "một mình", "cá nhân", "không cần bạn",
    ]):
        social = "solo"

    # Environment
    environment = "either"
    if "indoor" in lowered or "inside" in lowered or "trong nhà" in lowered:
        environment = "indoor"
    elif any(k in lowered for k in ["outdoor", "outside", "open air", "ngoài trời"]):
        environment = "outdoor"

    # Time
    time_available = "any"
    if any(k in lowered for k in ["30", "half hour", "quick", "nhanh", "30 phút"]):
        time_available = "30 mins"
    elif any(k in lowered for k in ["1-2 hour", "1 to 2", "couple hour", "an hour or two", "1 2 hour"]):
        time_available = "1-2 hours"
    elif any(k in lowered for k in ["full evening", "whole evening", "all night", "all evening", "cả buổi tối"]):
        time_available = "full evening"

    # LLM fallback only when at least one dimension is still ambiguous
    if llm_client.is_mock:
        return {"energy": energy, "social": social, "environment": environment, "time": time_available}

    ambiguous = social == "either" or environment == "either" or time_available == "any"
    if ambiguous:
        system_prompt = """Extract the user's answers to these 4 questions from their message.
Questions asked: (1) energy level: high/medium/low, (2) group or solo, (3) indoor or outdoor, (4) time: 30 mins/1-2 hours/full evening.
Respond with exactly 4 comma-separated values in order: energy,social,environment,time.
Use "unknown" for any that cannot be determined.
Example: low,solo,indoor,30 mins"""
        response = llm_client.run_agent(system_prompt, f"User answer: '{message}'").strip()
        parts = [p.strip() for p in response.split(",")]
        if len(parts) == 4:
            if parts[0] != "unknown":
                energy = parts[0]
            if parts[1] != "unknown":
                social = parts[1]
            if parts[2] != "unknown":
                environment = parts[2]
            if parts[3] != "unknown":
                time_available = parts[3]

    return {"energy": energy, "social": social, "environment": environment, "time": time_available}
