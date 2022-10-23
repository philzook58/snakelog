from snakelog.common import *


def edgepath(s):
    edge = s.Relation("edge", Sort.NUMBER, Sort.NUMBER)
    path = s.Relation("path", Sort.NUMBER, Sort.NUMBER)
    x, y, z = Vars("x y z")
    s.add(edge(1, 2))
    s.add(edge(2, 3))
    s.add(path(x, y) <= edge(x, y))
    s.add(path(x, z) <= edge(x, y) & path(y, z))
    s.run()
    s.cur.execute("SELECT * FROM path")
    res = s.cur.fetchall()
    print("fetchall of path", res)
    assert set(res) == set([(1, 2), (2, 3), (1, 3)])


def edgepath_symbol(s):
    edge = s.Relation("edge", Sort.SYMBOL, Sort.SYMBOL)
    path = s.Relation("path", Sort.SYMBOL, Sort.SYMBOL)
    x, y, z = Vars("x y z")
    s.add(edge("a", "b"))
    s.add(edge("b", "c"))
    s.add(path(x, y) <= edge(x, y))
    s.add(path(x, z) <= edge(x, y) & path(y, z))
    s.run()
    s.cur.execute("SELECT * FROM path")
    assert set(s.cur.fetchall()) == set([("a", "b"), ("b", "c"), ("a", "c")])


progs = [edgepath,
         edgepath_symbol
         ]
