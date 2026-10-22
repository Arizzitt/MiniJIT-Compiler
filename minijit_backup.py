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

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 minijit.py prog.mj --tokens|--ast")
        return 1

    try:
        with open(sys.argv[1], encoding="utf-8") as source_file:
            source = source_file.read()

        tokens = lex(source)
        if sys.argv[2] == "--tokens":
            for token in tokens:
                print(token)
        elif sys.argv[2] == "--ast":
            show(Parser(tokens).program())
        else:
        elif sys.argv[2] == "--ir":
            ast = Parser(tokens).program()
            for instruction in generate_ir(ast):
                print(instruction)
            print("Unknown option:", sys.argv[2])
            return 1
    except (SyntaxError, OSError) as error:
        print("Error:", error)
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
