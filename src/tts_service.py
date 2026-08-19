import asyncio
import base64
import inspect
import os
import shutil
from typing import Any, Callable, Dict, List, Optional

import edge_tts


class TtsService:
    """
    Pure Python Text-to-Speech service using Microsoft Edge Neural Voices.

    Features:
    - Real-time streaming audio playback with sub-second latency.
    - Zero external Flutter extension dependencies.
    - Configurable voice, rate, pitch, volume.
    - Voice list discovery and filtering across 300+ voices.
    - MP3 file export and raw byte / base64 access.
    """

    def __init__(
        self,
        voice: str = "en-US-AriaNeural",
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
        on_complete: Optional[Callable[[Dict[str, Any]], Any]] = None,
        on_error: Optional[Callable[[str], Any]] = None,
    ):
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.pitch = pitch
        self.on_complete = on_complete
        self.on_error = on_error

        self._current_audio_data: Optional[bytes] = None
        self._current_audio_base64: Optional[str] = None
        self._is_speaking: bool = False
        self._active_player_proc: Optional[asyncio.subprocess.Process] = None

    async def _get_streaming_player(self) -> Optional[asyncio.subprocess.Process]:
        """Resolve available audio player (mpv, ffplay) and open a streaming stdin pipe."""
        player_bin = shutil.which("mpv") or shutil.which("ffplay")
        if not player_bin:
            return None

        if "mpv" in player_bin:
            return await asyncio.create_subprocess_exec(
                player_bin,
                "--no-video",
                "--really-quiet",
                "-",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
        elif "ffplay" in player_bin:
            return await asyncio.create_subprocess_exec(
                player_bin,
                "-nodisp",
                "-autoexit",
                "-loglevel",
                "quiet",
                "-i",
                "pipe:0",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
        return None

    async def speak(self, text: str, play_immediately: bool = True) -> Optional[bytes]:
        """
        Speak the given text using real-time streaming audio playback.
        Speech starts playing immediately as chunks stream from the network.
        """
        if not text or not text.strip():
            return None

        # Stop any ongoing playback first
        await self.stop()
        self._is_speaking = True

        player_proc = await self._get_streaming_player() if play_immediately else None
        self._active_player_proc = player_proc

        try:
            communicate = edge_tts.Communicate(
                text=text.strip(),
                voice=self.voice,
                rate=self.rate,
                volume=self.volume,
                pitch=self.pitch,
            )

            audio_chunks = []
            async for chunk in communicate.stream():
                if not self._is_speaking:
                    break

                if chunk["type"] == "audio":
                    data = chunk["data"]
                    audio_chunks.append(data)

                    # Pipe audio chunk immediately to player stdin
                    if player_proc and player_proc.stdin:
                        try:
                            player_proc.stdin.write(data)
                            await player_proc.stdin.drain()
                        except (BrokenPipeError, ConnectionResetError):
                            break

            # Close stdin so the player finishes playing the buffered stream
            if player_proc and player_proc.stdin:
                try:
                    player_proc.stdin.close()
                    await player_proc.stdin.wait_closed()
                except Exception:
                    pass

            if player_proc:
                try:
                    await player_proc.wait()
                except Exception:
                    pass

            self._current_audio_data = b"".join(audio_chunks)
            self._current_audio_base64 = (
                base64.b64encode(self._current_audio_data).decode("utf-8")
                if self._current_audio_data
                else None
            )

            if self._is_speaking and self.on_complete:
                data = {"bytes": len(self._current_audio_data)}
                if inspect.iscoroutinefunction(self.on_complete):
                    await self.on_complete(data)
                else:
                    self.on_complete(data)

            return self._current_audio_data

        except Exception as e:
            if self.on_error:
                if inspect.iscoroutinefunction(self.on_error):
                    await self.on_error(str(e))
                else:
                    self.on_error(str(e))
            raise e
        finally:
            self._is_speaking = False
            self._active_player_proc = None
            if player_proc:
                try:
                    if player_proc.returncode is None:
                        player_proc.kill()
                except Exception:
                    pass

    async def stop(self) -> None:
        """Instantly stop speech and terminate active audio player process."""
        self._is_speaking = False
        if self._active_player_proc:
            try:
                self._active_player_proc.kill()
            except Exception:
                pass
            self._active_player_proc = None

    async def set_voice(self, voice: str) -> None:
        """Set active TTS voice."""
        self.voice = voice

    async def set_rate(self, rate: str) -> None:
        """Set speech rate (e.g. '+0%', '-50%', '+100%')."""
        self.rate = rate

    async def set_volume(self, volume: str) -> None:
        """Set volume (e.g. '+0%', '-50%', '+100%')."""
        self.volume = volume

    async def set_pitch(self, pitch: str) -> None:
        """Set pitch (e.g. '+0Hz', '-50Hz', '+100Hz')."""
        self.pitch = pitch

    async def get_voices(self, locale_prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch available voices, optionally filtered by locale prefix (e.g. 'en', 'es', 'zh')."""
        voices = await edge_tts.list_voices()
        if locale_prefix:
            prefix = locale_prefix.lower()
            return [v for v in voices if v.get("Locale", "").lower().startswith(prefix)]
        return voices

    async def save_to_file(self, text: str, output_path: str) -> str:
        """Synthesize text and save directly to an MP3 file."""
        data = await self.speak(text, play_immediately=False)
        if data:
            with open(output_path, "wb") as f:
                f.write(data)
        return output_path

    async def get_audio_base64(self) -> Optional[str]:
        """Get base64-encoded audio data of the last generated speech."""
        return self._current_audio_base64

    async def get_audio_data(self) -> Optional[bytes]:
        """Get raw audio bytes of the last generated speech."""
        return self._current_audio_data

    @property
    def is_speaking(self) -> bool:
        """Check if speech is currently active."""
        return self._is_speaking
