#include "sqlite3.h"
#include <stdio.h>

int main()
{

    sqlite3 *db;
    char *err_msg = 0;
    sqlite3_stmt *res;

    int rc = sqlite3_open(":memory:", &db);
    if (rc != SQLITE_OK)
    {

        fprintf(stderr, "Cannot open database: %s\n", sqlite3_errmsg(db));
        sqlite3_close(db);

        return 1;
    }

    rc = sqlite3_prepare_v2(db, "SELECT SQLITE_VERSION()", -1, &res, 0);

    if (rc != SQLITE_OK)
    {

        fprintf(stderr, "Failed to fetch data: %s\n", sqlite3_errmsg(db));
        sqlite3_close(db);

        return 1;
    }

    rc = sqlite3_step(res);

    if (rc == SQLITE_ROW)
    {
        printf("%s\n", sqlite3_column_text(res, 0));
    }

    // Manually run the edge path query.
    rc = sqlite3_prepare_v2(db, "CREATE TABLE edge(x0,x1)", -1, &res, 0);
    if (rc != SQLITE_OK)
    {

        fprintf(stderr, "Failed to create table: %s\n", sqlite3_errmsg(db));
        sqlite3_close(db);

        return 1;
    }
    rc = sqlite3_step(res);
    rc = sqlite3_prepare_v2(db, "CREATE TABLE path(x0,x1)", -1, &res, 0);
    if (rc != SQLITE_OK)
    {

        fprintf(stderr, "Failed to create table: %s\n", sqlite3_errmsg(db));
        sqlite3_close(db);

        return 1;
    }
    rc = sqlite3_step(res);

    sqlite3_finalize(res);
    sqlite3_close(db);

    return 0;
}