import uuid
import bcrypt
from pymongo import MongoClient
import redis

# ----------------------------
# MongoDB Connection
# ----------------------------

mongo_client = MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["university_portal"]
users_collection = mongo_db["users"]

# ----------------------------
# Redis Connection
# ----------------------------

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)

SESSION_TTL_SECONDS = 600



def verify_password(password: str, stored_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), stored_hash.encode())

def authenticate_user(user_id: str, password: str) -> dict:
    user = users_collection.find_one({"user_id": user_id})

    if not user:
        return {"success": False}

    if not verify_password(password, user["password"]):
        return {"success": False}

    return {
        "success": True,
        "userID": user["user_id"],
        "role": user["role"]
    }


def create_user_session(userID: str, role: str) -> dict:
    session_id = str(uuid.uuid4())

    redis_client.hset(
        session_id,
        mapping={
            "userID": userID,
            "role": role
        }
    )
    redis_client.expire(session_id, SESSION_TTL_SECONDS)

    return {
        "success": True,
        "sessionID": session_id
    }

def refresh_user_session(session_id: str) -> dict:
    if not redis_client.exists(session_id):
        return {
            "success": False,
            "message": "Session not found or expired"
        }

    redis_client.expire(session_id, SESSION_TTL_SECONDS)

    return {
        "success": True
    }

def validate_session(sessionID: str) -> dict:
    if not redis_client.exists(sessionID):
        return {"valid": False}

    session_data = redis_client.hgetall(sessionID)

    return {
        "valid": True,
        "userID": session_data["userID"],
        "role": session_data["role"]
    }
