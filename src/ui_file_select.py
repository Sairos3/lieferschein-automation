import tkinter as tk
from tkinter import filedialog
from pathlib import Path


def pick_pdf_file(initial_dir: Path) -> Path | None:
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="Select a PDF to import",
        initialdir=str(initial_dir),
        filetypes=[("PDF files", "*.pdf")],
    )
    root.destroy()
    return Path(path) if path else None