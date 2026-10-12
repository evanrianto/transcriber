import pytest

from transcriber.media import MediaInfo, is_browser_playable


@pytest.mark.parametrize(
    "info",
    [
        MediaInfo(extension=".mp4", video_codec="h264", audio_codec="aac"),
        MediaInfo(extension=".mov", video_codec="h264", audio_codec="aac"),
        MediaInfo(extension=".m4v", video_codec="h264", audio_codec=None),
        MediaInfo(extension=".webm", video_codec="vp9", audio_codec="opus"),
        MediaInfo(extension=".mp3", video_codec=None, audio_codec="mp3"),
        MediaInfo(extension=".m4a", video_codec=None, audio_codec="aac"),
        MediaInfo(extension=".wav", video_codec=None, audio_codec="pcm_s16le"),
        MediaInfo(extension=".flac", video_codec=None, audio_codec="flac"),
        MediaInfo(extension=".ogg", video_codec=None, audio_codec="opus"),
    ],
    ids=lambda info: f"{info.extension}-{info.video_codec}-{info.audio_codec}",
)
def test_formats_the_browser_plays_are_used_as_they_are(info: MediaInfo) -> None:
    assert is_browser_playable(info)


@pytest.mark.parametrize(
    "info",
    [
        MediaInfo(extension=".mkv", video_codec="h264", audio_codec="aac"),
        MediaInfo(extension=".avi", video_codec="mpeg4", audio_codec="mp3"),
        MediaInfo(extension=".mov", video_codec="hevc", audio_codec="aac"),
        MediaInfo(extension=".mp4", video_codec="hevc", audio_codec="aac"),
        MediaInfo(extension=".mp4", video_codec="h264", audio_codec="ac3"),
        MediaInfo(extension=".wmv", video_codec="wmv2", audio_codec="wmav2"),
        MediaInfo(extension=".wma", video_codec=None, audio_codec="wmav2"),
    ],
    ids=lambda info: f"{info.extension}-{info.video_codec}-{info.audio_codec}",
)
def test_other_formats_need_a_preview(info: MediaInfo) -> None:
    assert not is_browser_playable(info)
