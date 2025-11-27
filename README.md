# CodeReview_engineer - Graph-Based Code Review System

## Overview
This is a graph-based code review system that uses graph databases to store and analyze relationships between code elements like functions, variables, classes, and modules. It's designed to handle longer code more effectively than traditional chunk-based approaches.

## Key Components

1. **AST Parser** (`ast_parser.py`): Parses code for different languages and versions (Python and C implemented, others as placeholders)

2. **Graph Builder** (`graph_builder.py`): Creates a graph representation of the code using Nebula Graph (a graph database)

3. **Signals Extractor** (`signals_extractor.py`): Extracts meaningful patterns and potential issues from the code

4. **Query System** (`query_system.py`): Provides methods to query the graph for relevant code context

5. **Review Algorithm** (`review_algorithm.py`): Performs code review using graph relationships

## Features

- **Multi-language Support**: Handles Python and C with version-specific parsing (C90, C99, C11, etc.)
- **Graph Representation**: Stores code relationships in Nebula Graph with vertices for functions, variables, classes, etc.
- **Security Analysis**: Identifies potential security vulnerabilities (dangerous functions, SQL injection, hardcoded credentials)
- **Code Quality Checks**: Analyzes function complexity, exception handling, and best practices
- **Relationship Analysis**: Tracks function calls, dependencies, and impacted components

## Architecture
- Uses Python's `ast` module for Python parsing
- Uses `libclang` for C parsing with version-specific standards
- Stores graph relationships in Nebula Graph using `nebula3-python`
- Implements language-version-aware parsing

## Deployment
- Docker-based setup with proper LLVM/Clang 16 installation
- Docker Compose for orchestration
- Makes use of external Nebula Graph instance

The project is well-structured with a focus on using graph databases to understand code relationships better than traditional approaches, which is particularly useful for identifying how changes in one part of the codebase might impact other parts.