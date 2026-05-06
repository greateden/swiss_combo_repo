#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path


SENTENCE_BOUNDARY_RE = re.compile(
    r"(?<=[.!?。！？])[\"]*[»“”]*\s+(?=(?:[\"«»“”„\-–]*\s*)?[A-ZÄÖÜ])"
    r"|(?<=[.!?。！？])(?=(?:[\"«»“”„\-–]*\s*)?[A-ZÄÖÜ])"
)

ALIGNMENT_NAMES = {
    "becker",
    "beck",
    "hansi",
    "kathmandu",
    "katja",
    "kioskfrau",
    "kohlrabi",
    "lisli",
    "mara",
    "matteo",
    "mika",
    "raffi",
    "schorsch",
    "tarzan",
}

TOKEN_REPLACEMENTS = {
    "au": "auch",
    "bänkeli": "bank",
    "bänkli": "bank",
    "bankli": "bank",
    "bizle": "bisschen",
    "bizli": "bisschen",
    "bitzli": "bisschen",
    "blueme": "blumen",
    "bankherde": "bankkarte",
    "chöne": "konnen",
    "chönne": "konnen",
    "chönt": "konnt",
    "chömed": "kommen",
    "chöme": "kommen",
    "chopf": "kopf",
    "cholchab": "kohlrabi",
    "cholchabi": "kohlrabi",
    "cholrabi": "kohlrabi",
    "chorabi": "kohlrabi",
    "chorrab": "kohlrabi",
    "chorrabi": "kohlrabi",
    "chulchab": "kohlrabi",
    "chume": "komme",
    "chumme": "komme",
    "chunnt": "kommt",
    "cho": "kommen",
    "chaufe": "kaufen",
    "d": "die",
    "de": "der",
    "dänn": "dann",
    "däh": "dieser",
    "di": "die",
    "eifach": "einfach",
    "en": "ein",
    "es": "ein",
    "gfröged": "gefragt",
    "gfröget": "gefragt",
    "gfragt": "gefragt",
    "ghoert": "gehort",
    "ghört": "gehort",
    "glasse": "glas",
    "glaser": "glas",
    "glasser": "glas",
    "gloosed": "gehort",
    "glueged": "geschaut",
    "glueget": "geschaut",
    "gluegt": "geschaut",
    "gmeint": "gemeint",
    "grad": "gerade",
    "grännt": "gerannt",
    "grennt": "gerannt",
    "gseh": "gesehen",
    "gseit": "gesagt",
    "gsässe": "sass",
    "gsasse": "sass",
    "gsi": "gewesen",
    "gwunke": "gewunken",
    "ha": "habe",
    "han": "habe",
    "händ": "haben",
    "haend": "haben",
    "hend": "haben",
    "häsch": "hast",
    "hät": "hat",
    "het": "hat",
    "hälfe": "helfen",
    "i": "ich",
    "id": "in die",
    "ine": "hinein",
    "inegrännt": "hinein gerannt",
    "inegrennt": "hinein gerannt",
    "isch": "ist",
    "katio": "katja",
    "kathio": "katja",
    "keis": "kein",
    "kohlrab": "kohlrabi",
    "koft": "hoffte",
    "kolra": "kohlrabi",
    "lüt": "leute",
    "lüüt": "leute",
    "maa": "mann",
    "mah": "mann",
    "maraa": "mara",
    "maran": "mara",
    "maren": "mara",
    "micah": "mika",
    "michael": "mika",
    "michaelisli": "mika",
    "micka": "mika",
    "mikha": "mika",
    "mikke": "mika",
    "mikat": "mika",
    "mir": "wir",
    "nase": "nasen",
    "ned": "nicht",
    "nei": "nein",
    "nid": "nicht",
    "nomal": "noch einmal",
    "nöd": "nicht",
    "nüme": "nicht mehr",
    "nüt": "nichts",
    "nuet": "nichts",
    "oepis": "etwas",
    "ois": "uns",
    "öper": "jemand",
    "öpis": "etwas",
    "pressiert": "pressieren",
    "s": "das",
    "scho": "schon",
    "schulterenzug": "schulter zuckte",
    "schorsch": "schorsch",
    "schräg": "schrag",
    "schraeg": "schrag",
    "schüche": "scheuchen",
    "schueche": "scheuchen",
    "schumme": "kommen wir",
    "si": "sie",
    "söll": "soll",
    "spitz": "spitzen",
    "uf": "auf",
    "ufem": "auf dem",
    "ume": "herum",
    "under": "unter",
    "umdreit": "drehte",
    "villicht": "vielleicht",
    "vili": "viele",
    "vieli": "viele",
    "vo": "von",
    "vom": "von dem",
    "wäg": "weg",
    "waelt": "welt",
    "wält": "welt",
    "wele": "wollte",
    "witer": "weiter",
    "wider": "wieder",
    "wötsch": "wolltest",
    "wotsch": "wolltest",
    "wottsch": "wolltest",
    "zvertrülle": "vertrullen",
    "zvertrulle": "vertrullen",
    "zrugg": "zuruck",
    "zrog": "zuruck",
    "zug": "zuruck",
}

NORMALIZED_TOKEN_REPLACEMENTS = {
    key.replace("ä", "a").replace("ö", "o").replace("ü", "u"): value.replace("ä", "a").replace("ö", "o").replace("ü", "u")
    for key, value in TOKEN_REPLACEMENTS.items()
}

