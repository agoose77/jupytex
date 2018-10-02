#!/usr/bin/env python3

"""Watch for any changed files in current job, and indicate job hash updated where necessary"""

import pathlib
import csv
import hashlib
from textwrap import dedent

def main():
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


if __name__ == "__main__":
    main()
