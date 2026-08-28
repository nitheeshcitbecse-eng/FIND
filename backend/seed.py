"""Create demo app users (login accounts for officer/verifier/admin roles).

Usage:
    python seed.py

Government identity data is separate — see seed_govern_db.py, which is the
only script that ever writes to govern_db.
"""

from app.database import SessionLocal, init_db
from app.models import User
from app.security import hash_password

DEMO_USERS = [
    ("admin", "Admin User", "admin123", "admin"),
    ("officer1", "Field Officer", "officer123", "officer"),
    ("verifier1", "Senior Verifier", "verify123", "verifier"),
]


def main() -> None:
    init_db()
    db = SessionLocal()

    for username, full_name, password, role in DEMO_USERS:
        if not db.query(User).filter(User.username == username).first():
            db.add(
                User(
                    username=username,
                    full_name=full_name,
                    password_hash=hash_password(password),
                    role=role,
                )
            )
            print(f"user created: {username} / {password}  ({role})")
    db.commit()
    db.close()


if __name__ == "__main__":
    main()