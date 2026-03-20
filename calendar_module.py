"""Simple calendar module to display today's date.

Usage:
  python calendar_module.py
  python calendar_module.py --gui
"""

from __future__ import annotations

import argparse
from datetime import datetime
import tkinter as tk
from tkinter import ttk


def get_today_date() -> str:
    """Return today's date in YYYY-MM-DD format."""
    return datetime.now().strftime("%Y-%m-%d")


def show_cli() -> None:
    """Print today's date in terminal."""
    print(f"Today's date: {get_today_date()}")


def show_gui() -> None:
    """Show today's date in a small Tkinter window."""
    root = tk.Tk()
    root.title("Calendar Module")
    root.resizable(False, False)

    frame = ttk.Frame(root, padding=16)
    frame.grid(row=0, column=0, sticky="nsew")

    date_var = tk.StringVar(value=f"Today's date: {get_today_date()}")
    ttk.Label(frame, textvariable=date_var).grid(row=0, column=0, sticky="w", pady=(0, 10))

    ttk.Button(
        frame,
        text="Refresh",
        command=lambda: date_var.set(f"Today's date: {get_today_date()}"),
    ).grid(row=1, column=0, sticky="ew")

    root.mainloop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Calendar module")
    parser.add_argument("--gui", action="store_true", help="show date in a GUI window")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.gui:
        show_gui()
        return
    show_cli()


if __name__ == "__main__":
    main()
