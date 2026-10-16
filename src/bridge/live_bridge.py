import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from src.config import settings

logger = logging.getLogger(__name__)


class LiveAEBridge:
    """Interfaces directly with a running Adobe After Effects instance on Windows."""

    def __init__(self, binary_path: Optional[str] = None):
        self.binary_path = binary_path or settings.ae_binary_path

    def is_ae_available(self) -> bool:
        """Checks if After Effects COM server can be acquired."""
        try:
            import win32com.client
            ae = win32com.client.Dispatch("AfterEffects.Application")
            return ae is not None
        except Exception:
            return False

    def execute_via_com(self, jsx_code: str) -> Dict[str, Any]:
        """Executes ExtendScript directly in the running After Effects session via COM."""
        try:
            import win32com.client
            ae = win32com.client.Dispatch("AfterEffects.Application")
            # DoScript executes jsx and returns result
            result_str = ae.DoScript(jsx_code)

            # Try to parse JSON result returned by ExtendScript wrapper
            try:
                result_json = json.loads(result_str)
                return {
                    "status": "success",
                    "mode": "live_com",
                    "result": result_json
                }
            except Exception:
                return {
                    "status": "success",
                    "mode": "live_com",
                    "raw_output": str(result_str)
                }
        except Exception as e:
            logger.error(f"COM execution error: {e}")
            return {
                "status": "error",
                "mode": "live_com",
                "error": str(e)
            }

    def execute_via_cli(self, script_path: str) -> Dict[str, Any]:
        """Fallback execution via AfterFX.exe -r <script>."""
        if not self.binary_path:
            return {"status": "error", "message": "AfterFX binary path not configured."}

        try:
            cmd = [self.binary_path, "-r", str(Path(script_path).resolve())]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return {
                "status": "success" if proc.returncode == 0 else "error",
                "mode": "live_cli",
                "stdout": proc.stdout,
                "stderr": proc.stderr
            }
        except Exception as e:
            return {"status": "error", "mode": "live_cli", "error": str(e)}
