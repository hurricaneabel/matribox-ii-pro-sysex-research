"""Compatibilidade com o antigo comando de validação do monitor.

O monitor consolidado agora está em:

    python -m tools.commands.matribox_monitor
"""

from __future__ import annotations

import sys

from tools.commands.matribox_monitor import main


if __name__ == "__main__":
    sys.exit(main())
