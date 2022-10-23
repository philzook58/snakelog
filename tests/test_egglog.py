from snakelog.common import *
from snakelog.egglog import *
from .progs import progs


def test_progs():
    for prog in progs:
        s = EgglogSolver()
        prog(s)
