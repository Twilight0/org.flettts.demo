import asyncio
import os
import time
from typing import Any, Dict, List, Optional

import flet as ft
try:
    from src.tts_service import TtsService
except ImportError:
    from tts_service import TtsService

POPULAR_VOICES = [
    ("en-US-AriaNeural", "Aria (English US - Female)"),
    ("en-US-GuyNeural", "Guy (English US - Male)"),
    ("en-US-JennyNeural", "Jenny (English US - Female)"),
    ("en-GB-SoniaNeural", "Sonia (English UK - Female)"),
    ("en-GB-RyanNeural", "Ryan (English UK - Male)"),
    ("es-ES-ElviraNeural", "Elvira (Spanish Spain - Female)"),
    ("es-MX-DaliaNeural", "Dalia (Spanish Mexico - Female)"),
    ("fr-FR-DeniseNeural", "Denise (French - Female)"),
    ("fr-FR-HenriNeural", "Henri (French - Male)"),
    ("de-DE-KatjaNeural", "Katja (German - Female)"),
    ("de-DE-ConradNeural", "Conrad (German - Male)"),
    ("it-IT-ElsaNeural", "Elsa (Italian - Female)"),
    ("pt-BR-FranciscaNeural", "Francisca (Portuguese BR - Female)"),
    ("ja-JP-NanamiNeural", "Nanami (Japanese - Female)"),
    ("ja-JP-KeitaNeural", "Keita (Japanese - Male)"),
    ("ko-KR-SunHiNeural", "SunHi (Korean - Female)"),
    ("zh-CN-XiaoxiaoNeural", "Xiaoxiao (Chinese Mandarin - Female)"),
    ("zh-CN-YunxiNeural", "Yunxi (Chinese Mandarin - Male)"),
    ("ru-RU-SvetlanaNeural", "Svetlana (Russian - Female)"),
    ("ar-SA-ZariyahNeural", "Zariyah (Arabic Saudi - Female)"),
    ("hi-IN-SwaraNeural", "Swara (Hindi India - Female)"),
]

SAMPLE_TEXTS = {
    "Welcome": "Hello! Welcome to the Flet Text-to-Speech demo powered by Microsoft Edge Neural Voices. Experience crystal-clear, lifelike speech synthesis right inside your Flet application!",
    "Tech Story": "Artificial intelligence and neural text-to-speech models have transformed how humans interact with machines, enabling natural intonations and emotive vocal expressions in hundreds of languages.",
    "Quote": "The future belongs to those who believe in the beauty of their dreams.",
    "Multilingual": "Bonjour tout le monde! ¡Hola a todos! こんにちは世界！ Guten Tag und herzlich willkommen!",
}


