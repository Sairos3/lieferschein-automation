import tkinter as tk
from tkinter import messagebox


def duplicate_dialog(filename):
    root = tk.Tk()
    root.withdraw()

    answer = messagebox.askyesno(
        "Duplicate detected",
        f"{filename} looks like a duplicate.\n\nDo you want to edit the data?"
    )

    root.destroy()
    return answer