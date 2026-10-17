"""Small tools whose answers can be checked without calling an LLM."""

import ast
import math
import operator
import re


OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}


def _evaluate(node):
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        value = node.value
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _evaluate(node.operand)
        if isinstance(node.op, ast.USub):
            value = -value
    elif isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
        left, right = _evaluate(node.left), _evaluate(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("Use an exponent between -100 and 100.")
        value = OPERATORS[type(node.op)](left, right)
    else:
        raise ValueError("Only numbers, parentheses and + - * / // % ** are allowed.")
    if isinstance(value, complex) or not math.isfinite(value) or abs(value) > 1e100:
        raise ValueError("The result must be a finite real number no larger than 1e100.")
    return value


def calculate(expression: str) -> dict:
    """Evaluate arithmetic safely. Use ** for powers and amount * rate / 100 for percentages.

    Args:
        expression: Arithmetic using numbers, parentheses, +, -, *, /, //, %, **.
    """
    if not isinstance(expression, str) or not expression.strip():
        return {"status": "error", "error": "Enter a nonempty arithmetic expression."}
    if len(expression) > 500:
        return {"status": "error", "error": "Keep expressions under 501 characters."}
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        if sum(1 for _ in ast.walk(tree)) > 100:
            raise ValueError("The expression has too many operations.")
        result = _evaluate(tree.body)
        return {"status": "success", "expression": expression, "result": result}
    except (SyntaxError, ValueError, TypeError, ZeroDivisionError, OverflowError,
            RecursionError) as error:
        return {"status": "error", "error": str(error)}


def analyze_text(text: str) -> dict:
    """Count characters, words and sentences in the exact input text.

    Args:
        text: The text to count, preserving its spaces and punctuation.

    Characters include spaces and punctuation. Words are whitespace-separated
    tokens containing a letter or number. Sentences are nonempty letter/number
    segments separated by . ! or ?. An unfinished final sentence counts too.
    This simple rule is not a linguistic parser; abbreviations can overcount.
    """
    if not isinstance(text, str):
        return {"status": "error", "error": "Text must be a string."}
    words = sum(any(char.isalnum() for char in word) for word in text.split())
    sentences = sum(
        any(char.isalnum() for char in part)
        for part in re.split(r"[.!?]+", text)
    )
    return {
        "status": "success",
        "character_count": len(text),
        "word_count": words,
        "sentence_count": sentences,
    }
