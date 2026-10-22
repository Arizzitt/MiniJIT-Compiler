import re
import sys

TOKEN_SPEC = [
    ("NUMBER", r"\d+"),
    ("IDENT", r"[A-Za-z_]\w*"),
    ("OP", r"[+\-*/=]"),
    ("PUNCT", r"[;:(){}]"),
    ("SKIP", r"\s+"),
    ("MISMATCH", r"."),
]

KEYWORDS = {"for", "to", "print"}

def lex(source):
    pattern = "|".join(
        f"(?P<{name}>{regex})" for name, regex in TOKEN_SPEC
    )
    tokens = []
    for match in re.finditer(pattern, source):
        kind, value = match.lastgroup, match.group()
        if kind == "SKIP":
            continue
        if kind == "MISMATCH":
            raise SyntaxError(f"Unexpected character {value!r}")
        if kind == "IDENT" and value in KEYWORDS:
            kind = "KEYWORD"
        tokens.append((kind, value))
    return tokens

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return ("EOF", "")

    def expect(self, kind, value=None):
        token = self.peek()
        if token[0] != kind or (
            value is not None and token[1] != value
        ):
            raise SyntaxError(
                f"Expected {value or kind}, found {token[1]!r}"
            )
        self.pos += 1
        return token

    def program(self):
        statements = []
        while self.peek()[0] != "EOF":
            statements.append(self.statement())
        return ("program", statements)

    def statement(self):
        kind, value = self.peek()

        if (kind, value) == ("KEYWORD", "for"):
            return self.for_statement()

        if (kind, value) == ("KEYWORD", "print"):
            self.expect("KEYWORD", "print")
            self.expect("PUNCT", "(")
            expr = self.expression()
            self.expect("PUNCT", ")")
            self.expect("PUNCT", ";")
            return ("print", expr)

        if kind == "IDENT":
            name = self.expect("IDENT")[1]
            self.expect("OP", "=")
            expr = self.expression()
            self.expect("PUNCT", ";")
            return ("assign", name, expr)

        raise SyntaxError(f"Unexpected token {value!r} in statement")

    def for_statement(self):
        self.expect("KEYWORD", "for")
        variable = self.expect("IDENT")[1]
        self.expect("OP", "=")
        start = self.expression()
        self.expect("KEYWORD", "to")
        end = self.expression()

        # Accept either colon syntax or brace syntax.
        if self.peek() == ("PUNCT", ":"):
            self.expect("PUNCT", ":")
            body = [self.statement()]
        else:
            self.expect("PUNCT", "{")
            body = []
            while self.peek() != ("PUNCT", "}"):
                if self.peek()[0] == "EOF":
                    raise SyntaxError("Missing closing '}'")
                body.append(self.statement())
            self.expect("PUNCT", "}")

        return ("for", variable, start, end, body)

    def expression(self):
        node = self.term()
        while self.peek() in (("OP", "+"), ("OP", "-")):
            op = self.expect("OP")[1]
            node = ("binop", op, node, self.term())
        return node

    def term(self):
        node = self.factor()
        while self.peek() in (("OP", "*"), ("OP", "/")):
            op = self.expect("OP")[1]
            node = ("binop", op, node, self.factor())
        return node

    def factor(self):
        kind, value = self.peek()
        if kind == "NUMBER":
            self.expect("NUMBER")
            return ("num", int(value))
        if kind == "IDENT":
            self.expect("IDENT")
            return ("var", value)
        if (kind, value) == ("PUNCT", "("):
            self.expect("PUNCT", "(")
            node = self.expression()
            self.expect("PUNCT", ")")
            return node
        raise SyntaxError(f"Unexpected {value!r} in expression")

def show(node, depth=0):
    pad = "  " * depth
    kind = node[0]

    if kind == "program":
        print(pad + "Program")
        for statement in node[1]:
            show(statement, depth + 1)
    elif kind == "assign":
        print(pad + f"Assign {node[1]}")
        show(node[2], depth + 1)
    elif kind == "for":
        print(pad + f"For {node[1]}")
        print(pad + "  From:")
        show(node[2], depth + 2)
        print(pad + "  To:")
        show(node[3], depth + 2)
        print(pad + "  Body:")
        for statement in node[4]:
            show(statement, depth + 2)
    elif kind == "print":
        print(pad + "Print")
        show(node[1], depth + 1)
    elif kind == "num":
        print(pad + f"Num({node[1]})")
    elif kind == "var":
        print(pad + f"Var({node[1]})")
    elif kind == "binop":
        print(pad + f"BinOp({node[1]})")
        show(node[2], depth + 1)
        show(node[3], depth + 1)


