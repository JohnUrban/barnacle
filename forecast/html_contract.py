"""Dependency-free DOM and accessibility checks for current web surfaces."""

from __future__ import annotations

import datetime as dt
from html.parser import HTMLParser
import json
from pathlib import Path
from typing import TypedDict, TypeAlias


VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}
Attributes: TypeAlias = dict[str, str | None]
Control: TypeAlias = tuple[str, Attributes, bool]
NamedElement: TypeAlias = tuple[Attributes, str]


class Frame(TypedDict):
    tag: str
    attrs: Attributes
    text: list[str]


class SurfaceParser(HTMLParser):
    """Collect the small DOM subset required by the publish contract."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[Frame] = []
        self.ids: list[str] = []
        self.fragment_refs: list[str] = []
        self.explicit_labels: set[str] = set()
        self.controls: list[Control] = []
        self.canvases: list[Attributes] = []
        self.images: list[Attributes] = []
        self.links: list[NamedElement] = []
        self.buttons: list[NamedElement] = []
        self.html_lang: str | None = None
        self.main_count = 0
        self.h1_count = 0
        self.title_text: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = dict(attrs)
        if tag == "html":
            self.html_lang = attributes.get("lang")
        if tag == "main":
            self.main_count += 1
        if tag == "h1":
            self.h1_count += 1
        if identifier := attributes.get("id"):
            self.ids.append(identifier)
        href = attributes.get("href") or ""
        if href.startswith("#") and len(href) > 1:
            self.fragment_refs.append(href[1:])
        label_target = attributes.get("for")
        if tag == "label" and label_target:
            self.explicit_labels.add(label_target)
        wrapped = any(frame["tag"] == "label" for frame in self.stack)
        if tag in {"input", "select", "textarea"}:
            self.controls.append((tag, attributes, wrapped))
        if tag == "canvas":
            self.canvases.append(attributes)
        if tag == "img":
            self.images.append(attributes)
        frame: Frame = {"tag": tag, "attrs": attributes, "text": []}
        if tag not in VOID_ELEMENTS:
            self.stack.append(frame)

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.handle_starttag(tag, attrs)

    def handle_data(self, data: str) -> None:
        for frame in self.stack:
            frame["text"].append(data)
        if any(frame["tag"] == "title" for frame in self.stack):
            self.title_text.append(data)

    def handle_endtag(self, tag: str) -> None:
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


def current_surface_paths(root: str | Path) -> list[Path]:
    """Return landing/reference/map/index plus every current per-tide page."""
    root = Path(root)
    paths = [
        root / "docs" / "index.html",
        root / "docs" / "details.html",
        root / "docs" / "outlook.html",
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


def validate_surface(path: str | Path) -> list[str]:
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


def validate_current_surfaces(root: str | Path) -> list[tuple[str, str]]:
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
