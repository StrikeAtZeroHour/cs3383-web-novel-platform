"""Minimal .po -> .mo compiler using only the standard library.

Why: the Windows environment used for this project has no GNU gettext
(`msgfmt`) on PATH, so `manage.py compilemessages` cannot run. This is a
faithful port of CPython's Tools/i18n/msgfmt.py logic, sufficient for the
single-plural-form zh_Hant catalogue in this repository.

Usage:
    python -m tools.compile_po locale/zh_Hant/LC_MESSAGES/django.po

This is an environment/setup utility, not application code, and changes no
production behaviour.
"""

import ast
import struct
import sys


def _parse(path):
    messages = {}
    msgid = msgstr = ""
    in_msgid = in_msgstr = False
    have_entry = False

    with open(path, "rb") as fh:
        for raw in fh:
            line = raw
            if line.strip() == b"":
                if have_entry:
                    messages[msgid] = msgstr
                msgid = msgstr = ""
                in_msgid = in_msgstr = False
                have_entry = False
                continue
            if line.lstrip().startswith(b"#"):
                continue
            if line.startswith(b"msgid "):
                in_msgid = True
                in_msgstr = False
                have_entry = True
                msgid = _decode(line[6:].strip())
            elif line.startswith(b"msgstr "):
                in_msgstr = True
                in_msgid = False
                have_entry = True
                msgstr = _decode(line[7:].strip())
            elif line.startswith(b'"'):
                text = _decode(line.strip())
                if in_msgid:
                    msgid += text
                elif in_msgstr:
                    msgstr += text
    if have_entry:
        messages[msgid] = msgstr
    # NOTE: the "" header entry must be kept; it carries the charset declaration
    # that Python's gettext reads to decode the catalogue as UTF-8.
    return messages


def _decode(token):
    return ast.literal_eval(token.decode("utf-8"))


def _build(messages):
    keys = sorted(messages)
    offsets = []
    ids = strs = b""
    for key in keys:
        msgid = key.encode("utf-8")
        msgstr = messages[key].encode("utf-8")
        offsets.append((len(ids), len(msgid), len(strs), len(msgstr)))
        ids += msgid + b"\x00"
        strs += msgstr + b"\x00"

    keystart = 7 * 4 + 16 * len(keys)
    valuestart = keystart + len(ids)
    koffsets = []
    voffsets = []
    for o1, l1, o2, l2 in offsets:
        koffsets += [l1, o1 + keystart]
        voffsets += [l2, o2 + valuestart]
    offset_table = struct.pack("I" * len(koffsets), *koffsets)
    value_table = struct.pack("I" * len(voffsets), *voffsets)
    return (
        struct.pack("Iiiiiii", 0x950412DE, 0, len(keys), 7 * 4, 7 * 4 + len(keys) * 8, 0, 0)
        + offset_table
        + value_table
        + ids
        + strs
    )


def main(argv):
    if len(argv) != 2:
        print("usage: compile_po <file.po>", file=sys.stderr)
        return 2
    po_path = argv[1]
    mo_path = po_path[:-3] + ".mo"
    messages = _parse(po_path)
    data = _build(messages)
    with open(mo_path, "wb") as fh:
        fh.write(data)
    print(f"compiled {len(messages)} messages into {mo_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
