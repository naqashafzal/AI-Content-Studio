"""Unit tests for the Magic Clipper intelligence engine (pure functions, no network/GPU)."""
from server.core import clip_intelligence as ci


def _words(text: str, start: float = 0.0, step: float = 0.35, gap_after: dict = None):
    gap_after = gap_after or {}
    out, t = [], start
    for i, tok in enumerate(text.split()):
        out.append({"word": tok, "start": round(t, 2), "end": round(t + step - 0.05, 2)})
        t += step + gap_after.get(i, 0.0)
    return out


SAMPLE = ("So welcome back everyone. Here is the thing nobody tells you about money. "
          "Most people save first and invest later. That is backwards! "
          "You should automate investing on payday. Then you spend what is left. "
          "I did this for ten years and it changed everything. Seriously.")


def test_sentences_split_on_punctuation_and_pauses():
    words = _words("hello there friend. how are you today? fine", gap_after={1: 2.0})
    sents = ci.build_sentences(words)
    assert [s["text"] for s in sents] == ["hello there", "friend.", "how are you today?", "fine"]


def test_snap_aligns_to_sentence_edges_and_enforces_duration():
    words = ci.clean_words(_words(SAMPLE))
    sents = ci.build_sentences(words)
    # LLM gives a sloppy mid-word start and a too-short window
    st, en, clean = ci.snap_to_boundaries(sents[1]["start"] + 0.4, sents[1]["end"] + 0.3, sents,
                                          min_dur=8.0, max_dur=20.0)
    assert abs((st + 0.12) - sents[1]["start"]) < 0.01           # snapped to sentence start (with lead pad)
    assert any(abs((en - 0.25) - s["end"]) < 0.01 for s in sents)  # ends on a sentence end
    assert 8.0 <= (en - st) <= 20.0 + 0.4
    assert clean


def test_snap_trims_overlong_clip():
    words = ci.clean_words(_words(SAMPLE))
    sents = ci.build_sentences(words)
    st, en, _ = ci.snap_to_boundaries(0.0, 999.0, sents, min_dur=5.0, max_dur=10.0)
    assert en - st <= 10.0 + 0.4


def test_windows_never_split_lines():
    lines = [f"[{i}.0-{i+1}.0] " + "x" * 50 for i in range(100)]
    wins = ci.build_windows(lines, max_chars=600, overlap_lines=2)
    assert len(wins) > 1
    for w in wins:
        for line in w.split("\n"):
            assert line in lines
    assert lines[-1] in wins[-1]


def test_parse_llm_json_handles_fences_prose_and_trailing_commas():
    assert ci.extract_clip_list(ci.parse_llm_json('```json\n{"clips":[{"start":1,"end":20}]}\n```'))[0]["end"] == 20
    assert ci.extract_clip_list(ci.parse_llm_json('Sure! Here: [{"start": 2, "end": 30,}] hope it helps'))[0]["start"] == 2
    assert ci.parse_llm_json("not json at all") is None


def test_nms_removes_overlapping_duplicates():
    clips = [{"start": 0, "end": 30, "score": 80}, {"start": 3, "end": 31, "score": 90},
             {"start": 60, "end": 90, "score": 70}]
    kept = ci.non_max_suppression(clips, 0.35)
    assert [c["score"] for c in kept] == [90, 70]


def test_composite_score_penalises_context_dependency_and_dead_air():
    base = {"start": 0, "end": 30, "hook_score": 85, "retention_score": 80, "payoff_score": 80}
    good_m = {"wps": 2.8, "dead_air_ratio": 0.02, "lead_silence": 0.1}
    bad_m = {"wps": 1.0, "dead_air_ratio": 0.4, "lead_silence": 2.0}
    good, bd = ci.composite_score(dict(base), good_m, 70, True, 15, 60)
    bad, bd2 = ci.composite_score(dict(base, self_contained=False), bad_m, 70, False, 15, 60)
    assert good > bad
    assert "needs_context" in bd2["penalties"] and "slow_start" in bd2["penalties"]
    assert 1 <= bad <= 99 and 1 <= good <= 99


def test_multimodal_score_is_relative_to_video_baseline():
    audio = [0.2] * 50 + [0.9] * 10 + [0.2] * 40
    assert ci.multimodal_score(50, 60, audio, []) > 80
    assert ci.multimodal_score(0, 10, audio, []) < 50


def test_deleted_segments_become_ripple_cuts():
    segs = [{"start": 0.0, "end": 4.0, "deleted": False},
            {"start": 4.2, "end": 8.0, "deleted": True},
            {"start": 8.1, "end": 12.0, "deleted": False}]
    kept = ci.kept_intervals_from_segments(segs, 12.5)
    assert kept == [(0.0, 4.2), (8.0, 12.5)]
    assert ci.kept_intervals_from_segments([dict(s, deleted=False) for s in segs], 12.5) is None


def test_remap_words_follows_ripple_cuts():
    words = [{"word": "a", "start": 10.5, "end": 10.9},   # kept
             {"word": "b", "start": 15.0, "end": 15.5},   # deleted region
             {"word": "c", "start": 19.0, "end": 19.4}]   # kept, shifted left
    out = ci.remap_words(words, 10.0, 22.0, [(0.0, 4.2), (8.0, 12.0)])
    assert [w["word"] for w in out] == ["a", "c"]
    assert abs(out[1]["start"] - (4.2 + 1.0)) < 1e-6


def test_diversify_limits_single_category_domination():
    clips = [{"score": 99 - i, "category": "humor"} for i in range(5)] + [{"score": 50, "category": "insight"}]
    picked = ci.diversify(clips, 4, max_per_category=3)
    assert sum(c["category"] == "humor" for c in picked) == 3
    assert any(c["category"] == "insight" for c in picked)

