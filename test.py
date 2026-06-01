from pathlib import Path

def show_tree(path=Path("."), prefix=""):
    for item in path.iterdir():
        print(prefix + item.name)
        if item.is_dir():
            show_tree(item, prefix + "  ")

show_tree(Path("."))