#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import contextlib
import decimal
import io
import json
import re
import tarfile
import tempfile
import typing
import webbrowser
import zipfile

import numpy
import requests
import yaml

STANDARD_DEVIATION = decimal.Decimal("10.25")
COLOR_DISTANCE = decimal.Decimal("63.25")


class RGB(typing.NamedTuple):
    name: str
    R: int
    G: int
    B: int
    A: int

    def to_grayscale_color(self) -> typing.Self:
        deviation = numpy.std((self.R, self.G, self.B))
        if deviation < STANDARD_DEVIATION:
            R = self.R * decimal.Decimal("0.2989")
            G = self.G * decimal.Decimal("0.5870")
            B = self.B * decimal.Decimal("0.1140")
            value = int((R + G + B).to_integral_value(rounding=decimal.ROUND_HALF_UP))
            return RGB(self.name, value, value, value, self.A)
        else:
            return self

    def to_similar_color(
        self, colors: typing.List[typing.Self], grayscale=True
    ) -> typing.Self:
        if grayscale or not self.R == self.G == self.B:
            distance = None
            selected = None
            for color in colors:
                d = numpy.sqrt(
                    numpy.square(self.R - color.R)
                    + numpy.square(self.G - color.G)
                    + numpy.square(self.B - color.B)
                )
                if distance is None or d < distance:
                    distance = d
                    selected = RGB(self.name, color.R, color.G, color.B, color.A)
            if selected is not None and distance < COLOR_DISTANCE:
                return selected
        return self

    def __str__(self) -> str:
        if self.A == 255:
            return f"#{bytes((self.R, self.G, self.B)).hex()}"
        else:
            return f"#{bytes((self.R, self.G, self.B, self.A)).hex()}"


class HSL(typing.NamedTuple):
    name: str
    H: int
    S: int
    L: int
    A: decimal.Decimal

    def to_RGB(self) -> RGB:
        to_int = lambda v: int(
            (v * 255).to_integral_value(rounding=decimal.ROUND_HALF_UP)
        )
        S = self.S / decimal.Decimal(100)
        L = self.L / decimal.Decimal(100)
        c = (1 - abs(2 * L - 1)) * S
        x = c * (1 - abs((self.H / decimal.Decimal(60)) % 2 - 1))
        m = L - c / decimal.Decimal(2)
        if 0 <= self.H < 60:
            R, G, B = c, x, 0
        elif 60 <= self.H < 120:
            R, G, B = x, c, 0
        elif 120 <= self.H < 180:
            R, G, B = 0, c, x
        elif 180 <= self.H < 240:
            R, G, B = 0, x, c
        elif 240 <= self.H < 300:
            R, G, B = x, 0, c
        else:
            R, G, B = c, 0, x
        return RGB(
            self.name, to_int(R + m), to_int(G + m), to_int(B + m), to_int(self.A)
        )


def get_sublime_colors() -> list[RGB]:
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
            colors.append(
                HSL(
                    color,
                    int(m.group("H")),
                    int(m.group("S")),
                    int(m.group("L")),
                    decimal.Decimal(m.group("A") or "1.0"),
                ).to_RGB()
            )
        return colors
    else:
        raise Exception("Failed to retrieve Sublime Text download URL")


def get_gogh_colors() -> list[RGB]:
    r = requests.get(
        "https://raw.githubusercontent.com/Gogh-Co/Gogh/refs/heads/master/themes/Monokai%20Dark.yml"
    )
    r.raise_for_status()
    scheme = yaml.load(r.text, yaml.SafeLoader)

    def to_int(color):
        R, G, B = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        if len(color) == 7:
            return R, G, B, 255
        else:
            return R, G, B, int(color[:9], 16)

    colors = list()

    for color in ["background", "foreground", *range(16)]:
        if type(color) == int:
            name = f"color{str(color)}"
            R, G, B, A = to_int(scheme[f"color_{str(color % 8 + 1).zfill(2)}"])
        else:
            name = color
            R, G, B, A = to_int(scheme[color])
        colors.append(RGB(name, R, G, B, A))
    return colors


def main() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as file:
        background_color = RGB("background", 221, 221, 221, 255)
        text_color = RGB("text", 34, 34, 34, 255)

        print(f"<!DOCTYPE html>", file=file)
        print(f"<html>", file=file)
        print(f"<head>", file=file)
        print(f"<title>Auf zum Atem!</title>", file=file)
        print(f'<meta charset="utf-8"/>', file=file)
        print(f"</head>", file=file)
        print(f'<body style="background-color:{background_color};">', file=file)

        def print_large_text(text):
            print(
                f'<p style="font-family:monospace;font-size:24px;color:{text_color};">{text}</p>',
                file=file,
            )

        def print_small_text(text):
            print(
                f'<p style="font-family:monospace;font-size:16px;color:{text_color};">{text}</p>',
                file=file,
            )

        def print_text_block(text):
            print(
                f'<td style="width:100px;font-family:monospace;font-size:10px;color:{text_color};">{text}</td>',
                file=file,
            )

        def print_color_block(color):
            print(
                f'<td style="width:100px;height:50px;background-color:{color}"></td>',
                file=file,
            )

        def print_separator():
            print("</tr>", file=file)
            print('<tr height="5px">', file=file)
            print("</tr>", file=file)
            print("<tr>", file=file)

        def print_colors(colors):
            print('<table cellspacing="0" cellpadding="0">', file=file)
            print("<tbody>", file=file)
            print("<tr>", file=file)
            for color in colors:
                print_text_block(color.name)
            print_separator()
            for color in colors:
                print_color_block(color)
            print_separator()
            for color in colors:
                print_text_block(f"{color}")
            print("</tr>", file=file)
            print("</tbody>", file=file)
            print("</table>", file=file)

        print_large_text("Sublime Text Monokai")

        print_small_text("Theme")
        sublime_colors = get_sublime_colors()
        print_colors(sublime_colors)

        print_small_text("Grayscale")
        sublime_grayscale_colors = [
            color.to_grayscale_color() for color in sublime_colors
        ]
        print_colors(sublime_grayscale_colors)

        print_small_text("Selected")
        sublime_selected_colors = []
        for color in sublime_grayscale_colors:
            sublime_selected_colors.append(
                color.to_similar_color(sublime_selected_colors, grayscale=False)
            )
        print_colors(sublime_selected_colors)

        print_large_text("Gogh Monokai Dark")

        print_small_text("Theme")
        gogh_colors = get_gogh_colors()
        print_colors(gogh_colors)

        print_small_text("Grayscale")
        gogh_grayscale_colors = [color.to_grayscale_color() for color in gogh_colors]
        print_colors(gogh_grayscale_colors)

        print_small_text("Selected")
        gogh_selected_colors = [
            color.to_similar_color(sublime_selected_colors) for color in gogh_colors
        ]
        print_colors(gogh_selected_colors)

        print("</body>", file=file)
        print("</html>", file=file)

    webbrowser.open(file.name)


if __name__ == "__main__":
    main()
