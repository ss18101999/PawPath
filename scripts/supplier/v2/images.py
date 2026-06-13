"""V2 image quality evaluation engine."""

from __future__ import annotations

import re
import struct
import urllib.error
import urllib.request
from typing import Optional

from ..progress import ProgressLogger
from .models import ImageAssessment

WATERMARK_PATTERNS = [
    r"watermark",
    r"aliexpress",
    r"1688",
    r"alibaba",
    r"made-in-china",
    r"shutterstock",
    r"getty",
]

MIN_BYTES = 12_000
MIN_PIXELS = 400 * 400


def _read_image_dimensions(data: bytes) -> tuple[int, int]:
    if data[:2] == b"\xff\xd8":
        return _jpeg_size(data)
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", data[16:24])
        return w, h
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        if data[12:16] == b"VP8 ":
            w = struct.unpack("<H", data[26:28])[0] & 0x3FFF
            h = struct.unpack("<H", data[28:30])[0] & 0x3FFF
            return w, h
    return 0, 0


def _jpeg_size(data: bytes) -> tuple[int, int]:
    idx = 2
    while idx < len(data):
        if data[idx] != 0xFF:
            break
        marker = data[idx + 1]
        idx += 2
        if marker in (0xC0, 0xC1, 0xC2):
            h = struct.unpack(">H", data[idx + 3 : idx + 5])[0]
            w = struct.unpack(">H", data[idx + 5 : idx + 7])[0]
            return w, h
        length = struct.unpack(">H", data[idx : idx + 2])[0]
        idx += length
    return 0, 0


def assess_image(url: str, *, timeout: int = 12) -> ImageAssessment:
    reasons: list[str] = []
    score = 50.0
    width = height = 0
    size = 0

    url_l = url.lower()
    for pat in WATERMARK_PATTERNS:
        if re.search(pat, url_l):
            reasons.append("watermark_url_pattern")
            score -= 30

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PawPathCatalogBot/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            size = int(resp.headers.get("Content-Length") or 0)
            chunk = resp.read(65536)
            if not size:
                size = len(chunk)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return ImageAssessment(url=url, score=0, rejected=True, reasons=[f"fetch_failed:{exc}"])

    if size < MIN_BYTES:
        reasons.append("low_resolution_or_small_file")
        score -= 25

    width, height = _read_image_dimensions(chunk)
    pixels = width * height
    if pixels >= 800 * 800:
        score += 25
    elif pixels >= MIN_PIXELS:
        score += 15
    elif pixels > 0:
        reasons.append("low_pixel_dimensions")
        score -= 15
    else:
        if size >= 80_000:
            score += 10
        else:
            reasons.append("unknown_dimensions_small_file")
            score -= 10

    # Prefer clean product shots (heuristic from URL/filename)
    if any(k in url_l for k in ("white", "main", "product", "hero")):
        score += 5
    if any(k in url_l for k in ("lifestyle", "scene", "outdoor", "dog")):
        score += 8

    score = max(0.0, min(100.0, score))
    rejected = score < 35 or "watermark_url_pattern" in reasons
    return ImageAssessment(
        url=url,
        score=score,
        width=width,
        height=height,
        bytes_size=size,
        rejected=rejected,
        reasons=reasons,
    )


def assess_product_images(
    urls: list[str],
    *,
    max_images: int = 6,
    log: Optional[ProgressLogger] = None,
) -> tuple[list[ImageAssessment], float]:
    """Return assessments and aggregate image score."""
    unique = []
    seen: set[str] = set()
    for u in urls:
        if u and u.startswith("http") and u not in seen:
            seen.add(u)
            unique.append(u)
    if not unique:
        return [], 0.0

    batch = unique[:max_images]
    if log:
        log.detail(f"checking {len(batch)} image(s)...")

    assessments = []
    for i, u in enumerate(batch, start=1):
        assessments.append(assess_image(u))
        if log and (i == len(batch) or i % 2 == 0):
            log.detail(f"  image {i}/{len(batch)} score={assessments[-1].score:.0f}")
    usable = [a for a in assessments if not a.rejected]
    if not usable:
        return assessments, 0.0
    usable.sort(key=lambda a: a.score, reverse=True)
    top = usable[:3]
    aggregate = sum(a.score for a in top) / len(top)
    return assessments, aggregate
