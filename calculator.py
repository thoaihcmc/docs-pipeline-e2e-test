"""Simple calculator app with CLI and GUI modes.

Usage examples:
  python calculator.py add 5 3
  python calculator.py div 10 2
  python calculator.py sqrt 49
  python calculator.py
  python calculator.py --gui
"""

from __future__ import annotations

import argparse
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk


OPS = {
    "add": lambda a, b: a + b,
    "sub": lambda a, b: a - b,
    "mul": lambda a, b: a * b,
    "div": lambda a, b: a / b,
    "pow": lambda a, b: a**b,
    "mod": lambda a, b: a % b,
    "sqrt": lambda a, _b: a**0.5,
    "pct": lambda a, b: (a / 100) * b,
}

UNARY_OPS = {"sqrt"}


def calculate(op: str, a: float, b: float = 0.0) -> float:
    """Run one calculator operation with basic validation."""
    if op not in OPS:
        raise ValueError(f"Unsupported operation: {op}")
    if op == "div" and b == 0:
        raise ValueError("Cannot divide by zero")
    if op == "mod" and b == 0:
        raise ValueError("Cannot modulo by zero")
    if op == "sqrt" and a < 0:
        raise ValueError("Cannot calculate sqrt of negative number")
    return OPS[op](a, b)


def run_interactive() -> None:
    """Run prompt-based calculator session."""
    print("Calculator interactive mode")
    print("Operations: add, sub, mul, div, pow, mod, sqrt, pct")
    print("Type 'exit' as operation to quit.")
    history: list[str] = []

    while True:
        op = input("Operation: ").strip().lower()
        if op == "exit":
            print("Goodbye.")
            return

        if op not in OPS:
            print(f"Invalid operation '{op}'. Try again.")
            continue

        try:
            a = float(input("First number: ").strip())
            b = 0.0
            if op not in UNARY_OPS:
                b = float(input("Second number: ").strip())
            result = calculate(op, a, b)
            print(f"Result: {result}")
            expr = f"{op}({a}) = {result}" if op in UNARY_OPS else f"{a} {op} {b} = {result}"
            history.append(expr)
            if len(history) > 5:
                history.pop(0)
            print("Recent history:")
            for item in history:
                print(f"  - {item}")
        except ValueError as exc:
            print(f"Error: {exc}")


def run_gui() -> None:
    """Run Tkinter-based calculator window."""
    root = tk.Tk()
    root.title("Python Calculator")
    root.resizable(False, False)

    main = ttk.Frame(root, padding=12)
    main.grid(row=0, column=0, sticky="nsew")

    ttk.Label(main, text="First number").grid(row=0, column=0, sticky="w", pady=(0, 4))
    first_var = tk.StringVar()
    first_entry = ttk.Entry(main, textvariable=first_var, width=20)
    first_entry.grid(row=1, column=0, sticky="ew", pady=(0, 10))

    ttk.Label(main, text="Operation").grid(row=2, column=0, sticky="w", pady=(0, 4))
    op_var = tk.StringVar(value="add")
    op_combo = ttk.Combobox(
        main,
        textvariable=op_var,
        values=sorted(OPS.keys()),
        state="readonly",
        width=18,
    )
    op_combo.grid(row=3, column=0, sticky="ew", pady=(0, 10))

    ttk.Label(main, text="Second number").grid(row=4, column=0, sticky="w", pady=(0, 4))
    second_var = tk.StringVar()
    second_entry = ttk.Entry(main, textvariable=second_var, width=20)
    second_entry.grid(row=5, column=0, sticky="ew", pady=(0, 10))

    result_var = tk.StringVar(value="Result: -")
    ttk.Label(main, textvariable=result_var).grid(row=8, column=0, sticky="w", pady=(8, 0))

    ttk.Label(main, text="History").grid(row=9, column=0, sticky="w", pady=(10, 4))
    history_list = tk.Listbox(main, height=6, width=36)
    history_list.grid(row=10, column=0, sticky="ew")

    def on_calculate() -> None:
        try:
            a = float(first_var.get().strip())
            op = op_var.get().strip()
            b = 0.0
            if op not in UNARY_OPS:
                b = float(second_var.get().strip())
            result = calculate(op, a, b)
            result_var.set(f"Result: {result}")
            expr = f"{op}({a}) = {result}" if op in UNARY_OPS else f"{a} {op} {b} = {result}"
            history_list.insert(0, expr)
            if history_list.size() > 10:
                history_list.delete(10, tk.END)
        except ValueError as exc:
            messagebox.showerror("Calculation error", str(exc))

    def on_clear() -> None:
        first_var.set("")
        second_var.set("")
        op_var.set("add")
        result_var.set("Result: -")
        history_list.delete(0, tk.END)
        second_entry.state(["!disabled"])
        first_entry.focus_set()

    def on_op_change(*_args: object) -> None:
        if op_var.get() in UNARY_OPS:
            second_var.set("")
            second_entry.state(["disabled"])
        else:
            second_entry.state(["!disabled"])

    op_var.trace_add("write", on_op_change)

    buttons = ttk.Frame(main)
    buttons.grid(row=6, column=0, sticky="ew")
    buttons.columnconfigure(0, weight=1)
    buttons.columnconfigure(1, weight=1)
    ttk.Button(buttons, text="Calculate", command=on_calculate).grid(
        row=0, column=0, sticky="ew", padx=(0, 4)
    )
    ttk.Button(buttons, text="Clear", command=on_clear).grid(
        row=0, column=1, sticky="ew", padx=(4, 0)
    )

    first_entry.focus_set()
    root.bind("<Return>", lambda _event: on_calculate())
    root.mainloop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simple Python calculator app")
    parser.add_argument("--gui", action="store_true", help="launch graphical calculator")
    parser.add_argument("operation", nargs="?", choices=sorted(OPS.keys()))
    parser.add_argument("a", nargs="?", type=float)
    parser.add_argument("b", nargs="?", type=float)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.gui:
        run_gui()
        return

    if args.operation is None:
        run_interactive()
        return

    if args.a is None:
        parser.error("operation mode requires at least: operation a")
    if args.operation not in UNARY_OPS and args.b is None:
        parser.error("binary operation mode requires: operation a b")

    try:
        second = 0.0 if args.b is None else args.b
        result = calculate(args.operation, args.a, second)
    except ValueError as exc:
        parser.error(str(exc))
        return

    print(result)


if __name__ == "__main__":
    main()
