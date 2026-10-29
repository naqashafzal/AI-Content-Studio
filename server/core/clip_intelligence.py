"""
Clip Intelligence Engine for the Magic Clipper.

Pure, testable helpers that turn a word-level transcript + multimodal signals
into well-bounded, de-duplicated, calibrated short-clip candidates.

Pipeline:
    words -> sentences -> annotated lines -> LLM windows -> candidates
          -> boundary snapping -> speech metrics -> composite score
          -> temporal NMS -> (optional) global LLM re-rank -> top-N
"""
from __future__ import annotations

import json
import logging
import math
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

SENTENCE_END = (".", "!", "?", "…")


# --------------------------------------------------------------------------- #
# Transcript structure
# --------------------------------------------------------------------------- #
def clean_words(words: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalises Whisper word dicts and drops empty / malformed entries."""
    out = []
    for w in words or []:
        try:
            text = str(w.get("word", "")).strip()
            st, en = float(w["start"]), float(w["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if not text or en < st:
            continue
        out.append({"word": text, "start": st, "end": en})
    out.sort(key=lambda x: x["start"])
    return out


def build_sentences(words: Sequence[Dict[str, Any]], pause_split: float = 1.2,
                    max_sentence_sec: float = 15.0) -> List[Dict[str, Any]]:
    """Groups words into sentences using punctuation, long pauses, and a hard length cap."""
    sentences: List[Dict[str, Any]] = []
    cur: List[Dict[str, Any]] = []

    def flush():
        if cur:
            sentences.append({
                "start": cur[0]["start"],
                "end": cur[-1]["end"],
                "text": " ".join(w["word"] for w in cur),
                "n_words": len(cur),
            })

    for i, w in enumerate(words):
        if cur:
            gap = w["start"] - cur[-1]["end"]
            if gap >= pause_split or (w["end"] - cur[0]["start"]) > max_sentence_sec:
                flush()
                cur = []
        cur.append(w)
        if w["word"].endswith(SENTENCE_END):
            flush()
            cur = []
    flush()
    return sentences


def _profile_slice_mean(profile: Sequence[float], start: float, end: float, interval: float = 1.0) -> Optional[float]:
    if not profile:
        return None
    s = max(0, int(start / interval))
    e = max(s + 1, int(math.ceil(end / interval)))
    vals = profile[s:min(e, len(profile))]
    return sum(vals) / len(vals) if vals else None


def _zscore_fn(profile: Sequence[float]):
    if not profile:
        return lambda _v: 0.0
    mean = sum(profile) / len(profile)
    var = sum((p - mean) ** 2 for p in profile) / len(profile)
    std = math.sqrt(var) or 1e-6
    return lambda v: (v - mean) / std


def annotate_lines(sentences: Sequence[Dict[str, Any]], audio_profile: Sequence[float],
                   target_line_sec: float = 12.0) -> List[str]:
    """
    Builds transcript lines aligned to sentence boundaries, tagged with relative
    vocal energy (relative to this video's own baseline) and long pauses, so the
    LLM can 'hear' emphasis instead of reading a flat transcript.
    """
    z = _zscore_fn(audio_profile)
    lines: List[str] = []
    bucket: List[Dict[str, Any]] = []

    def flush():
        if not bucket:
            return
        st, en = bucket[0]["start"], bucket[-1]["end"]
        tags = []
        e = _profile_slice_mean(audio_profile, st, en)
        if e is not None:
            ez = z(e)
            if ez >= 1.0:
                tags.append("ENERGY:HIGH")
            elif ez <= -1.0:
                tags.append("ENERGY:LOW")
        text = " ".join(s["text"] for s in bucket)
        tag_str = f" {{{', '.join(tags)}}}" if tags else ""
        lines.append(f"[{st:.1f}-{en:.1f}]{tag_str} {text}")

    for i, s in enumerate(sentences):
        if bucket and (s["start"] - bucket[-1]["end"]) >= 2.0:
            flush()
            lines.append(f"[{bucket[-1]['end']:.1f}-{s['start']:.1f}] {{PAUSE}}")
            bucket = []
        bucket.append(s)
        if bucket[-1]["end"] - bucket[0]["start"] >= target_line_sec:
            flush()
            bucket = []
    flush()
    return lines


def build_windows(lines: Sequence[str], max_chars: int = 12000, overlap_lines: int = 8) -> List[str]:
    """Line-aware sliding windows (never splits a timestamped line in half)."""
    windows: List[str] = []
    i = 0
    n = len(lines)
    while i < n:
        size, j = 0, i
        while j < n and (size + len(lines[j]) + 1 <= max_chars or j == i):
            size += len(lines[j]) + 1
            j += 1
        windows.append("\n".join(lines[i:j]))
        if j >= n:
            break
        i = max(i + 1, j - overlap_lines)
    return windows


# --------------------------------------------------------------------------- #
# LLM I/O
# --------------------------------------------------------------------------- #
def parse_llm_json(text: str) -> Any:
    """Robustly extracts JSON from an LLM response (fences, prose, trailing commas)."""
    if not text:
        return None
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.IGNORECASE | re.MULTILINE).strip()
    for candidate in (t, _first_balanced(t, "{", "}"), _first_balanced(t, "[", "]")):
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            try:
                return json.loads(re.sub(r",\s*([\]}])", r"\1", candidate))
            except json.JSONDecodeError:
                continue
    return None


def _first_balanced(t: str, open_c: str, close_c: str) -> Optional[str]:
    start = t.find(open_c)
    if start < 0:
        return None
    depth, in_str, esc = 0, False, False
    for k in range(start, len(t)):
        c = t[k]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == open_c:
            depth += 1
        elif c == close_c:
            depth -= 1
            if depth == 0:
                return t[start:k + 1]
    return None


def extract_clip_list(parsed: Any) -> List[Dict[str, Any]]:
    if isinstance(parsed, list):
        return [c for c in parsed if isinstance(c, dict)]
    if isinstance(parsed, dict):
        for key in ("clips", "candidates", "results", "items"):
            if isinstance(parsed.get(key), list):
                return [c for c in parsed[key] if isinstance(c, dict)]
        if "start" in parsed and "end" in parsed:
            return [parsed]
    return []


def build_candidate_prompt(window: str, min_dur: float, max_dur: float, max_clips: int,
                           context_hint: str = "") -> str:
    return f"""You are a senior short-form video editor and retention strategist (YouTube Shorts, TikTok, Reels).
Find the strongest standalone moments in this transcript window.

TRANSCRIPT FORMAT
- Each line is "[start-end] {{optional signal tags}} text". Times are in seconds from the start of the source video.
- {{ENERGY:HIGH}} = noticeably louder/more animated than this speaker's baseline. {{PAUSE}} = a long silence.
{context_hint}
WHAT MAKES A GREAT CLIP
1. HOOK (first 3 seconds): a bold claim, surprising number, conflict, question, or strong emotion. No greetings, no "so, um", no setup.
2. PAYOFF: the clip resolves what the hook promised (an answer, punchline, reveal, or lesson).
3. SELF-CONTAINED: a stranger with zero context understands it. Avoid clips that depend on "as I said earlier", or on unexplained pronouns.
4. PACE: dense speech, little dead air.
5. Duration STRICTLY between {min_dur:.0f} and {max_dur:.0f} seconds.

HARD RULES
- Use ONLY timestamps that appear in the transcript lines. "start" must be the start of a line or sentence. "end" must be where a thought finishes.
- Do not invent facts. "hook_text" must be faithful to what is actually said (8 words max). Never put words in the speaker's mouth.
- Return at most {max_clips} clips, best first. Return fewer if the window has no strong moments.

Return ONLY a JSON object:
{{
  "clips": [
    {{
      "start": float, "end": float,
      "title": "short punchy title (max 60 chars)",
      "hook_text": "on-screen hook, max 8 words, faithful to content",
      "category": "one of: insight | story | controversy | humor | emotional | how-to | prediction | data-reveal",
      "hook_score": int 1-100, "retention_score": int 1-100, "payoff_score": int 1-100,
      "self_contained": true/false,
      "reason": "one sentence: why this holds attention",
      "seo_title": "YouTube Shorts title #shorts",
      "seo_description": "1-2 sentence description",
      "seo_tags": "comma, separated, tags",
      "broll": [{{"start_offset": int, "end_offset": int, "subject": "concrete stock-footage search term"}}]
    }}
  ]
}}

TRANSCRIPT WINDOW:
{window}
"""


def build_rerank_prompt(candidates: Sequence[Dict[str, Any]]) -> str:
    rows = []
    for c in candidates:
        rows.append({
            "id": c["id"],
            "duration": round(c["end"] - c["start"], 1),
            "category": c.get("category", ""),
            "title": c.get("title", ""),
            "opening": c.get("_opening", "")[:220],
            "ending": c.get("_ending", "")[:160],
        })
    return f"""You are the final editor choosing which short clips to publish from one long video.
The candidates below came from separate passes, so their scores aren't comparable yet. Judge them all on ONE scale.

For each candidate, score 1-100 on:
- "judge_score": the overall likelihood that viewers watch to the end and share it. Weigh the opening hook most, then a clear payoff, then whether it stands alone.
Penalise openings that start mid-thought, with filler, or with unexplained references. Penalise endings that cut off before the point lands.

Return ONLY JSON: {{"rankings": [{{"id": "...", "judge_score": int, "note": "max 12 words"}}]}}

CANDIDATES:
{json.dumps(rows, ensure_ascii=False, indent=1)}
"""


# --------------------------------------------------------------------------- #
# Boundary snapping & metrics
# --------------------------------------------------------------------------- #
def snap_to_boundaries(start: float, end: float, sentences: Sequence[Dict[str, Any]],
                       min_dur: float, max_dur: float, search_sec: float = 4.0,
                       lead_pad: float = 0.12, tail_pad: float = 0.25) -> Tuple[float, float, bool]:
    """
    Snaps LLM-proposed [start, end] onto sentence edges so clips never start or end
    mid-word. Enforces the duration window by extending or trimming whole sentences.
    Returns (start, end, clean_boundaries).
    """
    if not sentences:
        return start, end, False

    starts = [s["start"] for s in sentences]
    ends = [s["end"] for s in sentences]

    def nearest(arr, target):
        idx = min(range(len(arr)), key=lambda k: abs(arr[k] - target))
        return idx, abs(arr[idx] - target)

    si, sd = nearest(starts, start)
    ei, ed = nearest(ends, end)
    clean = sd <= search_sec and ed <= search_sec
    if ei < si:
        ei = si

    # Extend forward with whole sentences until min duration is met
    while (ends[ei] - starts[si]) < min_dur and ei + 1 < len(sentences):
        ei += 1
    # Extend backward if still too short (end of video)
    while (ends[ei] - starts[si]) < min_dur and si > 0:
        si -= 1
    # Trim whole sentences from the end while too long
    while (ends[ei] - starts[si]) > max_dur and ei > si:
        ei -= 1

    s_t, e_t = starts[si], ends[ei]
    if (e_t - s_t) > max_dur:  # a single over-long sentence
        e_t = s_t + max_dur
        clean = False
    return max(0.0, round(s_t - lead_pad, 2)), round(e_t + tail_pad, 2), clean


def speech_metrics(words: Sequence[Dict[str, Any]], start: float, end: float) -> Dict[str, float]:
    """Words/sec, dead-air ratio and leading silence for a clip window."""
    dur = max(0.1, end - start)
    cw = [w for w in words if w["end"] > start and w["start"] < end]
    if not cw:
        return {"wps": 0.0, "dead_air_ratio": 1.0, "lead_silence": dur, "n_words": 0}
    dead = 0.0
    prev_end = start
    for w in cw:
        gap = w["start"] - prev_end
        if gap > 0.7:
            dead += gap
        prev_end = max(prev_end, w["end"])
    if end - prev_end > 0.7:
        dead += end - prev_end
    return {
        "wps": round(len(cw) / dur, 2),
        "dead_air_ratio": round(min(1.0, dead / dur), 3),
        "lead_silence": round(max(0.0, cw[0]["start"] - start), 2),
        "n_words": len(cw),
    }


def multimodal_score(start: float, end: float, audio_profile: Sequence[float],
                     visual_profile: Sequence[float]) -> float:
    """0-100 excitement score relative to the video's own baseline (z-scored, sigmoid)."""
    parts, weights = [], []
    for profile, wt in ((audio_profile, 0.65), (visual_profile, 0.35)):
        m = _profile_slice_mean(profile, start, end)
        if m is None:
            continue
        zv = _zscore_fn(profile)(m)
        parts.append(1.0 / (1.0 + math.exp(-1.5 * zv)))
        weights.append(wt)
    if not parts:
        return 50.0
    return round(100.0 * sum(p * w for p, w in zip(parts, weights)) / sum(weights), 1)


def _clamp_int(v: Any, default: int = 60) -> int:
    try:
        return max(1, min(100, int(round(float(v)))))
    except (TypeError, ValueError):
        return default


def composite_score(clip: Dict[str, Any], metrics: Dict[str, float], mm: float,
                    clean_bounds: bool, min_dur: float, max_dur: float) -> Tuple[int, Dict[str, Any]]:
    """Blends LLM judgement with measurable signals into a single explainable score."""
    hook = _clamp_int(clip.get("hook_score", clip.get("score")))
    ret = _clamp_int(clip.get("retention_score", clip.get("score")))
    pay = _clamp_int(clip.get("payoff_score", clip.get("score")))
    llm = 0.40 * hook + 0.35 * ret + 0.25 * pay

    wps = metrics.get("wps", 0.0)
    pace = 100.0 if 2.0 <= wps <= 3.8 else max(0.0, 100.0 - abs(wps - 2.9) * 45.0)
    speech = 0.6 * pace + 0.4 * (100.0 * (1.0 - metrics.get("dead_air_ratio", 0.0)))

    dur = clip["end"] - clip["start"]
    sweet_lo, sweet_hi = max(min_dur, 20.0), min(max_dur, 45.0)
    if sweet_lo <= dur <= sweet_hi:
        dur_fit = 100.0
    else:
        dist = (sweet_lo - dur) if dur < sweet_lo else (dur - sweet_hi)
        dur_fit = max(0.0, 100.0 - dist * 6.0)

    score = 0.68 * llm + 0.14 * mm + 0.11 * speech + 0.07 * dur_fit
    penalties = []
    if not clean_bounds:
        score -= 4
        penalties.append("boundary_adjusted")
    if clip.get("self_contained") is False:
        score -= 8
        penalties.append("needs_context")
    if metrics.get("lead_silence", 0) > 1.0:
        score -= 3
        penalties.append("slow_start")

    breakdown = {
        "llm": round(llm, 1), "hook": hook, "retention": ret, "payoff": pay,
        "multimodal": round(mm, 1), "speech": round(speech, 1), "duration_fit": round(dur_fit, 1),
        "penalties": penalties,
    }
    return max(1, min(99, int(round(score)))), breakdown


# --------------------------------------------------------------------------- #
# Selection
# --------------------------------------------------------------------------- #
def temporal_iou(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    inter = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
    union = max(a[1], b[1]) - min(a[0], b[0])
    return inter / union if union > 0 else 0.0


def non_max_suppression(clips: Sequence[Dict[str, Any]], iou_thresh: float = 0.35,
                        key: str = "score") -> List[Dict[str, Any]]:
    """Keeps the best clip among heavily overlapping candidates (temporal NMS)."""
    kept: List[Dict[str, Any]] = []
    for c in sorted(clips, key=lambda x: x.get(key, 0), reverse=True):
        rng = (c["start"], c["end"])
        if all(temporal_iou(rng, (k["start"], k["end"])) < iou_thresh for k in kept):
            kept.append(c)
    return kept


def diversify(clips: Sequence[Dict[str, Any]], n: int, max_per_category: Optional[int] = None) -> List[Dict[str, Any]]:
    """Picks top-N while avoiding a feed of near-identical clip types."""
    if max_per_category is None:
        max_per_category = max(2, math.ceil(n * 0.5))
    picked, overflow, counts = [], [], {}
    for c in clips:
        cat = (c.get("category") or "other").lower()
        if counts.get(cat, 0) < max_per_category:
            picked.append(c)
            counts[cat] = counts.get(cat, 0) + 1
        else:
            overflow.append(c)
        if len(picked) >= n:
            break
    for c in overflow:
        if len(picked) >= n:
            break
        picked.append(c)
    return sorted(picked, key=lambda x: x.get("score", 0), reverse=True)


def text_between(sentences: Sequence[Dict[str, Any]], start: float, end: float) -> Tuple[str, str]:
    inside = [s for s in sentences if s["end"] > start and s["start"] < end]
    if not inside:
        return "", ""
    opening = " ".join(s["text"] for s in inside[:2])
    ending = " ".join(s["text"] for s in inside[-1:])
    return opening, ending


# --------------------------------------------------------------------------- #
# Rendering helpers (timeline remap + captions)
# --------------------------------------------------------------------------- #
def kept_intervals_from_segments(segments: Sequence[Dict[str, Any]], clip_duration: float,
                                 min_keep: float = 0.15) -> Optional[List[Tuple[float, float]]]:
    """
    Converts TimelineEditor segments (with "deleted" flags) into kept intervals on the
    clip timeline. Natural gaps between sentences are preserved; only deleted
    sentences are removed. Returns None when nothing was deleted.
    """
    if not segments:
        return None
    has_flags = any("deleted" in s for s in segments)
    if has_flags:
        deleted = sorted(
            (max(0.0, float(s.get("start", 0))), min(clip_duration, float(s.get("end", 0))))
            for s in segments if s.get("deleted")
        )
        if not deleted:
            return None
        kept, cursor = [], 0.0
        for d0, d1 in deleted:
            if d0 - cursor >= min_keep:
                kept.append((round(cursor, 3), round(d0, 3)))
            cursor = max(cursor, d1)
        if clip_duration - cursor >= min_keep:
            kept.append((round(cursor, 3), round(clip_duration, 3)))
        return kept or None
    # Legacy payload: explicit list of kept segments
    kept = []
    for s in segments:
        a = max(0.0, float(s.get("start", 0)))
        b = min(clip_duration, float(s.get("end", a)))
        if b - a >= min_keep:
            kept.append((a, b))
    return kept or None


def remap_words(words: Sequence[Dict[str, Any]], clip_start: float, clip_end: float,
                kept: Optional[Sequence[Tuple[float, float]]] = None) -> List[Dict[str, Any]]:
    """Maps source-video word timestamps onto the final (possibly ripple-cut) clip timeline."""
    rel = []
    for w in words:
        if w["end"] <= clip_start or w["start"] >= clip_end:
            continue
        rel.append({"word": w["word"], "start": max(0.0, w["start"] - clip_start),
                    "end": min(clip_end - clip_start, w["end"] - clip_start)})
    if not kept:
        return rel
    out, offset = [], 0.0
    for a, b in kept:
        for w in rel:
            mid = (w["start"] + w["end"]) / 2
            if a <= mid < b:
                out.append({"word": w["word"],
                            "start": max(0.0, w["start"] - a) + offset,
                            "end": min(b, w["end"]) - a + offset})
        offset += b - a
    return out


def group_caption_lines(words: Sequence[Dict[str, Any]], max_words: int = 4,
                        max_chars: int = 22, pause: float = 0.45) -> List[List[Dict[str, Any]]]:
    """Groups words into short caption lines, breaking on real pauses and punctuation."""
    lines, cur = [], []
    for w in words:
        if cur:
            gap = w["start"] - cur[-1]["end"]
            chars = sum(len(x["word"]) + 1 for x in cur) + len(w["word"])
            if len(cur) >= max_words or chars > max_chars or gap > pause:
                lines.append(cur)
                cur = []
        cur.append(w)
        if w["word"].endswith(SENTENCE_END + (",",)):
            lines.append(cur)
            cur = []
    if cur:
        lines.append(cur)
    return lines
