import os
import shutil
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

PANEL_SOURCE = Path(__file__).resolve().parent.parent / "extendscript" / "AfterBrain.jsx"


def find_after_effects_scriptui_dirs() -> List[Path]:
    """Discovers all After Effects ScriptUI Panels directories on Windows."""
    discovered = []
    
    # 1. User AppData (e.g., %APPDATA%\Adobe\After Effects\23.2\Scripts\ScriptUI Panels)
    appdata = os.environ.get("APPDATA")
    if appdata:
        ae_user_base = Path(appdata) / "Adobe" / "After Effects"
        if ae_user_base.exists():
            for version_dir in ae_user_base.iterdir():
                if version_dir.is_dir() and not version_dir.name.lower().startswith("logs"):
                    panels_dir = version_dir / "Scripts" / "ScriptUI Panels"
                    discovered.append(panels_dir)

    # 2. Program Files (e.g., C:\Program Files\Adobe\Adobe After Effects 2023\Support Files\Scripts\ScriptUI Panels)
    prog_files = os.environ.get("ProgramFiles", "C:\\Program Files")
    adobe_base = Path(prog_files) / "Adobe"
    if adobe_base.exists():
        for ae_folder in adobe_base.glob("Adobe After Effects*"):
            support_scripts = ae_folder / "Support Files" / "Scripts" / "ScriptUI Panels"
            if support_scripts.exists():
                discovered.append(support_scripts)

    return list(dict.fromkeys(discovered))


def install_afterbrain_panel() -> List[Path]:
    """
    Installs or updates AfterBrain.jsx into all detected After Effects ScriptUI Panels folders.
    Returns list of successfully installed paths.
    """
    if not PANEL_SOURCE.exists():
        logger.warning(f"AfterBrain panel source not found at: {PANEL_SOURCE}")
        return []

    target_dirs = find_after_effects_scriptui_dirs()
    installed = []

    for target_dir in target_dirs:
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            dest_file = target_dir / "AfterBrain.jsx"
            shutil.copy2(str(PANEL_SOURCE), str(dest_file))
            installed.append(dest_file)
            logger.info(f"Installed AfterBrain.jsx to: {dest_file}")
        except Exception as e:
            logger.warning(f"Could not install to {target_dir}: {e}")

    return installed


if __name__ == "__main__":
    results = install_afterbrain_panel()
    if results:
        print(f"Successfully installed AfterBrain panel to {len(results)} location(s):")
        for r in results:
            print(f"  [OK] {r}")
    else:
        print("No After Effects installation folders found to install to.")
