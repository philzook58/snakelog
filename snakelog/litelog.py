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
    expr: str


# https://www.sqlite.org/datatype3.html
INTEGER = "INTEGER"
TEXT = "TEXT"
REAL = "REAL"
BLOB = "BLOB"
JSON = "TEXT"

'''keyword is prepended to avoid name collision with user given names'''
keyword = "litelog"


def delta(name):
    '''Helpers to derive auxiliary relation names from user relation name'''
    return f"{keyword}_delta_{name}"


def old(name):
    return f"{keyword}_old_{name}"


def new(name):
    return f"{keyword}_new_{name}"


def validate(name):
    '''Validates valid identifiers'''
    return re.fullmatch("[_a-zA-Z][_a-zA-Z0-9]*", name) != None


class VarMap():
    '''
    Union Find Dict https://www.philipzucker.com/union-find-dict/
    self.data holds either Var or list as value.
    If Var, iterate lookup until reach list.
    Values held in dict are merged upon union
    '''

    def __init__(self):
        self.data = defaultdict(list)

    def find(self, x):
        # no path compression. Simple.
        varmap = self.data
        while isinstance(varmap[x], Var):
            x = varmap[x]
        return x

    def __getitem__(self, x: Var):
        return self.data[self.find(x)]

    def __setitem__(self, k: Var, v):
        self.data[self.find(k)] = v

    def union(self, x: Var, y: Var):
        x1 = self.find(x)
        y1 = self.find(y)
        varmap = self.data
        if varmap[x1] == []:
            varmap[x1] = y1
        elif varmap[y1] == []:
            varmap[y1] == x1
        else:
            temp = varmap[x1]
            varmap[x1] = y1
            varmap[y1] += temp

    def formatmap(self):
        return {k.name: self[k][0] for k in self.data.keys()}

    def values(self):
        return [x for x in self.data.values() if not isinstance(x, Var)]


class ConstantMap(dict):
    ''' ConstantMap hold a mapping between named SQL parameters and their pythonic values'''

    def add_constant(self, x):
        N = len(self)
        self[str(N)] = x
        return f":{N}"


def construct(arg, varmap, constants):
    if isinstance(arg, SQL):
        formatvarmap = varmap.formatmap()
        return arg.expr.format(**formatvarmap)
    elif isinstance(arg, dict):
        entries = ",".join(
            [f"'{k}',json({construct(v, varmap, constants)})" for k, v in arg.items()])
        return f"json_object({entries})"
    elif isinstance(arg, Var):
        return str(varmap[arg][0])
    else:
        return constants.add_constant(arg)


def compile_query(body: List[Formula]):
    # map from variables to columns where they appear
    # We use WHERE clauses and let SQL do the heavy lifting
    counter = 0

    # fresh names to label SQL rows with
    def fresh(name):
        nonlocal counter
        counter += 1
        return f"{keyword}_{name}{counter}"

    varmap = VarMap()
    constants = ConstantMap()

    froms = []
    wheres = []

    def match_(x, pat):
        if isinstance(pat, Var):
            varmap[pat] += [x]
        # elif isinstance(pat, SQL):
        #    varmap[find(pat)] += [x]  # I should put this not in varmap
        elif isinstance(pat, dict):
            for k, v in pat.items():
                match_(f"json_extract({x},'$.{k}')", v)
        elif isinstance(pat, list):
            wheres.append(f"json_array_length({x}) = {len(pat)}")
            for n, v in enumerate(pat):
                match_(f"json_extract({x},'$[{n}]')", v)
        else:
            # Assume constant can be handled by SQLite adapter
            id_ = constants.add_constant(pat)
            wheres.append(f"{id_} = {x}")

    for rel in body:
        # Every relation in the body creates a new FROM term bounded to
        # a freshname because we may have multiple instances of the same relation
        # The arguments are processed to fill a varmap, which becomes the WHERE clause
        if (isinstance(rel, Atom)):
            name = rel.name
            args = rel.args
            freshname = fresh(name)
            froms.append((name, freshname))

            for n, arg in enumerate(args):
                colname = f"{freshname}.x{n}"
                match_(colname, arg)
        elif isinstance(rel, Eq):
            if isinstance(rel.lhs, Var):
                if isinstance(rel.rhs, Var):
                    varmap.union(rel.lhs, rel.rhs)
                else:
                    varmap[rel.lhs] += [rel.rhs]
            else:
                if isinstance(rel.rhs, Var):
                    varmap[rel.rhs] += [rel.lhs]
                else:
                    # hmm. shouldn't I be using constantmap here?
                    wheres.append(f"{rel.lhs} = {rel.rhs}")
    formatvarmap = varmap.formatmap()

    for c in body:
        if isinstance(c, str):  # Injected SQL constraint expressions
            wheres.append(c.format(**formatvarmap))
        if isinstance(c, Not) and isinstance(c.val, Atom):
            args = c.val.args
            fname = fresh(c.val.name)
            conds = " AND ".join(
                [f"{fname}.x{n} = {construct(arg,varmap,constants)}" for n, arg in enumerate(args)])
            wheres.append(
                f"NOT EXISTS (SELECT * FROM {c.val.name} AS {fname} WHERE {conds})")

    # implicit equality constraints
    for argset in varmap.values():
        for arg in argset:
            if argset[0] != arg:
                wheres.append(f"{argset[0]} = {arg}")

    '''
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
    '''
    return varmap, constants, froms, wheres


