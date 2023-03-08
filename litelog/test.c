#include <stdio.h>
#include <stdlib.h>

#define YYSTYPE LITELOGSTYPE
#include "parser.tab.h"
#include "lex.litelog.h"

int main()
{
    int i;
    struct sexpr *expr;
    yyscan_t scanner;
    YY_BUFFER_STATE buf;

    if ((i = liteloglex_init(&scanner)) != 0)
        exit(i);

    char *test = "foo(bar,biz) :- flum(), flim(). baz(boz).";
    // char *test = "baz().";
    buf = litelog_scan_string(test, scanner);
    int e = litelogparse(scanner);
    printf("Code = %d\n", e);
    if (e == 0) // success
    {
        // sexpr_print(expr, 0);
        // sexpr_free(expr);
    }

    liteloglex_destroy(scanner);
    return 0;
    // yyparse();
}