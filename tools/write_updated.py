#!/usr/bin/env python3
"""
Write the date the footer shows as "Updated YYYY-MM-DD".

  Runs before every render (project: pre-render in _quarto.yml).

The date is the committer date of the last commit (git log -1 --format=%cs),
not the date of the render, so rendering the same commit twice gives the same
pages. It goes into _variables.yml, which the footer reads with
{{< var updated >}}. That file is generated, so it is gitignored.
"""
import pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "_variables.yml"

def main():
    try:
        date = subprocess.run(["git", "log", "-1", "--format=%cs"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        date = ""
    if not date:
        if OUT.exists():
            print("write_updated: no git history here; keeping _variables.yml as it is",
                  file=sys.stderr)
            return
        sys.exit("write_updated: no git history to take the date from")
    text = ("# Written by tools/write_updated.py before every render. Do not edit.\n"
            f'updated: "{date}"\n')
    # Only write on a change, so a running preview is not sent round in a loop.
    if not OUT.exists() or OUT.read_text() != text:
        OUT.write_text(text)

if __name__ == "__main__":
    main()
