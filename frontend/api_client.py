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
        end_time: Optional[str] = None, guidelines: Optional[str] = None
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
        if guidelines:
            payload["guidelines"] = guidelines
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

    def delete_activity(self, activity_id: int, user_id: int) -> Dict[str, Any]:
        try:
            response = requests.delete(
                f"{self.base_url}/api/activities/{activity_id}",
                params={"user_id": user_id}
            )
            if response.status_code == 200:
                return response.json()
            return {"success": False, "message": response.json().get("detail", "API error")}
        except Exception as e:
            print(f"Error deleting activity: {e}")
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
            relative_url = f"/api/users/{user_id}/interests"
            response = requests.put(
                f"{self.base_url}{relative_url}",
                json=interests
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error updating user interests: {e}")
            return None

    def log_recommendation(self, user_id: int, activity_id: Optional[int] = None, gym_class_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        payload = {
            "user_id": user_id,
            "activity_id": activity_id,
            "gym_class_id": gym_class_id
        }
        try:
            response = requests.post(f"{self.base_url}/api/recommendations/log", json=payload)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error logging recommendation: {e}")
            return None

    def update_recommendation_status(self, log_id: int, status: str) -> Optional[Dict[str, Any]]:
        try:
            response = requests.put(
                f"{self.base_url}/api/recommendations/log/{log_id}/status",
                json={"status": status}
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error updating recommendation status: {e}")
            return None

    def update_recommendation_status_by_user(
        self, user_id: int, status: str, activity_id: Optional[int] = None, gym_class_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        params = {}
        if activity_id is not None:
            params["activity_id"] = activity_id
        if gym_class_id is not None:
            params["gym_class_id"] = gym_class_id
        try:
            response = requests.put(
                f"{self.base_url}/api/recommendations/log/user/{user_id}/status",
                json={"status": status},
                params=params
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Error updating recommendation status by user: {e}")
            return []

    def create_user_experience(
        self, user_id: int, activity_id: Optional[int] = None, gym_class_id: Optional[int] = None,
        energy_rating: Optional[int] = None, connections_made: int = 0, notes: Optional[str] = None,
        communities_enjoyed: List[str] = []
    ) -> Optional[Dict[str, Any]]:
        payload = {
            "user_id": user_id,
            "activity_id": activity_id,
            "gym_class_id": gym_class_id,
            "energy_rating": energy_rating,
            "connections_made": connections_made,
            "notes": notes,
            "communities_enjoyed": communities_enjoyed
        }
        try:
            response = requests.post(f"{self.base_url}/api/users/{user_id}/experiences", json=payload)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error creating user experience: {e}")
            return None

    def get_user_experiences(self, user_id: int) -> List[Dict[str, Any]]:
        try:
            response = requests.get(f"{self.base_url}/api/users/{user_id}/experiences")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Error fetching user experiences: {e}")
            return []

    def get_pending_journal_prompt(self, user_id: int) -> Dict[str, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/users/{user_id}/journal/pending")
            if response.status_code == 200:
                return response.json()
            return {"prompt": False}
        except Exception as e:
            print(f"Error fetching pending journal prompt: {e}")
            return {"prompt": False}

    def resolve_journal_prompt(
        self, user_id: int, status: str, activity_id: Optional[int] = None,
        gym_class_id: Optional[int] = None, custom_activity: Optional[str] = None
    ) -> Dict[str, Any]:
        payload = {
            "status": status,
            "activity_id": activity_id,
            "gym_class_id": gym_class_id,
            "custom_activity": custom_activity
        }
        try:
            response = requests.post(f"{self.base_url}/api/users/{user_id}/journal/resolve", json=payload)
            if response.status_code == 200:
                return response.json()
            return {"success": False, "message": "API error resolving journal prompt"}
        except Exception as e:
            print(f"Error resolving journal prompt: {e}")
            return {"success": False, "message": f"Connection error: {e}"}

    def get_notifications(self, user_id: int) -> List[Dict[str, Any]]:
        try:
            response = requests.get(f"{self.base_url}/api/users/{user_id}/notifications")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Error fetching notifications: {e}")
            return []

    def mark_notification_read(self, notification_id: int) -> Dict[str, Any]:
        try:
            response = requests.put(f"{self.base_url}/api/notifications/{notification_id}/read")
            if response.status_code == 200:
                return response.json()
            return {"success": False, "message": "API error marking notification as read"}
        except Exception as e:
            print(f"Error marking notification as read: {e}")
            return {"success": False, "message": f"Connection error: {e}"}

    def login(self, domain, password) -> Dict[str, Any]:
        try:
            response = requests.post(f"{self.base_url}/api/auth/login", json={"domain": domain, "password": password})
            if response.status_code == 200:
                return response.json()
            return {"success": False, "message": "API error logging in"}
        except Exception as e:
            print(f"Error logging in: {e}")
            return {"success": False, "message": f"Connection error: {e}"}

    def register(self, domain, password) -> Dict[str, Any]:
        try:
            response = requests.post(f"{self.base_url}/api/auth/register", json={"domain": domain, "password": password})
            if response.status_code == 200:
                return response.json()
            return {"success": False, "message": "API error registering"}
        except Exception as e:
            print(f"Error registering: {e}")
            return {"success": False, "message": f"Connection error: {e}"}

    def me(self, token: str) -> Dict[str, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/auth/me", params={"token": token})
            if response.status_code == 200:
                return response.json()
            return {"success": False, "message": "Invalid session"}
        except Exception as e:
            return {"success": False, "message": f"Connection error: {e}"}

    def logout(self, token: str) -> None:
        try:
            requests.post(f"{self.base_url}/api/auth/logout", params={"token": token})
        except Exception:
            pass

    def dev_reset(self) -> Dict[str, Any]:
        try:
            response = requests.post(f"{self.base_url}/api/dev/reset")
            if response.status_code == 200:
                return response.json()
            return {"success": False, "message": "Reset failed"}
        except Exception as e:
            return {"success": False, "message": f"Connection error: {e}"}

    def onboard_user(self, user_id: int, onboarding_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            response = requests.post(f"{self.base_url}/api/users/{user_id}/onboard", json=onboarding_data)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error onboarding user: {e}")
            return None

api_client = APIClient()
