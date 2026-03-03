from pathlib import Path
import re

def safe_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9ÄÖÜäöüß._-]+", "_", s).strip("_")

def archive_pdf(pdf_path: Path, archive_root: Path, supplier: str, delivery_date: str | None) -> Path:
    # delivery_date format: dd.mm.yyyy (or dd.mm.yyy in your template)
    yyyy_mm = "unknown-date"
    if delivery_date and len(delivery_date.split(".")) == 3:
        parts = delivery_date.split(".")
        yyyy = parts[2]
        mm = parts[1]
        if len(yyyy) == 3:  # your template 1 has "202"
            yyyy = "unknown-year"
        yyyy_mm = f"{yyyy}-{mm}"

    target_dir = archive_root / safe_name(supplier or "UNKNOWN") / yyyy_mm
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / pdf_path.name
    # Copy (not move) so input remains intact during testing:
    target_path.write_bytes(pdf_path.read_bytes())
    return target_path