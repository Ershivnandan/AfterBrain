import logging
import re
from typing import Dict, Any, Optional
import ollama
from src.config import settings
from src.character.memory import CharacterMemory
from src.extendscript.validator import ExtendScriptValidator
from src.worker.prompt_templates import WorkerPrompts

logger = logging.getLogger(__name__)


class OllamaWorkerClient:
    """Interacts with locally running Qwen model via Ollama to generate ExtendScript code."""

    def __init__(self, memory: Optional[CharacterMemory] = None):
        self.client = ollama.Client(host=settings.ollama_host)
        self.model = settings.ollama_model
        self.memory = memory or CharacterMemory()

    def check_connection(self) -> Dict[str, Any]:
        """Verifies Ollama is running and checks if the model is available."""
        try:
            models_response = self.client.list()
            # In ollama python client, models can be a list of Model objects or dicts
            model_names = []
            for m in getattr(models_response, "models", []):
                name = getattr(m, "model", None) or getattr(m, "name", None) or str(m)
                model_names.append(name)

            has_model = any(self.model in name for name in model_names)
            return {
                "ollama_connected": True,
                "host": settings.ollama_host,
                "target_model": self.model,
                "model_available": has_model,
                "available_models": model_names,
            }
        except Exception as e:
            return {
                "ollama_connected": False,
                "error": str(e),
                "host": settings.ollama_host,
                "target_model": self.model,
            }

    def generate_extendscript(self, user_prompt: str, character_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Sends prompt to Qwen with After Effects system context and extracts clean ExtendScript.
        """
        char_context = self.memory.get_prompt_context()
        system_content = WorkerPrompts.get_system_prompt(character_context=char_context)

        if character_name:
            char_info = self.memory.get_character(character_name)
            if char_info:
                user_content = WorkerPrompts.get_character_prompt(
                    character_name=character_name,
                    user_prompt=user_prompt,
                    layer_name=char_info.get("layer_name", character_name),
                    rig_type=char_info.get("rig_type", "puppet_pins"),
                    pin_mapping=str(char_info.get("pin_mapping", {})),
                    description=char_info.get("description", ""),
                    personality=char_info.get("personality", ""),
                )
            else:
                user_content = f"Character '{character_name}' requested. User prompt: {user_prompt}"
        else:
            user_content = WorkerPrompts.get_general_prompt(user_prompt=user_prompt)

        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_content},
                ],
                options={"temperature": 0.2},
            )

            response_text = response["message"]["content"]
            jsx_code = self._extract_jsx(response_text)

            # Validate syntax
            is_valid, validation_msg = ExtendScriptValidator.validate(jsx_code)

            return {
                "status": "success",
                "model": self.model,
                "jsx_code": jsx_code,
                "explanation": self._extract_explanation(response_text),
                "syntax_valid": is_valid,
                "validation_message": validation_msg,
            }
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return {
                "status": "error",
                "error": str(e),
                "model": self.model,
            }

    def _extract_jsx(self, text: str) -> str:
        """Extracts code from ```jsx, ```javascript, or raw text."""
        # Find code blocks
        matches = re.findall(r"```(?:jsx|javascript|extendscript|js)?\s*\n([\s\S]*?)```", text, flags=re.IGNORECASE)
        if matches:
            # Pick longest code block
            return sorted(matches, key=len, reverse=True)[0].strip()

        # If no code fences, check if text contains ExtendScript keywords
        if any(kw in text for kw in ["app.beginUndoGroup", "app.project", "var comp", "comp.layer", "app.activeItem"]):
            return text.strip()

        return ""

    def _extract_explanation(self, text: str) -> str:
        """Removes code blocks to return just the conversational explanation."""
        cleaned = re.sub(r"```[\s\S]*?```", "", text).strip()
        if not cleaned:
            first_comment = re.search(r"//\s*(.+)", text)
            if first_comment:
                return first_comment.group(1).strip()
            return "Applied motion animation in active composition."
        return cleaned[:500] if len(cleaned) > 500 else cleaned
