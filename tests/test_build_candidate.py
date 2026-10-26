"""The release build (scripts/build_candidate.py): each face's finishing pass hooks one class."""
import ast, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_no_build_step_is_defined_twice():
    # a second definition of a step silently replaces the first, and with it another face's finishing pass
    tree = ast.parse(open(os.path.join(ROOT, 'scripts', 'build_candidate.py'), encoding='utf-8').read())
    for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
        names = [f.name for f in cls.body if isinstance(f, ast.FunctionDef)]
        assert len(names) == len(set(names)), (cls.name, sorted({n for n in names if names.count(n) > 1}))
