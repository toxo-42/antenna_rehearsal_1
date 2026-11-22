"""Structure rules from CLAUDE.md, checked with ast over app.py and src/*.py.

Do not raise these limits or add exceptions in later phases.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_FILE_LINES = 300
MAX_FUNC_LINES = 40
MAX_ARGS = 5

FuncNode = ast.FunctionDef | ast.AsyncFunctionDef


def source_files() -> list[Path]:
    return [ROOT / "app.py", *sorted((ROOT / "src").glob("*.py"))]


def py_files_of_tests() -> list[Path]:
    return sorted((ROOT / "tests").glob("*.py"))


def src_files() -> list[Path]:
    return sorted((ROOT / "src").glob("*.py"))


def nested_py_files(src_dir: Path) -> list[Path]:
    """Python files below src/ that the flat src/*.py glob would not check."""
    return sorted(p for p in src_dir.rglob("*.py") if p.parent != src_dir)


def line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def functions(tree: ast.AST) -> list[FuncNode]:
    return [n for n in ast.walk(tree) if isinstance(n, FuncNode)]


def func_lines(func: FuncNode) -> int:
    return (func.end_lineno or func.lineno) - func.lineno + 1


def arg_count(func: FuncNode) -> int:
    spec = func.args
    names = [a.arg for a in spec.posonlyargs + spec.args + spec.kwonlyargs]
    names += [a.arg for a in (spec.vararg, spec.kwarg) if a is not None]
    return len([n for n in names if n != "self"])


def imported_names(tree: ast.AST) -> set[str]:
    """Absolute dotted names imported by a module that lives directly in src/."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            package = "src" if node.level else ""
            base = ".".join(part for part in (package, node.module) if part)
            found.add(base)
            found.update(f"{base}.{alias.name}" for alias in node.names)
    return found


def imports_app(tree: ast.AST) -> bool:
    return any(name == "app" or name.startswith("app.") for name in imported_names(tree))


def src_dependencies(tree: ast.AST, modules: set[str]) -> set[str]:
    deps: set[str] = set()
    for name in imported_names(tree):
        parts = name.split(".")
        if len(parts) > 1 and parts[0] == "src" and parts[1] in modules:
            deps.add(parts[1])
    return deps


def find_cycle(graph: dict[str, set[str]]) -> list[str]:
    """Return one import cycle as a module path, or [] when there is none."""
    done: set[str] = set()

    def visit(node: str, trail: list[str]) -> list[str]:
        if node in trail:
            return [*trail[trail.index(node) :], node]
        if node in done:
            return []
        for dep in sorted(graph.get(node, ())):
            cycle = visit(dep, [*trail, node])
            if cycle:
                return cycle
        done.add(node)
        return []

    for start in sorted(graph):
        cycle = visit(start, [])
        if cycle:
            return cycle
    return []


def test_files_are_at_most_300_lines() -> None:
    """Test files count too: the project rule says "파일 300줄" without an exception."""
    counts = {p: line_count(p) for p in [*source_files(), *py_files_of_tests()]}
    too_long = [f"{p.relative_to(ROOT)}: {n}" for p, n in counts.items() if n > MAX_FILE_LINES]
    assert too_long == []


def test_src_is_flat() -> None:
    nested = [str(p.relative_to(ROOT)) for p in nested_py_files(ROOT / "src")]
    assert nested == []


def test_functions_are_at_most_40_lines() -> None:
    too_long = [
        f"{path.relative_to(ROOT)}:{func.lineno} {func.name}: {func_lines(func)}"
        for path in source_files()
        for func in functions(parse(path))
        if func_lines(func) > MAX_FUNC_LINES
    ]
    assert too_long == []


def test_functions_take_at_most_5_arguments() -> None:
    too_many = [
        f"{path.relative_to(ROOT)}:{func.lineno} {func.name}: {arg_count(func)}"
        for path in source_files()
        for func in functions(parse(path))
        if arg_count(func) > MAX_ARGS
    ]
    assert too_many == []


def test_src_does_not_import_app() -> None:
    offenders = [str(p.relative_to(ROOT)) for p in src_files() if imports_app(parse(p))]
    assert offenders == []


def test_src_has_no_circular_imports() -> None:
    modules = {p.stem for p in src_files()}
    graph = {p.stem: src_dependencies(parse(p), modules) for p in src_files()}
    assert find_cycle(graph) == []


# The checks above pass trivially on an empty src/, so prove the detectors fire.


def test_detectors_catch_violations() -> None:
    func = functions(ast.parse("def f(self, a, b, c, d, e, *, g):\n" + "    pass\n" * 40))[0]
    assert func_lines(func) == 41
    assert arg_count(func) == 6

    assert imports_app(ast.parse("from app import app"))
    assert imports_app(ast.parse("import app.settings"))
    assert not imports_app(ast.parse("from .application import run\nimport apple"))

    modules = {"a", "b", "c"}
    assert src_dependencies(ast.parse("from src.b import x\nfrom . import c"), modules) == {
        "b",
        "c",
    }
    assert src_dependencies(ast.parse("from .b import x\nimport src.c"), modules) == {"b", "c"}

    assert find_cycle({"a": {"b"}, "b": {"c"}, "c": {"a"}}) == ["a", "b", "c", "a"]
    assert find_cycle({"a": {"b", "c"}, "b": {"c"}, "c": set()}) == []


def test_file_detectors_catch_violations(tmp_path: Path) -> None:
    long_file = tmp_path / "long.py"
    long_file.write_text("x = 1\n" * (MAX_FILE_LINES + 1), encoding="utf-8")
    assert line_count(long_file) == MAX_FILE_LINES + 1

    nested = tmp_path / "sub" / "deep.py"
    nested.parent.mkdir()
    nested.write_text("", encoding="utf-8")
    assert nested_py_files(tmp_path) == [nested]
