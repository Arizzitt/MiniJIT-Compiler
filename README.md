# MiniJIT Compiler

A Mini Just-In-Time (JIT) Compiler implemented in Python for the **BCSE307P – Compiler Design Lab** at Vellore Institute of Technology.

This project demonstrates core compiler-design concepts through a small custom programming language, including lexical analysis, recursive-descent parsing, Abstract Syntax Tree (AST) construction, three-address intermediate representation, interpretation, runtime profiling, hotspot detection, optimization, generated Python code, correctness checking, and benchmarking.

## Project Overview

Traditional interpreters repeatedly evaluate program statements at runtime. Just-In-Time compilation aims to improve execution by identifying frequently executed code regions and compiling them during execution.

This project implements an educational MiniJIT pipeline to demonstrate these concepts in a small and inspectable system.

### Objectives

- Implement a lexer that converts source characters into tokens.
- Parse statements and arithmetic expressions using recursive descent.
- Construct an Abstract Syntax Tree.
- Generate three-address intermediate representation (IR).
- Execute programs using a baseline interpreter.
- Demonstrate loop profiling and hotspot-threshold detection.
- Explore basic IR optimization.
- Generate and execute equivalent Python source code.
- Compare execution outputs and measure performance.

## System Architecture

```text
Source Program (.mj)
        |
        v
Lexical Analysis
        |
        v
Syntax Analysis
        |
        v
Abstract Syntax Tree (AST)
        |
        v
Intermediate Representation (TAC)
        |
        +----------------------+
        |                      |
        v                      v
Baseline Interpreter     Generated Python Code
        |                      |
        v                      v
Program Output           Program Output
        |                      |
        +----------+-----------+
                   |
                   v
          Correctness Comparison
                   |
                   v
          Performance Benchmark
```

## Technologies Used

- **Language:** Python 3
- **Parsing:** Recursive-descent parser
- **Intermediate representation:** Three-address code
- **Testing:** Output comparison and execution benchmarks
- **Development environment:** macOS Terminal

## Project Files

| File | Purpose |
|---|---|
| `minijit.py` | Main implementation of the compiler pipeline |
| `prog.mj` | Sample program used for demonstrations |
| `cold.mj` | Short-loop test for hotspot-threshold behavior |

## Requirements

- Python 3
- macOS, Linux, or another environment capable of running Python 3

No external Python packages are required by the current implementation.

## Setup and Execution

Clone the repository:

```bash
git clone https://github.com/YOUR-USERNAME/MiniJIT-Compiler.git
cd MiniJIT-Compiler
```

Replace `YOUR-USERNAME` with the GitHub account that owns the repository.

Check the Python version:

```bash
python3 --version
```

Check the syntax of the implementation:

```bash
python3 -m py_compile minijit.py
```

### Available Commands

Run the following commands from the project directory, provided the corresponding options are present in the submitted version of `minijit.py`.

**1. Display lexical tokens**

```bash
python3 minijit.py prog.mj --tokens
```

**2. Display the AST**

```bash
python3 minijit.py prog.mj --ast
```

**3. Generate three-address IR**

```bash
python3 minijit.py prog.mj --ir
```

**4. Execute using the baseline interpreter**

```bash
python3 minijit.py prog.mj --run
```

**5. Display profiler and hotspot information**

```bash
python3 minijit.py prog.mj --profile
```

**6. Display IR before and after optimization**

```bash
python3 minijit.py prog.mj --opt
```

**7. Display generated Python source**

```bash
python3 minijit.py prog.mj --jit-code
```

**8. Compare baseline and generated-code outputs**

```bash
python3 minijit.py prog.mj --compare
```

**9. Benchmark execution and inspect hotspot thresholds**

```bash
python3 minijit.py prog.mj --bench
```

**10. Test a short loop**

```bash
python3 minijit.py cold.mj --profile
```

## Sample Program

The sample program initializes a variable, calculates the sum of integers from 1 through 1000, and prints the result.

```text
x = 0;
for i = 1 to 1000: x = x + i;
print(x);
```

Expected output:

```text
500500
```

The expected result follows from the arithmetic-series formula:

\[
S = \frac{n(n+1)}{2}
\]

For \(n=1000\), the
