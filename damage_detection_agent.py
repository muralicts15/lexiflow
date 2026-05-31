"""Damage Detection Agent for LexiFlow."""

import base64
import json
import os
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

VISION_MODEL = os.getenv("VISION_MODEL", "gpt-4.1-mini")


def inspect_product_image(image_path: str, image_url: str = None) -> Dict:
    """Inspect an uploaded product image and return a structured report."""
    path = Path(image_path)
    size_bytes = path.stat().st_size if path.exists() else 0

    if not path.exists() or size_bytes == 0:
        return {
            "inspection_status": "failed",
            "damage_detected": False,
            "damage_type": "unknown",
            "severity": "unknown",
            "confidence": 0.0,
            "needs_human_review": True,
            "recommendation": "ask_customer_for_clearer_photo",
            "image_url": image_url or image_path,
            "notes": "Image file was missing or empty.",
        }

    if os.getenv("DAMAGE_DETECTION_USE_MOCK") == "1":
        return mock_damage_report(image_path, image_url=image_url)

    if os.getenv("OPENAI_API_KEY"):
        try:
            return inspect_product_image_with_openai(path, image_url=image_url)
        except Exception as exc:
            fallback = mock_damage_report(image_path, image_url=image_url)
            fallback["inspection_status"] = "fallback"
            fallback["notes"] = f"Vision inspection failed, using fallback mock result. Error: {exc}"
            return fallback

    return mock_damage_report(image_path, image_url=image_url)


def inspect_product_image_with_openai(path: Path, image_url: str = None) -> Dict:
    """Use an OpenAI vision model to inspect product damage."""
    client = OpenAI()
    data_url = encode_image_as_data_url(path)
    response = client.responses.create(
        model=VISION_MODEL,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Inspect this customer-uploaded product image for visible product damage. "
                            "Return only valid JSON with these keys: inspection_status, damage_detected, "
                            "damage_type, severity, confidence, needs_human_review, recommendation, notes. "
                            "Use severity low, medium, high, or unknown. confidence must be a number from 0 to 1. "
                            "If the image is unclear or does not show the product, set inspection_status to "
                            "inconclusive and needs_human_review to true. Do not approve refunds or replacements."
                        ),
                    },
                    {
                        "type": "input_image",
                        "image_url": data_url,
                        "detail": "low",
                    },
                ],
            }
        ],
    )
    parsed = parse_json_response(response.output_text)
    return normalize_report(parsed, image_url=image_url or str(path), source="openai_vision")


def encode_image_as_data_url(path: Path) -> str:
    mime_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(path.suffix.lower(), "image/jpeg")
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def parse_json_response(text: str) -> Dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    return json.loads(cleaned)


def normalize_report(report: Dict, image_url: str, source: str) -> Dict:
    confidence = report.get("confidence", 0.0)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0

    return {
        "inspection_status": str(report.get("inspection_status", "completed")),
        "damage_detected": bool(report.get("damage_detected", False)),
        "damage_type": str(report.get("damage_type", "unknown")),
        "severity": str(report.get("severity", "unknown")),
        "confidence": max(0.0, min(1.0, confidence)),
        "needs_human_review": bool(report.get("needs_human_review", True)),
        "recommendation": str(report.get("recommendation", "eligible_for_complaint_review")),
        "image_url": image_url,
        "notes": str(report.get("notes", "")),
        "source": source,
        "model": VISION_MODEL if source == "openai_vision" else "mock",
    }


def mock_damage_report(image_path: str, image_url: str = None) -> Dict:
    """Fallback demo result when no vision API is available."""
    return {
        "inspection_status": "completed",
        "damage_detected": True,
        "damage_type": "possible_visible_damage",
        "severity": "medium",
        "confidence": 0.76,
        "needs_human_review": True,
        "recommendation": "eligible_for_complaint_review",
        "image_url": image_url or image_path,
        "notes": "Mock inspection result. Replace with trained damage model or vision tool.",
        "source": "mock",
        "model": "mock",
    }


def format_damage_report(report: Dict) -> str:
    """Format a damage report for inclusion in the customer-care prompt."""
    if not report:
        return "No product image inspection report is available."

    return f"""
Image inspection:
- Status: {report.get('inspection_status')}
- Damage detected: {report.get('damage_detected')}
- Damage type: {report.get('damage_type')}
- Severity: {report.get('severity')}
- Confidence: {report.get('confidence')}
- Needs human review: {report.get('needs_human_review')}
- Recommendation: {report.get('recommendation')}
- Image URL: {report.get('image_url')}
- Source: {report.get('source')}
- Model: {report.get('model')}
- Notes: {report.get('notes')}
""".strip()
