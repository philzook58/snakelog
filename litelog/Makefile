

litelog: litelog.c
	gcc litelog.c -L. -I. -lsqlite3 -o litelog -std=c99 

sqlite3: 
	gcc sqlite3 -o sqlite3.o

parser: scanner.l parser.y
	bison -d parser.y -Wall
	flex scanner.l
	gcc lex.litelog.c parser.tab.c test.c -Wall 