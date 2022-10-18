from snakelog import *
from snakelog.litelog import *
import json


def test_edge():
    s = Solver()
    edge = s.Relation("edge", INTEGER, INTEGER)
    path = s.Relation("path", INTEGER, INTEGER)
    N = 10
    x, y, z = Vars("x y z")
    s.add_fact(edge(0, 1))
    s.add_rule(edge(0, 1), [])
    s.add_rule(edge(y, SQL("{y} + 1")), [edge(x, y), f"{{y}} < {N}"])
    s.add_rule(path(x, y), [edge(x, y)])
    s.add_rule(path(x, z), [edge(x, y), path(y, z)])

    verts = s.Relation("verts", INTEGER)
    s.add_rule(verts(x), [edge(x, y)])
    s.add_rule(verts(y), [edge(x, y)])
    nopath = s.Relation("nopath", INTEGER, INTEGER)
    s.add_rule(nopath(x, y), [verts(x), verts(y), Not(path(x, y))])

    s.run()

    ans = {(i, j) for i in range(N+1) for j in range(N+1) if i < j}
    s.cur.execute("SELECT * FROM path")
    assert set(s.cur.fetchall()) == ans

    ans = {(i, j) for i in range(N+1) for j in range(N+1)} - ans
    s.cur.execute("SELECT * FROM nopath")
    assert set(s.cur.fetchall()) == ans


def test_notation():
    s = Solver()
    x, y, z = Vars("x y z")
    edge = s.Relation("edge", INTEGER, INTEGER)
    path = s.Relation("path", INTEGER, INTEGER)
    s.add(edge(1, 2))
    s.add(edge(2, 3))
    s.add(path(x, y) <= edge(x, y))
    s.add(path(x, z) <= edge(x, y) & path(y, z))
    s.run()
    s.cur.execute("SELECT * FROM path")
    assert set(s.cur.fetchall()) == {(1, 2), (2, 3), (1, 3)}


def jsonit(x):
    return json.dumps(x, separators=(',', ':'))


def succ(x):
    return {"succ": x}


zero = {"zero": None}  # , separators=(',', ':'))  # "{\"zero\":null}"


def test_succ_build():
    x, n = Vars("x n")
    s = Solver()
    nats = s.Relation("nats", JSON, INTEGER)
    s.add_fact(nats(zero, 0))
    # s.add_rule(nats(succ(x), SQL("{n} + 1")), [nats(x, n), "{n} < 3"])
    s.con.create_function("mysucc", 1, lambda x: x + 1, deterministic=True)
    s.add_rule(nats(succ(x), SQL("mysucc({n})")), [nats(x, n), "{n} < 3"])
    s.run()
    s.cur.execute("SELECT * FROM nats")
    assert set(s.cur.fetchall()) == {(jsonit(zero), 0),
                                     (jsonit(succ(zero)), 1),
                                     (jsonit(succ(succ(zero))), 2),
                                     (jsonit(succ(succ(succ(zero)))), 3)}


def test_succ2():
    s = Solver()
    x, n = Vars("x n")
    nats = s.Relation("nats", JSON)
    s.add_fact(nats(succ(succ(zero))))
    s.add_fact(nats(succ(zero)))
    s.add_rule(nats(x), [nats(succ(x))])
    s.run()
    s.cur.execute("SELECT * FROM nats")
    assert set(s.cur.fetchall()) == {(jsonit(zero),),
                                     (jsonit(succ(zero)),),
                                     (jsonit(succ(succ(zero))),)}