def generate_ir(ast):
    code = []
    temp_count = 0
    label_count = 0

    def new_temp():
        nonlocal temp_count
        temp_count += 1
        return f"t{temp_count}"

    def new_label():
        nonlocal label_count
        label_count += 1
        return f"L{label_count}"

    def expr(node):
        if node[0] == "num":
            return str(node[1])
        if node[0] == "var":
            return node[1]
        if node[0] == "binop":
            left = expr(node[2])
            right = expr(node[3])
            result = new_temp()
            code.append(f"{result} = {left} {node[1]} {right}")
            return result
        raise ValueError(f"Unsupported expression: {node[0]}")

    def stmt(node):
        if node[0] == "assign":
            code.append(f"{node[1]} = {expr(node[2])}")
        elif node[0] == "print":
            code.append(f"print {expr(node[1])}")
        elif node[0] == "for":
            var = node[1]
            start = expr(node[2])
            end = expr(node[3])
            code.append(f"{var} = {start}")
            begin = new_label()
            finish = new_label()
            code.append(f"{begin}:")
            code.append(f"if {var} > {end} goto {finish}")
            for child in node[4]:
                stmt(child)
            updated = new_temp()
            code.append(f"{updated} = {var} + 1")
            code.append(f"{var} = {updated}")
            code.append(f"goto {begin}")
            code.append(f"{finish}:")
        else:
            raise ValueError(f"Unsupported statement: {node[0]}")

    for item in ast[1]:
        stmt(item)
    return code



def execute_program(ast):
    env = {}
    output = []

    def evaluate(node):
        kind = node[0]

        if kind == "num":
            return node[1]
        if kind == "var":
            name = node[1]
            if name not in env:
                raise ValueError(f"Undefined variable: {name}")
            return env[name]
        if kind == "binop":
            left = evaluate(node[2])
            right = evaluate(node[3])
            op = node[1]

            if op == "+":
                return left + right
            if op == "-":
                return left - right
            if op == "*":
                return left * right
            if op == "/":
                if right == 0:
                    raise ValueError("Division by zero")
                return left / right

        raise ValueError(f"Unsupported expression: {kind}")

    def execute(statement):
        kind = statement[0]

        if kind == "assign":
            env[statement[1]] = evaluate(statement[2])

        elif kind == "print":
            value = evaluate(statement[1])
            output.append(value)
            print(value)

        elif kind == "for":
            variable = statement[1]
            start = evaluate(statement[2])
            end = evaluate(statement[3])

            for value in range(start, end + 1):
                env[variable] = value
                for child in statement[4]:
                    execute(child)

        else:
            raise ValueError(f"Unsupported statement: {kind}")

    for statement in ast[1]:
        execute(statement)

    return env, output



def profile_program(ast, threshold=100):
    loop_counts = 0
    hotspots = 0

    def evaluate(node, env):
        if node[0] == "num":
            return node[1]
        if node[0] == "var":
            return env[node[1]]
        if node[0] == "binop":
            a = evaluate(node[2], env)
            b = evaluate(node[3], env)
            return {
                "+": lambda: a + b,
                "-": lambda: a - b,
                "*": lambda: a * b,
                "/": lambda: a / b,
            }[node[1]]()
        raise ValueError(f"Unsupported expression: {node[0]}")

    env = {}

    print("Runtime profiler started")
    print(f"Hotspot threshold: {threshold} loop iterations")

    for statement in ast[1]:
        if statement[0] == "assign":
            env[statement[1]] = evaluate(statement[2], env)

        elif statement[0] == "for":
            var = statement[1]
            start = evaluate(statement[2], env)
            end = evaluate(statement[3], env)
            iterations = max(0, end - start + 1)
            print(f"Loop detected: {var} = {start} to {end}")
            print(f"Loop iteration count: {iterations}")

            for value in range(start, end + 1):
                env[var] = value
                loop_counts += 1

                for child in statement[4]:
                    if child[0] == "assign":
                        env[child[1]] = evaluate(child[2], env)
                    elif child[0] == "print":
                        print("Loop output:", evaluate(child[1], env))

                if loop_counts == threshold:
                    hotspots += 1
                    print(f"Hotspot detected at iteration {loop_counts}")
                    print("JIT trigger condition reached")

        elif statement[0] == "print":
            print("Program output:", evaluate(statement[1], env))

    print(f"Total loop iterations: {loop_counts}")
    print(f"Hotspots detected: {hotspots}")
    return env


