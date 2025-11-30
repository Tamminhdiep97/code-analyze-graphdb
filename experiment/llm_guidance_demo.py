"""
Demonstration script showing how to use graph database information 
to guide an LLM for more effective code review.
"""
from pathlib import Path
import tempfile
import os
from typing import Dict, List, Any

from experiment.review_algorithm import ReviewAlgorithm
from experiment.query_system import QuerySystem
from experiment.signals_extractor import Signal


def create_llm_prompt_with_graph_context(
    file_path: str,
    code: str,
    language: str = 'c',
    version: str = 'c99'
) -> str:
    """
    Create a comprehensive prompt for an LLM that includes graph-based context
    """
    # Initialize the review system
    review_algo = ReviewAlgorithm()

    # Process the code to build graph representation
    result = review_algo.review_code(
        code=code,
        file_path=file_path,
        language=language,
        version=version
    )

    # Get related components using the graph query system
    query_system = QuerySystem()

    # Get all related components to the file
    related_components = query_system.get_related_components(file_path)

    # Get function dependencies and callers
    function_names = [comp.get(
        'name') for comp in related_components if comp.get('type') == 'Function']
    all_relationships = []
    for func_name in function_names:
        deps = query_system.get_function_dependencies(func_name, file_path)
        callers = query_system.get_function_callers(func_name, file_path)
        all_relationships.extend(deps)
        all_relationships.extend(callers)

    # Get security vulnerability patterns in the codebase
    security_patterns = query_system.get_security_vulnerability_patterns()

    # Build comprehensive prompt for LLM
    prompt = f"""
CODE REVIEW REQUEST
===================

File to Review: {file_path}
Language: {language}

RAW CODE:
{code}

GRAPH-BASED CONTEXT:
===================

RELATED COMPONENTS IN CODEBASE:
{format_related_components(related_components)}

FUNCTION RELATIONSHIPS:
{format_function_relationships(all_relationships)}

SECURITY PATTERNS IN CODEBASE:
{format_security_patterns(security_patterns)}

REVIEW INSTRUCTIONS FOR LLM:
============================
1. Analyze the raw code for immediate issues
2. Consider the graph context to understand broader impact
3. Check if changes might affect related components
4. Verify against known security patterns in the codebase
5. Consider cross-file dependencies and relationships
6. Assess potential ripple effects based on function call relationships

SPECIFIC AREAS TO FOCUS ON:
- Functions that call or are called by functions in this file
- Variables and data flows between components
- Security patterns that appear elsewhere in the codebase
- Cross-file dependencies and potential impacts

Please provide a comprehensive review considering both the specific code and its relationships in the larger system.
"""

    return prompt


def format_related_components(components: List[Dict[str, Any]]) -> str:
    """Format related components for the prompt"""
    if not components:
        return "No related components found."

    formatted = []
    for comp in components:
        comp_type = comp.get('type', 'Unknown')
        name = comp.get('name', 'Unknown')
        line_start = comp.get('line_start', 'Unknown')
        formatted.append(f"  - {comp_type} {name} at line {line_start}")

    return "\n".join(formatted)


def format_function_relationships(relationships: List[Dict[str, Any]]) -> str:
    """Format function relationships for the prompt"""
    if not relationships:
        return "No function relationships found."

    formatted = []
    seen = set()
    for rel in relationships:
        name = rel.get('name', 'Unknown')
        file_path = rel.get('file_path', 'Unknown')
        line_start = rel.get('line_start', 'Unknown')

        # Use a tuple to avoid duplicates
        key = (name, file_path, line_start)
        if key not in seen:
            seen.add(key)
            formatted.append(
                f"  - Function {name} in {file_path} at line {line_start}")

    return "\n".join(formatted)


def format_security_patterns(patterns: List[Dict[str, Any]]) -> str:
    """Format security patterns for the prompt"""
    if not patterns:
        return "No security patterns found in the codebase."

    formatted = []
    for pattern in patterns:
        func_name = pattern.get('function_name', 'Unknown')
        file_path = pattern.get('file_path', 'Unknown')
        line_start = pattern.get('line_start', 'Unknown')
        dangerous_func = pattern.get(
            'dangerous_function', pattern.get('db_operation', 'Unknown'))

        formatted.append(
            f"  - Function {func_name} in {file_path} at line {line_start} uses {dangerous_func}")

    return "\n".join(formatted)


def demonstrate_llm_guidance():
    """
    Demonstrate how graph-based context can guide LLM code review
    """
    print("Demonstrating Graph-Based LLM Guidance for Code Review")
    print("=" * 60)

    # Example C code to demonstrate
    example_code = '''
#include "math_operations.h"
#include "utils.h"

int main() {
    int a = 5;
    int b = 10;
    int c = 3;

    int sum = add(a, b);
    print_result(sum);

    int product = multiply(sum, c);
    print_result(product);

    int complex_result = calculate_complex(a, b, c);
    print_result(complex_result);

    return 0;
}
'''

    # Write to a temporary file to simulate real workflow
    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write(example_code)
        temp_file_path = f.name

    try:
        print(f"Creating comprehensive prompt for file: {temp_file_path}")
        print("-" * 60)

        # Create the LLM prompt with graph context
        prompt = create_llm_prompt_with_graph_context(
            file_path=temp_file_path,
            code=example_code,
            language='c',
            version='c99'
        )

        print("Generated LLM Prompt with Graph Context:")
        print(prompt)

    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)


def review_multiple_files_with_context(file_paths: List[str], language: str = 'c', version: str = 'c99'):
    """
    Review multiple files and provide cross-file context for LLM
    """
    # First, process all files to build complete graph
    review_algo = ReviewAlgorithm()

    all_signals = []
    all_relationships = []

    for file_path in file_paths:
        with open(file_path, 'r') as f:
            code = f.read()

        result = review_algo.review_code(
            code=code,
            file_path=file_path,
            language=language,
            version=version
        )

        all_signals.extend(result.signals)
        all_relationships.extend(result.relationships)

    # Create comprehensive prompt for all files together
    prompt = f"""
MULTI-FILE CODE REVIEW REQUEST
=============================

FILES TO REVIEW: {", ".join(file_paths)}
LANGUAGE: {language}

COMBINED GRAPH CONTEXT:
======================
Total signals found across all files: {len(all_signals)}
Total relationships found across all files: {len(all_relationships)}

CROSS-FILE RELATIONSHIPS:
- Functions that span multiple files
- Data flows between files
- Dependency chains across the codebase

LLM REVIEW INSTRUCTIONS:
=======================
1. Analyze interdependencies between the files
2. Check for consistency across related functions
3. Identify potential issues in the integration points
4. Review shared data structures and interfaces
5. Assess the overall architecture and design patterns
6. Focus on security implications across file boundaries

Please provide a holistic review of the multi-file system, not just individual files.
"""

    return prompt


if __name__ == "__main__":
    demonstrate_llm_guidance()

    print("\n" + "=" * 60)
    print("Demonstrating Multi-File Review Capability")
    print("=" * 60)

    # List the test files we created
    test_dir = Path("experiment/test_code/c/project_test")
    c_files = list(test_dir.glob("*.c"))

    if c_files:
        print(f"Found {len(c_files)} C files to demonstrate multi-file review:")
        for file in c_files:
            print(f"  - {file}")

        multi_file_prompt = review_multiple_files_with_context(
            [str(f) for f in c_files])
        print("\nMulti-file LLM Prompt:")
        print(multi_file_prompt[:1000] +
              "..." if len(multi_file_prompt) > 1000 else multi_file_prompt)
    else:
        print("No test files found in project_test directory")
