from __future__ import annotations

import json
import sys
import time
import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, messagebox

try:
    import pygame
except Exception:
    pygame = None


WINDOW_BG = "#121218"
PANEL_BG = "#1a1a20"
CARD_BG = "#22222a"
CARD_BORDER = "#3a3a44"
TEXT_BASE = "#f5f5f5"
TEXT_TIMED = "#c2c2c2"
TEXT_MUTED = "#d2d2dc"
ACTIVE_BG = "#ffd740"
ACTIVE_TEXT = "#202020"
WORDLIST_BG = "#181820"
DELETE_BG = "#4a2630"
MAX_VISIBLE_LINES = 3
TICK_MS = 40
SHORT_GAP_HOLD_SECONDS = 1.5

ARTICLE_GENDERS = {
    "der": "m",
    "die": "f/pl",
    "das": "n",
    "ein": "m/n",
    "eine": "f",
    "einer": "f",
}


@dataclass
class SubtitleToken:
    text: str = ""
    source_id: int | None = None
    start: float | None = None
    end: float | None = None
    estimated: bool | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "SubtitleToken":
        return cls(
            text=data.get("text", ""),
            source_id=data.get("source_id"),
            start=data.get("start"),
            end=data.get("end"),
            estimated=data.get("estimated"),
        )

    def has_timing(self) -> bool:
        return self.start is not None and self.end is not None

    def is_active(self, time_seconds: float) -> bool:
        return self.has_timing() and self.start <= time_seconds <= self.end


@dataclass
class SubtitleLine:
    role: str = ""
    language: str = ""
    text: str = ""
    tokens: list[SubtitleToken] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "SubtitleLine":
        return cls(
            role=data.get("role", ""),
            language=data.get("language", ""),
            text=data.get("text", ""),
            tokens=[SubtitleToken.from_dict(token) for token in data.get("tokens", [])],
        )

    def display_name(self) -> str:
        if self.role and self.language:
            return f"{self.role} ({self.language.upper()})"
        if self.role:
            return self.role
        if self.language:
            return self.language.upper()
        return "Line"


@dataclass
class Sentence:
    index: int = 0
    start: float = 0.0
    end: float = 0.0
    mode: str = ""
    lines: list[SubtitleLine] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "Sentence":
        return cls(
            index=data.get("index", 0),
            start=float(data.get("start", 0.0)),
            end=float(data.get("end", 0.0)),
            mode=data.get("mode", ""),
            lines=[SubtitleLine.from_dict(line) for line in data.get("lines", [])],
        )

    def contains(self, time_seconds: float) -> bool:
        return self.start <= time_seconds <= self.end


@dataclass
class WordLinksProject:
    format: str = ""
    mode: str = ""
    sentences: list[Sentence] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "WordLinksProject":
        return cls(
            format=data.get("format", ""),
            mode=data.get("mode", ""),
            sentences=[Sentence.from_dict(sentence) for sentence in data.get("sentences", [])],
        )


class AudioPlayer:
    def __init__(self) -> None:
        self.available = pygame is not None
        self.loaded_path: Path | None = None
        self.playing = False
        self.anchor_seconds = 0.0
        self.anchor_perf = time.perf_counter()
        if self.available:
            try:
                pygame.mixer.init()
            except Exception:
                self.available = False

    def load(self, path: Path) -> None:
        if not self.available or pygame is None:
            raise RuntimeError("Optional audio playback needs pygame. Install it with: python3 -m pip install pygame")
        pygame.mixer.music.load(str(path))
        self.loaded_path = path
        self.playing = False
        self.anchor_seconds = 0.0

    def play(self, seconds: float) -> None:
        if not self.available or pygame is None or self.loaded_path is None:
            return
        seconds = max(seconds, 0.0)
        pygame.mixer.music.play(start=seconds)
        self.playing = True
        self.anchor_seconds = seconds
        self.anchor_perf = time.perf_counter()

    def pause(self) -> None:
        if self.available and pygame is not None:
            pygame.mixer.music.stop()
        self.playing = False

    def position(self, fallback_seconds: float) -> float:
        if not self.playing:
            return fallback_seconds
        return self.anchor_seconds + (time.perf_counter() - self.anchor_perf)


