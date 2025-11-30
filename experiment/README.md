# Graph-Based Code Review Experiment

This experiment implements a graph-based approach to code review to handle longer code more effectively than chunk-based approaches. The system can analyze multiple interconnected files and provides comprehensive context for code review and analysis.

## Overview

The traditional approach to code review involves processing code in chunks, which can miss relationships between distant code elements. This experiment uses graph databases to store relationships between code elements like functions, variables, classes, and modules.

## Architecture

The system consists of 6 main components:

1. **AST Parser** (`ast_parser.py`): Parses code for different languages and versions (e.g., C90 vs C11)
2. **Graph Builder** (`graph_builder.py`): Creates a graph representation of the code using Nebula Graph
3. **Signals Extractor** (`signals_extractor.py`): Extracts meaningful patterns and potential issues from the code
4. **Query System** (`query_system.py`): Provides methods to query the graph for relevant code context
5. **Review Algorithm** (`review_algorithm.py`): Performs code review using graph relationships
6. **LLM Guidance Demo** (`llm_guidance_demo.py`): Demonstrates how to leverage graph database information to provide comprehensive context for LLM-based code review

## Key Features

- **Language Support**: Handles different programming languages and versions (Python and C implemented, others as placeholders)
- **Multi-file Analysis**: Can process multiple interconnected source files and analyze relationships across files
- **Version-Aware Parsing**: Supports different C language standards (C90, C99, C11, etc.) using libclang
- **Graph Representation**: Stores code relationships in a Nebula Graph database
- **Pattern Recognition**: Identifies security, performance, and code quality issues
- **Context Extraction**: Retrieves relevant code context based on relationships
- **LLM Guidance**: Provides structured context from the graph database to guide LLM-based code review

## Usage

```bash
python main.py <file_path> --language python --version 3.8
```

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

## Example Output

The system successfully identifies:
- Function call relationships
- Security vulnerabilities (eval, hardcoded passwords, SQL injection)
- Code quality issues (function complexity, exception handling)
- Related code components

## Implementation Details

- Uses Python's built-in `ast` module for parsing
- Uses `libclang` for C parsing with version-specific standards
- Stores graph relationships in Nebula Graph with `nebula3-python`
- Implements language-version-aware parsing
- Provides graph-based context for enhanced LLM code analysis
- Focuses on relationships rather than raw code chunks