def compile(head: Atom, body: List[Formula], naive=False):
    assert isinstance(head, Atom)

    varmap, constants, froms, wheres = compile_query(body)
    if len(wheres) > 0:
        wheres = " WHERE " + " AND ".join(wheres)
    else:
        wheres = ""
    # Semi-naive bodies
    selects = ", ".join([construct(arg, varmap, constants)
                        for arg in head.args])
    if naive:
        if len(froms) > 0:
            froms = " FROM " + \
                ", ".join([f"{table} AS {row}" for table, row in froms])
        else:
            froms = ""
        return f"INSERT OR IGNORE INTO {new(head.name)} SELECT DISTINCT {selects}{froms}{wheres}", constants
    else:
        stmts = []
        for n in range(len(froms)):
            froms1 = copy(froms)
            froms1[n] = delta(froms1[n][0]), froms1[n][1]
            froms1 = ", ".join([f"{table} AS {row}" for table, row in froms1])
            stmts.append(
                (f"INSERT OR IGNORE INTO {new(head.name)} SELECT DISTINCT {selects} FROM {froms1}{wheres} ", constants))
        return stmts


class Solver(BaseSolver):
    '''
    SQLite based datalog solver
    '''

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

    def Relation(self, name: str, *types):
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
            args = ", ".join(
                [f"x{n} {typ} NOT NULL" for n, typ in enumerate(types)] + [f"{keyword}_timestamp INTEGER NOT NULL"])
            self.execute(
                f"CREATE TABLE {old(name)}({args}, PRIMARY KEY ({bareargs})) WITHOUT ROWID")
        else:
            assert self.rels[name] == types
        return lambda *args: Atom(name, args)

    def provenance(self, fact: Atom, timestamp: int):
        for rulen, (head, body) in enumerate(self.rules):
            if head.name != fact.name or len(head.args) != len(fact.args):
                continue
            query = [Eq(a, b) for a, b in zip(
                head.args, fact.args)] + body
            print(query)
            varmap, constants, froms, wheres = compile_query(query)
            wheres += [f"{row}.{keyword}_timestamp < :timestamp" for _, row in froms]
            # This section is repetitive
            if len(wheres) > 0:
                wheres = " WHERE " + " AND ".join(wheres)
            else:
                wheres = ""
            constants["timestamp"] = timestamp

            body_atoms = [
                rel for rel in body if isinstance(rel, Atom)]
            selects = [arg for rel in body_atoms for arg in rel.args]
            assert len(body_atoms) == len(froms)
            assert all([r1.name == table for r1, (table, _)
                        in zip(body_atoms, froms)])
            selects = [construct(arg, varmap, constants) for arg in selects]
            timestampind = len(selects)
            selects += [f"{row}.{keyword}_timestamp" for _, row in froms]
            selects = ", ".join(selects)
            if selects == "":
                selects = " * "
            if len(froms) > 0:
                froms = " FROM " + \
                    ", ".join(
                        [f"{old(table)} AS {row}" for table, row in froms])
            else:
                froms = " FROM (VALUES (42)) "
            # order by sum(timestamps) limit 1
            self.execute(f"SELECT {selects} {froms} {wheres}", constants)
            res = self.cur.fetchone()
            if res != None:
                timestamps = res[timestampind:]
                subproofs = []
                for rel, timestamp in zip(body, timestamps):
                    nargs = len(rel.args)
                    q = Atom(rel.name, res[:nargs])
                    res = res[nargs:]
                    subproofs.append(self.provenance(q, timestamp))
                return Proof(fact, subproofs, rulen)
        raise BaseException(
            f"No rules applied to derivation of {fact}, {timestamp}")

    def stratify(self):
        G = nx.DiGraph()

        for head, body in self.rules:
            # if len(body) == 0:
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
        timestamp = 0
        for strata in self.stratify():
            timestamp += 1
            stmts = []
            for head, body in self.rules:
                if head.name in strata:
                    # if len(body) == 0:
                    #    self.add_fact(head)
                    if any([rel.name in strata for rel in body if isinstance(rel, Atom)]):
                        stmts += compile(head, body)
                    else:
                        # These are not recursive rules
                        # They need to be run once naively and can then be forgotten
                        stmt, params = compile(head, body, naive=True)
                        self.execute(stmt, params)
            # Prepare initial delta relation
            for name in strata:
                self.execute(
                    f"INSERT OR IGNORE INTO {delta(name)} SELECT DISTINCT * FROM {new(name)}")
                self.execute(
                    f"INSERT OR IGNORE INTO {name} SELECT DISTINCT * FROM {new(name)}")
                self.execute(
                    f"INSERT OR IGNORE INTO {old(name)} SELECT *, ? FROM {new(name)}", (timestamp,))
                self.execute(
                    f"DELETE FROM {new(name)}")
            # Seminaive loop
            while True:
                timestamp += 1
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
                    self.execute(
                        f"INSERT OR IGNORE INTO {old(name)} SELECT *, ? FROM {delta(name)}", (timestamp,))
                    self.execute(f"DELETE FROM {new(name)}")

                    self.execute(f"SELECT COUNT(*) FROM {delta(name)}")
                    n = self.cur.fetchone()[0]
                    num_new += n
                if num_new == 0:
                    break
