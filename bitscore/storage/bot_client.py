from __future__ import annotations

from bitscore.config import TelegramSettings


class BotClient:
    def __init__(self, settings: TelegramSettings) -> None:
        self.settings = settings

    def configured(self) -> bool:
        return bool(self.settings.bot_token)
