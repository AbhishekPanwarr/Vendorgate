"""Safe policy expression evaluator (whitelist AST)."""

import ast
from typing import Any


class PolicyExpressionError(ValueError):
    pass


_ALLOWED_NODES = (
    ast.Expression,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.UnaryOp,
    ast.Not,
    ast.Compare,
    ast.Eq,
    ast.NotEq,
    ast.In,
    ast.NotIn,
    ast.Gt,
    ast.Lt,
    ast.GtE,
    ast.LtE,
    ast.Name,
    ast.Constant,
    ast.List,
    ast.Tuple,
    ast.Subscript,
    ast.Load,
)


def _resolve_name(name: str, context: dict[str, Any]) -> Any:
    if name not in context:
        raise PolicyExpressionError(f"unknown name: {name}")
    return context[name]


def _eval(node: ast.AST, context: dict[str, Any]) -> Any:
    if isinstance(node, ast.Expression):
        return _eval(node.body, context)
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (str, int, float, bool, type(None))):
            raise PolicyExpressionError("non-primitive constant")
        return node.value
    if isinstance(node, ast.Name):
        return _resolve_name(node.id, context)
    if isinstance(node, ast.List):
        return [_eval(e, context) for e in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_eval(e, context) for e in node.elts)
    if isinstance(node, ast.BoolOp):
        vals = [_eval(v, context) for v in node.values]
        if isinstance(node.op, ast.And):
            out = True
            for v in vals:
                out = out and v
            return out
        out = False
        for v in vals:
            out = out or v
        return out
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _eval(node.operand, context)
    if isinstance(node, ast.Compare):
        left = _eval(node.left, context)
        result = True
        for op, comp in zip(node.ops, node.comparators, strict=True):
            right = _eval(comp, context)
            if isinstance(op, ast.Eq):
                result = result and (left == right)
            elif isinstance(op, ast.NotEq):
                result = result and (left != right)
            elif isinstance(op, ast.In):
                result = result and (left in right)
            elif isinstance(op, ast.NotIn):
                result = result and (left not in right)
            elif isinstance(op, ast.Gt):
                result = result and (left > right)
            elif isinstance(op, ast.Lt):
                result = result and (left < right)
            elif isinstance(op, ast.GtE):
                result = result and (left >= right)
            elif isinstance(op, ast.LtE):
                result = result and (left <= right)
            else:
                raise PolicyExpressionError("comparison not allowed")
            left = right
        return result
    if isinstance(node, ast.Subscript):
        if not isinstance(node.value, ast.Name):
            raise PolicyExpressionError("subscript base must be a context name")
        base = _resolve_name(node.value.id, context)
        key = _eval(node.slice, context)
        try:
            return base[key]
        except Exception as e:
            raise PolicyExpressionError(f"subscript failed: {e}") from e
    raise PolicyExpressionError(f"node not allowed: {type(node).__name__}")


def safe_eval(expr: str, context: dict[str, Any]) -> Any:
    for v in context.values():
        if not isinstance(v, (str, int, float, bool, type(None), list, tuple, dict)):
            raise PolicyExpressionError("context values must be JSON primitives/lists/dicts")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise PolicyExpressionError(f"syntax error: {e}") from e
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise PolicyExpressionError(f"node not allowed: {type(node).__name__}")
        if isinstance(node, ast.Subscript) and not isinstance(node.value, ast.Name):
            raise PolicyExpressionError("subscript base must be a context name")
    return _eval(tree, context)
