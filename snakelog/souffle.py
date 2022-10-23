
import subprocess
import sqlite3
import tempfile
from .common import *


class SouffleSolver(BaseSolver):
    def __init__(self, output_db="souffle.db", input_db=None, execname="souffle", compiled=False):
        self.execname = execname
        self.options = {"compiled": compiled}
        self.rules = []
        self.rels = []
        self.funs = []
        self.output_db = output_db
        self.con = sqlite3.connect(database=output_db)
        self.input_db = input_db

    def Function(self, name, *types):
        self.funs.append((name, types))
        return lambda *args: Term(name, args)

    def Relation(self, name, *types):
        self.rels.append((name, types))
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
            args = ", ".join([f"x{n} : {typ}" for n, typ in enumerate(types)])
            stmts.append(f".decl {name}({args})")
            if self.input_db != None:
                stmts.append(
                    f".input {name}(IO=sqlite, filename=\"{self.input_db}\")")
            stmts.append(
                f".output {name}(IO=sqlite, filename=\"{self.output_db}\")")
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
        with tempfile.NamedTemporaryFile(suffix=".dl") as fp:
            fp.writelines([stmt.encode() + b"\n" for stmt in stmts])
            fp.flush()
            res = subprocess.run([self.execname, fp.name], capture_output=True)
            print(res.stdout.decode())
            print(res.stderr.decode())
