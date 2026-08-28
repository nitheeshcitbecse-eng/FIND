"""Insert sample records directly into govern_db.

This is the ONLY way govern_db is ever written to — no API endpoint creates,
edits, or deletes GovPerson rows. Once the real government database is
available, this script (or its successor) is how a snapshot gets loaded.

Usage:
    python seed_govern_db.py

Records are read from sample_data/govern_persons/<slug>/ containing:
    face.jpg     (any face photo)
    finger.png   (any fingerprint image, e.g. from the SOCOFing dataset)
    info.txt     (key=value lines)

Example info.txt:
    aadhaar=123456789012
    name=Ravi Kumar
    address=12 Anna Nagar, Chennai, Tamil Nadu 600040

Folders with no images, or missing an aadhaar number, are skipped. Re-running
is safe: existing records are matched and updated by aadhaar_number, never
duplicated.
"""

from pathlib import Path

from app.ai import face as face_ai
from app.ai import fingerprint as fp_ai
from app.config import SAMPLE_DIR
from app.govern_database import GovernSessionLocal, init_govern_db
from app.govern_models import GovPerson
from app.storage import save_bytes


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
    init_govern_db()
    db = GovernSessionLocal()

    persons_dir = SAMPLE_DIR / "govern_persons"
    if not persons_dir.exists():
        persons_dir.mkdir(parents=True, exist_ok=True)
        print(f"\nCreated {persons_dir}")
        print("Add one folder per person with face.jpg / finger.png / info.txt, then re-run.")
        db.close()
        return

    enrolled = updated = 0
    for folder in sorted(p for p in persons_dir.iterdir() if p.is_dir()):
        info = parse_info(folder / "info.txt")
        aadhaar = info.get("aadhaar", "").strip()
        if not aadhaar:
            print(f"skipped {folder.name}: no aadhaar= in info.txt")
            continue

        face_img = find_image(folder, ["face", "photo", "image"])
        finger_img = find_image(folder, ["finger", "fingerprint", "print"])
        if not face_img and not finger_img:
            print(f"skipped {folder.name}: no face or fingerprint image")
            continue

        existing = db.query(GovPerson).filter(GovPerson.aadhaar_number == aadhaar).first()
        person = existing or GovPerson(aadhaar_number=aadhaar)
        person.name = info.get("name", folder.name.replace("_", " ").title())
        person.address = info.get("address", "")

        if face_img:
            with save_bytes(
                face_img.read_bytes(), "govern/faces", face_img.suffix.lower(), target="govern"
            ) as (rel, local_path):
                person.face_photo_path = rel
                result = face_ai.embed_face(local_path)
                person.face_embedding = result["embedding"]

        if finger_img:
            with save_bytes(
                finger_img.read_bytes(), "govern/fingerprints", finger_img.suffix.lower(),
                target="govern",
            ) as (rel, local_path):
                person.fingerprint_path = rel
                person.fingerprint_template = fp_ai.extract_template(local_path)

        if existing:
            updated += 1
        else:
            db.add(person)
            enrolled += 1
        db.commit()
        print(f"{'updated' if existing else 'enrolled'} {person.name} ({aadhaar})")

    total = db.query(GovPerson).count()
    print(f"\n{enrolled} new, {updated} updated. Total govern_db records: {total}")
    db.close()


if __name__ == "__main__":
    main()
