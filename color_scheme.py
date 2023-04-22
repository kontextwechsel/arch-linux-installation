#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import colorsys
import contextlib
import io
import json
import re
import tarfile
import tempfile
import webbrowser
import zipfile

import numpy
import requests

STANDARD_DEVIATION = 0.05
COLOR_DISTANCE = 0.25


def get_sublime_HSL_colors():
    r = requests.get("https://www.sublimetext.com/download_thanks")
    r.raise_for_status()
    m = re.search(
        r"https://download\.sublimetext\.com/sublime_text_build_[0-9]+_x64\.tar\.xz",
        r.text,
    )
    if m:
        r = requests.get(m.group())
        r.raise_for_status()
        with contextlib.closing(
            tarfile.open(mode="r:xz", fileobj=io.BytesIO(r.content))
        ) as t:
            with zipfile.ZipFile(
                io.BytesIO(
                    t.extractfile(
                        "sublime_text/Packages/Color Scheme - Default.sublime-package"
                    ).read()
                )
            ) as z:
                scheme = json.loads(
                    re.sub(
                        r",\s*([]}])",
                        r"\1",
                        z.read("Monokai.sublime-color-scheme").decode(),
                    )
                )["variables"]
        colors = list()
        for color in scheme:
            m = re.fullmatch(
                r"hsl(a)?\((?P<H>[0-9]{1,3}),\s+(?P<S>[0-9]{1,3})%,\s+(?P<L>[0-9]{1,3})%(,\s+(?P<A>0\.[0-9]{1,2}))?\)",
                scheme[color],
            )
            H, S, L, A = (
                int(m.group("H")) / 360.0,
                int(m.group("S")) / 100.0,
                int(m.group("L")) / 100.0,
                float(m.group("A") or 1),
            )
            colors.append((color, (H, S, L), A))
        return colors
    else:
        raise Exception("Failed to retrieve Sublime Text download URL")


def get_sublime_RGB_colors(sublime_HSL_colors):
    colors = list()
    for name, (H, S, L), A in sublime_HSL_colors:
        colors.append((name, colorsys.hls_to_rgb(H, L, S), A))
    return colors


def get_gogh_RGB_colors():
    r = requests.get(
        "https://raw.githubusercontent.com/Gogh-Co/Gogh/master/json/monokai-dark.json"
    )
    r.raise_for_status()
    scheme = json.loads(r.text)

    def to_decimal(c):
        return tuple([int(c[x : x + 2], 16) / 255 for x in range(0, len(c), 2)])

    colors = list()
    for color in scheme:
        if color.startswith("color"):
            colors.append(
                (
                    f"color{int(color.split('_')[-1]) - 1}",
                    to_decimal(scheme[color][1:]),
                    1.0,
                )
            )
        if color in ["foreground", "background"]:
            colors.append((color, to_decimal(scheme[color][1:]), 1.0))
    return colors


def get_grayscale_RGB_colors(default_RGB_colors):
    colors = list()
    for name, (R, G, B), A in default_RGB_colors:
        if numpy.std((R, G, B)) < STANDARD_DEVIATION:
            value = 0.2989 * R + 0.5870 * G + 0.1140 * B
            colors.append((name, (value, value, value), A))
        else:
            colors.append((name, (R, G, B), A))
    return colors


def get_selected_RGB_colors(default_RGB_colors, reference_RGB_colors):
    colors = list()
    for default_name, (default_R, default_G, default_B), A in default_RGB_colors:
        min_distance = 1
        selected_color = None
        for (
            reference_name,
            (
                reference_R,
                reference_G,
                reference_B,
            ),
            _,
        ) in reference_RGB_colors:
            distance = numpy.sqrt(
                numpy.square(default_R - reference_R)
                + numpy.square(default_G - reference_G)
                + numpy.square(default_B - reference_B)
            )
            if distance < min_distance:
                min_distance = distance
                selected_color = (reference_R, reference_G, reference_B)
        if min_distance < COLOR_DISTANCE:
            colors.append((default_name, selected_color, A))
        else:
            colors.append((default_name, (default_R, default_G, default_B), A))
    return colors


