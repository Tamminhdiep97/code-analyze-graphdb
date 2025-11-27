# Graph-Based Code Review Experiment

This experiment implements a graph-based approach to code review to handle longer code more effectively than chunk-based approaches.

## Overview

The traditional approach to code review involves processing code in chunks, which can miss relationships between distant code elements. This experiment uses graph databases to store relationships between code elements like functions, variables, classes, and modules.

## Architecture

The system consists of 5 main components:

1. **AST Parser** (`ast_parser.py`): Parses code for different languages and versions (e.g., C90 vs C11)
2. **Graph Builder** (`graph_builder.py`): Creates a graph representation of the code using Neo4j
3. **Signals Extractor** (`signals_extractor.py`): Extracts meaningful patterns and potential issues from the code
4. **Query System** (`query_system.py`): Provides methods to query the graph for relevant code context
5. **Review Algorithm** (`review_algorithm.py`): Performs code review using graph relationships

## Key Features

- **Language Support**: Handles different programming languages and versions (Python and C implemented, others as placeholders)
- **Version-Aware Parsing**: Supports different C language standards (C90, C99, C11, etc.) using libclang
- **Graph Representation**: Stores code relationships in a Neo4j graph database
- **Pattern Recognition**: Identifies security, performance, and code quality issues
- **Context Extraction**: Retrieves relevant code context based on relationships

## Usage

```bash
python main.py <file_path> --language python --version 3.8
```

## Example Output

The system successfully identifies:
- Function call relationships
- Security vulnerabilities (eval, hardcoded passwords, SQL injection)
- Code quality issues (function complexity, exception handling)
- Related code components

## Implementation Details

- Uses Python's built-in `ast` module for parsing
- Stores graph relationships in Neo4j with `py2neo`
- Implements language-version-aware parsing
- Focuses on relationships rather than raw code chunks