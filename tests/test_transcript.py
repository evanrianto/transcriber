from datetime import datetime
from pathlib import Path

from transcriber.transcript import Segment, render_transcript, transcript_path_for


def test_renders_one_line_per_segment_with_start_time() -> None:
    segments = [
        Segment(start=0.0, end=4.2, text="Hello and welcome."),
        Segment(start=754.6, end=760.0, text=" Jadi basically kita harus submit report-nya besok."),
        Segment(start=3725.0, end=3730.0, text="Thanks."),
    ]

    assert render_transcript(segments) == (
        "[00:00:00] Hello and welcome.\n"
        "[00:12:34] Jadi basically kita harus submit report-nya besok.\n"
        "[01:02:05] Thanks.\n"
    )


def test_transcript_file_sits_next_to_the_recording_with_a_timestamped_name() -> None:
    recording = Path("D:/Videos/team meeting.final.mp4")

    path = transcript_path_for(recording, datetime(2026, 10, 12, 14, 30, 5))

    assert path == Path("D:/Videos/team meeting.final.transcript.2026-10-12_14-30-05.txt")
