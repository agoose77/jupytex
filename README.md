# JupyTeX
Provides Jupyter-backed execution of LaTeX `code` environments, and embeds the results. Similar in concept to [PythonTex](https://github.com/gpoore/PythonTex), but focuses on code _execution_, and avoids any language specific features.

## How to use
1. Install JupyTeX with `pip install git+https://github.com/agoose77/jupytex.git#egg=jupytex`
2. Run `jupytex install` in LaTeX project directory (or provide an install directory with `-d DIR`) to create the necessary `.latexmkrc` and `jupytex.sty` files
3. Add `\usepackage{jupytex}` to the document header
4. Declare code environments with
    ```latex
    \begin{code}{language}[opts]
        Some source code
    \end{code}
    ```
    See the configuration section for valid options in `opts`.
5. Run `jupytex make` (which is a pass-through to `latexmk --shell-escape`) to invoke `latexmk`.
6. Run `jupytex clean` (which is a pass-through to `latexmk -c` or `latexmk -C`) to remove both LaTeX and JupyTex-related run files.
7. Run `jupytex uninstall` in LaTeX project directory (or provide an install directory with `-d DIR`) to remove the installed `.latexmkrc` and `jupytex.sty` files
### Example Python Script
```latex
\begin{code}{python}[kernel=python3]
    print("$x + y = z$")
\end{code}
```
## JupyTeX flow control
1. `jupytex.sty` declares dependency upon `\jobname.timestamp`
1. `jupytex.sty` macro writes code blocks to numbered `.code` files and attempts to include results
1. Code 'blocks' are written to a `\jobname.blocks` csv file
1. `jupytex hash` is invoked to calculate the md5 hash for all of the blocks, which is written to `\jobname.hash`. In future this should only be performed per-kernel-session.
1. If `\jobname.hash` has been modified, `jupytex execute` is invoked for the corresponding job, the code blocks executed, and results written to `.result` files, and errors to `.traceback` files. Code blocks which do not write to stdout write an empty results file. `\jobname.timestamp` is updated with new timestamp.
1. `latexmk` performs a new pass for the dependencies upon `\jobname.timestamp`

## Configuration
Each code block must be given a language. One can specify the Jupyter kernel name with a `kernel` key parameter, which will be used instead of the language if present. In addition, a `session` key may be passed to create a distinct kernel for associated with the kernel-session pair. One can also access an existing kernel, using the `kernel` parameter, passing the name of a connection file.
