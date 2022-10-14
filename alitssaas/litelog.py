import json
from typing import Any, List
import sqlite3
from dataclasses import dataclass
from collections import defaultdict
from copy import copy
import networkx as nx
import time
import re
from .common import *

@dataclass(frozen=True)
class SQL:
    expr : str

# https://www.sqlite.org/datatype3.html
INTEGER = "INTEGER"
TEXT = "TEXT"
REAL = "REAL"
BLOB = "BLOB"
JSON = "TEXT"

keyword = "litelog"


def delta(name):
    return f"{keyword}_delta_{name}"


def new(name):
    return f"{keyword}_new_{name}"


def validate(name):
    return re.fullmatch("[_a-zA-Z][_a-zA-Z0-9]*", name) != None


class Solver(BaseSolver):
    def __init__(self, debug=False, database=":memory:"):
        self.con = sqlite3.connect(
            database=database, detect_types=sqlite3.PARSE_DECLTYPES)
        self.cur = self.con.cursor()
        self.rules = []
        self.rels = {}
        self.debug = debug
        self.stats = defaultdict(int)

    def execute(self, stmt, *args):

        if self.debug:
            print(stmt, args)
            start_time = time.time()
        try:
            self.cur.execute(stmt, *args)
        except BaseException as e:
            print("Error in SQL Query:", stmt, args)
            raise e
        if self.debug:
            end_time = time.time()
            self.stats[stmt] += end_time - start_time

    def Relation(self, name, *types):
        assert validate(name) and keyword not in name
        assert all([validate(typ) for typ in types])
        if name not in self.rels:
            self.rels[name] = types
            args = ", ".join(
                [f"x{n} {typ} NOT NULL" for n, typ in enumerate(types)])
            bareargs = ", ".join(
                [f"x{n}" for n, _typ in enumerate(types)])
            self.execute(
                f"CREATE TABLE {name}({args}, PRIMARY KEY ({bareargs})) WITHOUT ROWID")
            self.execute(
                f"CREATE TABLE {new(name)}({args}, PRIMARY KEY ({bareargs})) WITHOUT ROWID")
            self.execute(
                f"CREATE TABLE {delta(name)}({args}, PRIMARY KEY ({bareargs})) WITHOUT ROWID")
        else:
            assert self.rels[name] == types
        return lambda *args: Atom(name, args)


    def compile(self, head, body, naive=False):
        assert isinstance(head, Atom)
        # map from variables to columns where they appear
        # We use WHERE clauses and let SQL do the heavy lifting
        counter = 0

        def fresh(name):
            nonlocal counter
            counter += 1
            return f"dataduck_{name}{counter}"
        varmap = defaultdict(list)
        constants = {}

        def add_constant(x):
            N = len(constants)
            constants[str(N)] = x
            return f":{N}"

        froms = []
        wheres = []

        def match_(x, pat):
            if isinstance(pat, Var):
                varmap[pat] += [x]
            elif isinstance(pat, SQL):
                varmap[pat] += [x]  # I should put this not in varmap
            elif isinstance(pat, dict):
                for k, v in pat.items():
                    match_(f"json_extract({x},'$.{k}')", v)
            elif isinstance(pat, list):
                wheres.append(f"json_array_length({x}) = {len(pat)}")
                for n, v in enumerate(pat):
                    match_(f"json_extract({x},'$[{n}]')", v)
            else:
                # Assume constant can be handled by SQLite adapter
                id_ = add_constant(pat)
                wheres.append(f"{id_} = {x}")
        for rel in body:
            # Every relation in the body creates a new FROM term bounded to
            # a freshname because we may have multiple instances of the same relation
            # The arguments are processed to fill a varmap, which becomes the WHERE clause
            if (isinstance(rel, Atom)):
                name = rel.name
                args = rel.args
                freshname = fresh(name)
                froms.append(f"{name} AS {freshname}")

                for n, arg in enumerate(args):
                    colname = f"{freshname}.x{n}"
                    match_(colname, arg)

        formatvarmap = {k.name: i[0]
                        for k, i in varmap.items() if isinstance(k, Var)}

        def construct(arg):
            if isinstance(arg, SQL):
                return arg.expr.format(**formatvarmap)
            elif isinstance(arg, dict):
                entries = ",".join(
                    [f"'{k}',json({construct(v)})" for k, v in arg.items()])
                return f"json_object({entries})"
            elif arg in varmap:
                return varmap[arg][0]
            else:
                return add_constant(arg)

        for c in body:
            if isinstance(c, str):  # Injected SQL constraint expressions
                wheres.append(c.format(**formatvarmap))
            if isinstance(c, Not) and isinstance(c.val, Atom):
                args = c.val.args
                fname = fresh(c.val.name)
                conds = " AND ".join(
                    [f"{fname}.x{n} = {construct(arg)}" for n, arg in enumerate(args)])
                wheres.append(
                    f"NOT EXISTS (SELECT * FROM {c.val.name} AS {fname} WHERE {conds})")

        # implicit equality constraints
        for v, argset in varmap.items():
            for arg in argset:
                if isinstance(v, Var):  # a variable constraint
                    if argset[0] != arg:
                        wheres.append(f"{argset[0]} = {arg}")
                elif isinstance(v, SQL):  # Injected SQL expression argument
                    wheres.append(f"{v.format(**formatvarmap)} = {arg}")
                else:
                    print(v, argset)
                    assert False
        if len(wheres) > 0:
            wheres = " WHERE " + " AND ".join(wheres)
        else:
            wheres = ""
        # Semi-naive bodies
        selects = ", ".join([construct(arg) for arg in head.args])
        if naive:
            if len(froms) > 0:
                froms = " FROM " + ", ".join(froms)
            else:
                froms = ""
            return f"INSERT OR IGNORE INTO {new(head.name)} SELECT DISTINCT {selects}{froms}{wheres}", constants
        else:
            stmts = []
            for n in range(len(froms)):
                froms1 = copy(froms)
                # cheating a little here. froms actually contains "name AS alias"
                froms1[n] = delta(froms1[n])
                froms1 = ", ".join(froms1)
                stmts.append(
                    (f"INSERT OR IGNORE INTO {new(head.name)} SELECT DISTINCT {selects} FROM {froms1}{wheres} ", constants))
            return stmts

    def stratify(self):
        G = nx.DiGraph()

        for head, body in self.rules:
            if len(body) == 0:
                G.add_edge(head.name, head.name)
            for rel in body:
                if isinstance(rel, Atom):
                    G.add_edge(rel.name, head.name)
                elif isinstance(rel, Not):
                    assert isinstance(rel.val, Atom)
                    G.add_edge(rel.val.name, head.name)

        scc = list(nx.strongly_connected_components(G))
        cond = nx.condensation(G, scc=scc)
        for n in nx.topological_sort(cond):
            # TODO: negation check
            yield scc[n]

    def run(self):
        for strata in self.stratify():
            stmts = []
            for head, body in self.rules:
                if head.name in strata:
                    # if len(body) == 0:
                    #    self.add_fact(head)
                    if any([rel.name in strata for rel in body if isinstance(rel, Atom)]):
                        stmts += self.compile(head, body)
                    else:
                        # These are not recursive rules
                        # They need to be run once naively and can then be forgotten
                        stmt, params = self.compile(head, body, naive=True)
                        self.execute(stmt, params)
            # Prepare initial delta relation
            for name in strata:
                self.execute(
                    f"INSERT OR IGNORE INTO {delta(name)} SELECT DISTINCT * FROM {new(name)}")
                self.execute(
                    f"INSERT OR IGNORE INTO {name} SELECT DISTINCT * FROM {new(name)}")
                self.execute(
                    f"DELETE FROM {new(name)}")
            iter = 0
            # Seminaive loop
            while True:
                iter += 1
                # print(iter)
                for stmt, params in stmts:
                    self.execute(stmt, params)
                num_new = 0
                for name, types in self.rels.items():
                    self.execute(f"DELETE FROM {delta(name)}")
                    wheres = " AND ".join(
                        [f"{new(name)}.x{n} = {name}.x{n}" for n in range(len(types))])
                    self.execute(
                        f"INSERT OR IGNORE INTO {delta(name)} SELECT DISTINCT * FROM {new(name)}")
                    wheres = " AND ".join(
                        [f"{delta(name)}.x{n} = {name}.x{n}" for n in range(len(types))])
                    self.execute(
                        f"DELETE FROM {delta(name)} WHERE EXISTS (SELECT * FROM {name} WHERE {wheres})")
                    self.execute(
                        f"INSERT OR IGNORE INTO {name} SELECT * FROM {delta(name)}")
                    self.execute(f"DELETE FROM {new(name)}")

                    self.execute(f"SELECT COUNT(*) FROM {delta(name)}")
                    n = self.cur.fetchone()[0]
                    num_new += n
                if num_new == 0:
                    break