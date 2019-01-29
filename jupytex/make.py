import argparse
import csv
import hashlib
import pathlib
import queue
import re
import subprocess
import sys
import typing
from textwrap import dedent
from time import time
import logging

import jupyter_client

DATA_NAMES = (".latexmkrc", "jupytex.sty")
GENERATED_PATTERNS = ("*.blocks", "*.hash", "*.timestamp", "*.code", "*.result")
logger = logging.getLogger(__name__)


def make():
    sys_args = sys.argv[1:]
    subprocess.call(["latexmk", "--shell-escape", *sys_args])


def write_hash():
    """Watch for any changed files in current job, and indicate job hash updated where necessary"""
    cwd = pathlib.Path.cwd()
    for code_file_path in cwd.glob("*.blocks"):
        total_hash = hashlib.md5()

        with open(code_file_path) as f:
            reader = csv.DictReader(f, fieldnames=['path', 'language', 'kernel', 'session'])
            for row in reader:
                path = cwd / row['path']
                raw_contents = dedent(path.read_text())
                total_hash.update(raw_contents.encode('utf-8'))

        hash_file_path = code_file_path.parent / (code_file_path.stem + ".hash")
        hash_file_path.write_text(total_hash.hexdigest())


class CodeBlock(typing.NamedTuple):
    path: pathlib.Path
    language: str
    session: str = None
    kernel: str = None


class OutputResponse(typing.NamedTuple):
    text: str


class ErrorResponse(typing.NamedTuple):
    error_name: str
    error_value: str
    traceback: str


def format_traceback(traceback):
    ansi_pattern = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return ansi_pattern.sub('', traceback)


def unlink_kernel_config_files():
    # Unlink kernel config files
    cwd = pathlib.Path.cwd()
    for p in cwd.glob("kernel-*.json"):
        p.unlink()


def iter_code_blocks(block_file_path: pathlib.Path) -> typing.Iterator[CodeBlock]:
    with open(block_file_path) as f:
        reader = csv.DictReader(f, fieldnames=['path', 'language', 'kernel', 'session'])
        for row in reader:
            path = block_file_path.parent / row['path']
            kernel = row['kernel']
            language = row['language']
            session = row['session']
            yield CodeBlock(path, language, session, kernel)


SESSION_INFO_TYPE = typing.Tuple[str, typing.Optional[str]]


class SessionKernelManager:
    """Manage lifetime of kernels associated with different session IDs."""

    def __init__(self):
        self.kernel_spec_manager = jupyter_client.kernelspec.KernelSpecManager()
        self.kernel_manager = jupyter_client.MultiKernelManager()

        self._session_info_to_kernel_id: typing.Dict[SESSION_INFO_TYPE, str] = {}
        self._kernel_id_to_session: typing.Dict[str, typing.Tuple[SESSION_INFO_TYPE, jupyter_client.KernelClient]] = {}

    @property
    def kernel_ids(self) -> typing.Set[str]:
        return set(self._kernel_id_to_session)

    def find_kernel_name(self, language: str) -> str:
        """Find the name of the kernel associated with a given language.

        :param language: code language
        :return: the associated kernel name
        """
        language_to_name = {s['spec']['language'].lower(): n for n, s in
                            self.kernel_spec_manager.get_all_specs().items()}
        try:
            return language_to_name[language]
        except KeyError:
            raise ValueError(f"No kernel found for {language}. Available kernels: {[*language_to_name]}")

    def execute_code(self, kernel_id: str, code: str):
        """Execute code in the kernel associated with the given kernel ID.

        :param kernel_id: ID of appropriate kernel
        :param code: string of code to execute
        :return: response from kernel
        """
        _, client = self._kernel_id_to_session[kernel_id]
        message_id = client.execute(code, allow_stdin=False)
        assert client.is_alive()

        status = 'busy'
        response = None

        while status != 'idle':
            try:
                message = client.get_iopub_msg(timeout=None)
            except queue.Empty:
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

    def find_or_create_kernel_id(self, kernel_name: str, session_name: str = None) -> str:
        """
        Find the existing kernel for a given kernel name and session name, or create.

        :param kernel_name: name of kernel
        :param session_name: name of session or None
        :return: ID of kernel
        """
        session_info = kernel_name, session_name

        try:
            kernel_id = self._session_info_to_kernel_id[session_info]

        except KeyError:
            self._session_info_to_kernel_id[session_info] = kernel_id = self.kernel_manager.start_kernel(
                kernel_name=kernel_name)
            client = self.kernel_manager.get_kernel(kernel_id).client()
            self._kernel_id_to_session[kernel_id] = session_info, client
            client.start_channels()
            client.wait_for_ready(2)

        return kernel_id

    def close_kernel(self, kernel_id: str):
        """Close kernel with given ID.

        :param kernel_id: ID of kernel
        :return:
        """
        session_info, client = self._kernel_id_to_session.pop(kernel_id)
        del self._session_info_to_kernel_id[session_info]
        client.shutdown()


def execute():
    """Execute the code blocks referenced in a blocks file.

    This function is called by latexmk when the hash file (given on the commandline) is modified.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('hash_file_path', type=pathlib.Path)
    args = parser.parse_args()

    # Hash file changed, so run code
    block_file_path = args.hash_file_path.parent / (args.hash_file_path.stem + ".blocks")
    logger.info(f"Hash must have changed for {block_file_path} code file; re-executing...")

    session_kernel_manager = SessionKernelManager()
    for code_block in iter_code_blocks(block_file_path):
        kernel_name = code_block.kernel
        if not kernel_name:
            kernel_name = session_kernel_manager.find_kernel_name(code_block.language)

        session = session_kernel_manager.find_or_create_kernel_id(kernel_name, code_block.session)

        # Execute code
        raw_code = dedent(code_block.path.read_text())
        result = session_kernel_manager.execute_code(session, raw_code)

        # Prepare result files
        stderr_path = code_block.path.with_suffix(".traceback")
        if stderr_path.exists():
            stderr_path.unlink()

        stdout_path = code_block.path.with_suffix(".result")
        if stdout_path.exists():
            stdout_path.unlink()

        # Exception occurred, write traceback and throw error
        if isinstance(result, ErrorResponse):
            clean_traceback = format_traceback(''.join(result.traceback))
            stderr_path.write_text(clean_traceback)
            raise RuntimeError(clean_traceback)

        # Store code stdout response
        output = result.text if isinstance(result, OutputResponse) else ''
        stdout_path.write_text(output)

    # Close all running kernels
    for kernel_id in session_kernel_manager.kernel_ids:
        session_kernel_manager.close_kernel(kernel_id)

    # Update timestamp dependency file
    stamp_file_path = args.hash_file_path.parent / (args.hash_file_path.stem + ".timestamp")
    stamp_file_path.write_text(f"%{time()}")

    unlink_kernel_config_files()
