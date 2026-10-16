import json
import re
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

from src.config import settings
from src.vision.landmark_detector import LandmarkDetector
from src.character.memory import CharacterMemory
from src.character.rig_builder import CharacterRigBuilder
from src.audio.lipsync import LipSyncEngine
from src.bridge.dispatcher import AEBridgeDispatcher
from src.worker.ollama_client import OllamaWorkerClient

import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console()


def display_welcome():
    console.print(
        Panel.fit(
            "[bold cyan]AfterBrain: AI Worker & MCP Server for Adobe After Effects[/bold cyan]\n"
            "[green]Powered by local Ollama (qwen3:8b) & Windows Automation[/green]\n"
            "Interactive Character Onboarding • Vision Landmark Perception • Lip-Sync • Motion Graphics",
            border_style="cyan"
        )
    )


def show_status(dispatcher: AEBridgeDispatcher, worker: OllamaWorkerClient, memory: CharacterMemory):
    b_status = dispatcher.get_status()
    w_status = worker.check_connection()
    chars = memory.list_characters()

    table = Table(title="AfterBrain System & Bridge Status")
    table.add_column("Component", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Details", style="green")

    # Ollama
    ollama_state = "Connected [green][OK][/green]" if w_status.get("ollama_connected") else "Disconnected [red][X][/red]"
    table.add_row("Ollama Server", ollama_state, f"Host: {settings.ollama_host}")

    model_state = "Available [green][OK][/green]" if w_status.get("model_available") else "Missing [yellow][!][/yellow]"
    table.add_row("Target Model", model_state, f"Model: {settings.ollama_model}")

    # AE Bridge
    ae_mode = b_status.get("active_mode", "unknown")
    ae_detail = "Live Session Connected [green][OK][/green]" if ae_mode == "live" else "Mock Simulator (Saving .jsx) [yellow][Offline][/yellow]"
    table.add_row("After Effects Bridge", ae_mode.upper(), ae_detail)

    # Characters in Memory
    char_summary = []
    for c in chars:
        char_desc = f"{c['name']} ({c.get('role', 'Character')})"
        char_summary.append(char_desc)

    table.add_row(
        "Character Memory",
        f"{len(chars)} Registered",
        ", ".join(char_summary) if char_summary else "No characters registered yet (type 'register')"
    )

    console.print(table)


def clean_file_path(raw_path: str) -> Path:
    """Cleans up drag-and-dropped file paths by stripping quotes and whitespace."""
    cleaned = raw_path.strip().strip("'\"")
    # Handle Windows explorer file URI if pasted
    if cleaned.startswith("file:///"):
        cleaned = cleaned[8:]
    return Path(cleaned)


def interactive_register_wizard(
    detector: LandmarkDetector,
    dispatcher: AEBridgeDispatcher,
    memory: CharacterMemory,
    initial_path: str = "",
    initial_name: str = ""
):
    """
    Step-by-step interactive onboarding wizard for new characters.
    Takes image, asks for character personality, extracts vision landmarks,
    and commits to Character Memory.
    """
    console.print(Panel("[bold cyan]🧙 Character Onboarding Wizard[/bold cyan]\n"
                        "Register any 2D cartoon or character image into AfterBrain memory.",
                        border_style="cyan"))

    # 1. Image Path
    img_path = clean_file_path(initial_path) if initial_path else None
    while not img_path or not img_path.exists():
        if img_path:
            console.print(f"[red]File not found: {img_path}[/red]")
        raw_input = console.input("[bold yellow]📁 Character Image Path[/bold yellow] (or drag & drop image here): ").strip()
        if not raw_input:
            console.print("[yellow]Registration cancelled.[/yellow]")
            return
        img_path = clean_file_path(raw_input)

    # 2. Character Name
    default_name = initial_name or re.sub(r"[^a-zA-Z0-9_]", "", img_path.stem.title())
    name = console.input(f"[bold yellow]🏷️ Character Name[/bold yellow] [default: [cyan]{default_name}[/cyan]]: ").strip() or default_name

    # 3. Role
    role = console.input("[bold yellow]🎭 Character Role[/bold yellow] (e.g. Protagonist, Sidekick, Villain) [default: [cyan]Protagonist[/cyan]]: ").strip() or "Protagonist"

    # 4. Visual Description
    desc = console.input("[bold yellow]🎨 Visual Description[/bold yellow] (outfit, colors, visual vibe): ").strip()

    # 5. Personality / Acting Style
    personality = console.input("[bold yellow]⚡ Personality & Acting Style[/bold yellow] (e.g. Goofy, hyperactive, serious, heroic): ").strip()

    # 6. Vision Landmark Detection
    console.print(f"\n[cyan]🔍 Running Vision Landmark Perception on [bold]{img_path.name}[/bold]...[/cyan]")
    try:
        landmarks = detector.detect(str(img_path), character_name=name)

        # Show landmark results table
        lm_table = Table(title=f"Detected Landmarks for '{name}'")
        lm_table.add_column("Anatomical Feature", style="cyan")
        lm_table.add_column("Normalized (0-1)", style="magenta")
        lm_table.add_column("AE 1080p Pixels", style="green")

        comp_coords = landmarks.get_comp_coordinates(1920, 1080)
        lm_dict = landmarks.to_dict()["landmarks"]

        for feature in ["mouth", "eye_left", "eye_right", "head_top", "hand_left", "hand_right", "neck", "hip"]:
            norm_pt = lm_dict.get(feature, [])
            px_pt = comp_coords.get(feature, [])
            lm_table.add_row(feature.replace("_", " ").title(), str(norm_pt), f"[{px_pt[0]}px, {px_pt[1]}px]")

        console.print(lm_table)

        # 7. Rig Building & Dispatch
        console.print("[cyan]⚙️ Generating After Effects Puppet Tool Rig...[/cyan]")
        rig_script = CharacterRigBuilder.build_puppet_rig_script(landmarks)
        exec_res = dispatcher.dispatch(rig_script, script_name_prefix=f"rig_{name}")

        # 8. Commit to Character Memory
        char_data = memory.register_character(
            name=name,
            image_path=str(img_path),
            landmarks=landmarks.to_dict()["landmarks"],
            rig_type="puppet_pins",
            description=desc,
            personality=personality,
            role=role,
            layer_name=name
        )

        console.print(Panel(
            f"[bold green]✓ Character '{name}' successfully registered in AfterBrain Memory![/bold green]\n\n"
            f"• [bold]Role[/bold]: {role}\n"
            f"• [bold]Description[/bold]: {desc or 'N/A'}\n"
            f"• [bold]Personality[/bold]: {personality or 'N/A'}\n"
            f"• [bold]Execution Mode[/bold]: {exec_res.get('mode')}\n"
            f"• [bold]Saved Script[/bold]: [underline]{exec_res.get('saved_script_path')}[/underline]\n\n"
            f"[bold yellow]Try animating now:[/bold yellow]\n"
            f"  [cyan]animate {name} \"wave his right hand enthusiastically and smile\"[/cyan]\n"
            f"  [cyan]lipsync {name} \"Hello everyone! Welcome to my world!\"[/cyan]",
            title="Registration Complete",
            border_style="green"
        ))

    except Exception as e:
        console.print(f"[bold red]Registration error:[/bold red] {e}")


def main():
    display_welcome()
    memory = CharacterMemory()
    detector = LandmarkDetector()
    dispatcher = AEBridgeDispatcher()
    worker = OllamaWorkerClient(memory=memory)

    show_status(dispatcher, worker, memory)

    console.print("\n[bold yellow]Available Commands:[/bold yellow]")
    console.print("  [cyan]register[/cyan]                     - Launch interactive Character Onboarding Wizard")
    console.print("  [cyan]register <image_path> [name][/cyan] - Quick register with image")
    console.print("  [cyan]list[/cyan]                         - View all registered characters & acting traits")
    console.print("  [cyan]animate <name> <prompt>[/cyan]     - Animate a character with natural language")
    console.print("  [cyan]lipsync <name> [audio/text][/cyan]  - Lip-sync character to speech audio or dialogue")
    console.print("  [cyan]generate <prompt>[/cyan]            - Generate motion graphics / kinetic typography")
    console.print("  [cyan]status[/cyan]                       - Check connection status")
    console.print("  [cyan]exit[/cyan]                         - Quit\n")

    while True:
        try:
            user_input = console.input("[bold green]AfterBrain > [/bold green]").strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                console.print("[dim]Goodbye![/dim]")
                break

            if user_input.lower() == "status":
                show_status(dispatcher, worker, memory)
                continue

            if user_input.lower() == "list":
                chars = memory.list_characters()
                if not chars:
                    console.print("[yellow]No characters registered yet. Type 'register' to add one![/yellow]")
                    continue

                table = Table(title="Registered Characters in AfterBrain")
                table.add_column("Name", style="cyan", no_wrap=True)
                table.add_column("Role", style="magenta")
                table.add_column("Personality / Traits", style="green")
                table.add_column("Image File", style="dim")

                for c in chars:
                    table.add_row(
                        c["name"],
                        c.get("role", "Character"),
                        c.get("personality") or c.get("description") or "Default",
                        Path(c["image_path"]).name
                    )
                console.print(table)
                continue

            if user_input.lower() == "register":
                # Full interactive wizard
                interactive_register_wizard(detector, dispatcher, memory)
                continue

            if user_input.startswith("register "):
                raw_args = user_input[9:].strip()
                # Split respecting quotes
                parts = re.findall(r'(?:[^\s"\']|"[^"]*"|\'[^\']*\')+', raw_args)
                init_path = parts[0].strip("\"'") if len(parts) > 0 else ""
                init_name = parts[1].strip("\"'") if len(parts) > 1 else ""
                interactive_register_wizard(detector, dispatcher, memory, initial_path=init_path, initial_name=init_name)
                continue

            if user_input.startswith("animate "):
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
                continue

            if user_input.startswith("lipsync "):
                parts = user_input.split(maxsplit=2)
                char_name = parts[1] if len(parts) > 1 else ""
                audio_or_text = parts[2] if len(parts) > 2 else ""
                if not char_name:
                    console.print("[red]Usage: lipsync <character_name> [audio_path or text][/red]")
                    continue

                cleaned_target = clean_file_path(audio_or_text) if audio_or_text else None
                if cleaned_target and cleaned_target.exists():
                    jsx = LipSyncEngine.build_audio_driven_lipsync_script(char_name, str(cleaned_target))
                    console.print(f"[cyan]Generated Audio-Driven Amplitude Lip Sync for '{char_name}'[/cyan]")
                else:
                    dialogue = audio_or_text or "Hello there! Welcome to AfterBrain."
                    jsx = LipSyncEngine.build_text_dialogue_lipsync_script(char_name, dialogue)
                    console.print(f"[cyan]Generated Syllable Lip Sync for dialogue: \"{dialogue}\"[/cyan]")

                exec_res = dispatcher.dispatch(jsx, script_name_prefix=f"lipsync_{char_name}")
                console.print(f"[green]✓ Lip Sync script saved & dispatched![/green] ({exec_res.get('saved_script_path')})")
                continue

            if user_input.startswith("generate "):
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
                continue

            console.print("[yellow]Unknown command. Type 'register', 'list', 'animate', 'lipsync', 'generate', or 'status'.[/yellow]")

        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    main()
