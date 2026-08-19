import asyncio
import os
import tempfile
import pytest
from src.tts_service import TtsService


@pytest.mark.asyncio
async def test_tts_service_init():
    tts = TtsService()
    assert tts.voice == "en-US-AriaNeural"
    assert tts.rate == "+0%"
    assert tts.volume == "+0%"
    assert tts.pitch == "+0Hz"
    assert tts.is_speaking is False


@pytest.mark.asyncio
async def test_tts_service_setters():
    tts = TtsService()
    await tts.set_voice("en-US-GuyNeural")
    await tts.set_rate("+20%")
    await tts.set_volume("+10%")
    await tts.set_pitch("+5Hz")

    assert tts.voice == "en-US-GuyNeural"
    assert tts.rate == "+20%"
    assert tts.volume == "+10%"
    assert tts.pitch == "+5Hz"


@pytest.mark.asyncio
async def test_tts_service_get_voices():
    tts = TtsService()
    all_voices = await tts.get_voices()
    assert len(all_voices) > 100

    en_voices = await tts.get_voices("en-US")
    assert len(en_voices) > 5
    assert all(v["Locale"].lower().startswith("en-us") for v in en_voices)


@pytest.mark.asyncio
async def test_tts_service_synthesis():
    tts = TtsService(voice="en-US-AriaNeural")
    data = await tts.speak("Test speech synthesis in pure python", play_immediately=False)
    assert data is not None
    assert len(data) > 1000

    b64 = await tts.get_audio_base64()
    assert b64 is not None
    assert len(b64) > 1000

    raw = await tts.get_audio_data()
    assert raw == data


@pytest.mark.asyncio
async def test_tts_service_save_to_file():
    tts = TtsService(voice="en-US-GuyNeural")
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        saved_path = await tts.save_to_file("Testing audio file saving.", tmp_path)
        assert os.path.exists(saved_path)
        assert os.path.getsize(saved_path) > 1000
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@pytest.mark.asyncio
async def test_tts_service_events():
    completed = False
    event_data = None

    def on_done(data):
        nonlocal completed, event_data
        completed = True
        event_data = data

    tts = TtsService(voice="en-US-AriaNeural", on_complete=on_done)
    await tts.speak("Short event test", play_immediately=False)

    assert completed is True
    assert event_data is not None
    assert "bytes" in event_data
