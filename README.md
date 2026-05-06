# Swiss Combo Subtitles

This app turns one audio file into subtitle text.

For Swiss German audio, it writes each sentence as three lines:

```text
Swiss German
Standard German
English
```

It also writes an `.srt` subtitle file with timestamps, so the same lines can be shown while the audio is playing.

## How It Works

The app runs the same audio through two speech-to-text models:

- one model hears the audio and writes Swiss German-style text
- one model hears the audio and writes Standard German text

Then the app compares those two transcripts sentence by sentence. This matters because the two models do not always split the audio in exactly the same place. The app lines up the matching sentences, keeps the best timestamp for each sentence, and translates the Standard German sentence into English.

The final output is written in two formats:

- `.txt`: easy to read or edit
- `.srt`: subtitle format for video/audio players

Intermediate files are kept in `work/`, so rerunning the same audio can reuse existing transcripts and translations.

## Build

On Aoraki:

```bash
cd swiss_combo_repo
bash build.sh
```

This installs the needed Python packages into `python_packages/` and downloads the speech, translation, and word-alignment models into this repo. These downloaded files are ignored by git.

The build also creates the default Whisper deployments if they are missing:

- `swiss-german-swiss/`: Swiss German audio to Swiss German-style text
- `swiss_german/`: Swiss German audio to Standard German text

The generated deployments force Whisper language `de`, which helps reduce cases where the Swiss German model drifts into English or unrelated scripts.

If you already have your own deployments, point to them like this:

```bash
DIALECT_DIR=/path/to/swiss-german-model \
STANDARD_DIR=/path/to/standard-german-model \
bash build.sh
```

Each deployment folder must contain `env.sh` and `scripts/transcribe.py`.

## Run With Swiss German Audio

```bash
bash submit_combo.sh path/to/audio.mp3
```

By default, this writes:

```text
outputs/audio.parallel.txt
outputs/audio.parallel.srt
```

Each sentence block looks like this:

```text
I ha de Eden gseh.
Ich habe Eden gesehen.
I saw Eden.
```

You can choose the output path:

```bash
bash submit_combo.sh path/to/audio.mp3 outputs/my_file.parallel.txt
```

## Run With Standard German Audio

If the input audio is already Standard German, use `--standard-german`:

```bash
bash submit_combo.sh --standard-german path/to/audio.mp3
```

This skips the Swiss German transcript and writes only two lines per sentence:

```text
Ich habe Eden gesehen.
I saw Eden.
```

By default, this writes:

```text
outputs/audio.standard.txt
outputs/audio.standard.srt
```

## Word-By-Word JSON

Use `--word-by-word` when you want a JSON file for language learning:

```bash
bash submit_combo.sh --word-by-word path/to/audio.mp3
```

This writes JSON only:

```text
outputs/audio.parallel.wordlinks.json
```

For Standard German audio:

```bash
bash submit_combo.sh --standard-german --word-by-word path/to/audio.mp3
```

This writes:

```text
outputs/audio.standard.wordlinks.json
```

The JSON uses `source_id` numbers. The numbers always come from the original language:

- Swiss German audio: Swiss German words get IDs `0, 1, 2, ...`
- Standard German audio: Standard German words get IDs `0, 1, 2, ...`

Matched words in the other languages reuse the same `source_id`. Extra words in Standard German or English stay unlinked with `"source_id": null`.

Example:

```json
{
  "text": "Mika",
  "source_id": 1,
  "start": 95.2,
  "end": 95.35
}
```

The `start` and `end` values are word timestamps from the original audio. If the app cannot get exact word timestamps from Whisper, it estimates them inside the sentence and adds `"estimated": true`.

The word matching uses a multilingual BERT-style alignment model, plus simple exact-name and number matching so names like Mika keep the same ID across languages.

For the Zambo test file used in this repo:

```bash
bash submit_combo.sh --word-by-word audio/Zambo_Hoerspiele_fuer_Kinder_radio_AUDI20260415_NR_0022_684146339442420ca5187a1c4f5e92b1.mp3
```

That writes:

```text
outputs/Zambo_Hoerspiele_fuer_Kinder_radio_AUDI20260415_NR_0022_684146339442420ca5187a1c4f5e92b1.parallel.wordlinks.json
```

## View Wordlinks

Open the JSON viewer:

```bash
python3 subtitle_viewer.py outputs/audio.parallel.wordlinks.json
```

The viewer can:

- show the current sentence and highlighted word timing
- swap the language order
- scale the GUI larger or smaller
- show elapsed time and minutes remaining
- apply a subtitle offset if you are playing audio somewhere else

If `pygame` is installed on your laptop, the viewer can also load and play an audio file directly:

```bash
python3 -m pip install pygame
python3 subtitle_viewer.py outputs/audio.parallel.wordlinks.json
```

Then click `Load Audio`.

## Lighter Local Pipeline Ideas

The current pipeline uses large Whisper deployments because Swiss German speech recognition is hard. For a laptop-friendly version, the most practical direction is:

- use `faster-whisper` / CTranslate2 with int8 quantization for lower CPU/GPU memory use
- try smaller Whisper models first, such as `small` or `medium`, and accept lower accuracy
- try Distil-Whisper for faster, smaller Whisper-style transcription
- keep translation local with OPUS-MT or another small local machine-translation model
- keep word alignment local with multilingual BERT embeddings plus the current dictionary hints

The likely tradeoff is accuracy. A smaller model may run on a normal laptop, but it may produce more English hallucinations or worse Swiss German spelling. For best quality, the ASR model choice matters more than the viewer or JSON format.

## Useful Options

Rerun everything from scratch:

```bash
FORCE=1 bash submit_combo.sh path/to/audio.mp3
```

Choose Slurm resources:

```bash
TIME=08:00:00 MEM=120G CPUS=4 PARTITION=aoraki_gpu_L40 bash submit_combo.sh path/to/audio.mp3
```

## Important Files

- `build.sh`: installs packages and downloads models.
- `submit_combo.sh`: the normal command to submit a job.
- `run_combo.slurm`: the Slurm job script.
- `scripts/build_parallel_subtitles.py`: lines up sentences, translates them, and writes `.txt`, `.srt`, or wordlink `.json` output.
- `work/`: intermediate transcripts and translation cache.
- `outputs/`: final text, subtitle, and alignment files.
