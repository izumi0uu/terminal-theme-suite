from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Theme:
    id: str
    name: str
    description: str
    ansi: List[str]
    colors: Dict[str, str]
    herdr_theme: str
    herdr_panel_bg: str = "background"
    background: Optional[Path] = None
    blend: float = 0.65
    image_mode: int = 2
    enabled: bool = True
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def profile_name(self) -> str:
        return f"TTS - {self.name}"


@dataclass
class UserConfig:
    themes: List[Theme]
    base_profile_guid: Optional[str] = None
    scope: str = "all"
    shortcuts: bool = True
    command_path: Optional[str] = None
    iterm_daemon: Optional[str] = None
