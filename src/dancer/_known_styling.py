"""Known styles and themes"""
import os.path
from importlib.resources import files as _files

styles: dict[str, str] = {}
base_styles_path = _files("dancer._styling.styles")
for styles_file in base_styles_path.iterdir():
    if styles_file.name.endswith(".qst"):
        style_content: str
        with styles_file.open("r") as f:
            style_content = f.read()
        styles[os.path.basename(str(styles_file))] = style_content

themes: dict[str, str] = {}
base_themes_path = _files("dancer._styling.themes")
for themes_file in base_themes_path.iterdir():
    if themes_file.name.endswith(".qth"):
        theme_content: str
        with themes_file.open("r") as f:
            theme_content = f.read()
        themes[os.path.basename(str(themes_file))] = theme_content
