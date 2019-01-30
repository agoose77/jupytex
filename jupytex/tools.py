import logging
import pathlib
import subprocess
import typing
import importlib_resources as resources

from . import data

logger = logging.getLogger(__name__)


def get_resource_names(package: resources.Package) -> typing.Iterator[str]:
    for name in resources.contents(package):
        if name == "__init__.py":
            continue

        if resources.is_resource(package, name):
            yield name


def install(directory: pathlib.Path):
    logger.info(f"Installing Jupytex into {directory}")

    for name in get_resource_names(data):
        logger.info(f"Copying {name}")
        source = resources.read_text(data, name)
        (directory / name).write_text(source)

    logger.info("Done!")


def uninstall(directory: pathlib.Path):
    logger.info(f"Uninstalling Jupytex from {directory}")
    for name in get_resource_names(data):
        logger.info(f"Removing {name}")
        resource_path = directory / name
        if resource_path.exists():
            resource_path.unlink()

    logger.info("Done!")


def make(sys_args: typing.List[str]):
    subprocess.call(["latexmk", "--shell-escape", *sys_args])


def clean(sys_args: typing.List[str], full: bool = False):
    clean_type = "-C" if full else "-c"
    subprocess.run(["latexmk", clean_type, *sys_args])
