"""The release build (scripts/build_candidate.py on build_original_study.Study): each face's finishing pass hooks the same classes."""
import ast, glob, os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.mark.parametrize('script', sorted(glob.glob(os.path.join(ROOT, 'scripts', '*.py'))), ids=os.path.basename)
def test_no_build_step_is_defined_twice(script):
    # a second definition of a step silently replaces the first, and with it another face's finishing pass
    tree = ast.parse(open(script, encoding='utf-8').read())
    for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
        names = [f.name for f in cls.body if isinstance(f, ast.FunctionDef)]
        assert len(names) == len(set(names)), (cls.name, sorted({n for n in names if names.count(n) > 1}))
