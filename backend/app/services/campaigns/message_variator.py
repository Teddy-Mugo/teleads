import random
import re
from typing import List, Optional


class MessageVariator:
    """
    Generates human-like variations of ad messages.
    """

    def __init__(
        self,
        *,
        emoji_sets: Optional[List[List[str]]] = None,
        shuffle_lines: bool = True,
        random_spacing: bool = True,
    ):
        self.emoji_sets = emoji_sets or [
            ["🔥", "✨", "🚀"],
            ["💥", "⚡", "🌟"],
            ["📢", "🛒", "💰"],
            ["🔔", "📌", "👉"],
        ]
        self.shuffle_lines = shuffle_lines
        self.random_spacing = random_spacing

    # --------------------
    # Public API
    # --------------------

    def vary(self, text: str) -> str:
        """
        Main entry point.
        """
        if random.random() < 0.2:
            return text

        lines = self._split_lines(text)

        if self.shuffle_lines and len(lines) > 1:
            random.shuffle(lines)

        lines = [self._vary_line(line) for line in lines]

        return "\n".join(lines)

    # --------------------
    # Line-level variation
    # --------------------

    def _vary_line(self, line: str) -> str:
        line = self._swap_emojis(line)
        line = self._randomize_spacing(line)
        line = self._soft_punctuation_variation(line)
        return line.strip()

    # --------------------
    # Variators
    # --------------------

    def _swap_emojis(self, text: str) -> str:
        """
        Replaces emojis with random alternatives.
        """
        emojis = self._extract_emojis(text)
        if not emojis:
            return text

        for emoji in emojis:
            replacement = random.choice(random.choice(self.emoji_sets))
            text = text.replace(emoji, replacement, 1)

        return text

    def _randomize_spacing(self, text: str) -> str:
        """
        Adds or removes spaces subtly.
        """
        if not self.random_spacing:
            return text

        text = re.sub(r"\s{2,}", " ", text)

        if random.random() < 0.3:
            text = text.replace(" ", "  ", 1)

        if random.random() < 0.2:
            text = text.replace("!", "!!", 1)

        return text

    def _soft_punctuation_variation(self, text: str) -> str:
        """
        Light punctuation changes.
        """
        replacements = {
            "!": ["!", "!!", " 🔥"],
            ".": [".", "..."],
        }

        for k, variants in replacements.items():
            if k in text and random.random() < 0.3:
                text = text.replace(k, random.choice(variants), 1)

        return text

    # --------------------
    # Helpers
    # --------------------

    @staticmethod
    def _split_lines(text: str) -> List[str]:
        return [line.strip() for line in text.split("\n") if line.strip()]

    @staticmethod
    def _extract_emojis(text: str) -> List[str]:
        emoji_pattern = re.compile(
            "["
            "\U0001F300-\U0001F5FF"
            "\U0001F600-\U0001F64F"
            "\U0001F680-\U0001F6FF"
            "\U0001F700-\U0001F77F"
            "\U0001F780-\U0001F7FF"
            "\U0001F800-\U0001F8FF"
            "\U0001F900-\U0001F9FF"
            "\U0001FA00-\U0001FAFF"
            "]+",
            flags=re.UNICODE,
        )
        return emoji_pattern.findall(text)
