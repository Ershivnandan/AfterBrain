import json
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

from src.config import settings
from src.vision.landmark_detector import LandmarkDetector
from src.character.memory import CharacterMemory
from src.character.rig_builder import CharacterRigBuilder
from src.audio.lipsync import LipSyncEngine
from src.bridge.dispatcher import AEBridgeDispatcher
from src.worker.ollama_client import OllamaWorkerClient

console = Console()


def display_welcome():
    console.print(
        Panel.fit(
            "[bold cyan]🎬 Adobe After Effects AI Worker (AnMCP)[/bold cyan]\n"
            "[green]Powered by local Ollama (qwen3:8b)[/green]\n"
            "2D Character Rigging • Vision Landmark Perception • Lip-Sync • Motion Graphics",
            border_style="cyan"
        )
    )


def show_status(dispatcher: AEBridgeDispatcher, worker: OllamaWorkerClient, memory: CharacterMemory):
    b_status = dispatcher.get_status()
    w_status = worker.check_connection()
    chars = memory.list_characters()

    table = Table(title="System & Bridge Status")
    table.add_column("Component", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Details", style="green")

    # Ollama
    ollama_state = "Connected [green]✓[/green]" if w_status.get("ollama_connected") else "Disconnected [red]✗[/red]"
    table.add_row("Ollama Server", ollama_state, f"Host: {settings.ollama_host}")

    model_state = "Available [green]✓[/green]" if w_status.get("model_available") else "Missing [yellow]![/yellow]"
    table.add_row("Target Model", model_state, f"Model: {settings.ollama_model}")

    # AE Bridge
    ae_mode = b_status.get("active_mode", "unknown")
    ae_detail = "Live COM Connected [green]✓[/green]" if ae_mode == "live" else "Mock Simulator (Saving .jsx) [yellow]⚡[/yellow]"
    table.add_row("After Effects Bridge", ae_mode.upper(), ae_detail)

    # Characters
    table.add_row("Character Memory", f"{len(chars)} Registered", ", ".join([c['name'] for c in chars]) or "None")

    console.print(table)


def main():
    display_welcome()
    memory = CharacterMemory()
    detector = LandmarkDetector()
    dispatcher = AEBridgeDispatcher()
    worker = OllamaWorkerClient(memory=memory)

    show_status(dispatcher, worker, memory)

    console.print("\n[bold yellow]Commands:[/bold yellow]")
    console.print("  [cyan]register <image_path> <name>[/cyan] - Detect landmarks & rig character with puppet pins")
    console.print("  [cyan]animate <name> <prompt>[/cyan]     - Animate a registered character")
    console.print("  [cyan]lipsync <name> [audio_path][/cyan]  - Lip sync with audio or dialogue")
    console.print("  [cyan]generate <prompt>[/cyan]            - Generate motion graphics or typography")
    console.print("  [cyan]status[/cyan]                       - Refresh and print connection status")
    console.print("  [cyan]exit[/cyan]                         - Quit\n")

    while True:
        try:
            user_input = console.input("[bold green]AnMCP > [/bold green]").strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                console.print("[dim]Goodbye![/dim]")
                break

            if user_input.lower() == "status":
                show_status(dispatcher, worker, memory)
                continue

            if user_input.startswith("register "):
                parts = user_input.split(maxsplit=2)
                if len(parts) < 3:
                    console.print("[red]Usage: register <image_path> <name>[/red]")
                    continue
                img_path, char_name = parts[1], parts[2]
                console.print(f"[cyan]Scanning {img_path} with Vision Landmark Engine...[/cyan]")
                try:
                    landmarks = detector.detect(img_path, character_name=char_name)
                    rig_script = CharacterRigBuilder.build_puppet_rig_script(landmarks)
                    res = dispatcher.dispatch(rig_script, script_name_prefix=f"rig_{char_name}")
                    memory.register_character(
                        name=char_name,
                        image_path=img_path,
                        landmarks=landmarks.to_dict()["landmarks"],
                        rig_type="puppet_pins"
                    )
                    console.print(f"[green]✓ Character '{char_name}' registered successfully![/green]")
                    console.print(f"  Mouth: {landmarks.mouth.to_list()} | Hand R: {landmarks.hand_right.to_list()} | Hand L: {landmarks.hand_left.to_list()}")
                    console.print(f"  Script saved to: [underline]{res.get('saved_script_path')}[/underline]")
                except Exception as e:
                    console.print(f"[red]Failed to register character: {e}[/red]")

            elif user_input.startswith("animate "):
                parts = user_input.split(maxsplit=2)
                if len(parts) < 3:
                    console.print("[red]Usage: animate <character_name> <prompt>[/red]")
                    continue
                char_name, prompt = parts[1], parts[2]
                console.print(f"[cyan]Prompting Qwen to animate '{char_name}'...[/cyan]")
                res = worker.generate_extendscript(prompt, character_name=char_name)
                jsx = res.get("jsx_code", "")
                if jsx:
                    exec_res = dispatcher.dispatch(jsx, script_name_prefix=f"anim_{char_name}")
                    console.print(f"[green]✓ Animation script dispatched![/green] (Mode: {exec_res.get('mode')})")
                    console.print(f"  Saved JSX: {exec_res.get('saved_script_path')}")
                else:
                    console.print(f"[red]Failed to generate JSX: {res.get('error')}[/red]")

            elif user_input.startswith("lipsync "):
                parts = user_input.split(maxsplit=2)
                char_name = parts[1] if len(parts) > 1 else ""
                audio_or_text = parts[2] if len(parts) > 2 else ""
                if not char_name:
                    console.print("[red]Usage: lipsync <character_name> [audio_path or text][/red]")
                    continue

                if audio_or_text and Path(audio_or_text).exists():
                    jsx = LipSyncEngine.build_audio_driven_lipsync_script(char_name, audio_or_text)
                    console.print(f"[cyan]Generated Audio-Driven Amplitude Lip Sync for '{char_name}'[/cyan]")
                else:
                    dialogue = audio_or_text or "Hello there! Welcome to After Effects."
                    jsx = LipSyncEngine.build_text_dialogue_lipsync_script(char_name, dialogue)
                    console.print(f"[cyan]Generated Syllable Lip Sync for dialogue: \"{dialogue}\"[/cyan]")

                exec_res = dispatcher.dispatch(jsx, script_name_prefix=f"lipsync_{char_name}")
                console.print(f"[green]✓ Lip Sync script saved & dispatched![/green] ({exec_res.get('saved_script_path')})")

            elif user_input.startswith("generate "):
                prompt = user_input[9:].strip()
                console.print(f"[cyan]Generating motion graphics from: '{prompt}'...[/cyan]")
                res = worker.generate_extendscript(prompt)
                jsx = res.get("jsx_code", "")
                if jsx:
                    exec_res = dispatcher.dispatch(jsx, script_name_prefix="gen_anim")
                    console.print(f"[green]✓ Motion script generated & dispatched![/green] ({exec_res.get('saved_script_path')})")
                    if res.get("explanation"):
                        console.print(f"[italic]{res.get('explanation')}[/italic]")
                else:
                    console.print(f"[red]Error: {res.get('error')}[/red]")

            else:
                console.print("[yellow]Unknown command. Type 'generate <prompt>', 'register', 'animate', 'lipsync', or 'status'.[/yellow]")

        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    main()
