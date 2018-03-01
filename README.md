# jupytex
Jupyter execution of Tex `code` environments
Currently this repository is awkward to install, which must be done by hand.


# How to use
After including `juyter.sty`, code environments can be declared with

```
\begin{code}{language}[opts]
    Some source code
\end{code}
```

Running latexmk with --shell-escape (required for the code hash utility) will lead to the following control flow

1. jupyter.sty declares dependency upon `\jobname.timetamp`
1. jupyter.sty macro writes code blocks to numbered .code files and attempts to include results 
1. code 'blocks' are written to a `\jobname.blocks` csv file
1. `watcher.py` is invoked for the written blocks file, and the md5 hash for all of the blocks is computed, and written to `\jobname.hash`. In future this should only be performed after the entire document has been processed, and per-kernel-session. 
1. If `\jobname.hash` has been modified, `execute.py` is invoked for the corresponding job, and the code blocks executed and results written to .result files. Code blocks which do not write to stdout write an empty results file. `\jobname.timestamp` is updated with new timestamp.
1. latexmk performs a new pass for the dependencies upon `\jobname.timestamp`

## Configuration
Each code block must be given a language. One can specify the Jupyter kernel name with a `kernel` key parameter, which will be used instead of the language if present. In addition, a `session` key may be passed to create a distinct kernel for associated with the kernel-session pair.
