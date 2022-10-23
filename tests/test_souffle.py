from snakelog import *
from snakelog.souffle import *
from .progs import progs


def test_progs():
    for prog in progs:
        prog(SouffleSolver())


def test_edge():
    s = SouffleSolver()
    edge = s.Relation("edge", "number", "number")
    path = s.Relation("path", "number", "number")
    s.add_fact(edge(1, 2))
    s.add_fact(edge(2, 3))
    x, y, z = Vars("x y z")
    print(x, y, z)
    s.add(path(x, y) <= edge(x, y))
    s.add_rule(path(x, z), [edge(x, y), path(y, z)])
    print(s.rules)
    s.run()

    res = s.con.execute("SELECT * FROM path")
    assert set(res.fetchall()) == {(1, 2), (2, 3), (1, 3)}


def test_list():
    s = SouffleSolver()
    lists = s.Relation("lists", "term")
    cons = s.Function("Cons", "number", "term")
    nil = s.Function("Nil")()
    s.add_fact(lists(cons(1, cons(2, nil))))
    x, y, z = Vars("x y z")
    s.add(lists(y) <= lists(cons(x, y)))
    s.run()

    res = s.con.execute("SELECT * FROM lists")
    assert set(res.fetchall()) == {
        ("$Cons(1, $Cons(2, $Nil))",), ("$Cons(2, $Nil)",), ("$Nil",)}
