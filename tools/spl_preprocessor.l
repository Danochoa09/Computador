/* spl_preprocessor.l - skeleton FLEX file for SPL preprocessor
   Responsibilities:
   - Handle #include "file.spl"
   - Handle simple macro definitions: #define NAME replacement
   - Remove comments and output the processed source to stdout

   This is a skeleton: replace action bodies with desired logic.
*/
%{
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <errno.h>

/* This FLEX lexer is a thin wrapper that delegates the real preprocessing
   work to the Python module `tools.parser_spl`. The generated executable
   will replace itself with a Python process so stdin/stdout are preserved
   and the pipeline `cat file | spl_preprocessor.exe | assembler.exe` works.

   If execlp fails we fall back to calling system() as a degraded mode.
*/
%}

%%
"#include"[ \t]+\"[^\"]+\"    { /* passthrough - delegate to Python */ ECHO; }
"#define"[ \t]+[A-Za-z_][A-Za-z0-9_]*[ \t]+[^\r\n]+  { /* passthrough */ ECHO; }
"//".*                        { /* skip single-line comments */ }
"/\*"([^*]|\*+[^*/])*"*/"  { /* skip block comment */ }
[ \t\r\n]+                    { ECHO; }
.                              { ECHO; }
%%

int main(int argc, char **argv) {
    /* Replace this process with `python -c "..."` which reads stdin and
       writes the preprocessed output to stdout by calling the Python
       pipeline function. Using execlp preserves stdin/stdout for pipes. */
    const char *pycode = "import sys; from tools.parser_spl import compile_high_level; txt=sys.stdin.read(); sys.stdout.write(compile_high_level(txt))";

    /* Try to replace process */
    execlp("python", "python", "-c", pycode, (char *)NULL);

    /* If we reach here execlp failed; fall back to system() as degraded mode */
    fprintf(stderr, "execlp failed: %s\n", strerror(errno));
    char cmd[4096];
    snprintf(cmd, sizeof(cmd), "python -c \"%s\"", pycode);
    return system(cmd);
}
