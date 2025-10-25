SPL Vocabulary and Lexical Categories
=====================================

1. Overview
-----------
SPL is an imperative language designed for the course, supporting:
- Variables (scalars), arrays and matrices.
- Control: sequence, selection (if/else), iteration (while, for).
- Procedures/functions with parameters and return values.
- Basic types: integer (signed), boolean.

2. Lexical categories (tokens)
-----------------------------
- KEYWORDS: if, else, while, for, return, proc, begin, end, var, array, matrix, true, false
- IDENTIFIER: [A-Za-z_][A-Za-z0-9_]*
- INTEGER_LITERAL: [0-9]+ (decimal). Optionally: 0x[0-9A-Fa-f]+ (hex), 0b[01]+ (binary)
- STRING_LITERAL: "(\\.|[^"])*"
- OPERATORS: + - * / % == != < <= > >= && || ! := =
- PUNCTUATION: ( ) { } [ ] ; , :
- COMMENT: //.*  (single-line), /* ... */ (multi-line)

3. Regular expressions (POSIX/FLEX style)
-----------------------------------------
- DIGIT      [0-9]
- HEXDIGIT   [0-9A-Fa-f]
- ID         [A-Za-z_][A-Za-z0-9_]*
- INT_DEC    {DIGIT}+
- INT_HEX    0[xX]{HEXDIGIT}+
- INT_BIN    0[bB][01]+
- STRING     \"([^\"\\]|\\.)*\"

4. Example token rules (FLEX)
-----------------------------
%%
"if"            { return T_IF; }
"else"          { return T_ELSE; }
"while"         { return T_WHILE; }
"for"           { return T_FOR; }
"proc"          { return T_PROC; }
"return"        { return T_RETURN; }
"var"           { return T_VAR; }
"array"         { return T_ARRAY; }
"matrix"        { return T_MATRIX; }
"true"|"false" { yylval.boolean = strcmp(yytext, "true")==0; return T_BOOLEAN; }
{ID}             { yylval.str = strdup(yytext); return T_ID; }
{INT_HEX}        { yylval.integer = strtol(yytext, NULL, 16); return T_INT; }
{INT_BIN}        { yylval.integer = strtol(yytext+2, NULL, 2); return T_INT; }
{INT_DEC}        { yylval.integer = atoi(yytext); return T_INT; }
{STRING}         { yylval.str = strdup(yytext); return T_STRING; }
"//".*          { /* skip single-line comments */ }
"/*"([^*]|\*+[^*/])*"*/"   { /* skip block comment */ }
[ \t\r\n]+     { /* skip whitespace */ }
.                { return yytext[0]; }
%%

5. Notes
--------
- The assembler and preprocessor will share many lexical rules (identifiers, numbers, punctuation).
- The assembler uses a subset of these tokens (identifiers for labels/symbols, integer literals, directives like .data, .text, .global).

6. Next steps
-------------
- Map SPL AST nodes to sequences of assembly templates.
- Define calling convention and runtime layout for arrays/matrices.
- Implement full FLEX grammars (or use Python `lex.py` for faster prototyping).