# Transcriber

A personal, local web app that turns a video or audio file into a timestamped text transcript, in English, Indonesian, or a mix of both.

## Language

**Recording**:
The video or audio file the user imports to be transcribed.
_Avoid_: Upload, file, media

**Transcript**:
The timestamped text produced from one Recording.
_Avoid_: Result, output, subtitles

**Segment**:
One timestamped span of a Transcript: a start time, an end time, and the words spoken between them.
_Avoid_: Line, chunk, caption

**Job**:
One attempt to turn a Recording into a Transcript. It moves from extracting audio to transcribing, and ends as done, failed, or cancelled. A cancelled Job leaves no Transcript behind.
_Avoid_: Task, run

**Language Mode**:
The user's statement, made at import time, of which language a Recording is spoken in: English, Indonesian, or Mixed (Indonesian with English words and phrases woven into the same sentences).
_Avoid_: Locale, language setting
