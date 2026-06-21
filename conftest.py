"""pytest 設定 — `src` レイアウトを import パスに追加する。

これにより `pytest` を引数なしで実行しても `import officina` が解決される。
"""

import sys
from pathlib import Path

SRC = Path(__file__).parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
