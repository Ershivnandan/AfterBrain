import re
from typing import Dict, Tuple


class ExtendScriptValidator:
    """Validates and cleans ExtendScript code before dispatching to After Effects."""

    @staticmethod
    def clean_code(raw_code: str) -> str:
        """Strips markdown code blocks and trims whitespace."""
        code = raw_code.strip()
        # Remove ```javascript, ```jsx, ```extendscript, or ```
        code = re.sub(r"^```(?:javascript|jsx|extendscript|js)?\s*", "", code, flags=re.IGNORECASE)
        code = re.sub(r"\s*```$", "", code)
        return code.strip()

    @staticmethod
    def validate(code: str) -> Tuple[bool, str]:
        """
        Validates bracket balance and basic ExtendScript syntax.
        Returns (is_valid, error_message).
        """
        cleaned = ExtendScriptValidator.clean_code(code)
        if not cleaned:
            return False, "Script content is empty."

        # Check bracket and parenthesis balance
        stack = []
        matching = {')': '(', '}': '{', ']': '['}

        in_single_quote = False
        in_double_quote = False
        in_template_quote = False
        in_line_comment = False
        in_block_comment = False

        i = 0
        n = len(cleaned)

        while i < n:
            ch = cleaned[i]

            # Handle comments
            if not (in_single_quote or in_double_quote or in_template_quote):
                if in_line_comment:
                    if ch == '\n':
                        in_line_comment = False
                    i += 1
                    continue
                if in_block_comment:
                    if ch == '*' and i + 1 < n and cleaned[i + 1] == '/':
                        in_block_comment = False
                        i += 2
                        continue
                    i += 1
                    continue
                if ch == '/' and i + 1 < n:
                    if cleaned[i + 1] == '/':
                        in_line_comment = True
                        i += 2
                        continue
                    if cleaned[i + 1] == '*':
                        in_block_comment = True
                        i += 2
                        continue

            # Handle string escapes
            if ch == '\\' and (in_single_quote or in_double_quote or in_template_quote):
                i += 2
                continue

            if ch == "'" and not (in_double_quote or in_template_quote or in_line_comment or in_block_comment):
                in_single_quote = not in_single_quote
            elif ch == '"' and not (in_single_quote or in_template_quote or in_line_comment or in_block_comment):
                in_double_quote = not in_double_quote
            elif ch == '`' and not (in_single_quote or in_double_quote or in_line_comment or in_block_comment):
                in_template_quote = not in_template_quote

            # Check brackets outside strings and comments
            if not (in_single_quote or in_double_quote or in_template_quote or in_line_comment or in_block_comment):
                if ch in "({[":
                    stack.append((ch, i))
                elif ch in ")}]":
                    if not stack:
                        return False, f"Unmatched closing bracket '{ch}' at character position {i}"
                    top, _ = stack.pop()
                    if matching[ch] != top:
                        return False, f"Mismatched bracket: expected closing for '{top}' but got '{ch}' at position {i}"

            i += 1

        if stack:
            unmatched_char, pos = stack[-1]
            return False, f"Unclosed bracket '{unmatched_char}' opened at position {pos}"

        return True, "Valid"
