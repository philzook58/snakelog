from __future__ import annotations
from typing import Any, List
from dataclasses import dataclass


@dataclass(frozen=True)
class Var:
    name: str

    def __eq__(self, rhs):
        return Eq(self, rhs)

    def __add__(self, rhs):
        return Term("+", [self, rhs])

    def __str__(self):
        return self.name


def Vars(xs):
    return [Var(x) for x in xs.split()]


@dataclass(frozen=True)
class Term():
    name: str
    args: List[Any]


class Formula():
    def __and__(self, rhs):
        if isinstance(rhs, Formula):
            return Body([self, rhs])
        elif isinstance(rhs, Body):
            return Body([self] + rhs)
        else:
            raise Exception(f"{self} & {rhs} is invalid")

    def __le__(self, rhs):
        if isinstance(rhs, Formula):
            b = Body([rhs])
            return Clause(self, b)
        elif isinstance(rhs, Body):
            return Clause(self, rhs)
        else:
            raise Exception(f"{self} <= {rhs} is invalid")


@dataclass(frozen=True)
class Eq(Formula):
    lhs: Any
    rhs: Any

    def __str__(self):
        return f"{repr(self.lhs)} = {repr(self.rhs)}"


@dataclass
class Not(Formula):
    val: Any


fresh_counter = 0


def FreshVar():
    global fresh_counter
    fresh_counter += 1
    return Var(f"duckegg_x{fresh_counter}")


@dataclass(frozen=True)
class QuasiQuote:
    expr: str


Q = QuasiQuote


@dataclass
class Atom(Formula):
    name: str
    args: List[Any]

    def __str__(self):
        args = ",".join(map(repr, self.args))
        return f"{self.name}({args})"


@dataclass
class Proof:
    conc: Formula
    subproofs: List[Proof]
    reason: Any

    def bussproof(self):
        conc = self.conc
        reason = self.reason
        hyps = self.subproofs
        if len(hyps) == 0:
            return f"\\RightLabel{{{reason}}} \\AxiomC{{{self.conc}}}"
        elif len(hyps) == 1:
            return f"{hyps[0].bussproof()} \\RightLabel{{{reason}}} \\UnaryInfC{{{conc}}}"
        elif len(hyps) == 2:
            return f"{hyps[0].bussproof()} {hyps[1].bussproof()} \\RightLabel{{{reason}}}  \\BinaryInfC{{{conc}}}"
        elif len(hyps) == 3:
            return f"{hyps[0].bussproof()} {hyps[1].bussproof()} {hyps[2].bussproof()} \\RightLabel{{{reason}}}  \\TrinaryInfC{{{conc}}}"
        elif len(hyps) >= 3:
            return f"{hyps[0].bussproof()} {hyps[1].bussproof()} \\AxiomC{{{...}}} \\RightLabel{{{reason}}} \\TrinaryInfC{{{conc}}}"


@dataclass
class Body:
    atoms: List[Atom]

    def __and__(self, rhs):
        if isinstance(rhs, Formula):
            return Body(self.atoms + [rhs])
        elif isinstance(rhs, Body):
            return Body(self.atoms + rhs)
        else:
            raise Exception(f"{self} & {rhs} is invalid")

    def __str__(self):
        return ", ".join(map(str, self.atoms))


@dataclass
class Clause:
    head: Atom
    body: Body

    def __str__(self):
        return f"{self.head} :- {self.body}."


class BaseSolver():
    def add_rule(self, head, body):
        self.rules.append((head, body))

    def add_fact(self, fact: Atom):
        self.add_rule(fact, [])

    def add(self, x):
        if isinstance(x, Atom):
            self.add_fact(x)
        elif isinstance(x, Clause):
            self.add_rule(x.head, x.body.atoms)
        else:
            raise Exception(f"Solver.add: Unexpected thing {x}")
