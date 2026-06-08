import os
import requests
from typing import List, Dict, Any, Optional

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

class APIClient:
    def __init__(self):
        self.base_url = BACKEND_URL

    def get_users(self) -> List[Dict[str, Any]]:
        try:
            response = requests.get(f"{self.base_url}/api/users")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Error fetching users: {e}")
            return []

    def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        try:
            response = requests.get(f"{self.base_url}/api/users/{user_id}")
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error fetching user profile: {e}")
            return None

    def get_user_memories(self, user_id: int) -> List[Dict[str, Any]]:
        try:
            response = requests.get(f"{self.base_url}/api/users/{user_id}/memories")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Error fetching user memories: {e}")
            return []

    def get_user_history(self, user_id: int) -> List[Dict[str, Any]]:
        try:
            response = requests.get(f"{self.base_url}/api/users/{user_id}/history")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Error fetching user history: {e}")
            return []

    def get_activities(self) -> List[Dict[str, Any]]:
        try:
            response = requests.get(f"{self.base_url}/api/activities")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Error fetching activities: {e}")
            return []

    def create_activity(
        self, title: str, description: str, activity_type: str, 
        start_time: str, location: str, participant_limit: int, creator_id: int,
        end_time: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        start_time and end_time should be ISO format strings (e.g. 2026-06-07T18:00:00)
        """
        payload = {
            "title": title,
            "description": description,
            "activity_type": activity_type.lower(),
            "start_time": start_time,
            "location": location,
            "participant_limit": int(participant_limit)
        }
        if end_time:
            payload["end_time"] = end_time
        try:
            response = requests.post(
                f"{self.base_url}/api/activities", 
                json=payload, 
                params={"creator_id": creator_id}
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error creating activity: {e}")
            return None

    def join_activity(self, activity_id: int, user_id: int) -> Dict[str, Any]:
        try:
            response = requests.post(
                f"{self.base_url}/api/activities/{activity_id}/join",
                json={"user_id": user_id}
            )
            if response.status_code == 200:
                return response.json()
            return {"success": False, "message": "API error joining activity"}
        except Exception as e:
            print(f"Error joining activity: {e}")
            return {"success": False, "message": f"Connection error: {e}"}

    def get_gym_classes(self) -> List[Dict[str, Any]]:
        try:
            response = requests.get(f"{self.base_url}/api/gym-classes")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Error fetching gym classes: {e}")
            return []

    def send_chat(self, user_id: int, message: str) -> str:
        payload = {
            "user_id": user_id,
            "message": message
        }
        try:
            response = requests.post(f"{self.base_url}/api/chat", json=payload)
            if response.status_code == 200:
                return response.json().get("response", "No response received.")
            detail = response.json().get("detail", "Unknown server error.")
            return f"❌ **Error**: {detail}"
        except Exception as e:
            return f"❌ **Connection Error**: Could not connect to backend server at {self.base_url}. Details: {e}"

    def get_activity_candidates(self, activity_id: int) -> List[Dict[str, Any]]:
        try:
            relative_url = f"/api/activities/{activity_id}/candidates"
            response = requests.get(f"{self.base_url}{relative_url}")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Error fetching activity candidates: {e}")
            return []

    def update_user_interests(self, user_id: int, interests: List[str]) -> Optional[Dict[str, Any]]:
        try:
            response = requests.put(
                f"{self.base_url}/api/users/{user_id}/interests",
                json=interests
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error updating user interests: {e}")
            return None

api_client = APIClient()
