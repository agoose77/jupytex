import pathlib
import itertools
import argparse
import subprocess
from importlib import resources

DATA_NAMES = (".latexmkrc", "jupytex.sty")
GENERATED_PATTERNS = ("*.blocks", "*.hash", "*.timestamp", "*.code", "*.result")


def clean():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--full", action='store_true')
    args = parser.parse_args()

    cwd = pathlib.Path.cwd()

    to_remove = itertools.chain.from_iterable(
        (cwd.glob(p) for p in GENERATED_PATTERNS))
    for path in to_remove:
        path.unlink()

    if args.full:
        subprocess.run(['latexmk', '-c'])


def install():
    cwd = pathlib.Path.cwd()

    print(f"Installing Jupytex into {cwd}")

    for name in DATA_NAMES:
        print(f"Copying {name}")
        source = resources.open_text('jupytex', name).read()
        target =  (cwd / name)
        target.write_text(source)

    print("Done!")
