/* assembler.l - skeleton FLEX for the assembler
   This lexer identifies labels, directives and operands and emits simple object format lines.
   It expects input in a simple assembly language (result of preprocessor).
*/
%{
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <errno.h>

/* Assembler wrapper: delegate to Python assembler (`tools/assembler_from_as.py`).
    The generated executable will exec python so stdin/stdout are preserved for
    piping. If execlp fails we fallback to system() as degraded mode.
*/
%}

DIGIT   [0-9]
ID      [A-Za-z_][A-Za-z0-9_]*
HEX     0[xX][0-9A-Fa-f]+
BIN     0[bB][01]+
INT     {DIGIT}+

%%
".text"                { ECHO; }
".data"                { ECHO; }
".global"[ \t]+{ID}   { ECHO; }
{ID}":"                { ECHO; }
{HEX}                  { ECHO; }
{BIN}                  { ECHO; }
{INT}                  { ECHO; }
";".*                  { /* comment */ }
[ \t\r\n]+            { /* skip */ }
.                      { ECHO; }
%%

int main(int argc, char **argv) {
    /* Call Python assembler. If possible pass a basename to allow the
       assembler to write a .meta.json next to the image. If argv[1] exists
       we pass it through. */
    const char *pycode =
        "import sys; from tools.assembler_from_as import assemble_text; txt=sys.stdin.read(); "
        "maybe=assemble_text(txt);\n"
        "if isinstance(maybe, tuple) and len(maybe)==2:\n"
        "  lines,meta=maybe\n"
        "  sys.stdout.write('\n'.join(lines))\n"
        "  # write meta if assembler received a basename arg\n"
        "  try:\n"
        "    import json, os, sys as _sys\n"
        "    if meta:\n"
        "      if len(_sys.argv)>1:\n"
        "        import pathlib\n"
        "        p=pathlib.Path(_sys.argv[1]).with_suffix('.meta.json')\n"
        "        p.write_text(json.dumps(meta, indent=2), encoding='utf-8')\n"
        "      else:\n"
        "        open('assembler.meta.json','w',encoding='utf-8').write(json.dumps(meta,indent=2))\n"
        "  except Exception:\n"
        "    pass\n"
        "else:\n"
        "  # old behaviour: maybe is a list
        "  try:\n"
        "    for l in maybe:\n"
        "      sys.stdout.write(str(l)+'\n')\n"
        "  except Exception:\n"
        "    sys.stdout.write(str(maybe)+'\n')\n";

    /* execute python with -c and pass optional basename as arg */
    if (argc > 1) {
        execlp("python", "python", "-c", pycode, argv[1], (char *)NULL);
    } else {
        execlp("python", "python", "-c", pycode, (char *)NULL);
    }
    fprintf(stderr, "execlp failed: %s\n", strerror(errno));
    /* fallback to system() if execlp fails */
    char cmd[16384];
    if (argc > 1) {
        snprintf(cmd, sizeof(cmd), "python -c \"%s\" %s", pycode, argv[1]);
    } else {
        snprintf(cmd, sizeof(cmd), "python -c \"%s\"", pycode);
    }
    return system(cmd);
}
