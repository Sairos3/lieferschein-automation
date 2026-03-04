import re
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class ParsedItem:
    line_no: int
    article_no: str | None
    description: str | None
    quantity: float
    unit_price: float | None
    line_total: float | None

def parse_template1(text: str) -> Dict[str, Any]:
    def m(pattern: str, flags: int = 0):
        mm = re.search(pattern, text, flags)
        return mm.group(1).strip() if mm else None

    # Supplier/company in your PDF: "Mustermann GmbH Kontakt:"
    supplier = m(r"^([A-Za-zÄÖÜäöüß0-9 .,&-]+)\s+Kontakt:", flags=re.MULTILINE)

    delivery_note_no = m(r"Liefer-Nr\.\s*:\s*([A-Za-z0-9-]+)")
    delivery_date = m(r"Datum\s*:\s*([0-9]{2}\.[0-9]{2}\.[0-9]{3,4})")  # your sample has 3-4 digits
    customer_no = m(r"Kunden-Nr\.\s*:\s*([A-Za-z0-9-]+)")
    order_no = m(r"Bestell-Nr\.\s*:\s*([A-Za-z0-9-]+)")
    tax_no = m(r"Steuer-Nr\.\:\s*([A-Z0-9]+)")
    
    items: List[ParsedItem] = []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    line_no = 1
    for ln in lines:
        # Example line: "1 Stk. 12345 Artikel 60,00 EUR 60,00 EUR"
        mm = re.match(
            r"^(\d+(?:[,.]\d+)?)\s+Stk\.\s+([A-Za-z0-9-]+)\s+(.+?)\s+([0-9]+(?:[,.][0-9]{2})?)\s+EUR\s+([0-9]+(?:[,.][0-9]{2})?)\s+EUR$",
            ln
        )
        if mm:
            qty = float(mm.group(1).replace(",", "."))
            art = mm.group(2)
            desc = mm.group(3).strip()
            unit = float(mm.group(4).replace(",", "."))
            total = float(mm.group(5).replace(",", "."))
            items.append(ParsedItem(line_no, art, desc, qty, unit, total))
            line_no += 1
    def money(pattern: str):
        mm = re.search(pattern, text)
        if not mm:
            return None
        return float(mm.group(1).replace(".", "").replace(",", "."))

    subtotal = money(r"Zwischensumme\s+([0-9]+(?:[.,][0-9]{2})?)\s+EUR")
    vat = money(r"19%\s+MwSt\.\s+([0-9]+(?:[.,][0-9]{2})?)\s+EUR")
    total = money(r"Gesamtbetrag\s+([0-9]+(?:[.,][0-9]{2})?)\s+EUR")

    def parse_money(value: str) -> float:
        # "1.234,56" -> 1234.56  |  "70,00" -> 70.00
        return float(value.replace(".", "").replace(",", "."))

    subtotal = None
    vat = None
    total = None

    m_sub = re.search(r"Zwischensumme\s+([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)\s+EUR", text)
    if m_sub:
        subtotal = parse_money(m_sub.group(1))

    m_vat = re.search(r"(?:19%\s+MwSt\.|MwSt\.\s*19%)\s+([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)\s+EUR", text)
    if m_vat:
        vat = parse_money(m_vat.group(1))

    m_total = re.search(r"Gesamtbetrag\s+([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)\s+EUR", text)
    if m_total:
        total = parse_money(m_total.group(1))
    return {
        "supplier": supplier,
        "delivery_note_no": delivery_note_no,
        "delivery_date": delivery_date,
        "customer_no": customer_no,
        "order_no": order_no,
        "subtotal": subtotal,
        "vat": vat,
        "total": total,
        "items": items,
        "tax_no": tax_no,
    }