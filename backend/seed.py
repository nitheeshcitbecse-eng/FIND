"""Create demo users and enroll reference records.

Usage:
    python seed.py

Reference records are read from sample_data/persons/<slug>/ containing:
    face.jpg     (any face photo)
    finger.png   (any fingerprint image, e.g. from the SOCOFing dataset)
    info.txt     (key=value lines, all optional)

Example info.txt:
    name=Ravi Kumar
    sex=male
    age=42
    city=Chennai
    lat=13.0827
    lng=80.2707
    address=12 Anna Nagar, Chennai, Tamil Nadu 600040
    tattoo=om symbol on left forearm
    belongings=backpack, cell phone

Folders with no images are skipped. Run again after adding folders — existing
records are left alone.
"""

from pathlib import Path

from app.ai import face as face_ai
from app.ai import fingerprint as fp_ai
from app.ai import index as vindex
from app.config import SAMPLE_DIR
from app.database import SessionLocal, init_db
from app.models import ReferencePerson, User
from app.security import hash_password

DEMO_USERS = [
    ("admin", "Admin User", "admin123", "admin"),
    ("officer1", "Field Officer", "officer123", "officer"),
    ("verifier1", "Senior Verifier", "verify123", "verifier"),
]


def parse_info(path: Path) -> dict:
    data = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.split("=", 1)
                data[key.strip().lower()] = value.strip()
    return data


def find_image(folder: Path, stems: list[str]) -> Path | None:
    for stem in stems:
        for ext in (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".BMP", ".JPG", ".PNG"):
            candidate = folder / f"{stem}{ext}"
            if candidate.exists():
                return candidate
    return None


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

    persons_dir = SAMPLE_DIR / "persons"
    if not persons_dir.exists():
        persons_dir.mkdir(parents=True, exist_ok=True)
        print(f"\nCreated {persons_dir}")
        print("Add one folder per person with face.jpg / finger.png, then re-run.")
        db.close()
        return

    enrolled = 0
    for folder in sorted(p for p in persons_dir.iterdir() if p.is_dir()):
        record_ref = f"REF-{folder.name.upper()}"
        if db.query(ReferencePerson).filter(ReferencePerson.record_ref == record_ref).first():
            continue

        info = parse_info(folder / "info.txt")
        face_img = find_image(folder, ["face", "photo", "image"])
        finger_img = find_image(folder, ["finger", "fingerprint", "print"])
        if not face_img and not finger_img:
            print(f"skipped {folder.name}: no face or fingerprint image")
            continue

        person = ReferencePerson(
            record_ref=record_ref,
            name=info.get("name", folder.name.replace("_", " ").title()),
            sex=info.get("sex", "unknown"),
            age=int(info["age"]) if info.get("age", "").isdigit() else None,
            last_known_city=info.get("city", ""),
            last_known_lat=float(info["lat"]) if info.get("lat") else None,
            last_known_lng=float(info["lng"]) if info.get("lng") else None,
            address=info.get("address", ""),
            tattoo_description=info.get("tattoo", ""),
            known_belongings=info.get("belongings", ""),
            notes=info.get("notes", ""),
        )

        media_face = None
        if face_img:
            from app.storage import save_bytes

            rel = save_bytes(face_img.read_bytes(), "reference/faces", face_img.suffix.lower())
            person.face_photo_path = rel
            media_face = rel
            result = face_ai.embed_face(str((SAMPLE_DIR.parent / "media" / rel)))
            person.face_embedding = result["embedding"]

        if finger_img:
            from app.storage import save_bytes

            rel = save_bytes(
                finger_img.read_bytes(), "reference/fingerprints", finger_img.suffix.lower()
            )
            person.fingerprint_path = rel
            person.fingerprint_template = fp_ai.extract_template(
                str((SAMPLE_DIR.parent / "media" / rel))
            )

        db.add(person)
        db.commit()
        enrolled += 1
        print(f"enrolled {person.name}  face={bool(media_face)} finger={bool(finger_img)}")

    vindex.invalidate()
    total = db.query(ReferencePerson).count()
    print(f"\nEnrolled {enrolled} new record(s). Total reference records: {total}")
    print(f"Face engine: {face_ai.engine_name()}")
    db.close()


if __name__ == "__main__":
    main()