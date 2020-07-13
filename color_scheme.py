#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import colorsys
import contextlib
import json
import re
import tarfile
import tempfile
import urllib.request
import webbrowser
import zipfile

import numpy

STANDARD_DEVIATION = 0.05
COLOR_DISTANCE = 0.25


def get_sublime_HSL_mapping():
    with tempfile.TemporaryDirectory() as tmp:
        sublime_text_url = 'https://download.sublimetext.com/sublime_text_3_build_3211_x64.tar.bz2'
        sublime_text_tarball = f'''{tmp}/{sublime_text_url.split('/')[-1]}'''
        urllib.request.urlretrieve(sublime_text_url, filename=sublime_text_tarball)
        sublime_text_package = 'sublime_text_3/Packages/Color Scheme - Default.sublime-package'
        with contextlib.closing(tarfile.open(sublime_text_tarball)) as t:
            t.extract(sublime_text_package, path=tmp)
        sublime_text_color_scheme = 'Monokai.sublime-color-scheme'
        with zipfile.ZipFile(f'{tmp}/{sublime_text_package}') as z:
            scheme = z.read(sublime_text_color_scheme).decode()
        m = re.search(r'(?<=\"variables\")\s*:\s*(?P<variables>{.*?})', scheme, re.MULTILINE | re.DOTALL)
        variables = json.loads(m.group('variables'))
        mapping = list()
        for variable in sorted(variables):
            m = re.fullmatch(r'hsl\((?P<H>[0-9]{1,3}), (?P<S>[0-9]{1,3})%, (?P<L>[0-9]{1,3})%\)', variables[variable])
            H, S, L = int(m.group('H')) / 360., int(m.group('S')) / 100., int(m.group('L')) / 100.
            mapping.append((variable, (H, S, L)))
        return mapping


def get_sublime_RGB_mapping(sublime_HSL_mapping):
    mapping = list()
    for name, (H, S, L) in sublime_HSL_mapping:
        mapping.append((name, colorsys.hls_to_rgb(H, L, S)))
    return mapping


def get_gogh_RGB_mapping():
    mapping = list()
    lines = list()
    gogh_url = 'https://raw.githubusercontent.com/Mayccoll/Gogh/master/themes/monokai-dark.sh'
    with urllib.request.urlopen(gogh_url) as response:
        for line in response.readlines():
            s = line.decode()
            if s.startswith('export'):
                lines.append(s)
    number_mapping = list()
    for s in sorted(lines):
        m = re.match(r'COLOR_(?P<number>[0-9]{2})="#(?P<color>[a-zA-Z0-9]{6})"', re.split(r'\s+', s)[1])
        color = lambda c: tuple([int(c[x:x + 2], 16) / 255 for x in range(0, len(c), 2)])
        if m:
            number = int(m.group('number')) - 1
            number_mapping.append((f'color{number}', color(m.group('color'))))
        m = re.match(r'(?P<type>BACKGROUND|FOREGROUND)_COLOR="#(?P<color>[a-zA-Z0-9]{6})"', re.split(r'\s+', s)[1])
        if m:
            mapping.append((m.group('type').lower(), color(m.group('color'))))
    mapping.extend(number_mapping)
    return mapping


def get_grayscale_RGB_mapping(default_RGB_mapping):
    mapping = list()
    for name, (R, G, B) in default_RGB_mapping:
        if numpy.std((R, G, B)) < STANDARD_DEVIATION:
            value = 0.2989 * R + 0.5870 * G + 0.1140 * B
            mapping.append((name, (value, value, value)))
        else:
            mapping.append((name, (R, G, B)))
    return mapping