def optimize_ir(instructions):
    import ast as py_ast
    import operator

    folded = []
    constants = {}

    # Constant propagation and folding.
    for instruction in instructions:
        if instruction.endswith(":") or instruction.startswith("goto "):
            folded.append(instruction)
            continue

        if instruction.startswith("if ") or instruction.startswith("print "):
            for name, value in constants.items():
                instruction = instruction.replace(name, str(value))
            folded.append(instruction)
            continue

        if " = " not in instruction:
            folded.append(instruction)
            continue

        target, expression = instruction.split(" = ", 1)

        for name, value in constants.items():
            expression = expression.replace(name, str(value))

        try:
            tree = py_ast.parse(expression, mode="eval")
            value = eval(
                compile(tree, "<constant-expression>", "eval"),
                {"__builtins__": {}},
                {}
            )
            if isinstance(value, (int, float)):
                expression = str(value)
                constants[target] = value
        except Exception:
            constants.pop(target, None)

        folded.append(f"{target} = {expression}")

    # Dead assignment elimination: remove overwritten temporary assignments
    # only when that temporary is never subsequently used.
    used = set()
    for instruction in folded:
        if " = " in instruction:
            rhs = instruction.split(" = ", 1)[1]
            used.update(
                word for word in rhs.replace("+", " ").replace("-", " ")
                .replace("*", " ").replace("/", " ").split()
                if word.startswith("t")
            )
        else:
            used.update(
                word for word in instruction.replace(":", " ").split()
                if word.startswith("t")
            )

    result = []
    for instruction in folded:
        if " = " in instruction:
            target = instruction.split(" = ", 1)[0]
            if target.startswith("t") and target not in used:
                continue
        result.append(instruction)

    return result


def generate_jit_code(ast):
    lines = [
        "def jit_program():",
        "    x = 0",
    ]

    for statement in ast[1]:
        if statement[0] == "for":
            variable = statement[1]
            start = statement[2]
            end = statement[3]

            if start[0] != "num" or end[0] != "num":
                raise ValueError("JIT demo requires constant loop bounds")

            lines.append(
                f"    for {variable} in range({start[1]}, {end[1]} + 1):"
            )

            for child in statement[4]:
                if child[0] == "assign" and child[2][0] == "binop":
                    left = child[2][2]
                    right = child[2][3]
                    if left[0] == "var" and right[0] == "var":
                        lines.append(
                            f"        {child[1]} = {left[1]} "
                            f"{child[2][1]} {right[1]}"
                        )
                    else:
                        raise ValueError("Unsupported JIT expression")
                else:
                    raise ValueError("Unsupported loop body")

        elif statement[0] == "print":
            if statement[1][0] != "var":
                raise ValueError("Unsupported print expression")
            lines.append(f"    print({statement[1][1]})")

        elif statement[0] == "assign":
            if statement[2][0] != "num":
                raise ValueError("Unsupported assignment")
            lines.append(f"    {statement[1]} = {statement[2][1]}")

        else:
            raise ValueError(f"Unsupported statement: {statement[0]}")

    return "\n".join(lines)


