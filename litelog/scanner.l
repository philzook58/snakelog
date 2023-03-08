%option reentrant

%{
#include "parser.tab.h"
/* seems like a bug that I have to do this, since flex
   should know prefix=lisp and match bison's LISPSTYPE */
#define YYSTYPE LITELOGSTYPE
int litelogerror(const char *msg);
/* add in a code block by the %options */
#define YY_EXIT_FAILURE ((void)yyscanner, EXIT_FAILURE)

/* add definitions down by words_callback */

void *litelogalloc(size_t size, void *yyscanner)
{
    (void) yyscanner;
    return malloc(size);
}

void *litelogrealloc(void * ptr, size_t size, void *yyscanner)
{
    (void) yyscanner;
    return realloc(ptr, size);
}

void litelogfree(void *ptr, void *yyscanner)
{
    (void) yyscanner;
    free(ptr);
}

%}

/* disable unused functions so we don't
   get compiler warnings about them */

%option noyywrap nounput noinput
%option noyyalloc noyyrealloc noyyfree

%option prefix="litelog"
/* use the pure parser calling convention */
%option reentrant bison-bridge
%option header-file="lex.litelog.h"

%%
"("                                   { return LPAREN; }
")"                                   { return RPAREN; }
","                                   { return COMMA; }
"."                                   { return DOT; }

":-"                                  { return IF; }

[\?a-zA-Z]|[_\?a-zA-Z][_\?a-zA-Z0-9]+ {
                                        yylval->str = strdup(yytext);
                                        return IDENT;
                                      }


%%
/*
[0-9]+[.][0-9]+                       { return yy::parser::make_FLOAT(yytext, yylloc); }
[0-9]+                                { return yy::parser::make_NUMBER(yytext, yylloc); }
*/