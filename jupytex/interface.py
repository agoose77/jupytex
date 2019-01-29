import csv
import hashlib
import logging
import pathlib
import queue
import re
import typing
from textwrap import dedent
from time import time

import jupyter_client

DATA_NAMES = (".latexmkrc", "jupytex.sty")
GENERATED_PATTERNS = ("*.blocks", "*.hash", "*.timestamp", "*.code", "*.result")
logger = logging.getLogger(__name__)

SESSION_INFO_TYPE = typing.Tuple[str, typing.Optional[str]]


class CodeBlock(typing.NamedTuple):
    path: pathlib.Path
    language: str
    session: str
    kernel: str


class OutputResponse(typing.NamedTuple):
    text: str


class ErrorResponse(typing.NamedTuple):
    error_name: str
    error_value: str
    traceback: str


def write_blocks_hash(directory: pathlib.Path):
    """Watch for any changed files in current job, and indicate job hash updated where necessary.

    :param directory: Path to directory containing blocks files
    """
    for code_file_path in directory.glob("*.blocks"):
        total_hash = hashlib.md5()

        with open(code_file_path) as f:
            reader = csv.DictReader(f, fieldnames=['path', 'language', 'kernel', 'session'])
            for row in reader:
                raw_contents = dedent((directory / row['path']).read_text())
                total_hash.update(raw_contents.encode('utf-8'))

        hash_file_path = code_file_path.with_suffix(".hash")
        hash_file_path.write_text(total_hash.hexdigest())


def format_traceback(traceback: str) -> str:
    ansi_pattern = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return ansi_pattern.sub('', traceback)


def unlink_kernel_config_files():
    # Unlink kernel config files
    cwd = pathlib.Path.cwd()
    for p in cwd.glob("kernel-*.json"):
        p.unlink()


def iter_code_blocks(file_path: pathlib.Path) -> typing.Iterator[CodeBlock]:
    """Yield CodeBlock instances from a .blocks file

    :param file_path: Path to blocks file
    """
    with open(file_path) as f:
        reader = csv.DictReader(f, fieldnames=['path', 'language', 'kernel', 'session'])
        for row in reader:
            path = file_path.parent / row['path']
            kernel = row['kernel']
            language = row['language']
            session = row['session']
            yield CodeBlock(path, language, session, kernel)


class SessionKernelManager:
    """Manage lifetime of kernels associated with different session IDs."""

    def __init__(self):
        self.kernel_spec_manager = jupyter_client.kernelspec.KernelSpecManager()
        self.kernel_manager = jupyter_client.MultiKernelManager()

        self._session_info_to_client: typing.Dict[SESSION_INFO_TYPE, jupyter_client.KernelClient] = {}
        self._session_info_to_kernel_id: typing.Dict[SESSION_INFO_TYPE, str] = {}

    @property
    def session_infos(self) -> typing.Set[str]:
        return set(self._session_info_to_client)

    @property
    def owned_session_infos(self) -> typing.Set[str]:
        return set(self._session_info_to_kernel_id)

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

    def execute_code(self, session_info: SESSION_INFO_TYPE, code: str):
        """Execute code in the kernel associated with the given kernel ID.

        :param session_info: session info object
        :param code: string of code to execute
        :return: response from kernel
        """
        client = self._session_info_to_client[session_info]
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

    def find_or_create_session(self, kernel_name: str, session_name: str = None) -> SESSION_INFO_TYPE:
        """
        Find the existing kernel for a given kernel name and session name, or create.

        :param kernel_name: name of kernel
        :param session_name: name of session or None
        :return: session info
        """
        session_info = kernel_name, session_name
        try:
            client = self._session_info_to_client[session_info]

        except KeyError:
            # Try and load existing kernel from kernel name
            try:
                connection_file = jupyter_client.find_connection_file(kernel_name)
            except IOError:
                kernel_id = self.kernel_manager.start_kernel(kernel_name=kernel_name)
                client = self.kernel_manager.get_kernel(kernel_id).client()
            else:
                client = jupyter_client.BlockingKernelClient()
                client.load_connection_file(connection_file)

            client.start_channels()
            client.wait_for_ready(2)
            self._session_info_to_client[session_info] = client

        return session_info

    def close_session(self, session_info: SESSION_INFO_TYPE):
        """Close kernel with given ID.

        :param session info: session info
        :return:
        """
        client = self._session_info_to_client[session_info]
        client.shutdown()

        # Wait for shutdown reply
        while True:
            try:
                message = client.get_iopub_msg(timeout=None)
            except queue.Empty:
                continue
            if message["msg_type"] == "shutdown_reply":
                return


def process_blocks(session_kernel_manager: SessionKernelManager, block_file_path: pathlib.Path):
    for code_block in iter_code_blocks(block_file_path):
        kernel_name = code_block.kernel
        if not kernel_name:
            kernel_name = session_kernel_manager.find_kernel_name(code_block.language)

        session = session_kernel_manager.find_or_create_session(kernel_name, code_block.session)

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
            traceback = '\n'.join(result.traceback)
            stderr_path.write_text(format_traceback(traceback))
            raise RuntimeError(
                f"Error in executing code for kernel={kernel_name}, session={code_block.session or None}:\n{traceback}")

        # Store code stdout response
        output = result.text if isinstance(result, OutputResponse) else ''
        stdout_path.write_text(output)


def execute_blocks(hash_file_path: pathlib.Path):
    """Execute the code blocks referenced in a blocks file.

    This function is called by latexmk when the hash file (given on the commandline) is modified.

    :param hash_file_path: Path to .hash file
    """
    block_file_path = hash_file_path.with_suffix(".blocks")
    logger.info(f"Hash must have changed for {block_file_path} code file; re-executing...")

    session_kernel_manager = SessionKernelManager()

    try:
        process_blocks(session_kernel_manager, block_file_path)

    finally:
        # Close all running kernels
        for session_info in session_kernel_manager.owned_session_infos:
            session_kernel_manager.close_session(session_info)

        unlink_kernel_config_files()

    # Update timestamp dependency file
    stamp_file_path = hash_file_path.with_suffix(".timestamp")
    stamp_file_path.write_text(f"%{time()}")
