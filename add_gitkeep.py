from pathlib import Path

BASE = Path(".").resolve()

for p in BASE.iterdir():
    if not p.is_dir():
        continue

    # 跳過 .git 這種系統資料夾
    if p.name.startswith("."):
        continue

    gitkeep = p / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()
        print("added:", gitkeep)