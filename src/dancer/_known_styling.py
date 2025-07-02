"""Known styles and themes"""
import os

styles: dict[str, str] = {}
base_styles_path: str = os.path.abspath("./_styling/styles")
for styles_file in os.listdir(base_styles_path):
    if styles_file.endswith(".qst"):
        content: str
        with open(os.path.join(base_styles_path, styles_file)) as f:
            content = f.read()
        styles[styles_file] = content

themes: dict[str, str] = {}
base_themes_path: str = os.path.abspath("./_styling/themes")
for themes_file in os.listdir(base_themes_path):
    if themes_file.endswith(".qth"):
        content: str
        with open(os.path.join(base_themes_path, themes_file)) as f:
            content = f.read()
        themes[themes_file] = content