def main(page: ft.Page):
    page.title = "Flet TTS Demo (Pure Python)"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.spacing = 0

    tts = TtsService(
        voice="en-US-AriaNeural",
        rate="+0%",
        volume="+0%",
        pitch="+0Hz",
    )

    all_voices: List[Dict[str, Any]] = []

    def show_snack(message: str, is_error: bool = False):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color=ft.Colors.WHITE),
            bgcolor=ft.Colors.RED_700 if is_error else ft.Colors.GREEN_700,
            open=True,
        )
        page.update()

    # Header Controls
    def toggle_theme(e):
        if page.theme_mode == ft.ThemeMode.DARK:
            page.theme_mode = ft.ThemeMode.LIGHT
            theme_btn.icon = ft.Icons.DARK_MODE
            theme_btn.tooltip = "Switch to Dark Mode"
        else:
            page.theme_mode = ft.ThemeMode.DARK
            theme_btn.icon = ft.Icons.LIGHT_MODE
            theme_btn.tooltip = "Switch to Light Mode"
        page.update()

    theme_btn = ft.IconButton(
        icon=ft.Icons.LIGHT_MODE,
        tooltip="Switch to Light Mode",
        on_click=toggle_theme,
    )

    # Status / Info Badge
    status_icon = ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=18, color=ft.Colors.GREEN_400)
    status_label = ft.Text("Ready", size=13, weight=ft.FontWeight.W_500)
    latency_label = ft.Text("", size=12, color=ft.Colors.GREY_400)

    status_row = ft.Container(
        content=ft.Row(
            [
                status_icon,
                status_label,
                ft.Container(expand=True),
                latency_label,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
        border_radius=8,
    )

    # Text Input & Word Count
    char_count_text = ft.Text("0 chars | 0 words", size=12, color=ft.Colors.GREY_400)

    def on_text_change(e):
        text = text_input.value or ""
        chars = len(text)
        words = len(text.split()) if text.strip() else 0
        char_count_text.value = f"{chars} chars | {words} words"
        page.update()

    def clear_text(e):
        text_input.value = ""
        on_text_change(None)
        page.update()

    text_input = ft.TextField(
        label="Text to speak",
        hint_text="Type or paste text here...",
        value=SAMPLE_TEXTS["Welcome"],
        multiline=True,
        min_lines=4,
        max_lines=7,
        border_radius=10,
        expand=True,
        on_change=on_text_change,
    )

    def apply_preset(preset_name: str):
        def _handler(e):
            text_input.value = SAMPLE_TEXTS[preset_name]
            on_text_change(None)
            page.update()

        return _handler

    preset_chips = [
        ft.Chip(label=ft.Text("Welcome"), on_click=apply_preset("Welcome")),
        ft.Chip(label=ft.Text("Tech Story"), on_click=apply_preset("Tech Story")),
        ft.Chip(label=ft.Text("Quote"), on_click=apply_preset("Quote")),
        ft.Chip(label=ft.Text("Multilingual"), on_click=apply_preset("Multilingual")),
    ]

    preset_buttons = ft.Row(
        [
            ft.Text("Presets:", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
            *preset_chips,
            ft.Container(expand=True),
            ft.IconButton(
                icon=ft.Icons.CLEAR_ALL,
                tooltip="Clear Text",
                icon_size=20,
                on_click=clear_text,
            ),
        ],
        scroll=ft.ScrollMode.ADAPTIVE,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Voice Selection & Filters
    language_dropdown = ft.Dropdown(
        label="Language Filter",
        value="All",
        options=[
            ft.DropdownOption(key="All", text="All Languages"),
            ft.DropdownOption(key="en", text="English"),
            ft.DropdownOption(key="es", text="Spanish"),
            ft.DropdownOption(key="fr", text="French"),
            ft.DropdownOption(key="de", text="German"),
            ft.DropdownOption(key="it", text="Italian"),
            ft.DropdownOption(key="pt", text="Portuguese"),
            ft.DropdownOption(key="ja", text="Japanese"),
            ft.DropdownOption(key="ko", text="Korean"),
            ft.DropdownOption(key="zh", text="Chinese"),
            ft.DropdownOption(key="ru", text="Russian"),
            ft.DropdownOption(key="ar", text="Arabic"),
            ft.DropdownOption(key="hi", text="Hindi"),
        ],
        dense=True,
        expand=1,
    )

    gender_dropdown = ft.Dropdown(
        label="Gender",
        value="All",
        options=[
            ft.DropdownOption(key="All", text="All Genders"),
            ft.DropdownOption(key="Female", text="Female"),
            ft.DropdownOption(key="Male", text="Male"),
        ],
        dense=True,
        expand=1,
    )

    voice_search_field = ft.TextField(
        label="Search Voice",
        hint_text="e.g. Aria, Guy, Sonia...",
        prefix_icon=ft.Icons.SEARCH,
        dense=True,
        expand=2,
    )

    voice_dropdown = ft.Dropdown(
        label="Select Voice",
        value="en-US-AriaNeural",
        options=[ft.DropdownOption(key=v[0], text=v[1]) for v in POPULAR_VOICES],
        dense=True,
        expand=True,
    )

    voice_count_label = ft.Text(f"{len(POPULAR_VOICES)} popular voices", size=12, color=ft.Colors.GREY_400)

    def populate_voice_options(voices_list: List[Dict[str, Any]]):
        lang_filter = language_dropdown.value
        gender_filter = gender_dropdown.value
        search_query = (voice_search_field.value or "").strip().lower()

        filtered = []
        for v in voices_list:
            short_name = v.get("ShortName", "")
            friendly_name = v.get("FriendlyName", short_name)
            locale = v.get("Locale", "")
            gender = v.get("Gender", "")

            if lang_filter != "All" and not locale.lower().startswith(lang_filter.lower()):
                continue
            if gender_filter != "All" and gender.lower() != gender_filter.lower():
                continue
            if search_query and search_query not in short_name.lower() and search_query not in friendly_name.lower():
                continue

            display_name = f"{friendly_name} ({locale} - {gender})"
            filtered.append(ft.DropdownOption(key=short_name, text=display_name))

        if not filtered:
            voice_dropdown.options = [ft.DropdownOption(key="none", text="No matching voices found")]
            voice_dropdown.value = "none"
        else:
            voice_dropdown.options = filtered
            current_keys = [opt.key for opt in filtered]
            if voice_dropdown.value not in current_keys:
                voice_dropdown.value = current_keys[0]

        voice_count_label.value = f"{len(filtered)} voices available"
        page.update()

    def filter_voices_event(e):
        if all_voices:
            populate_voice_options(all_voices)
        else:
            lang_filter = language_dropdown.value
            search_query = (voice_search_field.value or "").strip().lower()
            filtered = []
            for k, name in POPULAR_VOICES:
                if search_query and search_query not in k.lower() and search_query not in name.lower():
                    continue
                filtered.append(ft.DropdownOption(key=k, text=name))
            voice_dropdown.options = filtered or [ft.DropdownOption(key="none", text="No voices found")]
            if filtered and voice_dropdown.value not in [opt.key for opt in filtered]:
                voice_dropdown.value = filtered[0].key
            voice_count_label.value = f"{len(filtered)} voices available"
            page.update()

    language_dropdown.on_select = filter_voices_event
    gender_dropdown.on_select = filter_voices_event
    voice_search_field.on_change = filter_voices_event

    def on_voice_select(e):
        if voice_dropdown.value and voice_dropdown.value != "none":
            tts.voice = voice_dropdown.value

    voice_dropdown.on_select = on_voice_select

    # Sliders: Rate, Pitch, Volume
    rate_val_text = ft.Text("+0%", size=12, weight=ft.FontWeight.BOLD)
    pitch_val_text = ft.Text("+0Hz", size=12, weight=ft.FontWeight.BOLD)
    vol_val_text = ft.Text("+0%", size=12, weight=ft.FontWeight.BOLD)

    def on_rate_change(e):
        val = int(e.control.value)
        rate_str = f"{val:+d}%"
        rate_val_text.value = rate_str
        tts.rate = rate_str
        page.update()

    def on_pitch_change(e):
        val = int(e.control.value)
        pitch_str = f"{val:+d}Hz"
        pitch_val_text.value = pitch_str
        tts.pitch = pitch_str
        page.update()

    def on_volume_change(e):
        val = int(e.control.value)
        vol_str = f"{val:+d}%"
        vol_val_text.value = vol_str
        tts.volume = vol_str
        page.update()

    rate_slider = ft.Slider(
        min=-50,
        max=100,
        divisions=30,
        value=0,
        expand=True,
        on_change=on_rate_change,
    )
    pitch_slider = ft.Slider(
        min=-50,
        max=50,
        divisions=20,
        value=0,
        expand=True,
        on_change=on_pitch_change,
    )
    volume_slider = ft.Slider(
        min=-50,
        max=50,
        divisions=20,
        value=0,
        expand=True,
        on_change=on_volume_change,
    )

    def reset_audio_params(e):
        rate_slider.value = 0
        pitch_slider.value = 0
        volume_slider.value = 0
        rate_val_text.value = "+0%"
        pitch_val_text.value = "+0Hz"
        vol_val_text.value = "+0%"
        tts.rate = "+0%"
        tts.pitch = "+0Hz"
        tts.volume = "+0%"
        page.update()

    # Playback Action Handlers
    speak_progress = ft.ProgressRing(width=16, height=16, stroke_width=2, visible=False)
    speak_btn = ft.FilledButton(
        content=ft.Row(
            [speak_progress, ft.Icon(ft.Icons.RECORD_VOICE_OVER), ft.Text("Speak Text", weight=ft.FontWeight.BOLD)],
            alignment=ft.MainAxisAlignment.CENTER,
            tight=True,
        ),
        expand=True,
    )
    stop_btn = ft.OutlinedButton(
        icon=ft.Icons.STOP,
        content="Stop",
        disabled=True,
    )
    save_btn = ft.IconButton(
        icon=ft.Icons.DOWNLOAD,
        tooltip="Export Last Generated MP3",
        disabled=True,
    )

    async def on_speak_clicked(e):
        text = (text_input.value or "").strip()
        if not text:
            show_snack("Please enter some text to speak!", is_error=True)
            return

        if voice_dropdown.value and voice_dropdown.value != "none":
            tts.voice = voice_dropdown.value

        speak_progress.visible = True
        speak_btn.disabled = True
        stop_btn.disabled = False
        status_icon.name = ft.Icons.GRAPHIC_EQ
        status_icon.color = ft.Colors.BLUE_400
        status_label.value = f"Speaking ({tts.voice})..."
        latency_label.value = ""
        page.update()

        t_start = time.time()
        is_web = page.web or sys.platform == "emscripten"
        try:
            audio_data = await tts.speak(text, play_immediately=True)
            duration_s = time.time() - t_start

            if audio_data:
                latency_label.value = f"Finished ({duration_s:.2f}s, {len(audio_data):,} B)"
                status_icon.name = ft.Icons.CHECK_CIRCLE_OUTLINE
                status_icon.color = ft.Colors.GREEN_400
                status_label.value = "Playing audio..." if is_web else "Speech completed"
                save_btn.disabled = False
            else:
                status_icon.name = ft.Icons.CHECK_CIRCLE_OUTLINE
                status_icon.color = ft.Colors.GREEN_400
                status_label.value = "Ready"

        except Exception as ex:
            status_icon.name = ft.Icons.ERROR_OUTLINE
            status_icon.color = ft.Colors.RED_400
            status_label.value = f"Error: {str(ex)}"
            show_snack(f"Speech failed: {str(ex)}", is_error=True)
            is_web = False  # disable stop on error
        finally:
            speak_progress.visible = False
            speak_btn.disabled = False
            # On web, audio plays asynchronously in the main thread after
            # speak() returns, so keep the stop button enabled.
            stop_btn.disabled = not is_web
            page.update()

    async def on_stop_clicked(e):
        await tts.stop()
        status_icon.name = ft.Icons.STOP_CIRCLE
        status_icon.color = ft.Colors.AMBER_400
        status_label.value = "Stopped"
        stop_btn.disabled = True
        speak_progress.visible = False
        speak_btn.disabled = False
        page.update()

    async def on_save_clicked(e):
        data = await tts.get_audio_data()
        if data:
            save_path = os.path.expanduser(f"~/flet_tts_output_{int(time.time())}.mp3")
            try:
                with open(save_path, "wb") as f:
                    f.write(data)
                show_snack(f"Saved audio to: {save_path}", is_error=False)
            except Exception as ex:
                show_snack(f"Failed to save file: {ex}", is_error=True)
        else:
            show_snack("Please speak text first to generate audio.", is_error=True)

    speak_btn.on_click = on_speak_clicked
    stop_btn.on_click = on_stop_clicked
    save_btn.on_click = on_save_clicked

    # App UI Layout Structure
    app_bar = ft.AppBar(
        leading=ft.Icon(ft.Icons.RECORD_VOICE_OVER, color=ft.Colors.PRIMARY),
        title=ft.Text("Flet TTS (Pure Python)", weight=ft.FontWeight.BOLD),
        center_title=False,
        bgcolor=ft.Colors.SURFACE_CONTAINER,
        actions=[
            theme_btn,
        ],
    )

    text_card = ft.Card(
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.EDIT_NOTE, color=ft.Colors.PRIMARY, size=20),
                            ft.Text("Text Input", size=16, weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            char_count_text,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    text_input,
                    preset_buttons,
                ],
                spacing=10,
            ),
            padding=16,
        ),
        elevation=2,
    )

    voice_card = ft.Card(
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.RECORD_VOICE_OVER, color=ft.Colors.PRIMARY, size=20),
                            ft.Text("Voice Selection", size=16, weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            voice_count_label,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.ResponsiveRow(
                        [
                            ft.Container(language_dropdown, col={"xs": 12, "sm": 6, "md": 4}),
                            ft.Container(gender_dropdown, col={"xs": 12, "sm": 6, "md": 4}),
                            ft.Container(voice_search_field, col={"xs": 12, "sm": 12, "md": 4}),
                        ],
                    ),
                    voice_dropdown,
                ],
                spacing=12,
            ),
            padding=16,
        ),
        elevation=2,
    )

    params_card = ft.Card(
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.TUNE, color=ft.Colors.PRIMARY, size=20),
                            ft.Text("Voice Parameters", size=16, weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            ft.TextButton(content="Reset Defaults", icon=ft.Icons.RESTART_ALT, on_click=reset_audio_params),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.ResponsiveRow(
                        [
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Row(
                                            [ft.Icon(ft.Icons.SPEED, size=16), ft.Text("Rate / Speed:"), rate_val_text]
                                        ),
                                        rate_slider,
                                    ],
                                    spacing=2,
                                ),
                                col={"xs": 12, "sm": 4},
                            ),
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Row(
                                            [
                                                ft.Icon(ft.Icons.GRAPHIC_EQ, size=16),
                                                ft.Text("Pitch:"),
                                                pitch_val_text,
                                            ]
                                        ),
                                        pitch_slider,
                                    ],
                                    spacing=2,
                                ),
                                col={"xs": 12, "sm": 4},
                            ),
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Row(
                                            [
                                                ft.Icon(ft.Icons.VOLUME_UP, size=16),
                                                ft.Text("Volume:"),
                                                vol_val_text,
                                            ]
                                        ),
                                        volume_slider,
                                    ],
                                    spacing=2,
                                ),
                                col={"xs": 12, "sm": 4},
                            ),
                        ],
                    ),
                ],
                spacing=10,
            ),
            padding=16,
        ),
        elevation=2,
    )

    player_card = ft.Card(
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.VOLUME_UP, color=ft.Colors.PRIMARY, size=20),
                            ft.Text("Speech & Audio Controls", size=16, weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            save_btn,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        [
                            speak_btn,
                            stop_btn,
                        ],
                        spacing=10,
                    ),
                    status_row,
                ],
                spacing=14,
            ),
            padding=16,
        ),
        elevation=2,
    )

    content_view = ft.Container(
        content=ft.Column(
            [
                text_card,
                voice_card,
                params_card,
                player_card,
                ft.Container(height=20),
            ],
            spacing=16,
            scroll=ft.ScrollMode.ADAPTIVE,
        ),
        padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        expand=True,
    )

    page.appbar = app_bar
    page.add(content_view)

    # Initial text counter update
    on_text_change(None)

    # Background voice list loading
    async def load_all_voices_task():
        nonlocal all_voices
        try:
            voices = await tts.get_voices()
            if voices:
                all_voices = voices
                populate_voice_options(all_voices)
        except Exception as e:
            print(f"Note: Background full voice fetch returned: {e}")

    page.run_task(load_all_voices_task)


if __name__ == "__main__":
    ft.run(main)
