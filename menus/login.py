from services.auth_user_service import authenticate_user
import time

def login_screen():
    while True:
        user_id = input("Insert UserID: ")
        password = input("Insert password: ")
        result = authenticate_user(user_id, password)
        if result['success'] == False:
            print("⚠️ Login failed. Please check your user ID and password.")
            time.sleep(1)
        else:
            return result
