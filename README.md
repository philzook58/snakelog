# A Log is the Same Shape as a Snake
### A Datalog Framework For Python

```python
from snakelog.common import *
from snakelog.litelog import Solver, TEXT
s = Solver()
x, y, z = Vars("x y z")
edge = s.Relation("edge", TEXT, TEXT)
path = s.Relation("path", TEXT, TEXT)

s.add(edge("a", "b"))
s.add(edge("b", "c"))
s.add(path(x, y) <= edge(x, y))
s.add(path(x, z) <= edge(x, y) & path(y, z))
s.run()

s.cur.execute("SELECT * FROM path")
assert set(s.cur.fetchall()) == {("a", "b"), ("b", "c"), ("a", "c")}
```