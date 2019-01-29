import argparse
import pathlib

from .interface import write_blocks_hash, execute_blocks
from .tools import install, uninstall, make, clean


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(required=True, dest='command')

    # Install script
    install_parser = subparsers.add_parser("install")
    install_parser.add_argument("-d", "--directory", default=pathlib.Path.cwd(), type=pathlib.Path)
    install_parser.set_defaults(handler=install)

    # Uninstall script
    uninstall_parser = subparsers.add_parser("uninstall")
    uninstall_parser.add_argument("-d", "--directory", default=pathlib.Path.cwd(), type=pathlib.Path)
    uninstall_parser.set_defaults(handler=uninstall)

    # Cleaner script
    clean_parser = subparsers.add_parser("clean")
    clean_parser.add_argument("-f", "--full", action="store_true")
    clean_parser.set_defaults(handler=clean, requires_sys_args=True)

    # Make script
    make_parser = subparsers.add_parser("make")
    make_parser.set_defaults(handler=make, requires_sys_args=True)

    # Hash script
    hash_parser = subparsers.add_parser("hash")
    hash_parser.add_argument("-d", "--directory", default=pathlib.Path.cwd(), type=pathlib.Path)
    hash_parser.set_defaults(handler=write_blocks_hash)

    # Execute script
    execute_parser = subparsers.add_parser("execute")
    execute_parser.add_argument("hash_file_path", type=pathlib.Path)
    execute_parser.set_defaults(handler=execute_blocks)

    args, unknown_args = parser.parse_known_args()

    kwargs = vars(args)
    command = kwargs.pop("command")
    requires_sys_args = kwargs.pop("requires_sys_args", False)

    # Some args might require any uncaptured arguments
    if requires_sys_args:
        kwargs['sys_args'] = unknown_args

    elif unknown_args:
        parser.error("unrecognized arguments: {}".format(' '.join(unknown_args)))

    handler = kwargs.pop("handler")
    handler(**kwargs)


if __name__ == "__main__":
    main()