def compare_execution(ast):
    import contextlib
    import io

    # Run the baseline interpreter and capture its output.
    baseline_buffer = io.StringIO()
    with contextlib.redirect_stdout(baseline_buffer):
        execute_program(ast)
    baseline_output = baseline_buffer.getvalue().strip()

    # Generate and execute the Python source produced by the JIT stage.
    generated_source = generate_jit_code(ast)
    namespace = {}
    exec(compile(generated_source, "<generated_jit>", "exec"),
         namespace)
    jit_buffer = io.StringIO()
    with contextlib.redirect_stdout(jit_buffer):
        namespace["jit_program"]()
    jit_output = jit_buffer.getvalue().strip()

    print("Correctness comparison: Baseline vs JIT")
    print("Baseline output:", baseline_output)
    print("JIT output:     ", jit_output)
    print("Result:", "PASS - outputs match"
          if baseline_output == jit_output
          else "FAIL - outputs differ")

    return baseline_output == jit_output



def run_benchmark(ast):
    import contextlib
    import io
    import statistics
    import time

    # Prepare both execution paths before measuring.
    generated_source = generate_jit_code(ast)
    namespace = {}
    exec(compile(generated_source, "<generated_jit>", "exec"), namespace)
    jit_function = namespace["jit_program"]

    def baseline_once():
        with contextlib.redirect_stdout(io.StringIO()):
            execute_program(ast)

    def jit_once():
        with contextlib.redirect_stdout(io.StringIO()):
            jit_function()

    # Warm up both paths before collecting measurements.
    for _ in range(3):
        baseline_once()
        jit_once()

    repeats = 20
    baseline_times = []
    jit_times = []

    for _ in range(repeats):
        start = time.perf_counter()
        baseline_once()
        baseline_times.append(time.perf_counter() - start)

        start = time.perf_counter()
        jit_once()
        jit_times.append(time.perf_counter() - start)

    baseline_ms = statistics.median(baseline_times) * 1000
    jit_ms = statistics.median(jit_times) * 1000

    print("Performance comparison (median of 20 runs)")
    print(f"Baseline interpreter: {baseline_ms:.3f} ms")
    print(f"Generated Python code: {jit_ms:.3f} ms")

    if jit_ms > 0:
        print(f"Baseline / generated-code time ratio: {baseline_ms / jit_ms:.2f}x")

    print("\\nHotspot threshold sweep")
    iterations = 0
    for statement in ast[1]:
        if statement[0] == "for":
            start_node, end_node = statement[2], statement[3]
            if start_node[0] == "num" and end_node[0] == "num":
                iterations += max(0, end_node[1] - start_node[1] + 1)

    for threshold in (10, 100, 500, 1000, 1500):
        triggered = iterations >= threshold
        status = "TRIGGERED" if triggered else "NOT TRIGGERED"
        print(
            f"Threshold {threshold:4d}: "
            f"{iterations} iterations -> {status}"
        )

    print("\\nNote: timings are for Python interpreter vs generated Python code.")
    print("They do not measure native machine-code JIT performance.")

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 minijit.py prog.mj --tokens|--ast|--ir|--run|--profile|--opt|--jit-code|--compare")
        return 1

    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            source = f.read()

        tokens = lex(source)
        option = sys.argv[2]

        if option == "--tokens":
            for token in tokens:
                print(token)
        elif option == "--ast":
            show(Parser(tokens).program())
        elif option == "--ir":
            for instruction in generate_ir(Parser(tokens).program()):
                print(instruction)
        elif option == "--opt":
            original = generate_ir(Parser(tokens).program())
            optimized = optimize_ir(original)
            print("IR BEFORE OPTIMIZATION:")
            print("\n".join(original))
            print("\nIR AFTER OPTIMIZATION:")
            print("\n".join(optimized))
        elif option == "--run":
            print("Baseline interpreter output:")
            execute_program(Parser(tokens).program())
        elif option == "--profile":
            profile_program(Parser(tokens).program(), threshold=100)
        elif option == "--jit-code":
            print("Generated JIT code (Python source):")
            print(generate_jit_code(Parser(tokens).program()))
        elif option == "--bench":
            run_benchmark(Parser(tokens).program())
        elif option == "--compare":
            success = compare_execution(Parser(tokens).program())
            return 0 if success else 2
        else:
            print("Unknown option:", option)
            return 1

    except (SyntaxError, OSError, ValueError, NameError, TypeError) as error:
        print("Error:", error)
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
