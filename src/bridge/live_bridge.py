import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from src.config import settings

logger = logging.getLogger(__name__)


class LiveAEBridge:
    """Interfaces directly with a running Adobe After Effects instance on Windows."""

    STANDARD_AE_PATHS = [
        r"C:\Program Files\Adobe\Adobe After Effects 2024\Support Files\AfterFX.exe",
        r"C:\Program Files\Adobe\Adobe After Effects 2023\Support Files\AfterFX.exe",
        r"C:\Program Files\Adobe\Adobe After Effects 2022\Support Files\AfterFX.exe",
        r"C:\Program Files\Adobe\Adobe After Effects 2025\Support Files\AfterFX.exe",
    ]

    def __init__(self, binary_path: Optional[str] = None):
        self.binary_path = binary_path or settings.ae_binary_path or self._detect_binary_path()

    def _detect_binary_path(self) -> Optional[str]:
        """Automatically detects installed AfterFX.exe location."""
        for p in self.STANDARD_AE_PATHS:
            if Path(p).exists():
                return p
        return None

    def is_process_running(self) -> bool:
        """Checks if AfterFX.exe process is currently active in Windows tasklist."""
        try:
            res = subprocess.run(["tasklist", "/fi", "imagename eq AfterFX.exe"], capture_output=True, text=True, timeout=5)
            return "afterfx.exe" in res.stdout.lower()
        except Exception:
            return False

    def is_ae_available(self) -> bool:
        """Returns True if After Effects is open and executable or COM is reachable."""
        # 1. Check COM Dispatch
        try:
            import win32com.client
            ae = win32com.client.Dispatch("AfterEffects.Application")
            if ae is not None:
                return True
        except Exception:
            pass

        # 2. Check if AfterFX.exe process is actively running and binary exists
        if self.binary_path and Path(self.binary_path).exists() and self.is_process_running():
            return True

        return False

    def execute_via_com(self, jsx_code: str) -> Dict[str, Any]:
        """Executes ExtendScript directly in the running After Effects session via COM."""
        try:
            import win32com.client
            ae = win32com.client.Dispatch("AfterEffects.Application")
            result_str = ae.DoScript(jsx_code)

            try:
                result_json = json.loads(result_str)
                return {"status": "success", "mode": "live_com", "result": result_json}
            except Exception:
                return {"status": "success", "mode": "live_com", "raw_output": str(result_str)}
        except Exception as e:
            return {"status": "error", "mode": "live_com", "error": str(e)}

    def execute_via_cli(self, script_path: str) -> Dict[str, Any]:
        """Executes JSX script in the running After Effects session via IPC (AfterFX.exe -r)."""
        if not self.binary_path or not Path(self.binary_path).exists():
            return {"status": "error", "message": f"AfterFX binary not found at: {self.binary_path}"}

        try:
            # Popen sends the script to the running After Effects instance asynchronously without blocking
            subprocess.Popen([self.binary_path, "-r", str(Path(script_path).resolve())])
            return {
                "status": "success",
                "mode": "live_ipc",
                "message": f"Script dispatched live to active After Effects session ({Path(self.binary_path).name})",
                "script_path": str(script_path),
            }
        except Exception as e:
            return {"status": "error", "mode": "live_ipc", "error": str(e)}
