import secrets
import string

from services.student_information_service import users_col, create_user


# =========================
# Password Generator
# =========================
def generate_password(length=10):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(chars) for _ in range(length))


# =========================
# Save Credentials
# =========================
def save_dean_credentials(user_id, password):
    with open("dean_credentials.txt", "a", encoding="utf-8") as f:
        f.write(f"{user_id} | {password}\n")


# =========================
# Seed Dean Account
# =========================
def seed_dean_account():
    dean_id = "dean"

    existing = users_col.find_one({"user_id": dean_id})
    if existing:
        print("ℹ️ Dean account already exists. Skipping creation.")
        return

    password = generate_password()

    result = create_user({
        "user_id": dean_id,
        "password": password,
        "role": "dean"
    })

    if not result["success"]:
        print("❌ Failed to create dean:", result["error"])
        return

    save_dean_credentials(dean_id, password)

    print("✅ Dean account created successfully")
    print("⚠️ Saved to dean_credentials.txt")
