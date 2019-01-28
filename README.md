# JupyTeX
Jupyter execution of LaTeX `code` environments

## How to use
1. Install JupyTeX `pip install git+https://github.com/agoose77/jupytex.git#egg=jupytex`
2. Run `jupytex-install` in LaTeX project directory
3. Add `\usepackage{jupytex}` to the document header
4. Declare code environments with
```
\begin{code}{language}[opts]
    Some source code
\end{code}
```
. See the configuration section for valid options in `opts`.
5. Run `jupytex-make` (which is a pass-through to `latexmk --shell-escape`)
6. Run `jupytex-clean` to remove JupyTex-related run files.

## JupyTeX flow control
1. `jupytex.sty` declares dependency upon `\jobname.timetamp`
1. `jupytex.sty` macro writes code blocks to numbered .code files and attempts to include results
1. Code 'blocks' are written to a `\jobname.blocks` csv file
1. `jupytex-watcher` is invoked for the written blocks file, and the md5 hash for all of the blocks is computed, and written to `\jobname.hash`. In future this should only be performed after the entire document has been processed, and per-kernel-session.
1. If `\jobname.hash` has been modified, `jupytex-execute` is invoked for the corresponding job, the code blocks executed and results written to .result files. Code blocks which do not write to stdout write an empty results file. `\jobname.timestamp` is updated with new timestamp.
1. latexmk performs a new pass for the dependencies upon `\jobname.timestamp`

## Configuration
Each code block must be given a language. One can specify the Jupyter kernel name with a `kernel` key parameter, which will be used instead of the language if present. In addition, a `session` key may be passed to create a distinct kernel for associated with the kernel-session pair.
