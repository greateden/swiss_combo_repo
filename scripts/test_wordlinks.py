#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from build_parallel_subtitles import NeuralWordAligner, OutputRow, TimedWord, make_wordlink_sentence


def source_words(words: list[str], start: float = 95.12) -> list[TimedWord]:
    return [TimedWord(text, start + index * 0.1, start + index * 0.1 + 0.06) for index, text in enumerate(words)]


def test_swiss_german_mika_ids() -> None:
    row = OutputRow(
        dialect_text="De Mika isch abegured und hät underem bänkli nahglueged.",
        standard_text="Mika ist runtergehurt und hat unter dem Bänklein nachgeschaut.",
        start=95.12,
        end=96.4,
        score=1.0,
    )
    sentence = make_wordlink_sentence(
        0,
        row,
        "Mika went down and looked under the little boy.",
        source_words(["De", "Mika", "isch", "abegured", "und", "hät", "underem", "bänkli", "nahglueged"]),
        NeuralWordAligner(Path("missing-model")),
        standard_german_only=False,
    )
    lines = {line["role"]: line for line in sentence["lines"]}
    source = lines["source"]["tokens"]
    standard = lines["standard"]["tokens"]
    english = lines["english"]["tokens"]

    assert source[0]["text"] == "De"
    assert source[0]["source_id"] == 0
    assert source[1]["text"] == "Mika"
    assert source[1]["source_id"] == 1
    assert standard[0]["text"] == "Mika"
    assert standard[0]["source_id"] == 1
    assert english[0]["text"] == "Mika"
    assert english[0]["source_id"] == 1
    assert any(token["source_id"] is None for token in english[1:])


def test_standard_german_mode() -> None:
    row = OutputRow(
        dialect_text="",
        standard_text="Ich bin Eden.",
        start=0.0,
        end=1.5,
        score=1.0,
    )
    sentence = make_wordlink_sentence(
        0,
        row,
        "I am Eden.",
        source_words(["Ich", "bin", "Eden"], start=0.0),
        NeuralWordAligner(Path("missing-model")),
        standard_german_only=True,
    )
    lines = {line["role"]: line for line in sentence["lines"]}
    source = lines["source"]["tokens"]
    english = lines["english"]["tokens"]

    assert [token["source_id"] for token in source] == [0, 1, 2]
    assert english[-1]["text"] == "Eden"
    assert english[-1]["source_id"] == 2


def test_reordered_english_question() -> None:
    row = OutputRow(
        dialect_text="Was ghört?",
        standard_text="Was gehört?",
        start=488.096,
        end=488.56,
        score=1.0,
    )
    sentence = make_wordlink_sentence(
        56,
        row,
        "Hear what?",
        source_words(["Was", "ghört"], start=488.096),
        NeuralWordAligner(Path("missing-model")),
        standard_german_only=False,
    )
    lines = {line["role"]: line for line in sentence["lines"]}
    english = lines["english"]["tokens"]

    assert english[0]["text"] == "Hear"
    assert english[0]["source_id"] == 1
    assert english[1]["text"] == "what"
    assert english[1]["source_id"] == 0


def main() -> None:
    test_swiss_german_mika_ids()
    test_standard_german_mode()
    test_reordered_english_question()
    print("wordlink tests passed")


if __name__ == "__main__":
    main()
