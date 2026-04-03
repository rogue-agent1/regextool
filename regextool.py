#!/usr/bin/env python3
"""regextool - Regex tester, explainer, and pattern library.

Usage:
    regextool test "\\d{3}-\\d{4}" "555-1234 and 123-4567"
    regextool explain "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z]{2,}$"
    regextool library email
    regextool replace "\\bfoo\\b" "bar" "foo is not foobar"
    regextool split "\\s*,\\s*" "a, b,  c, d"
"""
import argparse
import re
import sys

LIBRARY = {
    "email": (r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$', "Email address"),
    "url": (r'https?://[^\s<>"{}|\\^`\[\]]+', "HTTP/HTTPS URL"),
    "ipv4": (r'\b(?:\d{1,3}\.){3}\d{1,3}\b', "IPv4 address"),
    "ipv6": (r'(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}', "IPv6 address (full)"),
    "phone-us": (r'\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}', "US phone number"),
    "date-iso": (r'\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])', "ISO date (YYYY-MM-DD)"),
    "time-24h": (r'(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?', "24-hour time"),
    "hex-color": (r'#(?:[0-9a-fA-F]{3}){1,2}\b', "Hex color (#RGB or #RRGGBB)"),
    "uuid": (r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', "UUID"),
    "semver": (r'\bv?(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[\w.]+)?(?:\+[\w.]+)?\b', "Semantic version"),
    "slug": (r'^[a-z0-9]+(?:-[a-z0-9]+)*$', "URL slug"),
    "mac": (r'(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}', "MAC address"),
    "credit-card": (r'\b(?:\d{4}[-\s]?){3}\d{4}\b', "Credit card number"),
    "jwt": (r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', "JWT token"),
    "domain": (r'\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b', "Domain name"),
    "ssn": (r'\b\d{3}-\d{2}-\d{4}\b', "US SSN (XXX-XX-XXXX)"),
    "zip-us": (r'\b\d{5}(?:-\d{4})?\b', "US ZIP code"),
}

TOKEN_EXPLAIN = {
    r'\d': "digit [0-9]",
    r'\D': "non-digit",
    r'\w': "word char [a-zA-Z0-9_]",
    r'\W': "non-word char",
    r'\s': "whitespace",
    r'\S': "non-whitespace",
    r'\b': "word boundary",
    r'\B': "non-word boundary",
    '.': "any character",
    '^': "start of string",
    '$': "end of string",
    '*': "0 or more (greedy)",
    '+': "1 or more (greedy)",
    '?': "0 or 1 (optional)",
    '*?': "0 or more (lazy)",
    '+?': "1 or more (lazy)",
    '??': "0 or 1 (lazy)",
}


def explain_regex(pattern: str) -> list[str]:
    """Break down regex into explained components."""
    explanations = []
    i = 0
    while i < len(pattern):
        ch = pattern[i]

        if ch == '\\' and i + 1 < len(pattern):
            token = pattern[i:i+2]
            desc = TOKEN_EXPLAIN.get(token, f"literal '{pattern[i+1]}'")
            explanations.append((token, desc))
            i += 2
        elif ch == '[':
            end = pattern.index(']', i) + 1
            charclass = pattern[i:end]
            explanations.append((charclass, f"character class {charclass}"))
            i = end
        elif ch == '(':
            if pattern[i:i+3] == '(?:':
                explanations.append(("(?:", "non-capturing group"))
                i += 3
            elif pattern[i:i+4] == '(?P<':
                end = pattern.index('>', i)
                name = pattern[i+4:end]
                explanations.append((pattern[i:end+1], f"named group '{name}'"))
                i = end + 1
            elif pattern[i:i+3] == '(?=':
                explanations.append(("(?=", "lookahead"))
                i += 3
            elif pattern[i:i+3] == '(?!':
                explanations.append(("(?!", "negative lookahead"))
                i += 3
            else:
                explanations.append(("(", "capturing group start"))
                i += 1
        elif ch == ')':
            explanations.append((")", "group end"))
            i += 1
        elif ch == '{':
            end = pattern.index('}', i) + 1
            quant = pattern[i:end]
            parts = quant[1:-1].split(',')
            if len(parts) == 1:
                explanations.append((quant, f"exactly {parts[0]} times"))
            elif parts[1] == '':
                explanations.append((quant, f"{parts[0]} or more times"))
            else:
                explanations.append((quant, f"{parts[0]} to {parts[1]} times"))
            i = end
        elif ch in TOKEN_EXPLAIN:
            explanations.append((ch, TOKEN_EXPLAIN[ch]))
            i += 1
        else:
            explanations.append((ch, f"literal '{ch}'"))
            i += 1

    return explanations


def cmd_test(args):
    try:
        pat = re.compile(args.pattern)
    except re.error as e:
        print(f"  ❌ Invalid regex: {e}", file=sys.stderr)
        sys.exit(1)

    matches = list(pat.finditer(args.text))
    print(f"  Pattern: {args.pattern}")
    print(f"  Text:    {args.text}")
    print(f"  Matches: {len(matches)}")
    print()

    for i, m in enumerate(matches):
        print(f"  [{i}] '{m.group()}' at {m.start()}-{m.end()}")
        if m.groups():
            for j, g in enumerate(m.groups(), 1):
                print(f"      Group {j}: '{g}'")
        if m.groupdict():
            for name, val in m.groupdict().items():
                print(f"      {name}: '{val}'")

    if not matches:
        print(f"  ❌ No matches")


def cmd_explain(args):
    print(f"  Pattern: {args.pattern}")
    print()
    tokens = explain_regex(args.pattern)
    for token, desc in tokens:
        print(f"  {token:>12s}  →  {desc}")


def cmd_library(args):
    if args.name:
        name = args.name.lower()
        if name in LIBRARY:
            pat, desc = LIBRARY[name]
            print(f"  {desc}")
            print(f"  Pattern: {pat}")
        else:
            print(f"  Unknown. Available: {', '.join(sorted(LIBRARY))}")
            sys.exit(1)
    else:
        print(f"  Available patterns ({len(LIBRARY)}):")
        for name, (pat, desc) in sorted(LIBRARY.items()):
            print(f"    {name:>15s}  {desc}")


def cmd_replace(args):
    try:
        result = re.sub(args.pattern, args.replacement, args.text)
    except re.error as e:
        print(f"  ❌ Invalid regex: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"  Before: {args.text}")
    print(f"  After:  {result}")


def cmd_split(args):
    try:
        parts = re.split(args.pattern, args.text)
    except re.error as e:
        print(f"  ❌ Invalid regex: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"  Parts ({len(parts)}):")
    for i, p in enumerate(parts):
        print(f"    [{i}] '{p}'")


def main():
    parser = argparse.ArgumentParser(description="Regex tester and explainer")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("test", help="Test regex against text")
    p.add_argument("pattern")
    p.add_argument("text")

    p = sub.add_parser("explain", help="Explain regex pattern")
    p.add_argument("pattern")

    p = sub.add_parser("library", help="Common regex patterns")
    p.add_argument("name", nargs="?")

    p = sub.add_parser("replace", help="Regex replace")
    p.add_argument("pattern")
    p.add_argument("replacement")
    p.add_argument("text")

    p = sub.add_parser("split", help="Regex split")
    p.add_argument("pattern")
    p.add_argument("text")

    args = parser.parse_args()
    {"test": cmd_test, "explain": cmd_explain, "library": cmd_library,
     "replace": cmd_replace, "split": cmd_split}[args.command](args)


if __name__ == "__main__":
    main()
