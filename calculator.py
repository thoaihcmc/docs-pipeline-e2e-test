"""Simple calculator CLI app.

Usage examples:
  python calculator.py add 5 3
  python calculator.py div 10 2
  python calculator.py
"""

from __future__ import annotations

import argparse


OPS = {
    "add": lambda a, b: a + b,
    "sub": lambda a, b: a - b,
    "mul": lambda a, b: a * b,
    "div": lambda a, b: a / b,
    "pow": lambda a, b: a**b,
    "mod": lambda a, b: a % b,
}


def calculate(op: str, a: float, b: float) -> float:
    """Run one calculator operation with basic validation."""
    if op not in OPS:
        raise ValueError(f"Unsupported operation: {op}")
    if op == "div" and b == 0:
        raise ValueError("Cannot divide by zero")
    if op == "mod" and b == 0:
        raise ValueError("Cannot modulo by zero")
    return OPS[op](a, b)


def run_interactive() -> None:
    """Run prompt-based calculator session."""
    print("Calculator interactive mode")
    print("Operations: add, sub, mul, div, pow, mod")
    print("Type 'exit' as operation to quit.")

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
            b = float(input("Second number: ").strip())
            result = calculate(op, a, b)
            print(f"Result: {result}")
        except ValueError as exc:
            print(f"Error: {exc}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simple Python calculator app")
    parser.add_argument("operation", nargs="?", choices=sorted(OPS.keys()))
    parser.add_argument("a", nargs="?", type=float)
    parser.add_argument("b", nargs="?", type=float)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.operation is None:
        run_interactive()
        return

    if args.a is None or args.b is None:
        parser.error("operation mode requires: operation a b")

    try:
        result = calculate(args.operation, args.a, args.b)
    except ValueError as exc:
        parser.error(str(exc))
        return

    print(result)


if __name__ == "__main__":
    main()
