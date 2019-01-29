import argparse
import itertools
import logging
import pathlib
import subprocess
from importlib import resources

logger = logging.getLogger(__name__)

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
    logger.info(f"Installing Jupytex into {cwd}")

    for name in DATA_NAMES:
        logger.info(f"Copying {name}")
        source = resources.open_text('jupytex', name).read()
        (cwd / name).write_text(source)

    logger.info("Done!")


def uninstall():
    cwd = pathlib.Path.cwd()
    logger.info(f"Uninstalling Jupytex from {cwd}")

    for name in DATA_NAMES:
        logger.info(f"Removing {name}")

        resource_path = cwd / name
        if resource_path.exists():
            resource_path.unlink()

    logger.info("Done!")
