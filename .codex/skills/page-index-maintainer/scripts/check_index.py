#!/usr/bin/env python3
"""Check that index.html covers every root HTML page in newest-first order."""

from __future__ import annotations

from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
import re
import sys


class IndexParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.cards: list[dict[str, str | None]] = []
        self._current_card: dict[str, str | None] | None = None
        self._in_footer = False
        self.footer_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "a" and "card" in classes:
            self._current_card = {"href": attributes.get("href"), "datetime": None}
            self.cards.append(self._current_card)
        elif tag == "time" and self._current_card is not None:
            self._current_card["datetime"] = attributes.get("datetime")
        elif tag == "footer":
            self._in_footer = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._current_card = None
        elif tag == "footer":
            self._in_footer = False

    def handle_data(self, data: str) -> None:
        if self._in_footer:
            self.footer_text.append(data)


def fail(messages: list[str]) -> None:
    for message in messages:
        print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    repo = Path(__file__).resolve().parents[4]
    index = repo / "index.html"
    if not index.is_file():
        fail(["repository root index.html is missing"])

    parser = IndexParser()
    parser.feed(index.read_text(encoding="utf-8"))

    expected = {path.name for path in repo.glob("*.html") if path.name != "index.html"}
    hrefs = [str(card["href"]) for card in parser.cards if card["href"]]
    listed = set(hrefs)
    errors: list[str] = []

    missing = sorted(expected - listed)
    extra = sorted(listed - expected)
    duplicates = sorted({href for href in hrefs if hrefs.count(href) > 1})
    if missing:
        errors.append(f"pages missing from index: {', '.join(missing)}")
    if extra:
        errors.append(f"index links without matching root pages: {', '.join(extra)}")
    if duplicates:
        errors.append(f"duplicate page cards: {', '.join(duplicates)}")

    dates: list[datetime] = []
    for card in parser.cards:
        href = card["href"] or "(missing href)"
        raw_date = card["datetime"]
        if not raw_date:
            errors.append(f"card has no datetime: {href}")
            continue
        try:
            dates.append(datetime.fromisoformat(raw_date))
        except ValueError:
            errors.append(f"card has invalid ISO datetime: {href}: {raw_date}")

    if len(dates) == len(parser.cards) and dates != sorted(dates, reverse=True):
        errors.append("cards are not sorted by added timestamp, newest first")

    footer = " ".join("".join(parser.footer_text).split())
    count_match = re.search(r"共\s*(\d+)\s*个页面", footer)
    if not count_match:
        errors.append("footer does not contain a '共 N 个页面' count")
    elif int(count_match.group(1)) != len(expected):
        errors.append(
            f"footer count is {count_match.group(1)}, but {len(expected)} pages exist"
        )

    if errors:
        fail(errors)
    print(f"Index OK: {len(expected)} pages, complete and newest-first.")


if __name__ == "__main__":
    main()
