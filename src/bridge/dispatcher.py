import logging
from typing import Dict, Any, Optional
from src.config import settings
from src.bridge.live_bridge import LiveAEBridge
from src.bridge.mock_bridge import MockAEBridge

logger = logging.getLogger(__name__)


class AEBridgeDispatcher:
    """Dispatches ExtendScript execution to Live AE or Mock Simulation depending on environment."""

    def __init__(self):
        self.live_bridge = LiveAEBridge()
        self.mock_bridge = MockAEBridge()

    def get_status(self) -> Dict[str, Any]:
        """Returns the current bridge status and active execution mode."""
        is_live_possible = self.live_bridge.is_ae_available()
        configured_mode = settings.ae_execution_mode.lower()

        if configured_mode == "live":
            active_mode = "live" if is_live_possible else "live_unavailable"
        elif configured_mode == "mock":
            active_mode = "mock"
        else:  # auto
            active_mode = "live" if is_live_possible else "mock"

        return {
            "configured_mode": configured_mode,
            "active_mode": active_mode,
            "after_effects_running": is_live_possible,
            "output_scripts_dir": str(settings.output_scripts_dir.resolve()),
        }

    def dispatch(self, jsx_code: str, script_name_prefix: str = "ai_anim") -> Dict[str, Any]:
        """Routes ExtendScript to the best available engine."""
        status = self.get_status()
        active_mode = status["active_mode"]

        # Always save a copy to output_scripts for user convenience
        mock_result = self.mock_bridge.execute(jsx_code, script_name_prefix=script_name_prefix)

        if active_mode == "live":
            logger.info("Attempting Live ExtendScript dispatch...")
            # 1. Try COM
            live_result = self.live_bridge.execute_via_com(jsx_code)
            if live_result.get("status") == "success":
                live_result["saved_script_path"] = mock_result["saved_script_path"]
                return live_result

            # 2. Fallback to AfterFX.exe IPC
            cli_result = self.live_bridge.execute_via_cli(mock_result["saved_script_path"])
            cli_result["saved_script_path"] = mock_result["saved_script_path"]
            return cli_result

        # Otherwise return mock simulation result
        return mock_result
