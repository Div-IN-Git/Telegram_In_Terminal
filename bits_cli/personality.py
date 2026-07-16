from __future__ import annotations

import random

LINES = {
    "chew": ["Chewing...", "Nom nom...", "On the plate."],
    "empty": ["I'm hungry.", "Nothing on the plate yet."],
    "eat": ["Yum, digested and stored!", "Gulp - saved!", "That went down nicely."],
    "remember": ["I remember that.", "Found it in the belly."],
    "digest": ["Blegh!", "Spat that one out."],
}


def line(event: str, quiet: bool = False) -> str:
    if quiet:
        return ""
    return random.choice(LINES.get(event, ["Done."]))