GERMAN_TO_ENGLISH_HINTS = {
    "aber": {"but"},
    "allein": {"alone"},
    "alles": {"all", "everything"},
    "auch": {"also", "too"},
    "auf": {"on", "up"},
    "auge": {"eye"},
    "augen": {"eyes"},
    "bank": {"bench", "bank"},
    "banklein": {"bench", "little"},
    "bei": {"by", "with", "at"},
    "bisschen": {"bit", "little"},
    "blumen": {"flowers"},
    "brot": {"bread"},
    "dann": {"then"},
    "das": {"that", "the", "it"},
    "dem": {"the"},
    "den": {"the"},
    "der": {"the", "who"},
    "die": {"the", "who"},
    "dieser": {"this"},
    "ein": {"a", "an", "one"},
    "eine": {"a", "an", "one"},
    "einen": {"a", "an", "one"},
    "einer": {"a", "an", "one"},
    "etwas": {"something", "what"},
    "fast": {"almost"},
    "frau": {"woman", "mrs"},
    "gefragt": {"asked"},
    "gegangen": {"gone", "went"},
    "gehort": {"hear", "heard", "listen"},
    "geschaut": {"looked", "seen"},
    "gesehen": {"seen", "saw"},
    "gesagt": {"said"},
    "gross": {"big", "large", "great"},
    "haben": {"have", "had", "has"},
    "habe": {"have", "had"},
    "hat": {"has", "had"},
    "ich": {"i"},
    "in": {"in", "into"},
    "ist": {"is", "was"},
    "ja": {"yes"},
    "kein": {"no", "not"},
    "kommen": {"come"},
    "kommt": {"comes"},
    "kopf": {"head"},
    "kohlrabi": {"kohlrabi"},
    "laut": {"loud"},
    "leute": {"people"},
    "mann": {"man"},
    "mit": {"with"},
    "nachgeschaut": {"looked", "checked"},
    "nacht": {"night"},
    "nein": {"no"},
    "nicht": {"not"},
    "nur": {"only", "just"},
    "oder": {"or"},
    "platz": {"place", "square"},
    "runter": {"down"},
    "runtergehurt": {"down"},
    "sagte": {"said"},
    "schon": {"already"},
    "schnell": {"quick", "quickly", "fast"},
    "sie": {"she", "they", "her"},
    "unter": {"under"},
    "viel": {"much", "many"},
    "vielleicht": {"maybe", "perhaps"},
    "von": {"from", "of"},
    "vor": {"before", "in", "front"},
    "was": {"what"},
    "weg": {"away"},
    "wenn": {"when", "if"},
    "wer": {"who"},
    "wie": {"how", "like"},
    "wieder": {"again"},
    "wir": {"we"},
    "wo": {"where", "when"},
    "zu": {"to"},
    "zuruck": {"back"},
}


@dataclass
class Segment:
    start: float
    end: float
    text: str


@dataclass
class Block:
    start: float
    end: float
    text: str
    index: int


@dataclass
class TextFeatures:
    text: str
    normalized: str
    tokens: set[str]
    char_grams: set[str]
    names: set[str]
    length: int


@dataclass
class AlignedSpan:
    dialect_blocks: list[Block]
    standard_blocks: list[Block]
    score: float


@dataclass
class OutputRow:
    dialect_text: str
    standard_text: str
    start: float
    end: float
    score: float


@dataclass
class TimedWord:
    text: str
    start: float
    end: float
    estimated: bool = False


@dataclass
class WordToken:
    text: str
    source_id: int | None = None
    start: float | None = None
    end: float | None = None
    estimated: bool = False


