
import subprocess
import sqlite3
import tempfile
from .common import *
import csv
from pathlib import Path
NUMBER = "number"
SYMBOL = "symbol"


def conv_type(typ):
    if typ == Sort.NUMBER:
        return NUMBER
    elif typ == Sort.SYMBOL:
        return SYMBOL
    else:
        return typ


def from_str(data, typ):
    if typ == NUMBER or typ == Sort.NUMBER:
        return int(data)
    else:
        return data


class SouffleSolver(BaseSolver):
    def __init__(self, output_db=":memory:", input_db=None, execname="souffle", compiled=False):
        self.execname = execname
        self.options = {"compiled": compiled}
        self.rules = []
        self.rels = []
        self.funs = []
        self.output_db = output_db
        self.con = sqlite3.connect(database=output_db)
        self.cur = self.con.cursor()
        self.input_db = input_db

    def Function(self, name, *types):
        self.funs.append((name, types))
        return lambda *args: Term(name, args)

    def Relation(self, name, *types):
        self.rels.append((name, types))
        args = ", ".join([f"x{n}" for n in range(len(types))])
        self.cur.execute(
            f"CREATE TABLE {name}({args}, PRIMARY KEY ({args})) WITHOUT ROWID")
        return lambda *args: Atom(name, args)

    def compile(self, head: Atom, body):
        def arg_str(x):
            if isinstance(x, Var):
                return x.name
            elif isinstance(x, Term):
                args = ", ".join(map(arg_str, x.args))
                return f"${x.name}({args})"
            elif isinstance(x, str):
                return f"\"{x}\""
            else:
                return str(x)

        def rel_str(rel: Atom):
            args = ", ".join(map(arg_str, rel.args))
            return f"{rel.name}({args})"
        if len(body) == 0:
            return f"{rel_str(head)}."
        else:
            body = ", ".join(map(rel_str, body))
            return f"{rel_str(head)} :- {body}."

    def run(self):
        stmts = []
        for name, types in self.rels:
            args = ", ".join(
                [f"x{n} : {conv_type(typ)}" for n, typ in enumerate(types)])
            stmts.append(f".decl {name}({args})")
            if self.input_db != None:
                stmts.append(
                    f".input {name}(IO=sqlite, filename=\"{self.input_db}\")")
            # stmts.append(
            #    f".output {name}(IO=file, filename=\"{self.output_db}\")")
            stmts.append(
                f".output {name}(IO=file, rfc4180=true)")
        if len(self.funs) != 0:
            constructors = []
            for name, types in self.funs:
                args = ", ".join(
                    [f"x{n} : {typ}" for n, typ in enumerate(types)])
                constructors.append(f"{name} {{{args}}}")
            constructors = " | ".join(constructors)
            stmts.append(f".type term = {constructors}")
        for head, body in self.rules:
            stmts.append(self.compile(head, body))
        with tempfile.TemporaryDirectory() as tmpdirname:
            with tempfile.NamedTemporaryFile(suffix=".dl", dir=tmpdirname) as fp:
                fp.writelines([stmt.encode() + b"\n" for stmt in stmts])
                fp.flush()
                res = subprocess.run(
                    [self.execname, fp.name, "-D", tmpdirname], capture_output=True)
                print(res.stdout.decode())
                print(res.stderr.decode())
                # The souffle sqlite output for records is no good.
                # It would be much preferable to use it for speed and simplicity rather than csv
                for name, types in self.rels:
                    with open(Path(tmpdirname) / f'{name}.csv') as f:
                        reader = csv.reader(f)
                        data = [[from_str(data, typ) for data, typ in zip(
                            row, types)] for row in reader]
                        args = ", ".join("?" * len(types))
                        self.cur.executemany(
                            f"INSERT OR IGNORE INTO {name} VALUES ({args});", data)
