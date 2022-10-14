from typing import Any, List
from dataclasses import dataclass

@dataclass(frozen=True)
class Term():
    f:str
    args:List[Any]

@dataclass(frozen=True)
class Var:
    name: str

    def __eq__(self, rhs):
        return Eq(self, rhs)
    def __add__(self,rhs):
        return Term("+", [self,rhs])


@dataclass(frozen=True)
class Eq:
    lhs: Any
    rhs: Any


@dataclass
class Not:
    val: Any


fresh_counter = 0


def FreshVar():
    global fresh_counter
    fresh_counter += 1
    return Var(f"duckegg_x{fresh_counter}")


def Vars(xs):
    return [Var(x) for x in xs.split()]


@dataclass
class Atom:
    name: str
    args: List[Any]

    def __repr__(self):
        args = ",".join(map(repr, self.args))
        return f"{self.name}({args})"


@dataclass
class Body(list):
    def __and__(self, rhs):
        if isinstance(rhs, Atom):
            return Body(self + [rhs])
        elif isinstance(rhs, Body):
            return Body(self + rhs)
        else:
            raise Exception(f"{self} & {rhs} is invalid")


@dataclass
class Clause:
    head: Atom
    body: Body