WORD_OR_PUNCT_RE = re.compile(r"\w+(?:['’]\w+)?|[^\w\s]", re.UNICODE)
WORD_RE = re.compile(r"\w+(?:['’]\w+)?", re.UNICODE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build aligned Swiss German / Standard German / English text blocks.")
    parser.add_argument("--dialect-json")
    parser.add_argument("--standard-json", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--dialect-words-json", help="Optional Swiss German word-timestamp JSON for --word-by-word.")
    parser.add_argument("--standard-words-json", help="Optional Standard German word-timestamp JSON for --word-by-word.")
    parser.add_argument(
        "--standard-german",
        action="store_true",
        help="Input audio is already Standard German; output only Standard German and English.",
    )
    parser.add_argument(
        "--word-by-word",
        action="store_true",
        help="Write source-anchored wordlink JSON instead of text/SRT output.",
    )
    parser.add_argument("--translation-model-dir", default=os.environ.get("TRANSLATION_MODEL_DIR"))
    parser.add_argument("--alignment-model-dir", default=os.environ.get("ALIGNMENT_MODEL_DIR"))
    parser.add_argument("--max-translate-chars", type=int, default=450)
    parser.add_argument("--lookahead", type=int, default=10)
    parser.add_argument("--max-span", type=int, default=3)
    parser.add_argument("--min-score", type=float, default=0.24)
    parser.add_argument("--limit", type=int, default=0, help="Only write the first N aligned rows; useful for debugging.")
    parser.add_argument("--skip-translation", action="store_true", help="Write blank English lines; useful for alignment debugging.")
    parser.add_argument("--debug-alignment", help="Optional TSV file with alignment scores and source sentence indexes.")
    parser.add_argument("--translation-cache", help="Optional JSONL cache for Standard German to English translations.")
    parser.add_argument("--srt-output", help="Optional SRT output path; defaults to the text output path with .srt suffix.")
    return parser.parse_args()


def clean_text(text: str) -> str:
    text = re.sub(r"[\u0c80-\u0cff]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def timestamp_value(value: object, fallback: float) -> float:
    if value is None:
        return fallback
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def load_segments(path: Path) -> list[Segment]:
    data = json.loads(path.read_text(encoding="utf-8"))
    chunks = data.get("chunks") if isinstance(data, dict) else None
    if not chunks:
        text = clean_text(data.get("text", "")) if isinstance(data, dict) else ""
        return [Segment(0.0, 0.0, text)] if text else []

    segments: list[Segment] = []
    last_end = 0.0
    for chunk in chunks:
        text = clean_text(str(chunk.get("text", "")))
        if not text:
            continue
        timestamp = chunk.get("timestamp") or chunk.get("timestamps") or (None, None)
        start = timestamp_value(timestamp[0] if len(timestamp) > 0 else None, last_end)
        end = timestamp_value(timestamp[1] if len(timestamp) > 1 else None, start)
        if end < start:
            end = start
        last_end = max(last_end, end)
        segments.append(Segment(start, end, text))
    return segments


def word_surfaces(text: str) -> list[str]:
    return [match.group(0) for match in WORD_RE.finditer(text)]


def split_timed_chunk(text: str, start: float, end: float) -> list[TimedWord]:
    words = word_surfaces(text)
    if not words:
        return []
    duration = max(end - start, 0.001)
    timed_words: list[TimedWord] = []
    for index, word in enumerate(words):
        word_start = start + duration * index / len(words)
        word_end = start + duration * (index + 1) / len(words)
        timed_words.append(TimedWord(word, word_start, word_end, estimated=len(words) > 1))
    return timed_words


def repair_timed_words(words: list[TimedWord]) -> list[TimedWord]:
    if not words:
        return []
    words = sorted(words, key=lambda word: (word.start + word.end) / 2)
    centers = [(word.start + word.end) / 2 for word in words]
    repaired: list[TimedWord] = []
    for index, word in enumerate(words):
        duration = word.end - word.start
        if duration > 0.03:
            repaired.append(word)
            continue

        previous_center = centers[index - 1] if index > 0 else centers[index] - 0.35
        next_center = centers[index + 1] if index + 1 < len(centers) else centers[index] + 0.35
        start = (previous_center + centers[index]) / 2
        end = (centers[index] + next_center) / 2
        if end <= start:
            start = centers[index] - 0.12
            end = centers[index] + 0.12
        repaired.append(TimedWord(word.text, max(start, 0.0), max(end, start + 0.001), estimated=True))
    return repaired


def load_timed_words(path: Path | None) -> list[TimedWord]:
    if path is None or not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    chunks = data.get("chunks") if isinstance(data, dict) else None
    if not chunks:
        return []

    timed_words: list[TimedWord] = []
    last_end = 0.0
    for chunk in chunks:
        text = clean_text(str(chunk.get("text", "")))
        if not text:
            continue
        timestamp = chunk.get("timestamp") or chunk.get("timestamps") or (None, None)
        start = timestamp_value(timestamp[0] if len(timestamp) > 0 else None, last_end)
        end = timestamp_value(timestamp[1] if len(timestamp) > 1 else None, start)
        if end <= start:
            end = start + 0.001
        timed_words.extend(split_timed_chunk(text, start, end))
        last_end = max(last_end, end)
    return repair_timed_words(timed_words)


def split_sentences(text: str) -> list[str]:
    text = clean_text(text)
    if not text:
        return []
    pieces = [clean_text(piece) for piece in SENTENCE_BOUNDARY_RE.split(text) if clean_text(piece)]
    return pieces


def make_sentence_blocks(segments: list[Segment]) -> list[Block]:
    blocks: list[Block] = []
    sentence_index = 0
    for segment in segments:
        sentences = split_sentences(segment.text)
        if not sentences:
            continue
        duration = max(segment.end - segment.start, 0.0)
        total_chars = sum(max(len(sentence), 1) for sentence in sentences)
        cursor = segment.start
        for index, sentence in enumerate(sentences):
            if index == len(sentences) - 1:
                end = segment.end
            elif duration > 0:
                end = cursor + duration * max(len(sentence), 1) / total_chars
            else:
                end = cursor
            blocks.append(Block(cursor, end, sentence, sentence_index))
            sentence_index += 1
            cursor = end
    return blocks


def join_block_text(blocks: list[Block]) -> str:
    return clean_text(" ".join(block.text for block in blocks))


def group_start_end(preferred_blocks: list[Block], fallback_blocks: list[Block]) -> tuple[float, float]:
    blocks = preferred_blocks or fallback_blocks
    if not blocks:
        return 0.0, 0.0
    start = min(block.start for block in blocks)
    end = max(block.end for block in blocks)
    if end <= start:
        end = start + 0.001
    return start, end


def normalize_for_alignment(text: str) -> str:
    text = text.lower().replace("ä", "a").replace("ö", "o").replace("ü", "u").replace("ß", "ss")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    normalized_tokens: list[str] = []
    for token in text.split():
        replacement = NORMALIZED_TOKEN_REPLACEMENTS.get(token, token)
        normalized_tokens.extend(replacement.split())
    return " ".join(normalized_tokens)


def character_grams(text: str, size: int = 3) -> set[str]:
    if len(text) < size:
        return {text} if text else set()
    return {text[index : index + size] for index in range(len(text) - size + 1)}


def make_text_features(text: str) -> TextFeatures:
    normalized = normalize_for_alignment(text)
    tokens = set(normalized.split())
    return TextFeatures(
        text=text,
        normalized=normalized,
        tokens=tokens,
        char_grams=character_grams(normalized),
        names=tokens & ALIGNMENT_NAMES,
        length=len(normalized),
    )


def feature_score(left: TextFeatures, right: TextFeatures) -> float:
    if not left.normalized or not right.normalized:
        return 0.0

    gram_union = left.char_grams | right.char_grams
    char_score = len(left.char_grams & right.char_grams) / len(gram_union) if gram_union else 0.0

    token_union = left.tokens | right.tokens
    token_score = len(left.tokens & right.tokens) / len(token_union) if token_union else 0.0

    shorter_token_count = min(len(left.tokens), len(right.tokens))
    containment_score = len(left.tokens & right.tokens) / shorter_token_count if shorter_token_count else 0.0

    longer_length = max(left.length, right.length)
    length_score = min(left.length, right.length) / longer_length if longer_length else 0.0

    name_union = left.names | right.names
    if name_union:
        name_score = len(left.names & right.names) / len(name_union)
    else:
        name_score = 0.6

    return (
        0.42 * char_score
        + 0.18 * token_score
        + 0.15 * containment_score
        + 0.15 * name_score
        + 0.10 * length_score
    )


def precompute_span_features(blocks: list[Block], max_span: int) -> list[dict[int, TextFeatures]]:
    span_features: list[dict[int, TextFeatures]] = []
    for index in range(len(blocks)):
        features_by_span: dict[int, TextFeatures] = {}
        for span_length in range(1, min(max_span, len(blocks) - index) + 1):
            features_by_span[span_length] = make_text_features(join_block_text(blocks[index : index + span_length]))
        span_features.append(features_by_span)
    return span_features


def best_single_sentence_potential(
    source_features: TextFeatures,
    target_features: list[dict[int, TextFeatures]],
    start: int,
    end: int,
) -> float:
    return max((feature_score(source_features, target_features[index][1]) for index in range(start, end)), default=0.0)


def align_blocks(
    dialect_blocks: list[Block],
    standard_blocks: list[Block],
    lookahead: int,
    max_span: int,
    min_score: float,
) -> tuple[list[AlignedSpan], list[Block], list[Block]]:
    dialect_features = precompute_span_features(dialect_blocks, max_span)
    standard_features = precompute_span_features(standard_blocks, max_span)

    dialect_index = 0
    standard_index = 0
    aligned: list[AlignedSpan] = []
    skipped_dialect: list[Block] = []
    skipped_standard: list[Block] = []

    while dialect_index < len(dialect_blocks) and standard_index < len(standard_blocks):
        best: tuple[float, float, int, int, int, int] | None = None
        dialect_end = min(len(dialect_blocks), dialect_index + lookahead)
        standard_end = min(len(standard_blocks), standard_index + lookahead)

        for candidate_dialect_index in range(dialect_index, dialect_end):
            for candidate_standard_index in range(standard_index, standard_end):
                skip_penalty = 0.04 * (
                    (candidate_dialect_index - dialect_index) + (candidate_standard_index - standard_index)
                )
                for dialect_span, dialect_feature in dialect_features[candidate_dialect_index].items():
                    for standard_span, standard_feature in standard_features[candidate_standard_index].items():
                        raw_score = feature_score(dialect_feature, standard_feature)
                        span_penalty = 0.02 * ((dialect_span - 1) + (standard_span - 1))
                        adjusted_score = raw_score - skip_penalty - span_penalty
                        if best is None or adjusted_score > best[0]:
                            best = (
                                adjusted_score,
                                raw_score,
                                candidate_dialect_index,
                                candidate_standard_index,
                                dialect_span,
                                standard_span,
                            )

        if best and best[1] >= min_score and best[0] >= min_score - 0.07:
            _, raw_score, candidate_dialect_index, candidate_standard_index, dialect_span, standard_span = best
            skipped_dialect.extend(dialect_blocks[dialect_index:candidate_dialect_index])
            skipped_standard.extend(standard_blocks[standard_index:candidate_standard_index])
            aligned.append(
                AlignedSpan(
                    dialect_blocks=dialect_blocks[candidate_dialect_index : candidate_dialect_index + dialect_span],
                    standard_blocks=standard_blocks[candidate_standard_index : candidate_standard_index + standard_span],
                    score=raw_score,
                )
            )
            dialect_index = candidate_dialect_index + dialect_span
            standard_index = candidate_standard_index + standard_span
            continue

        dialect_potential = best_single_sentence_potential(
            dialect_features[dialect_index][1],
            standard_features,
            standard_index,
            standard_end,
        )
        standard_potential = best_single_sentence_potential(
            standard_features[standard_index][1],
            dialect_features,
            dialect_index,
            dialect_end,
        )
        if standard_potential >= dialect_potential:
            skipped_dialect.append(dialect_blocks[dialect_index])
            dialect_index += 1
        else:
            skipped_standard.append(standard_blocks[standard_index])
            standard_index += 1

    skipped_dialect.extend(dialect_blocks[dialect_index:])
    skipped_standard.extend(standard_blocks[standard_index:])
    return aligned, skipped_dialect, skipped_standard


def candidate_partitions(blocks: list[Block], groups: int) -> list[list[list[Block]]]:
    if groups <= 1:
        return [[blocks]]
    if groups >= len(blocks):
        return [[[block] for block in blocks]]

    partitions: list[list[list[Block]]] = []
    for boundaries in itertools.combinations(range(1, len(blocks)), groups - 1):
        previous = 0
        partition: list[list[Block]] = []
        for boundary in (*boundaries, len(blocks)):
            partition.append(blocks[previous:boundary])
            previous = boundary
        partitions.append(partition)
    return partitions


def best_unequal_groups(
    shorter_blocks: list[Block],
    longer_blocks: list[Block],
    longer_blocks_are_standard: bool,
) -> list[tuple[list[Block], list[Block], float]]:
    best_partition: list[list[Block]] | None = None
    best_score = -1.0
    for partition in candidate_partitions(longer_blocks, len(shorter_blocks)):
        score = 0.0
        for shorter_block, longer_group in zip(shorter_blocks, partition):
            shorter_text = shorter_block.text
            longer_text = join_block_text(longer_group)
            if longer_blocks_are_standard:
                score += feature_score(make_text_features(shorter_text), make_text_features(longer_text))
            else:
                score += feature_score(make_text_features(longer_text), make_text_features(shorter_text))
        if score > best_score:
            best_score = score
            best_partition = partition

    if best_partition is None:
        return []

    grouped: list[tuple[list[Block], list[Block], float]] = []
    for shorter_block, longer_group in zip(shorter_blocks, best_partition):
        if longer_blocks_are_standard:
            dialect_group = [shorter_block]
            standard_group = longer_group
        else:
            dialect_group = longer_group
            standard_group = [shorter_block]
        score = feature_score(make_text_features(join_block_text(dialect_group)), make_text_features(join_block_text(standard_group)))
        grouped.append((dialect_group, standard_group, score))
    return grouped


def make_output_row(dialect_group: list[Block], standard_group: list[Block], score: float) -> OutputRow:
    start, end = group_start_end(standard_group, dialect_group)
    return OutputRow(
        dialect_text=join_block_text(dialect_group),
        standard_text=join_block_text(standard_group),
        start=start,
        end=end,
        score=score,
    )


def expand_aligned_spans(aligned_spans: list[AlignedSpan]) -> list[OutputRow]:
    rows: list[OutputRow] = []
    for aligned_span in aligned_spans:
        dialect_count = len(aligned_span.dialect_blocks)
        standard_count = len(aligned_span.standard_blocks)

        if dialect_count == standard_count and dialect_count > 1:
            for dialect_block, standard_block in zip(aligned_span.dialect_blocks, aligned_span.standard_blocks):
                score = feature_score(make_text_features(dialect_block.text), make_text_features(standard_block.text))
                rows.append(make_output_row([dialect_block], [standard_block], score))
            continue

        if dialect_count < standard_count:
            grouped_blocks = best_unequal_groups(
                shorter_blocks=aligned_span.dialect_blocks,
                longer_blocks=aligned_span.standard_blocks,
                longer_blocks_are_standard=True,
            )
            for dialect_group, standard_group, score in grouped_blocks:
                rows.append(make_output_row(dialect_group, standard_group, score))
            continue

        if standard_count < dialect_count:
            grouped_blocks = best_unequal_groups(
                shorter_blocks=aligned_span.standard_blocks,
                longer_blocks=aligned_span.dialect_blocks,
                longer_blocks_are_standard=False,
            )
            for dialect_group, standard_group, score in grouped_blocks:
                rows.append(make_output_row(dialect_group, standard_group, score))
            continue

        rows.append(make_output_row(aligned_span.dialect_blocks, aligned_span.standard_blocks, aligned_span.score))

    return rows


def load_translator(model_dir: Path):
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    model_kwargs: dict[str, object] = {"local_files_only": True}
    if (model_dir / "model.safetensors").exists():
        model_kwargs["use_safetensors"] = True
    model = AutoModelForSeq2SeqLM.from_pretrained(str(model_dir), **model_kwargs)
    model.to(device)
    return tokenizer, model, device


def cache_key(text: str) -> str:
    return hashlib.sha256(clean_text(text).encode("utf-8")).hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")
    temporary_path.write_text(text, encoding="utf-8")
    temporary_path.replace(path)


def load_translation_cache(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    if not path.exists():
        return {}, {}

    cache: dict[str, str] = {}
    source_by_key: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as error:
            print(f"[WARN] Ignoring invalid translation cache line {line_number}: {error}", flush=True)
            continue
        source = clean_text(str(entry.get("source", "")))
        translation = clean_text(str(entry.get("translation", "")))
        key = str(entry.get("key") or cache_key(source))
        if source and translation:
            cache[key] = translation
            source_by_key[key] = source
    return cache, source_by_key


def write_translation_cache(path: Path, cache: dict[str, str], source_by_key: dict[str, str]) -> None:
    lines: list[str] = []
    for key, source in sorted(source_by_key.items()):
        translation = cache.get(key)
        if translation is None:
            continue
        lines.append(
            json.dumps(
                {"key": key, "source": source, "translation": translation},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    atomic_write_text(path, "\n".join(lines).rstrip() + "\n")


def format_srt_timestamp(seconds: float) -> str:
    milliseconds_total = max(round(seconds * 1000), 0)
    hours, remainder = divmod(milliseconds_total, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{whole_seconds:02},{milliseconds:03}"


def srt_safe_text(text: str) -> str:
    return clean_text(text).replace("\n", " ")


def visible_lines(row: OutputRow, english_text: str, standard_german_only: bool, word_by_word: bool) -> list[str]:
    lines = [row.standard_text, english_text] if standard_german_only else [row.dialect_text, row.standard_text, english_text]
    return lines


def write_srt(path: Path, rows: list[OutputRow], english_lines: list[str], standard_german_only: bool, word_by_word: bool) -> None:
    blocks: list[str] = []
    previous_end = 0.0
    for index, (row, english_text) in enumerate(zip(rows, english_lines), start=1):
        start = max(row.start, previous_end)
        end = max(row.end, start + 0.001)
        previous_end = end
        cue_lines = [srt_safe_text(line) for line in visible_lines(row, english_text, standard_german_only, word_by_word)]
        blocks.append(
            "\n".join(
                [
                    str(index),
                    f"{format_srt_timestamp(start)} --> {format_srt_timestamp(end)}",
                    *cue_lines,
                ]
            )
        )
    atomic_write_text(path, "\n\n".join(blocks).rstrip() + "\n")


def normalized_word(text: str) -> str:
    return normalize_for_alignment(text)


def expanded_normalized_words(text: str) -> set[str]:
    normalized = normalized_word(text)
    if not normalized:
        return set()
    expanded: set[str] = set()
    for token in normalized.split():
        expanded.add(token)
        replacement = NORMALIZED_TOKEN_REPLACEMENTS.get(token)
        if replacement:
            expanded.update(replacement.split())
    return expanded


def bilingual_hint_match(source_words: set[str], target_words: set[str]) -> bool:
    if not source_words or not target_words:
        return False
    for source_word in source_words:
        if GERMAN_TO_ENGLISH_HINTS.get(source_word, set()) & target_words:
            return True
    return False


def estimate_timed_tokens(text: str, start: float, end: float) -> list[WordToken]:
    words = word_surfaces(text)
    if not words:
        return []
    duration = max(end - start, 0.001)
    tokens: list[WordToken] = []
    for index, word in enumerate(words):
        word_start = start + duration * index / len(words)
        word_end = start + duration * (index + 1) / len(words)
        tokens.append(WordToken(text=word, start=word_start, end=word_end, estimated=True))
    return tokens


def timed_words_for_span(words: list[TimedWord], start: float, end: float) -> list[TimedWord]:
    if not words:
        return []
    margin = 0.35
    selected: list[TimedWord] = []
    for word in words:
        center = (word.start + word.end) / 2
        if start - margin <= center <= end + margin:
            selected.append(word)
    return selected


def source_tokens_for_row(text: str, start: float, end: float, timed_words: list[TimedWord]) -> list[WordToken]:
    words = word_surfaces(text)
    if not words:
        return []
    selected = timed_words_for_span(timed_words, start, end)
    if not selected:
        return estimate_timed_tokens(text, start, end)
    if len(selected) != len(words) and all(word.estimated for word in selected):
        return estimate_timed_tokens(text, start, end)
    if len(selected) >= max(len(words) * 2, len(words) + 4):
        return estimate_timed_tokens(text, start, end)
    row_norms = [expanded_normalized_words(word) for word in words]
    selected_norms = [expanded_normalized_words(word.text) for word in selected]
    overlap = sum(1 for row_norm in row_norms if any(row_norm & selected_norm for selected_norm in selected_norms))
    if len(selected) != len(words) and overlap < min(len(words), len(selected)):
        return estimate_timed_tokens(text, start, end)

    tokens: list[WordToken] = []
    for index, word in enumerate(words):
        selected_index = round(index * (len(selected) - 1) / max(len(words) - 1, 1)) if len(selected) > 1 else 0
        timed_word = selected[min(selected_index, len(selected) - 1)]
        word_start = min(max(timed_word.start, start), end)
        if word_start >= end:
            word_start = max(start, end - 0.001)
        word_end = min(max(timed_word.end, word_start + 0.001), end)
        tokens.append(
            WordToken(
                text=word,
                start=word_start,
                end=word_end,
                estimated=timed_word.estimated or len(selected) != len(words),
            )
        )
    return tokens


def target_tokens_for_text(text: str) -> list[WordToken]:
    return [WordToken(text=word) for word in word_surfaces(text)]


class NeuralWordAligner:
    def __init__(self, model_dir: Path | None):
        self.model_dir = model_dir
        self.tokenizer = None
        self.model = None
        self.device = "cpu"
        self.load_failed = False
        self.available = bool(
            model_dir
            and (model_dir / "config.json").exists()
            and (model_dir / "vocab.txt").exists()
            and ((model_dir / "model.safetensors").exists() or (model_dir / "pytorch_model.bin").exists())
        )

    def load(self) -> None:
        if self.model is not None or not self.available or self.load_failed:
            return
        import torch
        from transformers import AutoModel, AutoTokenizer

        try:
            self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
            self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_dir), local_files_only=True, use_fast=True)
            self.model = AutoModel.from_pretrained(str(self.model_dir), local_files_only=True)
            self.model.to(self.device)
            self.model.eval()
        except Exception as error:
            self.load_failed = True
            self.available = False
            print(f"[WARN] Neural word alignment unavailable: {error}", flush=True)

    def word_embeddings(self, words: list[str]):
        import torch

        self.load()
        if self.model is None or self.tokenizer is None or not words:
            return None
        encoded = self.tokenizer(
            words,
            is_split_into_words=True,
            return_tensors="pt",
            truncation=True,
            max_length=256,
        )
        word_ids = encoded.word_ids()
        encoded = {key: value.to(self.device) for key, value in encoded.items()}
        with torch.no_grad():
            output = self.model(**encoded, output_hidden_states=True)
        layer_index = min(8, len(output.hidden_states) - 1)
        hidden = output.hidden_states[layer_index][0]
        vectors = []
        for word_index in range(len(words)):
            positions = [index for index, value in enumerate(word_ids) if value == word_index]
            if not positions:
                vectors.append(torch.zeros(hidden.shape[-1], device=self.device))
            else:
                vectors.append(hidden[positions].mean(dim=0))
        return torch.nn.functional.normalize(torch.stack(vectors), dim=1)

    def neural_pairs(self, source_words: list[str], target_words: list[str], threshold: float = 0.56) -> list[tuple[int, int, float]]:
        if not self.available or not source_words or not target_words:
            return []
        source_embeddings = self.word_embeddings(source_words)
        target_embeddings = self.word_embeddings(target_words)
        if source_embeddings is None or target_embeddings is None:
            return []
        scores = source_embeddings @ target_embeddings.T
        pairs: list[tuple[int, int, float]] = []
        for source_index in range(scores.shape[0]):
            for target_index in range(scores.shape[1]):
                score = float(scores[source_index, target_index].item())
                if score >= threshold:
                    pairs.append((source_index, target_index, score))
        pairs.sort(key=lambda item: item[2], reverse=True)
        return pairs

    def align(self, source_words: list[str], target_words: list[str]) -> dict[int, int]:
        source_to_target: dict[int, int] = {}
        used_targets: set[int] = set()
        source_norms = [expanded_normalized_words(word) for word in source_words]
        target_norms = [expanded_normalized_words(word) for word in target_words]

        def lexical_score(left: set[str], right: set[str], source_index: int, target_index: int) -> float:
            if not left or not right:
                return 0.0
            score = 0.0
            if left & right:
                score = 3.0
            if any(token.isdigit() for token in left | right):
                score = max(score, 3.2 if left & right else 0.0)
            if left & ALIGNMENT_NAMES and right & ALIGNMENT_NAMES:
                score = max(score, 3.3 if (left & ALIGNMENT_NAMES) & (right & ALIGNMENT_NAMES) else 0.0)
            if bilingual_hint_match(left, right):
                score = max(score, 2.9)
            if score <= 0.0:
                return 0.0
            source_position = source_index / max(len(source_words) - 1, 1)
            target_position = target_index / max(len(target_words) - 1, 1)
            return score - (0.25 * abs(source_position - target_position))

        lexical_pairs: list[tuple[int, int, float]] = []
        for source_index, left in enumerate(source_norms):
            for target_index, right in enumerate(target_norms):
                score = lexical_score(left, right, source_index, target_index)
                if score > 0.0:
                    lexical_pairs.append((source_index, target_index, score))

        lexical_pairs.sort(key=lambda item: item[2], reverse=True)
        used_sources: set[int] = set()
        for source_index, target_index, _score in lexical_pairs:
            if source_index in used_sources or target_index in used_targets:
                continue
            source_to_target[source_index] = target_index
            used_sources.add(source_index)
            used_targets.add(target_index)

        try:
            neural_pairs = self.neural_pairs(source_words, target_words)
        except Exception as error:
            print(f"[WARN] Neural word alignment unavailable: {error}", flush=True)
            neural_pairs = []

        for source_index, target_index, _score in neural_pairs:
            if source_index in used_sources or target_index in used_targets:
                continue
            source_to_target[source_index] = target_index
            used_sources.add(source_index)
            used_targets.add(target_index)

        return source_to_target


def set_source_ids(tokens: list[WordToken]) -> None:
    for index, token in enumerate(tokens):
        token.source_id = index


def source_time_by_id(tokens: list[WordToken]) -> dict[int, WordToken]:
    return {token.source_id: token for token in tokens if token.source_id is not None}


def apply_projected_ids(
    source_tokens: list[WordToken],
    target_tokens: list[WordToken],
    source_to_target: dict[int, int],
    source_times: dict[int, WordToken] | None = None,
) -> None:
    times = source_times or source_time_by_id(source_tokens)
    used_source_ids: set[int] = set()
    for source_index, target_index in sorted(source_to_target.items()):
        if source_index >= len(source_tokens) or target_index >= len(target_tokens):
            continue
        source_id = source_tokens[source_index].source_id
        if source_id is None or source_id in used_source_ids:
            continue
        source_time = times.get(source_id)
        target = target_tokens[target_index]
        target.source_id = source_id
        if source_time:
            target.start = source_time.start
            target.end = source_time.end
            target.estimated = source_time.estimated
        used_source_ids.add(source_id)


def fill_unassigned_from_direct_source(
    source_tokens: list[WordToken],
    target_tokens: list[WordToken],
    source_to_target: dict[int, int],
) -> None:
    source_times = source_time_by_id(source_tokens)
    used_target_indexes = {index for index, token in enumerate(target_tokens) if token.source_id is not None}
    used_source_ids = {token.source_id for token in target_tokens if token.source_id is not None}
    for source_index, target_index in sorted(source_to_target.items()):
        if target_index in used_target_indexes or source_index >= len(source_tokens) or target_index >= len(target_tokens):
            continue
        source_id = source_tokens[source_index].source_id
        if source_id is None or source_id in used_source_ids:
            continue
        target = target_tokens[target_index]
        source_time = source_times.get(source_id)
        target.source_id = source_id
        if source_time:
            target.start = source_time.start
            target.end = source_time.end
            target.estimated = source_time.estimated
        used_target_indexes.add(target_index)
        used_source_ids.add(source_id)


def token_to_json(token: WordToken) -> dict[str, object]:
    payload: dict[str, object] = {"text": token.text, "source_id": token.source_id}
    if token.start is not None:
        payload["start"] = round(token.start, 3)
    if token.end is not None:
        payload["end"] = round(token.end, 3)
    if token.estimated:
        payload["estimated"] = True
    return payload


def make_wordlink_sentence(
    index: int,
    row: OutputRow,
    english_text: str,
    source_words: list[TimedWord],
    aligner: NeuralWordAligner,
    standard_german_only: bool,
) -> dict[str, object]:
    if standard_german_only:
        source_tokens = source_tokens_for_row(row.standard_text, row.start, row.end, source_words)
        set_source_ids(source_tokens)
        english_tokens = target_tokens_for_text(english_text)
        apply_projected_ids(
            source_tokens,
            english_tokens,
            aligner.align([token.text for token in source_tokens], [token.text for token in english_tokens]),
        )
        lines = [
            {"role": "source", "language": "de", "text": row.standard_text, "tokens": [token_to_json(token) for token in source_tokens]},
            {"role": "english", "language": "en", "text": english_text, "tokens": [token_to_json(token) for token in english_tokens]},
        ]
        mode = "standard_german"
    else:
        source_tokens = source_tokens_for_row(row.dialect_text, row.start, row.end, source_words)
        set_source_ids(source_tokens)
        standard_tokens = target_tokens_for_text(row.standard_text)
        english_tokens = target_tokens_for_text(english_text)

        dialect_to_standard = aligner.align([token.text for token in source_tokens], [token.text for token in standard_tokens])
        apply_projected_ids(source_tokens, standard_tokens, dialect_to_standard)

        standard_to_english = aligner.align([token.text for token in standard_tokens], [token.text for token in english_tokens])
        apply_projected_ids(standard_tokens, english_tokens, standard_to_english, source_time_by_id(source_tokens))

        direct_dialect_to_english = aligner.align([token.text for token in source_tokens], [token.text for token in english_tokens])
        fill_unassigned_from_direct_source(source_tokens, english_tokens, direct_dialect_to_english)

        lines = [
            {"role": "source", "language": "gsw", "text": row.dialect_text, "tokens": [token_to_json(token) for token in source_tokens]},
            {"role": "standard", "language": "de", "text": row.standard_text, "tokens": [token_to_json(token) for token in standard_tokens]},
            {"role": "english", "language": "en", "text": english_text, "tokens": [token_to_json(token) for token in english_tokens]},
        ]
        mode = "swiss_german"

    return {
        "index": index,
        "start": round(row.start, 3),
        "end": round(row.end, 3),
        "mode": mode,
        "lines": lines,
    }


def write_wordlinks_json(
    path: Path,
    rows: list[OutputRow],
    english_lines: list[str],
    source_words: list[TimedWord],
    alignment_model_dir: Path | None,
    standard_german_only: bool,
) -> None:
    aligner = NeuralWordAligner(alignment_model_dir)
    if not aligner.available:
        print("[WARN] Alignment model not found; writing exact-match word links only.", flush=True)
    sentences = [
        make_wordlink_sentence(index, row, english_text, source_words, aligner, standard_german_only)
        for index, (row, english_text) in enumerate(zip(rows, english_lines))
    ]
    payload = {
        "format": "swiss-combo-wordlinks-v1",
        "mode": "standard_german" if standard_german_only else "swiss_german",
        "sentences": sentences,
    }
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def translate_one_text(text: str, tokenizer, model, device: str, max_chars: int) -> str:
    import torch

    text = clean_text(text)
    if not text:
        return ""
    chunks = [text[i : i + max_chars] for i in range(0, len(text), max_chars)]
    translated_chunks: list[str] = []
    for chunk in chunks:
        inputs = tokenizer(chunk, return_tensors="pt", truncation=True, max_length=512).to(device)
        with torch.no_grad():
            generated = model.generate(**inputs, max_new_tokens=256)
        translated_chunks.append(tokenizer.decode(generated[0], skip_special_tokens=True))
    return clean_text(" ".join(translated_chunks))


def translate_texts(
    texts: list[str],
    model_dir: Path,
    max_chars: int,
    translation_cache: Path | None = None,
) -> list[str]:
    cache: dict[str, str] = {}
    source_by_key: dict[str, str] = {}
    if translation_cache:
        cache, source_by_key = load_translation_cache(translation_cache)
        print(f"[INFO] Loaded {len(cache)} cached translations from {translation_cache}", flush=True)

    translations: list[str] = []
    translator: tuple[object, object, str] | None = None
    total = len(texts)
    for row_number, text in enumerate(texts, start=1):
        text = clean_text(text)
        if not text:
            translations.append("")
            continue

        key = cache_key(text)
        source_by_key.setdefault(key, text)
        if key in cache:
            translations.append(cache[key])
            print(f"[INFO] Translation {row_number}/{total}: cache hit", flush=True)
            continue

        if translator is None:
            translator = load_translator(model_dir)
        tokenizer, model, device = translator
        translation = translate_one_text(text, tokenizer, model, device, max_chars)
        cache[key] = translation
        translations.append(translation)
        if translation_cache:
            write_translation_cache(translation_cache, cache, source_by_key)
        print(f"[INFO] Translation {row_number}/{total}: translated", flush=True)
    return translations


def rows_from_standard_blocks(standard_blocks: list[Block]) -> list[OutputRow]:
    return [
        OutputRow(
            dialect_text="",
            standard_text=block.text,
            start=block.start,
            end=max(block.end, block.start + 0.001),
            score=1.0,
        )
        for block in standard_blocks
    ]


def main() -> None:
    args = parse_args()
    standard_blocks = make_sentence_blocks(load_segments(Path(args.standard_json)))
    if not standard_blocks:
        raise RuntimeError("No Standard German timestamp blocks found.")

    if args.standard_german:
        dialect_blocks: list[Block] = []
        skipped_dialect: list[Block] = []
        skipped_standard: list[Block] = []
        rows = rows_from_standard_blocks(standard_blocks)
    else:
        if not args.dialect_json:
            raise RuntimeError("Pass --dialect-json, or use --standard-german for Standard German input audio.")
        dialect_blocks = make_sentence_blocks(load_segments(Path(args.dialect_json)))
        if not dialect_blocks:
            raise RuntimeError("No Swiss German timestamp blocks found.")

        aligned_spans, skipped_dialect, skipped_standard = align_blocks(
            dialect_blocks=dialect_blocks,
            standard_blocks=standard_blocks,
            lookahead=args.lookahead,
            max_span=args.max_span,
            min_score=args.min_score,
        )
        rows = expand_aligned_spans(aligned_spans)
        if args.word_by_word and skipped_dialect:
            rows.extend(make_output_row([block], [], 0.0) for block in skipped_dialect)
            rows.sort(key=lambda row: (row.start, row.end, row.dialect_text))
    if args.limit > 0:
        rows = rows[: args.limit]

    if args.skip_translation:
        english_lines = [""] * len(rows)
    else:
        if not args.translation_model_dir:
            raise RuntimeError("Set TRANSLATION_MODEL_DIR or pass --translation-model-dir.")
        translation_model_dir = Path(args.translation_model_dir).resolve()
        translation_cache = Path(args.translation_cache).resolve() if args.translation_cache else None
        english_lines = translate_texts(
            [row.standard_text for row in rows],
            translation_model_dir,
            args.max_translate_chars,
            translation_cache,
        )

    if args.debug_alignment:
        debug_output = Path(args.debug_alignment).resolve()
        debug_output.parent.mkdir(parents=True, exist_ok=True)
        debug_lines = ["start\tend\tscore\tdialect\tstandard"]
        for row in rows:
            debug_lines.append(f"{row.start:.3f}\t{row.end:.3f}\t{row.score:.3f}\t{row.dialect_text}\t{row.standard_text}")
        atomic_write_text(debug_output, "\n".join(debug_lines) + "\n")

    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.word_by_word:
        if args.standard_german:
            source_words_path = Path(args.standard_words_json or args.standard_json).resolve()
        else:
            source_words_path = Path(args.dialect_words_json or args.dialect_json).resolve()
        source_words = load_timed_words(source_words_path)
        alignment_model_dir = Path(args.alignment_model_dir).resolve() if args.alignment_model_dir else None
        write_wordlinks_json(
            output,
            rows,
            english_lines,
            source_words,
            alignment_model_dir,
            args.standard_german,
        )
        print(f"Wrote {output}")
        return

    lines: list[str] = []
    for row, english_text in zip(rows, english_lines):
        lines.extend([*visible_lines(row, english_text, args.standard_german, args.word_by_word), ""])
    atomic_write_text(output, "\n".join(lines).rstrip() + "\n")
    print(f"Wrote {output}")

    srt_output = Path(args.srt_output).resolve() if args.srt_output else output.with_suffix(".srt")
    write_srt(srt_output, rows, english_lines, args.standard_german, args.word_by_word)
    print(f"Wrote {srt_output}")
    if args.standard_german:
        print(f"Wrote {len(rows)} rows from {len(standard_blocks)} Standard German sentences.")
    else:
        print(
            "Aligned "
            f"{len(rows)} rows from {len(dialect_blocks)} Swiss German and {len(standard_blocks)} Standard German sentences "
            f"({len(skipped_dialect)} Swiss German skipped, {len(skipped_standard)} Standard German skipped)."
        )


if __name__ == "__main__":
    main()
