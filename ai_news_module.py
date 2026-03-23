"""AI news fetcher module — searches for latest AI news and displays updates.

Fetches headlines from Google News RSS (no API key required).

Usage examples:
  python ai_news_module.py
  python ai_news_module.py --count 10
  python ai_news_module.py --query "large language models"
  python ai_news_module.py --gui
"""

from __future__ import annotations

import argparse
import html
import textwrap
import tkinter as tk
import webbrowser
from datetime import datetime
from tkinter import messagebox, ttk
from typing import NamedTuple
from urllib.error import URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from xml.etree import ElementTree


_DEFAULT_QUERY = "artificial intelligence"
_DEFAULT_COUNT = 5
_MAX_COUNT = 25
_RSS_BASE = "https://news.google.com/rss/search"
_REQUEST_TIMEOUT = 15
_USER_AGENT = "Mozilla/5.0 (compatible; AiNewsModule/1.0)"


class NewsItem(NamedTuple):
    title: str
    link: str
    source: str
    published: str


def _build_rss_url(query: str) -> str:
    return f"{_RSS_BASE}?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"


def fetch_news(query: str = _DEFAULT_QUERY, count: int = _DEFAULT_COUNT) -> list[NewsItem]:
    """Fetch AI-related news headlines from Google News RSS."""
    count = min(count, _MAX_COUNT)
    url = _build_rss_url(query)
    req = Request(url, headers={"User-Agent": _USER_AGENT})

    with urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
        tree = ElementTree.parse(resp)

    items: list[NewsItem] = []
    for entry in tree.findall(".//item"):
        if len(items) >= count:
            break
        title = entry.findtext("title", "").strip()
        link = entry.findtext("link", "").strip()
        pub_date = entry.findtext("pubDate", "").strip()
        source = entry.findtext("source", "").strip()

        title = html.unescape(title)
        source = html.unescape(source)

        items.append(NewsItem(title=title, link=link, source=source, published=pub_date))

    return items


def _format_date(pub_date: str) -> str:
    """Best-effort parse of RSS pubDate into a friendlier format."""
    try:
        dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return pub_date


def show_cli(query: str = _DEFAULT_QUERY, count: int = _DEFAULT_COUNT) -> None:
    """Print AI news headlines in the terminal."""
    print(f'\nFetching top {count} news for "{query}" ...\n')
    try:
        items = fetch_news(query, count)
    except URLError as exc:
        print(f"Network error: {exc}")
        return
    except ElementTree.ParseError:
        print("Failed to parse news feed.")
        return

    if not items:
        print("No articles found.")
        return

    for idx, item in enumerate(items, 1):
        date_str = _format_date(item.published)
        wrapped_title = textwrap.fill(item.title, width=80, initial_indent="  ", subsequent_indent="  ")
        print(f"[{idx}] {date_str}")
        print(wrapped_title)
        if item.source:
            print(f"  Source: {item.source}")
        print(f"  {item.link}")
        print()


def show_gui(query: str = _DEFAULT_QUERY, count: int = _DEFAULT_COUNT) -> None:
    """Show AI news in a Tkinter window with clickable headlines."""
    root = tk.Tk()
    root.title("AI News")
    root.geometry("700x520")
    root.minsize(500, 400)

    style = ttk.Style()
    style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"))
    style.configure("Headline.TLabel", font=("Segoe UI", 10, "bold"), foreground="#1a0dab")
    style.configure("Meta.TLabel", font=("Segoe UI", 8), foreground="#555555")

    top = ttk.Frame(root, padding=12)
    top.pack(fill="x")

    ttk.Label(top, text="AI News Feed", style="Title.TLabel").pack(side="left")

    search_frame = ttk.Frame(top)
    search_frame.pack(side="right")

    query_var = tk.StringVar(value=query)
    query_entry = ttk.Entry(search_frame, textvariable=query_var, width=28)
    query_entry.pack(side="left", padx=(0, 6))

    canvas = tk.Canvas(root, highlightthickness=0)
    scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
    scroll_frame = ttk.Frame(canvas, padding=(12, 0, 12, 12))

    scroll_frame.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    def _on_mousewheel(event: tk.Event) -> None:
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    status_var = tk.StringVar(value="Loading...")
    status_label = ttk.Label(root, textvariable=status_var, style="Meta.TLabel", padding=(12, 4))
    status_label.pack(fill="x", side="bottom")

    def _clear_frame() -> None:
        for widget in scroll_frame.winfo_children():
            widget.destroy()

    def _load_news() -> None:
        _clear_frame()
        q = query_var.get().strip() or _DEFAULT_QUERY
        status_var.set(f'Fetching news for "{q}" ...')
        root.update_idletasks()

        try:
            items = fetch_news(q, count)
        except (URLError, ElementTree.ParseError) as exc:
            messagebox.showerror("Fetch error", str(exc))
            status_var.set("Error.")
            return

        if not items:
            ttk.Label(scroll_frame, text="No articles found.").pack(anchor="w", pady=8)
            status_var.set("0 articles.")
            return

        for idx, item in enumerate(items):
            card = ttk.Frame(scroll_frame, relief="groove", borderwidth=1, padding=8)
            card.pack(fill="x", pady=(0, 8))

            headline = ttk.Label(card, text=item.title, style="Headline.TLabel", wraplength=620, cursor="hand2")
            headline.pack(anchor="w")
            url = item.link
            headline.bind("<Button-1>", lambda _e, u=url: webbrowser.open(u))

            meta_parts: list[str] = []
            if item.source:
                meta_parts.append(item.source)
            meta_parts.append(_format_date(item.published))
            ttk.Label(card, text=" | ".join(meta_parts), style="Meta.TLabel").pack(anchor="w", pady=(2, 0))

        status_var.set(f"{len(items)} article(s) loaded.")

    ttk.Button(search_frame, text="Search", command=_load_news).pack(side="left")
    root.bind("<Return>", lambda _e: _load_news())

    root.after(100, _load_news)
    root.mainloop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch and display latest AI news")
    parser.add_argument("--gui", action="store_true", help="show news in a GUI window")
    parser.add_argument(
        "--query", "-q", default=_DEFAULT_QUERY, help=f'search query (default: "{_DEFAULT_QUERY}")'
    )
    parser.add_argument(
        "--count", "-n", type=int, default=_DEFAULT_COUNT, help=f"number of articles (default: {_DEFAULT_COUNT})"
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.gui:
        show_gui(args.query, args.count)
        return
    show_cli(args.query, args.count)


if __name__ == "__main__":
    main()