class SubtitleLineView:
    def __init__(self, parent: tk.Widget, on_token_click=None) -> None:
        self.container = tk.Frame(parent, bg=CARD_BG, highlightthickness=1, highlightbackground=CARD_BORDER)
        self.on_token_click = on_token_click
        self.label_font = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        self.text_font = tkfont.Font(family="Segoe UI", size=18)
        self.label = tk.Label(
            self.container,
            text="Language",
            fg=TEXT_MUTED,
            bg=CARD_BG,
            font=self.label_font,
        )
        self.label.pack(fill="x", pady=(10, 4))

        self.text = tk.Text(
            self.container,
            wrap="word",
            height=4,
            bd=0,
            relief="flat",
            padx=16,
            pady=14,
            bg=PANEL_BG,
            fg=TEXT_BASE,
            insertbackground=TEXT_BASE,
            font=self.text_font,
        )
        self.text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.text.configure(state="disabled", cursor="arrow")

        self.text.tag_configure("plain", foreground=TEXT_BASE, background=PANEL_BG)
        self.text.tag_configure("timed", foreground=TEXT_TIMED, background=PANEL_BG)
        self.text.tag_configure("active", foreground=ACTIVE_TEXT, background=ACTIVE_BG)

    def set_scale(self, scale: float) -> None:
        self.label_font.configure(size=max(8, round(11 * scale)))
        self.text_font.configure(size=max(12, round(18 * scale)))
        self.text.configure(padx=round(16 * scale), pady=round(14 * scale), height=max(3, round(4 * scale)))

    def show(self) -> None:
        self.container.pack(fill="x", expand=False, pady=6)

    def hide(self) -> None:
        self.container.pack_forget()

    def clear(self) -> None:
        self.label.config(text="Language")
        self._set_readonly_text([])

    def render(self, line: SubtitleLine, active_time_seconds: float) -> None:
        self.label.config(text=line.display_name())
        parts: list[tuple[str, str, int | None]] = []

        if line.tokens:
            for index, token in enumerate(line.tokens):
                if index > 0:
                    parts.append((" ", "plain", None))
                style = "active" if token.is_active(active_time_seconds) else "timed" if token.has_timing() else "plain"
                parts.append((token.text or "", style, index))
        else:
            parts.append((line.text or "", "plain", None))

        self._set_readonly_text(parts, line)

    def _set_readonly_text(self, parts: list[tuple[str, str, int | None]], line: SubtitleLine | None = None) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")

        for content, tag, token_index in parts:
            if token_index is None or line is None or self.on_token_click is None:
                self.text.insert("end", content, tag)
                continue
            click_tag = f"token_{line.role}_{token_index}"
            self.text.insert("end", content, (tag, click_tag))
            self.text.tag_bind(click_tag, "<Button-1>", lambda _event, role=line.role, index=token_index: self.on_token_click(role, index))
            self.text.tag_bind(click_tag, "<Enter>", lambda _event: self.text.configure(cursor="hand2"))
            self.text.tag_bind(click_tag, "<Leave>", lambda _event: self.text.configure(cursor="arrow"))

        self.text.tag_add("center", "1.0", "end")
        self.text.tag_configure("center", justify="center")
        self.text.configure(state="disabled")


