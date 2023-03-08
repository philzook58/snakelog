// https://begriffs.com/posts/2021-11-28-practical-parsing.html

%define api.pure true
%define parse.error verbose
%define api.prefix {litelog}

%code requires {
    #include <stdio.h>
    #include <stdlib.h>
   // #include "lex.litelog.h"
}

%code {
	// int litelogerror(void * yylval, char const *msg);
    //int yylex(void);
  int litelogerror(void *foo, char const *msg);
	int liteloglex(void *lval, const void *s);
}

%param {void *scanner}

%token END 0                     "end of file"
%token <std::string> STRING      "symbol"
%token <std::string> IDENT       "identifier"
%token <std::string> NUMBER      "number"
%token <std::string> UNSIGNED    "unsigned number"
%token <std::string> FLOAT       "float"

%token IF                        ":-"
%token UNDERSCORE                "_"
%token LPAREN                    "("
%token RPAREN                    ")"
%token COMMA                     ","
%token DOT                       "."

/*
%type <Mov<Own<ast::Argument>>>                arg
%type <Mov<VecOwn<ast::Argument>>>             arg_list
%type <Mov<Own<ast::Atom>>>                    atom
%type <Mov<RuleBody>>                          body
%type <Mov<RuleBody>>                          conjunction
%type <Mov<Own<ast::Clause>>>                  fact
%type <Mov<VecOwn<ast::Atom>>>                 head
%type <Mov<ast::QualifiedName>>                qualified_name
%type <Mov<VecOwn<ast::Argument>>>             non_empty_arg_list
%type <Mov<VecOwn<ast::Clause>>>               rule
%type <Mov<RuleBody>>                          term
*/

%union
{
	int num;
	char *str;
	struct sexpr *node;
}

/* -- Grammar -- */
%%

%start program;

/**
 * Program
 */
program
  : unit
  ;

/**
 * Top-level Program Elements
 */
unit
  : %empty
    { }
  | unit rule
    {
      //for (auto&& cur : $rule   )
       // driver.addClause(std::move(cur));
    }
  | unit fact
    {
      //driver.addClause($fact);
    }

qualified_name
  : IDENT
    {
      //$$ = $IDENT;
    }
  ;

/**
 * Fact
 */
fact
  : atom DOT
    {
      //$$ = mk<ast::Clause>($atom, Mov<VecOwn<ast::Literal>> {}, nullptr, @$);
    }
  ;


/**
 * Rule Definition
 */
rule
  : head[heads] IF body DOT
    {
        /*
      auto bodies = $body->toClauseBodies();
      for (auto&& head : $heads) {
        for (auto&& body : bodies) {
          auto cur = clone(body);
          cur->setHead(clone(head));
          cur->setSrcLoc(@$);
          $$.push_back(std::move(cur));
        }
      }*/
    }
  ;


/**
 * Rule Head
 */
head
  : atom
    {
      //$$.push_back($atom);
    }
  | head COMMA atom
    {
      //$$ = $1; $$.push_back($atom);
    }
  ;

/**
 * Rule Body
 */
body : conjunction
    {
      //$$ = $conjunction;
    }
  ;

conjunction
  : term
    {
      //$$ = $term;
    }
  | conjunction COMMA term
    {
      //$$ = $1;
      //$$->conjunct($term);
    }
  ;

/**
 * Terms in Rule Bodies
 */
term
  : atom
    {
      //$$ = RuleBody::atom($atom);
    }
/*  | constraint
    {
      //$$ = RuleBody::constraint($constraint);
    } */
  | LPAREN conjunction RPAREN
    {
      //$$ = $conjunction;
    }
  ;

/**
 * Rule body atom
 */
atom
  : qualified_name LPAREN arg_list RPAREN
    {
      //$$ = mk<ast::Atom>($qualified_name, $arg_list, @$);
    }
  ;


/**
 * Argument List
 */
arg_list
  : %empty
    {
    }
  | non_empty_arg_list
    {
      //$$ = $1;
    } ;

non_empty_arg_list
  : arg
    {
      //$$.push_back($arg);
    }
  | non_empty_arg_list COMMA arg
    {
      //$$ = $1; $$.push_back($arg);
    }
  ;


/**
 * Atom argument
 */
arg
  : STRING
    {
      //$$ = mk<ast::StringConstant>($STRING, @$);
    }
  | FLOAT
    {
      //$$ = mk<ast::NumericConstant>($FLOAT, ast::NumericConstant::Type::Float, @$);
    }
  | UNSIGNED
    {
      //auto&& n = $UNSIGNED; // drop the last character (`u`)
      //$$ = mk<ast::NumericConstant>(n.substr(0, n.size() - 1), ast::NumericConstant::Type::Uint, @$);
    }
  | NUMBER
    {
      //$$ = mk<ast::NumericConstant>($NUMBER, @$);
    }
  | UNDERSCORE
    {
      //$$ = mk<ast::UnnamedVariable>(@$);
    }
  | IDENT
    {
      //$$ = mk<ast::Variable>($IDENT, @$);
    }
  | LPAREN arg RPAREN
    {
      //$$ = $2;
    }
  ;

%%

/* notice the extra parameters required
   by %param and %parse-param */

int litelogerror(void *yylval, char const *msg)
{
	(void)yylval;
	return fprintf(stderr, "%s\n", msg);
}