def get_selected_RGB_mapping(default_RGB_mapping, reference_RGB_mapping):
    mapping = list()
    for default_name, (default_R, default_G, default_B) in default_RGB_mapping:
        min_distance = 1
        selected_color = None
        for reference_name, (reference_R, reference_G, reference_B) in reference_RGB_mapping:
            distance = numpy.sqrt(numpy.square(default_R - reference_R) + numpy.square(default_G - reference_G) + numpy.square(default_B - reference_B))
            if distance < min_distance:
                min_distance = distance
                selected_color = (reference_R, reference_G, reference_B)
        if min_distance < COLOR_DISTANCE:
            mapping.append((default_name, selected_color))
        else:
            mapping.append((default_name, (default_R, default_G, default_B)))
    return mapping


if __name__ == '__main__':
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as file:
        background_color = '#DDDDDD'
        text_color = '#222222'

        print(f'<html><head><title>Auf zum Atem!</title><meta charset="utf-8"/></head><body style="background-color:{background_color};">', file=file)

        to_byte = lambda v: round(v * 255)
        to_hex = lambda v: hex(to_byte(v))[2:].zfill(2).lower()

        large_text = lambda text: f'<p style="font-family:monospace;font-size:24px;color:{text_color};">{text}</p>'
        medium_text = lambda text: f'<p style="font-family:monospace;font-size:16px;color:{text_color};">{text}</p>'
        small_text = lambda text: f'<p style="font-family:monospace;font-size:12px;color:{text_color};">{text}</p>'
        text_block = lambda text: f'<td width="100px" style="font-family:monospace;font-size:10px;color:{text_color};">{text}</td>'
        color_block = lambda color: f'<td width="100px" height="100px" style="background-color:{color}"></td>'

        table_open = '<table cellspacing="0" cellpadding="0"><tbody><tr>'
        table_separator = '</tr><tr height="5px" /><tr>'
        table_close = '</tr></tbody></table>'

        sublime_HSL_mapping = get_sublime_HSL_mapping()
        sublime_RGB_mapping = get_sublime_RGB_mapping(sublime_HSL_mapping)
        sublime_grayscale_RGB_mapping = get_grayscale_RGB_mapping(sublime_RGB_mapping)

        print(large_text('Sublime Text Monokai'), file=file)
        print(medium_text('Default'), file=file)
        print(table_open, file=file)
        for name, _ in sublime_HSL_mapping:
            print(text_block(name), file=file)
        print(table_separator, file=file)
        for name, (H, S, L) in sublime_HSL_mapping:
            print(color_block(f'hsl({int(H * 360)},{int(S * 100)}%,{int(L * 100)}%)'), file=file)
        print(table_separator, file=file)
        for name, (H, S, L) in sublime_HSL_mapping:
            print(text_block(f'{int(H * 360)}/{int(S * 100)}%/{int(L * 100)}%'), file=file)
        print(table_separator, file=file)
        for name, (R, G, B) in sublime_RGB_mapping:
            print(text_block(f'{to_byte(R)}/{to_byte(G)}/{to_byte(B)}'), file=file)
        print(table_separator, file=file)
        for name, (R, G, B) in sublime_RGB_mapping:
            print(text_block(f'#{to_hex(R)}{to_hex(G)}{to_hex(B)}'), file=file)
        print(table_close, file=file)
        print(medium_text('Normalized'), file=file)
        print(table_open, file=file)
        for name, _ in sublime_HSL_mapping:
            print(text_block(name), file=file)
        print(table_separator, file=file)
        for name, (R, G, B) in sublime_grayscale_RGB_mapping:
            print(color_block(f'rgb({to_byte(R)},{to_byte(G)},{to_byte(B)})'), file=file)
        print(table_separator, file=file)
        for name, (R, G, B) in sublime_grayscale_RGB_mapping:
            print(text_block(f'{to_byte(R)}/{to_byte(G)}/{to_byte(B)}'), file=file)
        print(table_separator, file=file)
        for name, (R, G, B) in sublime_grayscale_RGB_mapping:
            print(text_block(f'#{to_hex(R)}{to_hex(G)}{to_hex(B)}'), file=file)
        print(table_close, file=file)

        gogh_RGB_mapping = get_gogh_RGB_mapping()
        gogh_grayscale_RGB_mapping = get_grayscale_RGB_mapping(gogh_RGB_mapping)
        gogh_selected_RGB_mapping = get_selected_RGB_mapping(gogh_grayscale_RGB_mapping, sublime_grayscale_RGB_mapping)

        print(large_text('Gogh Monokai Dark'), file=file)
        print(medium_text('Default'), file=file)
        print(table_open, file=file)
        for name, _ in gogh_RGB_mapping:
            print(text_block(name), file=file)
        print(table_separator, file=file)
        for name, (R, G, B) in gogh_RGB_mapping:
            print(color_block(f'#{to_hex(R)}{to_hex(G)}{to_hex(B)}'), file=file)
        print(table_separator, file=file)
        for name, (R, G, B) in gogh_RGB_mapping:
            print(text_block(f'{to_byte(R)}/{to_byte(G)}/{to_byte(B)}'), file=file)
        print(table_separator, file=file)
        for name, (R, G, B) in gogh_RGB_mapping:
            print(text_block(f'#{to_hex(R)}{to_hex(G)}{to_hex(B)}'), file=file)
        print(table_close, file=file)
        print(medium_text('Normalized'), file=file)
        print(table_open, file=file)
        for name, _ in gogh_RGB_mapping:
            print(text_block(name), file=file)
        print(table_separator, file=file)
        for name, (R, G, B) in gogh_grayscale_RGB_mapping:
            print(color_block(f'rgb({to_byte(R)},{to_byte(G)},{to_byte(B)})'), file=file)
        print(table_separator, file=file)
        for name, (R, G, B) in gogh_grayscale_RGB_mapping:
            print(text_block(f'{to_byte(R)}/{to_byte(G)}/{to_byte(B)}'), file=file)
        print(table_separator, file=file)
        for name, (R, G, B) in gogh_grayscale_RGB_mapping:
            print(text_block(f'#{to_hex(R)}{to_hex(G)}{to_hex(B)}'), file=file)
        print(table_close, file=file)
        print(medium_text('Selected'), file=file)
        print(table_open, file=file)
        for name, _ in gogh_RGB_mapping:
            print(text_block(name), file=file)
        print(table_separator, file=file)
        for name, (R, G, B) in gogh_selected_RGB_mapping:
            print(color_block(f'rgb({to_byte(R)},{to_byte(G)},{to_byte(B)})'), file=file)
        print(table_separator, file=file)
        for name, (R, G, B) in gogh_selected_RGB_mapping:
            print(text_block(f'{to_byte(R)}/{to_byte(G)}/{to_byte(B)}'), file=file)
        print(table_separator, file=file)
        for name, (R, G, B) in gogh_selected_RGB_mapping:
            print(text_block(f'#{to_hex(R)}{to_hex(G)}{to_hex(B)}'), file=file)
        print(table_close, file=file)

        print(large_text('Script'), file=file)
        print(medium_text('Monokai.sublime-color-scheme'), file=file)
        text = ' \\<br />| '.join([
            f'sed -r "s/\\"({name})\\"(\\s*):(\\s*)\\"hsl\\(.*?\\)\\"/\\"\\1\\"\\2:\\3\\"rgb({to_byte(R)}, {to_byte(G)}, {to_byte(B)})\\"/g"'
            for i, (name, (R, G, B))
            in enumerate(sublime_grayscale_RGB_mapping) if (R, G, B) != sublime_RGB_mapping[i][1]
        ])
        print(small_text(f'cat Monokai.sublime-color-scheme \\<br />| {text}'), file=file)
        print(medium_text('.Xresources'), file=file)
        text = '<br />'.join([f'XTerm.VT100.{name}: rgb:{to_hex(R)}/{to_hex(G)}/{to_hex(B)}' for name, (R, G, B) in gogh_selected_RGB_mapping])
        print(small_text(text), file=file)

        print('</body></html>', file=file)
    webbrowser.open(file.name)
