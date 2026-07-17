"""ASCII banner shown at the top of `flipperkit --help`.

Generated art (dolphin + framed wordmark). Pure ASCII so it never trips the
Windows console codepage. Colours are applied at render time, not stored.
"""

from __future__ import annotations

DOLPHIN = "                                                   __\n                                               _.-~  )\n                                    _..--~~~~,'   ,-/     _\n                                 .-'. . . .'      ,-','    ,\n                               ,'. . . _   ,--~,-'__..-'  ,'\n                             ,'. . .  (@)' ---~~~~      ,'\n                            /. . . . '                 ,-'\n                           ; . . . .- .            ,-'\n                          : . . . .   `.       ,-'. .\n                         . . . . .      `.  ,-' . . .\n                        . . . . .         .' . . . . .\n                       .-.  . . . .     ,'  . . . . .\n                    `._`.`.__. . .  ,-'. . . . . . .\n                       `-.`-'`--...-'`-._ . . . . .\n                          `--..___..--~~~  `-. . .\n                                             `._ ."

FRAME = "+============================================================================+\n|                                                                            |\n| >BACKUP         _____ _ _                       _  ___ _              NFC. |\n| >PARSE         |  ___| (_)_ __  _ __   ___ _ __| |/ (_) |_         SubGhz. |\n| >INDEX         | |_  | | | '_ \\| '_ \\ / _ \\ '__| ' /| | __|          RFID. |\n| >REPORT        |  _| | | | |_) | |_) |  __/ |  | . \\| | |_        iButton. |\n|                |_|   |_|_| .__/| .__/ \\___|_|  |_|\\_\\_|\\__|                |\n|                          |_|   |_|                                         |\n|                                                                            |\n|                         Flipper Zero companion CLI                         |\n+============================================================================+"


def render_banner(console) -> None:
    """Print the banner: Flipper-orange dolphin over a green framed wordmark."""
    console.print(DOLPHIN, style="#ff8200", markup=False, highlight=False)
    console.print(FRAME, style="bold green", markup=False, highlight=False)
