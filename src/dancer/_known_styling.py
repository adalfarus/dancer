"""Known styles and themes"""
from importlib.resources import files as _files

styles: dict[str, str] = {}
base_styles_path = _files("dancer._styling.styles")
for styles_file in base_styles_path.iterdir():
    if styles_file.name.endswith(".qst"):
        content: str
        with styles_file.open("r") as f:
            content = f.read()
        styles[styles_file] = content

themes: dict[str, str] = {}
base_themes_path = _files("dancer._styling.themes")
for themes_file in base_themes_path.iterdir():
    if themes_file.name.endswith(".qth"):
        content: str
        with themes_file.open("r") as f:
            content = f.read()
        themes[themes_file] = content
