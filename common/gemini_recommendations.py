"""
gemini_recommendations.py
--------------------------
Generates the "Coaching recommendations" bullets on the Performance
Analytics Dashboard using Gemini, based on an athlete's real assessment
data (category ratings, trend, attendance, and — when available — the
coach's own free-text remarks from their latest submitted assessment).

Uses the GOOGLE_API_KEYS env var (set it in .env). If the key is missing,
the google-genai package isn't installed, or the API call fails for any
reason, this falls back to the existing rule-based recommendations in
common/models.py so the dashboard never breaks because of the LLM call.

Results are cached in-memory per process, keyed off the athlete's actual
numbers -- so the dashboard doesn't re-call Gemini on every page refresh,
only when an athlete's ratings/attendance actually change (i.e. after a
new assessment is submitted).
"""

import os
from common.logs import log

try:
    from google import genai
except ImportError:
    genai = None

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

_client = None
_rec_cache: dict = {}


def _get_client():
    global _client
    if _client is not None:
        return _client
    api_key = os.getenv("GOOGLE_API_KEYS")
    if not genai or not api_key:
        return None
    try:
        _client = genai.Client(api_key=api_key)
    except Exception as e:
        log(f"gemini_recommendations: failed to init client: {e}")
        _client = None
    return _client


def _build_prompt(name, sport, age, cat_current, cat_prev, attendance_pct, extra: dict) -> str:
    lines = [
        "You are helping a sports coach make sense of one athlete's latest performance assessment.",
        f"Athlete: {name}" + (f", age {age}" if age else "") + (f", sport: {sport}" if sport and sport != "-" else ""),
        "",
        "Category ratings (scale 1-5, current vs previous assessment):",
        f"- Physical: {cat_current['physical']:.1f} (was {cat_prev['physical']:.1f})",
        f"- Technical: {cat_current['technical']:.1f} (was {cat_prev['technical']:.1f})",
        f"- Tactical: {cat_current['tactical']:.1f} (was {cat_prev['tactical']:.1f})",
        f"- Behavioural: {cat_current['behavioral']:.1f} (was {cat_prev['behavioral']:.1f})",
    ]
    if attendance_pct is not None:
        lines.append(f"- Average attendance: {round(attendance_pct)}%")

    if extra.get("talent_category"):
        lines.append(f"- Talent category: {extra['talent_category']}")
    if extra.get("overall_progress"):
        lines.append(f"- Coach's overall progress rating: {extra['overall_progress']}")

    strengths = [extra.get(f"strength_{i}") for i in (1, 2, 3) if extra.get(f"strength_{i}")]
    improvements = [extra.get(f"improvement_{i}") for i in (1, 2, 3) if extra.get(f"improvement_{i}")]
    if strengths:
        lines.append("- Coach-noted strengths: " + "; ".join(strengths))
    if improvements:
        lines.append("- Coach-noted areas for improvement: " + "; ".join(improvements))
    if extra.get("coach_summary_remarks"):
        lines.append(f"- Coach's summary remarks: {extra['coach_summary_remarks']}")

    lines += [
        "",
        "Write exactly 3 short coaching recommendations for the coach, based only on the data above.",
        "Each recommendation must be one or two plain sentences, practical and specific to this athlete's numbers.",
        "Output ONLY the 3 recommendations, one per line, with no numbering, no bullet characters, and no markdown.",
    ]
    return "\n".join(lines)


def _parse_recommendations(text: str) -> list[str]:
    lines = []
    for raw in text.splitlines():
        line = raw.strip().lstrip("-*•").strip()
        # strip a leading "1. " / "1) " style numbering if the model adds one anyway
        for sep in (". ", ") "):
            if len(line) > 2 and line[0].isdigit() and sep in line[:4]:
                line = line.split(sep, 1)[1].strip()
                break
        if line:
            lines.append(line)
    return lines[:3]


def generate_coaching_recommendations(athlete_id, name, sport, age, cat_current, cat_prev,
                                       attendance_pct, extra: dict | None = None,
                                       fallback_fn=None) -> list[str]:
    """Returns up to 3 recommendation strings. Tries Gemini first (cached per
    athlete+numbers), falls back to fallback_fn(cat_current, cat_prev, attendance_pct)
    -- the existing rule-based generator -- if Gemini is unavailable or errors out."""
    extra = extra or {}

    cache_key = (
        athlete_id,
        tuple(sorted(cat_current.items())),
        tuple(sorted(cat_prev.items())),
        attendance_pct,
    )
    if cache_key in _rec_cache:
        return _rec_cache[cache_key]

    client = _get_client()
    result = None
    if client:
        try:
            prompt = _build_prompt(name, sport, age, cat_current, cat_prev, attendance_pct, extra)
            response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            parsed = _parse_recommendations(response.text or "")
            if parsed:
                result = parsed
        except Exception as e:
            log(f"gemini_recommendations: generation failed for athlete {athlete_id}: {e}")

    if result is None and fallback_fn:
        result = fallback_fn(cat_current, cat_prev, attendance_pct)

    _rec_cache[cache_key] = result or []
    return _rec_cache[cache_key]


def clear_recommendation_cache():
    """Call this after an assessment is created/updated if you want the next
    dashboard load to regenerate recs immediately rather than waiting for the
    athlete's numbers to change the cache key (they usually will anyway)."""
    _rec_cache.clear()
