import itertools
import logging
import pathlib
import subprocess
import typing
from importlib import resources

logger = logging.getLogger(__name__)

DATA_NAMES = (".latexmkrc", "jupytex.sty")
GENERATED_PATTERNS = ("*.blocks", "*.hash", "*.timestamp", "*.code", "*.result")


def install(directory: pathlib.Path):
    logger.info(f"Installing Jupytex into {directory}")

    for name in DATA_NAMES:
        logger.info(f"Copying {name}")
        source = resources.open_text('jupytex', name).read()
        (directory / name).write_text(source)

    logger.info("Done!")


def uninstall(directory: pathlib.Path):
    logger.info(f"Uninstalling Jupytex from {directory}")

    for name in DATA_NAMES:
        logger.info(f"Removing {name}")

        resource_path = directory / name
        if resource_path.exists():
            resource_path.unlink()

    logger.info("Done!")


def make(sys_args: typing.List[str]):
    subprocess.call(["latexmk", "--shell-escape", *sys_args])


def clean(sys_args: typing.List[str], full: bool=False):
    clean_type = "-C" if full else "-c"
    subprocess.run(['latexmk', clean_type, *sys_args])
