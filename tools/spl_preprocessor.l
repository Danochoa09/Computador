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

/* Very small macro table (linked list) for demo */
struct macro { char *name; char *value; struct macro *next; } *macros = NULL;

void add_macro(const char *name, const char *value) {
    struct macro *m = malloc(sizeof(*m));
    m->name = strdup(name);
    m->value = strdup(value);
    m->next = macros;
    macros = m;
}

char *lookup_macro(const char *name) {
    for (struct macro *m = macros; m; m = m->next) {
        if (strcmp(m->name, name) == 0) return m->value;
    }
    return NULL;
}
%}

%%
"#include"[ \t]+\"[^"]+\"    {
    /* very simple include handling: print a comment with filename */
    char *fn = strdup(yytext);
    printf("/* included: %s */\n", fn);
}
"#define"[ \t]+[A-Za-z_][A-Za-z0-9_]*[ \t]+[^\r\n]+  {
    /* parse macro definition and store - simplistic */
    /* This is a placeholder; full implementation should parse properly */
    printf("/* macro defined: %s */\n", yytext);
}
"//".*                        { /* skip single-line comments */ }
"/\*"([^*]|\*+[^*/])*"*/"  { /* skip block comment */ }
[ \t\r\n]+                    { ECHO; }
.                              { ECHO; }
%%

int main(int argc, char **argv) {
    yylex();
    return 0;
}