class SubtitleViewerApp:
    def __init__(self, initial_path: Path | None = None) -> None:
        self.root = tk.Tk()
        self.root.title("Wordlinks Subtitle Viewer")
        self.root.configure(bg=WINDOW_BG)
        self.root.minsize(1100, 700)

        self.project: WordLinksProject | None = None
        self.current_file: Path | None = None
        self.current_sentence: Sentence | None = None
        self.total_seconds = 0.0
        self.playback_seconds = 0.0
        self.playing = False
        self.last_tick = time.perf_counter()
        self.scrubbing = False
        self.ui_scale = 1.0
        self.line_order_modes = [
            ("Source → Standard → English", ["source", "standard", "english"]),
            ("English → Standard → Source", ["english", "standard", "source"]),
            ("Standard → Source → English", ["standard", "source", "english"]),
        ]
        self.line_order_index = 0
        self.audio_player = AudioPlayer()
        self.audio_file: Path | None = None
        self.wordbook_entries: list[dict[str, str]] = []

        self.file_var = tk.StringVar(value="No JSON loaded")
        self.audio_var = tk.StringVar(value="No audio loaded")
        self.current_time_var = tk.StringVar(value="00:00.00")
        self.remaining_time_var = tk.StringVar(value="Remaining: 00:00.00")
        self.active_sentence_var = tk.StringVar(value="No active subtitle")
        self.offset_var = tk.StringVar(value="Offset: 0 ms")
        self.speed_var = tk.StringVar(value="Speed: 1.00x")
        self.scale_var = tk.StringVar(value="Scale: 100%")
        self.line_order_var = tk.StringVar(value=self.line_order_modes[0][0])
        self.timeline_var = tk.DoubleVar(value=0.0)
        self.offset_ms_var = tk.IntVar(value=0)
        self.custom_speed_var = tk.StringVar(value="1.0")
        self.playback_speed = 1.0

        self.line_views: list[SubtitleLineView] = []
        self.wordbook_rows: list[tk.Frame] = []
        self._build_ui()

        if initial_path is not None:
            self.load_project(initial_path)

        self.root.after(TICK_MS, self._tick)

    def _build_ui(self) -> None:
        top = tk.Frame(self.root, bg=WINDOW_BG)
        top.pack(fill="x", padx=16, pady=(16, 0))

        load_button = tk.Button(top, text="Load JSON", command=self.choose_file, padx=12, pady=6)
        load_button.pack(side="left")

        audio_button = tk.Button(top, text="Load Audio", command=self.choose_audio, padx=12, pady=6)
        audio_button.pack(side="left", padx=(8, 0))

        file_label = tk.Label(top, textvariable=self.file_var, fg=TEXT_BASE, bg=WINDOW_BG, anchor="w", font=("Segoe UI", 10))
        file_label.pack(side="left", fill="x", expand=True, padx=(12, 0))

        audio_label = tk.Label(self.root, textvariable=self.audio_var, fg=TEXT_MUTED, bg=WINDOW_BG, anchor="w", font=("Segoe UI", 10))
        audio_label.pack(fill="x", padx=16, pady=(4, 0))

        body = tk.Frame(self.root, bg=WINDOW_BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        subtitle_frame = tk.Frame(body, bg=WINDOW_BG)
        subtitle_frame.pack(side="left", fill="both", expand=True)

        for _ in range(MAX_VISIBLE_LINES):
            line_view = SubtitleLineView(subtitle_frame, self.add_clicked_word)
            self.line_views.append(line_view)

        self.wordbook = tk.Frame(body, bg=WORDLIST_BG, highlightthickness=1, highlightbackground=CARD_BORDER, width=420)
        self.wordbook.pack(side="right", fill="y", padx=(14, 0))
        self.wordbook.pack_propagate(False)

        tk.Label(
            self.wordbook,
            text="Unknown Word Book",
            fg=TEXT_BASE,
            bg=WORDLIST_BG,
            font=("Segoe UI", 12, "bold"),
        ).pack(fill="x", padx=10, pady=(10, 6))

        header = tk.Frame(self.wordbook, bg=WORDLIST_BG)
        header.pack(fill="x", padx=8)
        for label, width in [("Swiss", 10), ("Standard (gender)", 16), ("English", 10), ("", 3)]:
            tk.Label(header, text=label, fg=TEXT_MUTED, bg=WORDLIST_BG, width=width, anchor="w", font=("Segoe UI", 9, "bold")).pack(side="left")

        self.wordbook_list = tk.Frame(self.wordbook, bg=WORDLIST_BG)
        self.wordbook_list.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        controls = tk.Frame(self.root, bg=WINDOW_BG)
        controls.pack(fill="x", padx=16, pady=(0, 16))

        info = tk.Frame(controls, bg=WINDOW_BG)
        info.pack(fill="x")

        tk.Label(info, textvariable=self.current_time_var, fg=TEXT_BASE, bg=WINDOW_BG, font=("Segoe UI", 11, "bold")).pack(side="left")
        tk.Label(info, textvariable=self.remaining_time_var, fg=TEXT_BASE, bg=WINDOW_BG, font=("Segoe UI", 11, "bold")).pack(side="left", padx=(16, 0))
        tk.Label(info, textvariable=self.active_sentence_var, fg=TEXT_MUTED, bg=WINDOW_BG, font=("Segoe UI", 11)).pack(side="left", padx=(16, 0))

        timeline = tk.Scale(
            controls,
            from_=0.0,
            to=1.0,
            resolution=0.01,
            orient="horizontal",
            variable=self.timeline_var,
            showvalue=False,
            highlightthickness=0,
            troughcolor=CARD_BORDER,
            bg=WINDOW_BG,
            fg=TEXT_BASE,
            activebackground=ACTIVE_BG,
            command=self.on_timeline_change,
        )
        timeline.pack(fill="x", pady=(8, 8))
        timeline.bind("<ButtonPress-1>", self.on_scrub_start)
        timeline.bind("<ButtonRelease-1>", self.on_scrub_end)
        self.timeline = timeline

        buttons = tk.Frame(controls, bg=WINDOW_BG)
        buttons.pack(fill="x")

        self.play_pause_button = tk.Button(buttons, text="Play", command=self.toggle_playback, state="disabled", padx=12, pady=6)
        self.play_pause_button.pack(side="left")

        tk.Button(buttons, text="Restart", command=self.restart_playback, padx=12, pady=6).pack(side="left", padx=(8, 0))
        tk.Button(buttons, text="-1s", command=lambda: self.set_playback_seconds(self.playback_seconds - 1.0), padx=12, pady=6).pack(side="left", padx=(8, 0))
        tk.Button(buttons, text="+1s", command=lambda: self.set_playback_seconds(self.playback_seconds + 1.0), padx=12, pady=6).pack(side="left", padx=(8, 0))

        offset_controls = tk.Frame(buttons, bg=WINDOW_BG)
        offset_controls.pack(side="left", padx=(18, 0))
        tk.Label(offset_controls, text="Subtitle offset", fg=TEXT_BASE, bg=WINDOW_BG, font=("Segoe UI", 10)).pack(side="left")

        offset_scale = tk.Scale(
            offset_controls,
            from_=-5000,
            to=5000,
            resolution=50,
            orient="horizontal",
            variable=self.offset_ms_var,
            showvalue=False,
            highlightthickness=0,
            troughcolor=CARD_BORDER,
            bg=WINDOW_BG,
            fg=TEXT_BASE,
            activebackground=ACTIVE_BG,
            length=220,
            command=self.on_offset_change,
        )
        offset_scale.pack(side="left", padx=(10, 8))
        self.offset_scale = offset_scale

        tk.Label(offset_controls, textvariable=self.offset_var, fg=TEXT_MUTED, bg=WINDOW_BG, font=("Segoe UI", 10)).pack(side="left")

        speed_controls = tk.Frame(buttons, bg=WINDOW_BG)
        speed_controls.pack(side="left", padx=(18, 0))
        tk.Label(speed_controls, text="Playback speed", fg=TEXT_BASE, bg=WINDOW_BG, font=("Segoe UI", 10)).pack(side="left")
        tk.Button(speed_controls, text="1.0x", command=lambda: self.set_playback_speed(1.0), padx=10, pady=4).pack(side="left", padx=(10, 0))
        tk.Button(speed_controls, text="0.8x", command=lambda: self.set_playback_speed(0.8), padx=10, pady=4).pack(side="left", padx=(6, 0))
        tk.Button(speed_controls, text="0.5x", command=lambda: self.set_playback_speed(0.5), padx=10, pady=4).pack(side="left", padx=(6, 0))

        custom_speed_entry = tk.Entry(speed_controls, textvariable=self.custom_speed_var, width=6)
        custom_speed_entry.pack(side="left", padx=(8, 0))
        custom_speed_entry.bind("<Return>", lambda _event: self.apply_custom_speed())

        tk.Button(speed_controls, text="Set", command=self.apply_custom_speed, padx=10, pady=4).pack(side="left", padx=(6, 0))
        tk.Label(speed_controls, textvariable=self.speed_var, fg=TEXT_MUTED, bg=WINDOW_BG, font=("Segoe UI", 10)).pack(side="left", padx=(8, 0))

        view_controls = tk.Frame(controls, bg=WINDOW_BG)
        view_controls.pack(fill="x", pady=(8, 0))

        tk.Button(view_controls, text="Swap language order", command=self.cycle_line_order, padx=12, pady=5).pack(side="left")
        tk.Label(view_controls, textvariable=self.line_order_var, fg=TEXT_MUTED, bg=WINDOW_BG, font=("Segoe UI", 10)).pack(side="left", padx=(8, 18))
        tk.Button(view_controls, text="A-", command=lambda: self.set_ui_scale(self.ui_scale - 0.1), padx=10, pady=5).pack(side="left")
        tk.Button(view_controls, text="A+", command=lambda: self.set_ui_scale(self.ui_scale + 0.1), padx=10, pady=5).pack(side="left", padx=(6, 0))
        tk.Label(view_controls, textvariable=self.scale_var, fg=TEXT_MUTED, bg=WINDOW_BG, font=("Segoe UI", 10)).pack(side="left", padx=(8, 0))

    def choose_file(self) -> None:
        initial_dir = self.current_file.parent if self.current_file else Path.cwd()
        selected = filedialog.askopenfilename(
            parent=self.root,
            title="Open subtitle JSON",
            initialdir=initial_dir,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if selected:
            self.load_project(Path(selected))

    def choose_audio(self) -> None:
        initial_dir = self.audio_file.parent if self.audio_file else Path.cwd()
        selected = filedialog.askopenfilename(
            parent=self.root,
            title="Open audio file",
            initialdir=initial_dir,
            filetypes=[("Audio files", "*.mp3 *.wav *.ogg *.flac *.m4a"), ("All files", "*.*")],
        )
        if not selected:
            return

        path = Path(selected)
        self.audio_file = path
        try:
            self.audio_player.load(path)
        except Exception as exc:
            self.audio_var.set(f"{path.name} | audio sync unavailable: {exc}")
            return
        self.audio_var.set(f"{path.name} | audio sync enabled")

    def load_project(self, path: Path) -> None:
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            self.project = WordLinksProject.from_dict(data)
        except Exception as exc:
            messagebox.showerror("Load error", f"Could not load JSON file:\n{exc}", parent=self.root)
            return

        self.pause_playback()
        self.current_file = path
        self.total_seconds = max((sentence.end for sentence in self.project.sentences), default=0.0)
        self.playback_seconds = 0.0
        self.timeline.configure(to=max(self.total_seconds, 1.0))
        self.timeline_var.set(0.0)
        self.file_var.set(f"{path.name} | format: {self.project.format or '-'} | mode: {self.project.mode or '-'}")
        self.root.title(f"Wordlinks Subtitle Viewer - {path.name}")
        self.play_pause_button.configure(state="normal" if self.total_seconds > 0.0 else "disabled")
        self.render_current_state()

    def toggle_playback(self) -> None:
        if self.playing:
            self.pause_playback()
        else:
            self.start_playback()

    def start_playback(self) -> None:
        if self.project is None:
            return
        if self.playback_seconds >= self.total_seconds:
            self.set_playback_seconds(0.0)
        if self.audio_player.loaded_path is not None:
            self.audio_player.play(self.playback_seconds)
        self.playing = True
        self.last_tick = time.perf_counter()
        self.play_pause_button.configure(text="Pause")

    def pause_playback(self) -> None:
        if self.audio_player.loaded_path is not None:
            self.audio_player.pause()
        self.playing = False
        self.play_pause_button.configure(text="Play")

    def restart_playback(self) -> None:
        self.pause_playback()
        self.set_playback_seconds(0.0)

    def on_scrub_start(self, _event: tk.Event) -> None:
        self.scrubbing = True

    def on_scrub_end(self, _event: tk.Event) -> None:
        self.scrubbing = False
        self.set_playback_seconds(self.timeline_var.get())
        self.last_tick = time.perf_counter()

    def on_timeline_change(self, raw_value: str) -> None:
        if self.project is None:
            return
        if self.scrubbing or not self.playing:
            self.set_playback_seconds(float(raw_value), update_scale=False)

    def on_offset_change(self, raw_value: str) -> None:
        self.offset_var.set(f"Offset: {int(float(raw_value))} ms")
        self.render_current_state()

    def set_playback_speed(self, speed: float) -> None:
        speed = max(0.05, speed)
        self.playback_speed = speed
        self.custom_speed_var.set(f"{speed:.2f}".rstrip("0").rstrip("."))
        self.speed_var.set(f"Speed: {speed:.2f}x")

    def apply_custom_speed(self) -> None:
        raw = self.custom_speed_var.get().strip()
        try:
            speed = float(raw)
        except ValueError:
            messagebox.showerror("Invalid speed", "Playback speed must be a number like 0.8, 0.5, or 1.25.", parent=self.root)
            return

        if speed <= 0:
            messagebox.showerror("Invalid speed", "Playback speed must be greater than 0.", parent=self.root)
            return

        self.set_playback_speed(speed)

    def set_playback_seconds(self, value: float, update_scale: bool = True, sync_audio: bool = True) -> None:
        self.playback_seconds = max(0.0, min(value, self.total_seconds))
        if sync_audio and self.playing and self.audio_player.loaded_path is not None:
            self.audio_player.play(self.playback_seconds)
        if update_scale:
            self.timeline_var.set(self.playback_seconds)
        self.render_current_state()

    def cycle_line_order(self) -> None:
        self.line_order_index = (self.line_order_index + 1) % len(self.line_order_modes)
        self.line_order_var.set(self.line_order_modes[self.line_order_index][0])
        self.render_current_state()

    def ordered_lines(self, lines: list[SubtitleLine]) -> list[SubtitleLine]:
        role_order = self.line_order_modes[self.line_order_index][1]
        visible_lines = [line for line in lines if line.tokens or line.text.strip()]
        by_role = {line.role: line for line in visible_lines}
        ordered = [by_role[role] for role in role_order if role in by_role]
        ordered.extend(line for line in visible_lines if line.role not in set(role_order))
        return ordered

    def set_ui_scale(self, scale: float) -> None:
        self.ui_scale = min(max(scale, 0.7), 1.8)
        self.scale_var.set(f"Scale: {round(self.ui_scale * 100)}%")
        self.root.tk.call("tk", "scaling", self.ui_scale)
        for line_view in self.line_views:
            line_view.set_scale(self.ui_scale)
        self.render_current_state()

    def render_current_state(self) -> None:
        self.current_time_var.set(self.format_time(self.playback_seconds))
        self.remaining_time_var.set(f"Remaining: {self.format_time(max(self.total_seconds - self.playback_seconds, 0.0))}")

        if self.project is None:
            self.current_sentence = None
            self.active_sentence_var.set("No active subtitle")
            self.clear_lines()
            return

        subtitle_time = self.playback_seconds - (self.offset_ms_var.get() / 1000.0)
        sentence = self.find_sentence_at(subtitle_time)

        if sentence is None:
            self.current_sentence = None
            self.active_sentence_var.set("No active subtitle")
            self.clear_lines()
            return

        self.current_sentence = sentence
        self.active_sentence_var.set(f"Sentence {sentence.index} | subtitle time {subtitle_time:.2f} s")

        lines = self.ordered_lines(sentence.lines)
        for index, line_view in enumerate(self.line_views):
            if index < len(lines):
                line_view.show()
                line_view.render(lines[index], subtitle_time)
            else:
                line_view.hide()
                line_view.clear()

    def add_clicked_word(self, role: str, token_index: int) -> None:
        if self.current_sentence is None:
            return
        entry = self.build_wordbook_entry(self.current_sentence, role, token_index)
        if entry is None:
            return
        key = (entry["swiss"].lower(), entry["standard"].lower(), entry["english"].lower())
        if not any((item["swiss"].lower(), item["standard"].lower(), item["english"].lower()) == key for item in self.wordbook_entries):
            self.wordbook_entries.append(entry)
            self.render_wordbook()

    @staticmethod
    def build_wordbook_entry(sentence: Sentence, role: str, token_index: int) -> dict[str, str] | None:
        line_by_role = {line.role: line for line in sentence.lines}
        clicked_line = line_by_role.get(role)
        if clicked_line is None or token_index >= len(clicked_line.tokens):
            return None
        clicked_token = clicked_line.tokens[token_index]
        source_id = clicked_token.source_id

        source_token = SubtitleViewerApp.find_token_by_source_id(line_by_role.get("source"), source_id)
        standard_token = SubtitleViewerApp.find_token_by_source_id(line_by_role.get("standard"), source_id)
        english_token = SubtitleViewerApp.find_token_by_source_id(line_by_role.get("english"), source_id)

        if source_token is None and role == "source":
            source_token = clicked_token
        if standard_token is None and role == "standard":
            standard_token = clicked_token
        if english_token is None and role == "english":
            english_token = clicked_token

        gender = SubtitleViewerApp.infer_gender(line_by_role.get("standard"), standard_token)
        return {
            "swiss": source_token.text if source_token else "",
            "standard": standard_token.text if standard_token else "",
            "gender": gender,
            "english": english_token.text if english_token else "",
        }

    @staticmethod
    def find_token_by_source_id(line: SubtitleLine | None, source_id: int | None) -> SubtitleToken | None:
        if line is None or source_id is None:
            return None
        for token in line.tokens:
            if token.source_id == source_id:
                return token
        return None

    @staticmethod
    def infer_gender(standard_line: SubtitleLine | None, standard_token: SubtitleToken | None) -> str:
        if standard_line is None or standard_token is None:
            return "?"
        stripped_token = standard_token.text.strip(".,;:!?«»\"'()[]{}")
        if not stripped_token[:1].isupper():
            return "?"
        for index, token in enumerate(standard_line.tokens):
            if token is not standard_token:
                continue
            for previous in reversed(standard_line.tokens[max(0, index - 3) : index]):
                article = previous.text.lower().strip(".,;:!?«»\"'()[]{}")
                if article in ARTICLE_GENDERS:
                    return ARTICLE_GENDERS[article]
            return "?"
        return "?"

    def render_wordbook(self) -> None:
        for row in self.wordbook_rows:
            row.destroy()
        self.wordbook_rows = []

        for index, entry in enumerate(self.wordbook_entries):
            row = tk.Frame(self.wordbook_list, bg=WORDLIST_BG)
            row.pack(fill="x", pady=2)
            standard = entry["standard"]
            if entry["gender"] and entry["gender"] != "?":
                standard = f"{standard} ({entry['gender']})"
            for value, width in [(entry["swiss"], 10), (standard or "?", 16), (entry["english"], 10)]:
                tk.Label(row, text=value or "-", fg=TEXT_BASE, bg=WORDLIST_BG, width=width, anchor="w", font=("Segoe UI", 9)).pack(side="left")
            tk.Button(row, text="x", bg=DELETE_BG, fg=TEXT_BASE, command=lambda i=index: self.delete_wordbook_entry(i), padx=4, pady=0).pack(side="left")
            self.wordbook_rows.append(row)

    def delete_wordbook_entry(self, index: int) -> None:
        if 0 <= index < len(self.wordbook_entries):
            del self.wordbook_entries[index]
            self.render_wordbook()

    def clear_lines(self) -> None:
        for line_view in self.line_views:
            line_view.hide()
            line_view.clear()

    def find_sentence_at(self, subtitle_time: float) -> Sentence | None:
        if self.project is None:
            return None
        previous: Sentence | None = None
        for sentence in self.project.sentences:
            if sentence.contains(subtitle_time):
                return sentence
            if sentence.end < subtitle_time:
                previous = sentence
                continue
            if previous is not None and 0.0 < subtitle_time - previous.end <= SHORT_GAP_HOLD_SECONDS:
                return previous
            if 0.0 < sentence.start - subtitle_time <= SHORT_GAP_HOLD_SECONDS:
                return sentence
            return None
        return None

    def _tick(self) -> None:
        if self.playing and not self.scrubbing:
            now = time.perf_counter()
            delta = now - self.last_tick
            self.last_tick = now
            if self.audio_player.loaded_path is not None:
                next_seconds = self.audio_player.position(self.playback_seconds)
            else:
                next_seconds = self.playback_seconds + (delta * self.playback_speed)
            self.set_playback_seconds(next_seconds, sync_audio=False)
            if self.playback_seconds >= self.total_seconds:
                self.pause_playback()
        else:
            self.last_tick = time.perf_counter()

        self.root.after(TICK_MS, self._tick)

    @staticmethod
    def format_time(seconds: float) -> str:
        minutes = int(seconds // 60)
        remaining_seconds = seconds - (minutes * 60)
        return f"{minutes:02d}:{remaining_seconds:05.2f}"

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    initial_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    app = SubtitleViewerApp(initial_path)
    app.run()


if __name__ == "__main__":
    main()
