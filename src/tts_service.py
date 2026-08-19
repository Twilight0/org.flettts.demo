import asyncio
import base64
import inspect
import json
import os
import shutil
import sys
from typing import Any, Callable, Dict, List, Optional
import urllib.request

IS_WEB = sys.platform == "emscripten" or "pyodide" in sys.modules
PROXY_URL = "https://edge-tts-proxy.twilight0.workers.dev"
PROXY_WSS = "wss://edge-tts-proxy.twilight0.workers.dev"


class TtsService:
    """
    Text-to-Speech service with cross-platform support:
    - Desktop / Native: Fast local streaming to audio pipeline via edge-tts.
    - Web / WASM (GitHub Pages): Browser Web Audio & WebSocket via Cloudflare proxy.
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
        """Resolve available audio player on desktop."""
        if IS_WEB:
            return None

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
        Speak text with instant playback across Desktop and Web / Pyodide.
        """
        if not text or not text.strip():
            return None

        await self.stop()
        self._is_speaking = True

        if IS_WEB:
            return await self._speak_web(text.strip(), play_immediately)
        else:
            return await self._speak_native(text.strip(), play_immediately)

    async def _speak_native(self, text: str, play_immediately: bool) -> Optional[bytes]:
        """Native desktop streaming via edge-tts."""
        import edge_tts

        player_proc = await self._get_streaming_player() if play_immediately else None
        self._active_player_proc = player_proc

        try:
            communicate = edge_tts.Communicate(
                text=text,
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

                    if player_proc and player_proc.stdin:
                        try:
                            player_proc.stdin.write(data)
                            await player_proc.stdin.drain()
                        except (BrokenPipeError, ConnectionResetError):
                            break

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

    async def _speak_web(self, text: str, play_immediately: bool) -> Optional[bytes]:
        """Web/Pyodide synthesis using browser WebSockets and Cloudflare Proxy."""
        import js
        from pyodide.ffi import create_proxy

        loop = asyncio.get_event_loop()
        future = loop.create_future()

        audio_chunks = []

        def on_open(event):
            ts = js.Date.new().toString()
            req_id = js.crypto.randomUUID().replaceAll("-", "")

            # 1. Send speech.config
            config_msg = (
                f"X-Timestamp:{ts}\r\n"
                "Content-Type:application/json; charset=utf-8\r\n"
                "Path:speech.config\r\n\r\n"
                '{"context":{"synthesis":{"audio":{"metadataoptions":{"sentenceBoundaryEnabled":"false","wordBoundaryEnabled":"false"},"outputFormat":"audio-24khz-48kbitrate-mono-mp3"}}}}\r\n'
            )
            ws.send(config_msg)

            # 2. Send SSML
            escaped_text = (
                text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;")
            )
            ssml = (
                f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>"
                f"<voice name='{self.voice}'>"
                f"<prosody pitch='{self.pitch}' rate='{self.rate}' volume='{self.volume}'>"
                f"{escaped_text}"
                f"</prosody></voice></speak>"
            )
            ssml_msg = (
                f"X-RequestId:{req_id}\r\n"
                "Content-Type:application/ssml+xml\r\n"
                f"X-Timestamp:{ts}Z\r\n"
                f"Path:ssml\r\n\r\n{ssml}"
            )
            ws.send(ssml_msg)

        async def process_binary_data(array_buffer):
            uint8 = js.Uint8Array.new(array_buffer)
            if uint8.length < 2:
                return
            view = js.DataView.new(array_buffer)
            header_len = view.getUint16(0, False)
            if uint8.length > 2 + header_len:
                audio_slice = uint8.slice(2 + header_len)
                audio_bytes = bytes(audio_slice.to_py())
                audio_chunks.append(audio_bytes)

        def on_message(event):
            if isinstance(event.data, str):
                if "Path:turn.end" in event.data:
                    ws.close()
                    if not future.done():
                        future.set_result(b"".join(audio_chunks))
            else:
                asyncio.create_task(process_binary_data(event.data))

        def on_error(event):
            ws.close()
            if not future.done():
                future.set_exception(Exception("WebSocket error during web speech synthesis"))

        def on_close(event):
            if not future.done():
                future.set_result(b"".join(audio_chunks))

        ws = js.WebSocket.new(PROXY_WSS)
        ws.binaryType = "arraybuffer"

        p_open = create_proxy(on_open)
        p_msg = create_proxy(on_message)
        p_err = create_proxy(on_error)
        p_close = create_proxy(on_close)

        ws.addEventListener("open", p_open)
        ws.addEventListener("message", p_msg)
        ws.addEventListener("error", p_err)
        ws.addEventListener("close", p_close)

        try:
            audio_data = await asyncio.wait_for(future, timeout=20.0)
            self._current_audio_data = audio_data
            self._current_audio_base64 = (
                base64.b64encode(audio_data).decode("utf-8") if audio_data else None
            )

            if play_immediately and audio_data:
                b64_audio = self._current_audio_base64
                js.eval(
                    "(function() {"
                    "  var g = typeof globalThis !== 'undefined' ? globalThis : (typeof self !== 'undefined' ? self : {});"
                    "  var b64 = '" + b64_audio + "';"
                    "  if (typeof window !== 'undefined' && typeof window.Audio !== 'undefined') {"
                    "    if (window.__flet_tts_audio) window.__flet_tts_audio.pause();"
                    "    window.__flet_tts_audio = new Audio('data:audio/mp3;base64,' + b64);"
                    "    window.__flet_tts_audio.play();"
                    "  } else {"
                    "    try {"
                    "      var AudioCtx = g.AudioContext || g.webkitAudioContext;"
                    "      if (AudioCtx) {"
                    "        if (g.__flet_audio_ctx) try { g.__flet_audio_ctx.close(); } catch(e){}"
                    "        var ctx = new AudioCtx();"
                    "        g.__flet_audio_ctx = ctx;"
                    "        var binaryStr = atob(b64);"
                    "        var bytes = new Uint8Array(binaryStr.length);"
                    "        for (var i = 0; i < binaryStr.length; i++) {"
                    "          bytes[i] = binaryStr.charCodeAt(i);"
                    "        }"
                    "        ctx.decodeAudioData(bytes.buffer, function(buffer) {"
                    "          var src = ctx.createBufferSource();"
                    "          src.buffer = buffer;"
                    "          src.connect(ctx.destination);"
                    "          src.start(0);"
                    "          g.__flet_audio_source = src;"
                    "        });"
                    "      }"
                    "    } catch(err) { console.error('AudioContext error:', err); }"
                    "  }"
                    "})();"
                )

            if self.on_complete and audio_data:
                data = {"bytes": len(audio_data)}
                if inspect.iscoroutinefunction(self.on_complete):
                    await self.on_complete(data)
                else:
                    self.on_complete(data)

            return audio_data
        except Exception as ex:
            if self.on_error:
                if inspect.iscoroutinefunction(self.on_error):
                    await self.on_error(str(ex))
                else:
                    self.on_error(str(ex))
            raise ex
        finally:
            self._is_speaking = False
            p_open.destroy()
            p_msg.destroy()
            p_err.destroy()
            p_close.destroy()

    async def stop(self) -> None:
        """Instantly stop speech and terminate playback across platforms."""
        self._is_speaking = False
        if IS_WEB:
            try:
                import js
                js.eval(
                    "(function() {"
                    "  var g = typeof globalThis !== 'undefined' ? globalThis : (typeof self !== 'undefined' ? self : {});"
                    "  if (typeof window !== 'undefined' && window.__flet_tts_audio) {"
                    "    window.__flet_tts_audio.pause();"
                    "    window.__flet_tts_audio.currentTime = 0;"
                    "  }"
                    "  if (g.__flet_audio_ctx) {"
                    "    try { g.__flet_audio_ctx.close(); } catch(e){}"
                    "    g.__flet_audio_ctx = null;"
                    "  }"
                    "})();"
                )
            except Exception:
                pass
        else:
            if self._active_player_proc:
                try:
                    self._active_player_proc.kill()
                except Exception:
                    pass
                self._active_player_proc = None

    async def set_voice(self, voice: str) -> None:
        self.voice = voice

    async def set_rate(self, rate: str) -> None:
        self.rate = rate

    async def set_volume(self, volume: str) -> None:
        self.volume = volume

    async def set_pitch(self, pitch: str) -> None:
        self.pitch = pitch

    async def get_voices(self, locale_prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch available voices (via Cloudflare Proxy on Web, or edge-tts on Desktop)."""
        if IS_WEB:
            try:
                req = urllib.request.Request(
                    f"{PROXY_URL}/voices",
                    headers={"User-Agent": "FletTTS-Web/1.0"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    voices = json.loads(resp.read().decode("utf-8"))
            except Exception:
                return []
        else:
            import edge_tts
            voices = await edge_tts.list_voices()

        if locale_prefix:
            prefix = locale_prefix.lower()
            return [v for v in voices if v.get("Locale", "").lower().startswith(prefix)]
        return voices

    async def save_to_file(self, text: str, output_path: str) -> str:
        data = await self.speak(text, play_immediately=False)
        if data:
            with open(output_path, "wb") as f:
                f.write(data)
        return output_path

    async def get_audio_base64(self) -> Optional[str]:
        return self._current_audio_base64

    async def get_audio_data(self) -> Optional[bytes]:
        return self._current_audio_data

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking
