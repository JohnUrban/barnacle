"""Dependency-free DOM and accessibility checks for current web surfaces."""

from __future__ import annotations

import datetime as dt
from html.parser import HTMLParser
import json
from pathlib import Path


VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}


class SurfaceParser(HTMLParser):
    """Collect the small DOM subset required by the publish contract."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.ids = []
        self.fragment_refs = []
        self.explicit_labels = set()
        self.controls = []
        self.canvases = []
        self.images = []
        self.links = []
        self.buttons = []
        self.html_lang = None
        self.main_count = 0
        self.h1_count = 0
        self.title_text = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "html":
            self.html_lang = attributes.get("lang")
        if tag == "main":
            self.main_count += 1
        if tag == "h1":
            self.h1_count += 1
        if identifier := attributes.get("id"):
            self.ids.append(identifier)
        href = attributes.get("href", "")
        if href.startswith("#") and len(href) > 1:
            self.fragment_refs.append(href[1:])
        if tag == "label" and attributes.get("for"):
            self.explicit_labels.add(attributes["for"])
        wrapped = any(frame["tag"] == "label" for frame in self.stack)
        if tag in {"input", "select", "textarea"}:
            self.controls.append((tag, attributes, wrapped))
        if tag == "canvas":
            self.canvases.append(attributes)
        if tag == "img":
            self.images.append(attributes)
        frame = {"tag": tag, "attrs": attributes, "text": []}
        if tag not in VOID_ELEMENTS:
            self.stack.append(frame)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_data(self, data):
        for frame in self.stack:
            frame["text"].append(data)
        if any(frame["tag"] == "title" for frame in self.stack):
            self.title_text.append(data)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] != tag:
                continue
            frame = self.stack[index]
            self.stack = self.stack[:index]
            text = " ".join("".join(frame["text"]).split())
            if tag == "a":
                self.links.append((frame["attrs"], text))
            elif tag == "button":
                self.buttons.append((frame["attrs"], text))
            break


def current_surface_paths(root):
    """Return landing/reference/map/index plus every current per-tide page."""
    root = Path(root)
    paths = [
        root / "docs" / "index.html",
        root / "docs" / "details.html",
        root / "docs" / "highlands.html",
        root / "docs" / "tides" / "index.html",
    ]
    forecast = json.loads(
        (root / "docs" / "forecast.json").read_text(encoding="utf-8")
    )
    for tide in forecast["all_tides"]:
        stamp = dt.datetime.fromisoformat(tide["time"])
        slug = stamp.strftime("%Y-%m-%dT%H-%M")
        paths.append(root / "docs" / "tides" / slug / "index.html")
    return list(dict.fromkeys(paths))


def validate_surface(path):
    """Return DOM/accessibility contract failures for one HTML surface."""
    path = Path(path)
    if not path.is_file():
        return ["current HTML surface is missing"]
    try:
        parser = SurfaceParser()
        parser.feed(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        return [f"HTML read/parse failed: {exc}"]

    failures = []
    if parser.html_lang != "en":
        failures.append("html lang must be en")
    if parser.main_count != 1:
        failures.append(f"expected one main landmark, found {parser.main_count}")
    if parser.h1_count != 1:
        failures.append(f"expected one h1, found {parser.h1_count}")
    if not "".join(parser.title_text).strip():
        failures.append("document title is empty")

    duplicates = sorted({
        value for value in parser.ids if parser.ids.count(value) > 1
    })
    if duplicates:
        failures.append(f"duplicate element ids: {duplicates}")
    missing_fragments = sorted(set(parser.fragment_refs) - set(parser.ids))
    if missing_fragments:
        failures.append(f"same-page fragments lack targets: {missing_fragments}")

    for tag, attrs, wrapped in parser.controls:
        if attrs.get("type") == "hidden":
            continue
        named = (
            wrapped
            or attrs.get("id") in parser.explicit_labels
            or attrs.get("aria-label")
            or attrs.get("aria-labelledby")
        )
        if not named:
            failures.append(f"unnamed {tag} control: {attrs.get('id')}")
    for attrs, text in parser.buttons:
        if not (text or attrs.get("aria-label") or attrs.get("title")):
            failures.append(f"unnamed button: {attrs.get('id')}")
    for attrs, text in parser.links:
        if not (text or attrs.get("aria-label") or attrs.get("title")):
            failures.append(f"unnamed link: {attrs.get('href')}")
    for attrs in parser.images:
        if "alt" not in attrs:
            failures.append(f"image lacks alt: {attrs.get('src')}")
    for attrs in parser.canvases:
        if attrs.get("role") != "img":
            failures.append(f"canvas lacks img role: {attrs.get('id')}")
        if not (attrs.get("aria-label") or attrs.get("aria-labelledby")):
            failures.append(f"canvas lacks accessible name: {attrs.get('id')}")
    return failures


def validate_current_surfaces(root):
    """Return (path, reason) failures for every currently published page."""
    try:
        paths = current_surface_paths(root)
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
        forecast = Path(root) / "docs" / "forecast.json"
        return [(str(forecast), f"cannot enumerate current surfaces: {exc}")]
    return [
        (str(path), reason)
        for path in paths
        for reason in validate_surface(path)
    ]
