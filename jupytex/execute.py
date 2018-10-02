#!/usr/bin/env python3

import argparse
import pathlib
import jupyter_client
import typing
import csv
import re
from textwrap import dedent
from pprint import pprint


class OutputResponse(typing.NamedTuple):
    text: str


class ErrorResponse(typing.NamedTuple):
    error_name: str
    error_value: str
    traceback: str


def find_kernel_name(kernel_spec_manager, language):
    for name, spec in kernel_spec_manager.get_all_specs().items():
        if spec['spec']['language'].lower() == language:
            return name
    raise ValueError(f"No kernel found for {language}")


def format_traceback(traceback):
    ansi_pattern = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return ansi_pattern.sub('', traceback)


def execute_statement(client, statement):
    message_id = client.execute(statement, allow_stdin=False)
    assert client.is_alive()

    status = 'busy'
    response = None

    while status != 'idle':
        try:
            message = client.get_iopub_msg(timeout=None)
        except Empty:
            continue

        message_type = message['header']['msg_type']

        if message_type == 'status':
            # If a status message concerning our request
            if message['parent_header'].get('msg_id') == message_id:
                status = message['content']['execution_state']

        elif message_type == 'stream':
            if message['content']['name'] == 'stdout':
                response = OutputResponse(message['content']['text'])

        elif message_type == 'error':
            content = message['content']
            response = ErrorResponse(content['ename'],
                                    content['evalue'],
                                    content['traceback'])
    return response


def unlink_kernel_config_files():
    # Unlink kernel config files
    cwd = pathlib.Path.cwd()
    for p in cwd.glob("kernel-*.json"):
        p.unlink()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('hash_file_path', type=pathlib.Path)
    args = parser.parse_args()

    # Hash file changed, so run code
    block_file_path = args.hash_file_path.parent / (args.hash_file_path.stem + ".blocks")

    kernel_spec_manager = jupyter_client.kernelspec.KernelSpecManager()
    kernel_manager = jupyter_client.MultiKernelManager()

    session_info_to_kernel_id = {}
    kernel_id_to_client = {}
    print(f"\u001b[0mHash must have changed for {block_file_path} code file; re-executing...")

    with open(block_file_path) as f:
        reader = csv.DictReader(f, fieldnames=['path', 'language', 'kernel', 'session'])
        for row in reader:
            path = block_file_path.parent / row['path']
            kernel_name = row['kernel']
            language = row['language']
            session_name = row['session']

            if not kernel_name:
                kernel_name = find_kernel_name(kernel_spec_manager, language)

            session_info = kernel_name, session_name
            try:
                kernel_id = session_info_to_kernel_id[session_info]
                client = kernel_id_to_client[kernel_id]

            except KeyError:
                session_info_to_kernel_id[session_info] = kernel_id = \
                kernel_manager.start_kernel(kernel_name=kernel_name)
                client = kernel_id_to_client[kernel_id] = \
                kernel_manager.get_kernel(kernel_id).client()
                client.start_channels()
                client.wait_for_ready(2)

            # Execute code
            raw_code = dedent(path.read_text())
            result = execute_statement(client, raw_code)

            # Exception occurred, write traceback and throw error
            if isinstance(result, ErrorResponse):
                clean_traceback = format_traceback(''.join(result.traceback))
                traceback_path = pathlib.Path(path.stem + ".traceback")
                traceback_path.write_text(clean_traceback)
                raise RuntimeError(clean_traceback)

            # Store code stdout response
            result_path = pathlib.Path(path.stem + ".result")
            output = result.text if isinstance(result, OutputResponse) else ''
            result_path.write_text(output)

    for client in kernel_id_to_client.values():
        client.shutdown()

    unlink_kernel_config_files()

    stamp_file_path = args.hash_file_path.parent / (args.hash_file_path.stem + ".timestamp")

    from time import time
    stamp_file_path.write_text(f"%{time()}")


if __name__ == "__main__":
    main()
