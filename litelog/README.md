
The idea is to make a C based datalog that interoperates with sqlite for maximum portability (Thanks to Michael Greenberg for the idea).

We can take different subproblems

1. Make a C datalog parser
2. Assume whatevr data structure or interface for constructing terms
3. Naive evaluation first
4. Just make a super with recursive



Injection: should use sqlite parser to validate names aren't injected


```C
int litelog_create_relation(sqlite3 *db, char* name, int arity){
    // Validate name as valid sqlite identifier
    sprintf("CREATE TABLE %s() ", name);
    res = sqlite3_exec(db, stmt);
    if res != SQLITE_OK {

    }
    // seminaive
    //sprintf("CREATE TABLE new_%s()", name);
    //sprintf("CREATE TABLE delta_%s()", name);
}
```

```sql
INSERT OR IGNORE INTO path SELECT edge0.x0, edge0.x1 DISTINCT FROM edge as edge0 
INSERT OR IGNORE INTO path SELECT edge0.x0, path0.x1 
    DISTINCT FROM edge as edge0, path as path0 WHERE edge0.x1 = path0.x0

```

```
#define MAXSIZE 20
struct clause {
    char* head_relation,
    char* froms[MAXSIZE],
    char* select_table[MAXSIZE],
    char* select_row[MAXSIZE],
    char* wheres[MAXSIZE],
    int nfrom,
    int nselect,
    int nwhere
}

prepare_clause(cls) {
    sprintf("INSERT OR IGNORE INTO %s SELECT ");
    sqlite3_prepare()
}



init_clause(cls){
    cls.nfrom = 0;
    cls.nselect = 0;
    cls.nwhere = 0;
    cls.head_relation = NULL;
}


insert(clause* cls, ) {
    cls->
}

head_relation(cls, char* name){
    
}
cls = create_clause();
head_relation(cls, "path");
bind_from(cls, "edge", "edge0");
bind_from(cls, "path", "path0");
insert(cls, "path");
select(cls, "edge0.x0");
select(cls, "edge0.x0");
select(cls, "edge0.x0");
where(cls, "edge0.x1 = path0.x0");
prep = prepare_clause(cls);
delete_clause(cls)
delete_prep();
```
