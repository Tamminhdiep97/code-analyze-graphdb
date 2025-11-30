# Code_engineer - Graph-Based Code System

## Overview
This is a graph-based code system that uses graph databases to store and analyze relationships between code elements like functions, variables, classes, and modules. It's designed to handle longer code more effectively than traditional chunk-based approaches. The system can analyze multiple interconnected files and provides comprehensive context for code review and analysis.

## Key Components

1. **AST Parser** (`ast_parser.py`): Parses code for different languages and versions (Python and C implemented, others as placeholders)

2. **Graph Builder** (`graph_builder.py`): Creates a graph representation of the code using Nebula Graph (a graph database)

3. **Signals Extractor** (`signals_extractor.py`): Extracts meaningful patterns and potential issues from the code

4. **Query System** (`query_system.py`): Provides methods to query the graph for relevant code context

5. **Review Algorithm** (`review_algorithm.py`): Performs code analyze using graph relationships

6. **LLM Guidance Demo** (`llm_guidance_demo.py`): Demonstrates how to leverage graph database information to provide comprehensive context for LLM-based code review

## Features

- **Multi-language Support**: Handles Python and C with version-specific parsing (C90, C99, C11, etc.)
- **Multi-file Analysis**: Can process multiple interconnected source files and analyze relationships across files
- **Graph Representation**: Stores code relationships in Nebula Graph with vertices for functions, variables, classes, etc.
- **Security Analysis**: Identifies potential security vulnerabilities (dangerous functions, SQL injection, hardcoded credentials)
- **Code Quality Checks**: Analyzes function complexity, exception handling, and best practices
- **Relationship Analysis**: Tracks function calls, dependencies, and impacted components
- **LLM Guidance**: Provides structured context from the graph database to guide LLM-based code review

## Architecture
- Uses Python's `ast` module for Python parsing
- Uses `libclang` for C parsing with version-specific standards
- Stores graph relationships in Nebula Graph using `nebula3-python`
- Implements language-version-aware parsing
- Provides graph-based context for enhanced LLM code analysis

## LLM Code Review Guidance

The system provides comprehensive context for LLM-based code review by extracting and organizing information from the graph database:

- **Cross-file Dependencies**: Shows relationships between functions across different files
- **Call Graph Analysis**: Provides information about which functions call the reviewed function and which functions it calls
- **Security Patterns**: Identifies known security vulnerability patterns in the codebase
- **Data Flow Information**: Shows how data flows through the system
- **Related Components**: Lists all related code components that might be affected by changes

To demonstrate this capability, run the guidance demo:
```bash
python -m experiment.llm_guidance_demo
```

## Deployment
- Docker-based setup with proper LLVM/Clang 16 installation
- Docker Compose for orchestration
- Makes use of external Nebula Graph instance

The project is well-structured with a focus on using graph databases to understand code relationships better than traditional approaches, which is particularly useful for identifying how changes in one part of the codebase might impact other parts.
