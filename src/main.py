import json
import logging
from pathlib import Path
from src.pdf_text import extract_text
from src.parsers.template1 import parse_template1
from src.db import get_con, insert_delivery_note, upsert_supplier, delivery_note_exists
from src.export_excel import export_to_excel
from src.archive import archive_pdf
from src.logging_config import setup_logging
from src.ui_review import needs_review, review_dialog
from src.ui_duplicate import duplicate_dialog

def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    cfg = load_config()
    input_dir = Path(cfg["paths"]["input_dir"])
    db_path = Path(cfg["paths"]["db_path"])

    pdfs = sorted(input_dir.glob("*.pdf"))
    logger.info(f"Found {len(pdfs)} PDF(s) in {input_dir.resolve()}")
    for i, p in enumerate(pdfs, start=1):
        print(f"  {i}. {p.name}")

    if not pdfs:
        return

    imported = 0
    skipped = 0

    for pdf_path in pdfs:

        # Skip scanned PDFs
        if "scanned" in pdf_path.name.lower():
            print(f"\n--- SKIP (scanned for now) --- {pdf_path.name}")
            skipped += 1
            continue

        logger.info(f"Processing file: {pdf_path.name}")

        text = extract_text(pdf_path)
        result = parse_template1(text)

        # ---- Totals validation ----
        items_sum = round(sum((it.line_total or 0) for it in result["items"]), 2)
        subtotal = result.get("subtotal")
        vat = result.get("vat")
        total = result.get("total")

        tol = 0.01

        if subtotal is not None and abs(items_sum - subtotal) > tol:
            logger.warning(
                f"Subtotal mismatch in {pdf_path.name}: items_sum={items_sum} subtotal={subtotal}"
            )

        if subtotal is not None and vat is not None and total is not None:
            calc_total = round(subtotal + vat, 2)
            if abs(calc_total - total) > tol:
                logger.warning(
                    f"Total mismatch in {pdf_path.name}: subtotal+vat={calc_total} total={total}"
                )

        logger.info(f"Totals: subtotal={subtotal} vat={vat} total={total}")

        print("  supplier:", result["supplier"])
        print("  delivery_note_no:", result["delivery_note_no"])
        print("  delivery_date:", result["delivery_date"])
        print("  items:", len(result["items"]))

        # ---- Manual review UI ----
        if needs_review(result):
            logger.warning(f"Needs manual review: {pdf_path.name}")

            corrected = review_dialog(result, title=f"Review: {pdf_path.name}")

            if corrected is None:
                logger.warning(f"User cancelled review, skipping: {pdf_path.name}")
                skipped += 1
                continue

            result = corrected
            logger.info(f"User corrected data for: {pdf_path.name}")

        # ---- Save to database ----
        with get_con(db_path) as con:

            # Check duplicate first
            supplier_id = upsert_supplier(
                con,
                (result.get("supplier") or "UNKNOWN"),
                (result.get("tax_no") or "")
            )

            if delivery_note_exists(
                con,
                supplier_id=supplier_id,
                delivery_date=result.get("delivery_date"),
                customer_no=result.get("customer_no"),
                order_no=result.get("order_no"),
                tax_no=result.get("tax_no"),
            ):

                logger.warning(f"Duplicate detected: {pdf_path.name}")

                if duplicate_dialog(pdf_path.name):

                    corrected = review_dialog(result, title=f"Edit duplicate: {pdf_path.name}")

                    if corrected is None:
                        skipped += 1
                        continue

                    result = corrected
                    logger.info("User edited duplicate data")

                else:
                    skipped += 1
                    logger.info("User confirmed duplicate skip")
                    continue

            try:
                dn_id = insert_delivery_note(con, result, source_pdf=pdf_path.name)
                con.commit()

                logger.info(f"Saved to DB. delivery_note_id={dn_id}")
                imported += 1

            except Exception:
                logger.exception("Unexpected error while processing file")
                skipped += 1
                continue
        # ---- Archive PDF ----
        archive_root = Path(cfg["paths"]["archive_dir"])
        archived_to = archive_pdf(pdf_path, archive_root, result["supplier"], result["delivery_date"])
        print("  Archived to:", archived_to)
    print(f"\nDone. Imported={imported}, Skipped={skipped}")

    output_file = Path(cfg["paths"]["output_dir"]) / "master.xlsx"
    export_to_excel(db_path, output_file)

if __name__ == "__main__":
    main()