if __name__ == "__main__":
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as file:
        background_color = "#dddddd"
        text_color = "#222222"

        print(
            f'<html><head><title>Auf zum Atem!</title><meta charset="utf-8"/></head><body style="background-color:{background_color};">',
            file=file,
        )

        to_byte = lambda v: round(v * 255)
        to_hex = lambda v: hex(to_byte(v))[2:].zfill(2).lower()

        large_text = (
            lambda text: f'<p style="font-family:monospace;font-size:24px;color:{text_color};">{text}</p>'
        )
        medium_text = (
            lambda text: f'<p style="font-family:monospace;font-size:16px;color:{text_color};">{text}</p>'
        )
        small_text = (
            lambda text: f'<p style="font-family:monospace;font-size:12px;color:{text_color};">{text}</p>'
        )
        text_block = (
            lambda text: f'<td width="100px" style="font-family:monospace;font-size:10px;color:{text_color};">{text}</td>'
        )
        color_block = (
            lambda color: f'<td width="100px" height="100px" style="background-color:{color}"></td>'
        )

        table_open = '<table cellspacing="0" cellpadding="0"><tbody><tr>'
        table_separator = '</tr><tr height="5px" /><tr>'
        table_close = "</tr></tbody></table>"

        sublime_HSL_colors = get_sublime_HSL_colors()
        sublime_RGB_colors = get_sublime_RGB_colors(sublime_HSL_colors)
        sublime_grayscale_RGB_colors = get_grayscale_RGB_colors(sublime_RGB_colors)

        print(large_text("Sublime Text Monokai"), file=file)
        print(medium_text("Default"), file=file)
        print(table_open, file=file)
        for name, _, _ in sublime_HSL_colors:
            print(text_block(name), file=file)
        print(table_separator, file=file)
        for name, (H, S, L), _ in sublime_HSL_colors:
            print(
                color_block(f"hsl({int(H * 360)},{int(S * 100)}%,{int(L * 100)}%)"),
                file=file,
            )
        print(table_separator, file=file)
        for name, (H, S, L), _ in sublime_HSL_colors:
            print(
                text_block(f"{int(H * 360)}/{int(S * 100)}%/{int(L * 100)}%"), file=file
            )
        print(table_separator, file=file)
        for name, (R, G, B), _ in sublime_RGB_colors:
            print(text_block(f"{to_byte(R)}/{to_byte(G)}/{to_byte(B)}"), file=file)
        print(table_separator, file=file)
        for name, (R, G, B), _ in sublime_RGB_colors:
            print(text_block(f"#{to_hex(R)}{to_hex(G)}{to_hex(B)}"), file=file)
        print(table_close, file=file)
        print(medium_text("Normalized"), file=file)
        print(table_open, file=file)
        for name, _, _ in sublime_HSL_colors:
            print(text_block(name), file=file)
        print(table_separator, file=file)
        for name, (R, G, B), _ in sublime_grayscale_RGB_colors:
            print(
                color_block(f"rgb({to_byte(R)},{to_byte(G)},{to_byte(B)})"), file=file
            )
        print(table_separator, file=file)
        for name, (R, G, B), _ in sublime_grayscale_RGB_colors:
            print(text_block(f"{to_byte(R)}/{to_byte(G)}/{to_byte(B)}"), file=file)
        print(table_separator, file=file)
        for name, (R, G, B), _ in sublime_grayscale_RGB_colors:
            print(text_block(f"#{to_hex(R)}{to_hex(G)}{to_hex(B)}"), file=file)
        print(table_close, file=file)

        gogh_RGB_colors = get_gogh_RGB_colors()
        gogh_grayscale_RGB_colors = get_grayscale_RGB_colors(gogh_RGB_colors)
        gogh_selected_RGB_colors = get_selected_RGB_colors(
            gogh_grayscale_RGB_colors, sublime_grayscale_RGB_colors
        )

        print(large_text("Gogh Monokai Dark"), file=file)
        print(medium_text("Default"), file=file)
        print(table_open, file=file)
        for name, _, _ in gogh_RGB_colors:
            print(text_block(name), file=file)
        print(table_separator, file=file)
        for name, (R, G, B), _ in gogh_RGB_colors:
            print(color_block(f"#{to_hex(R)}{to_hex(G)}{to_hex(B)}"), file=file)
        print(table_separator, file=file)
        for name, (R, G, B), _ in gogh_RGB_colors:
            print(text_block(f"{to_byte(R)}/{to_byte(G)}/{to_byte(B)}"), file=file)
        print(table_separator, file=file)
        for name, (R, G, B), _ in gogh_RGB_colors:
            print(text_block(f"#{to_hex(R)}{to_hex(G)}{to_hex(B)}"), file=file)
        print(table_close, file=file)
        print(medium_text("Normalized"), file=file)
        print(table_open, file=file)
        for name, _, _ in gogh_RGB_colors:
            print(text_block(name), file=file)
        print(table_separator, file=file)
        for name, (R, G, B), _ in gogh_grayscale_RGB_colors:
            print(
                color_block(f"rgb({to_byte(R)},{to_byte(G)},{to_byte(B)})"), file=file
            )
        print(table_separator, file=file)
        for name, (R, G, B), _ in gogh_grayscale_RGB_colors:
            print(text_block(f"{to_byte(R)}/{to_byte(G)}/{to_byte(B)}"), file=file)
        print(table_separator, file=file)
        for name, (R, G, B), _ in gogh_grayscale_RGB_colors:
            print(text_block(f"#{to_hex(R)}{to_hex(G)}{to_hex(B)}"), file=file)
        print(table_close, file=file)
        print(medium_text("Selected"), file=file)
        print(table_open, file=file)
        for name, _, _ in gogh_RGB_colors:
            print(text_block(name), file=file)
        print(table_separator, file=file)
        for name, (R, G, B), _ in gogh_selected_RGB_colors:
            print(
                color_block(f"rgb({to_byte(R)},{to_byte(G)},{to_byte(B)})"), file=file
            )
        print(table_separator, file=file)
        for name, (R, G, B), _ in gogh_selected_RGB_colors:
            print(text_block(f"{to_byte(R)}/{to_byte(G)}/{to_byte(B)}"), file=file)
        print(table_separator, file=file)
        for name, (R, G, B), _ in gogh_selected_RGB_colors:
            print(text_block(f"#{to_hex(R)}{to_hex(G)}{to_hex(B)}"), file=file)
        print(table_close, file=file)

        print(large_text("Script"), file=file)
        print(medium_text("Monokai.sublime-color-scheme"), file=file)
        colors = {}
        for name, (R, G, B), A in sublime_grayscale_RGB_colors:
            if A == 1.0:
                colors[name] = f"rgb({to_byte(R)}, {to_byte(G)}, {to_byte(B)})"
            else:
                colors[name] = f"rgba({to_byte(R)}, {to_byte(G)}, {to_byte(B)}, {A})"
        text = (
            json.dumps({"variables": colors}, indent=2)
            .replace(" ", "&nbsp;")
            .replace("\n", "<br />")
        )
        print(small_text(f"{text}"), file=file)

        print(medium_text(".Xresources"), file=file)
        text = "<br />".join(
            [
                f"XTerm.VT100.{name}: rgb:{to_hex(R)}/{to_hex(G)}/{to_hex(B)}"
                for name, (R, G, B), _ in gogh_selected_RGB_colors
            ]
        )
        print(small_text(text), file=file)

        print("</body></html>", file=file)
    webbrowser.open(file.name)
