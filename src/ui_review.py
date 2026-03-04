import tkinter as tk
from tkinter import ttk, messagebox
import re
from typing import Dict, Any, Optional


DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")


def needs_review(data: Dict[str, Any]) -> bool:
    """Return True if required fields are missing/invalid."""
    date = (data.get("delivery_date") or "").strip()
    if not DATE_RE.match(date):
        return True
    # add more rules if you want:
    if not (data.get("delivery_note_no") or "").strip():
        return True
    if not (data.get("supplier") or "").strip():
        return True
    return False


def review_dialog(data: Dict[str, Any], title: str = "Review extracted data") -> Optional[Dict[str, Any]]:
    """
    Opens a modal dialog to correct extracted fields.
    Returns corrected dict or None if user cancels.
    """
    root = tk.Tk()
    root.title(title)
    root.geometry("520x260")
    root.resizable(False, False)

    # Make it modal-ish
    root.attributes("-topmost", True)

    frm = ttk.Frame(root, padding=12)
    frm.pack(fill="both", expand=True)

    ttk.Label(frm, text="Please review/correct the extracted fields:", font=("Segoe UI", 10, "bold")).grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
    )

    # Fields to edit
    fields = [
        ("Supplier", "supplier"),
        ("Delivery Note No", "delivery_note_no"),
        ("Delivery Date (dd.mm.yyyy)", "delivery_date"),
        ("Customer No", "customer_no"),
        ("Order No", "order_no"),
    ]

    vars_ = {}
    for i, (label, key) in enumerate(fields, start=1):
        ttk.Label(frm, text=label).grid(row=i, column=0, sticky="w", pady=4)
        v = tk.StringVar(value=(data.get(key) or ""))
        ent = ttk.Entry(frm, textvariable=v, width=40)
        ent.grid(row=i, column=1, sticky="w", pady=4)
        vars_[key] = v

    hint = ttk.Label(frm, text="Tip: Date must be exactly dd.mm.yyyy (e.g. 26.02.2026).")
    hint.grid(row=6, column=0, columnspan=2, sticky="w", pady=(8, 6))

    btns = ttk.Frame(frm)
    btns.grid(row=7, column=0, columnspan=2, sticky="e", pady=(10, 0))

    result: Optional[Dict[str, Any]] = None

    def on_ok():
        nonlocal result
        corrected = {**data}
        for _, key in fields:
            corrected[key] = vars_[key].get().strip()

        # Validate
        if not corrected["supplier"]:
            messagebox.showerror("Validation", "Supplier is required.")
            return
        if not corrected["delivery_note_no"]:
            messagebox.showerror("Validation", "Delivery Note No is required.")
            return
        if not DATE_RE.match(corrected["delivery_date"]):
            messagebox.showerror("Validation", "Date must be dd.mm.yyyy (e.g. 26.02.2026).")
            return

        result = corrected
        root.destroy()

    def on_cancel():
        nonlocal result
        result = None
        root.destroy()

    ttk.Button(btns, text="Cancel", command=on_cancel).pack(side="right")
    ttk.Button(btns, text="OK", command=on_ok).pack(side="right", padx=(0, 8))

    root.mainloop()
    return result