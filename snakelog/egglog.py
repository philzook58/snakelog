
import subprocess
import sqlite3
import tempfile
from .common import *
import sexpdata
I64 = "i64"
STRING = "String"
SORT = "SORT"

execname = "/home/philip/Documents/rust/egg-smol2/target/release/egg-smol"


def conv_type(typ):
    if typ == Sort.NUMBER:
        return I64
    elif typ == Sort.SYMBOL:
        return STRING
    else:
        return typ


def from_str(data, typ):
    if typ == NUMBER or typ == Sort.NUMBER:
        return int(data)
    else:
        return data


class EgglogException(Exception):
    pass


class EgglogSolver(BaseSolver):
    def __init__(self, db=":memory:", execname=execname):
        self.execname = execname
        self.options = {}
        self.rules = []
        self.rels = []
        self.funs = []
        self.sorts = []
        self.con = sqlite3.connect(database=db)
        self.cur = self.con.cursor()

    def Sort(self, name):
        assert name not in self.sorts
        self.sorts.append(name)
        return name

    def Function(self, name, *types):
        self.funs.append((name, types))
        args = ", ".join([f"x{n}" for n in range(len(types))])
        self.cur.execute(
            f"CREATE TABLE {name}({args}, PRIMARY KEY ({args})) WITHOUT ROWID")
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
                args = " ".join(map(arg_str, x.args))
                return f"({x.name} {args})"
            elif isinstance(x, str):
                return f"\"{x}\""
            else:
                return str(x)

        def rel_str(rel: Atom):
            args = " ".join(map(arg_str, rel.args))
            return f"({rel.name} {args})"
        if len(body) == 0:
            return f"{rel_str(head)}"
        else:
            body = " ".join(map(rel_str, body))
            return f"(rule ({body})\n\t({rel_str(head)}))"

    def run(self):
        stmts = []
        for name in self.sorts:
            stmts.append(f"(define-datatype {name})")
        for name, types in self.rels:
            args = " ".join(
                [f"{conv_type(typ)}" for typ in types])
            stmts.append(f"(relation {name} ({args}))")
        for name, types in self.funs:
            args = " ".join(
                [f"{conv_type(typ)}" for typ in types])
            stmts.append(f"(function {name} ({args}))")

        for head, body in self.rules:
            stmts.append(self.compile(head, body))
        stmts.append("(run 10)")
        for name, types in self.rels:
            stmts.append(f"(print {name} 1000000)")
        for name, types in self.funs:
            stmts.append(f"(print {name} 1000000)")
        print(stmts)
        with tempfile.TemporaryDirectory() as tmpdirname:
            with tempfile.NamedTemporaryFile(suffix=".egg", dir=tmpdirname) as fp:
                fp.writelines([stmt.encode() + b"\n" for stmt in stmts])
                fp.flush()
                res = subprocess.run(
                    [self.execname, fp.name], capture_output=True)

                err = res.stderr.decode()
                print(err)
                for line in res.stdout.decode().split(sep="\n"):
                    print(line)
                    try:
                        data = sexpdata.loads(line)
                    except:
                        print(f"WARNING Egglog stdout {line} is not sexp")
                        continue
                    args = ", ".join("?" * (len(data) - 1))
                    self.cur.executemany(
                        f"INSERT OR IGNORE INTO {data[0].value()} VALUES ({args});", [tuple(data[1:])])
