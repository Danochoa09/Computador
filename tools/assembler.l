/* assembler.l - skeleton FLEX for the assembler
   This lexer identifies labels, directives and operands and emits simple object format lines.
   It expects input in a simple assembly language (result of preprocessor).
*/
%{
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* helper: print INST lines or SYM lines to stdout */
%}

DIGIT   [0-9]
ID      [A-Za-z_][A-Za-z0-9_]*
HEX     0[xX][0-9A-Fa-f]+
BIN     0[bB][01]+
INT     {DIGIT}+

%%
".text"                { printf("--code\n"); }
".data"                { printf("--data\n"); }
".global"[ \t]+{ID}   { printf("SYM: %s,0,global\n", yytext+8); }
{ID}":"                { printf("LABEL: %s\n", yytext); }
{HEX}                  { printf("NUM: %s\n", yytext); }
{BIN}                  { printf("NUM: %s\n", yytext); }
{INT}                  { printf("NUM: %s\n", yytext); }
";".*                  { /* comment */ }
[ \t\r\n]+            { /* skip */ }
.                      { ECHO; }
%%

int main(int argc, char **argv) {
    yylex();
    return 0;
}
