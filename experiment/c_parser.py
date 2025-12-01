"""
C Parser module using libclang to handle different C language versions
"""
from typing import Optional, Dict, Any
from pathlib import Path
import tempfile
import os

# Import clang only if available
from clang import cindex
from clang.cindex import Index, TranslationUnit, TranslationUnitLoadError
import clang
from loguru import logger


CLANG_AVAILABLE = True


class CParser:
    """
    Parser for C code that handles different language standards (C90, C99, C11, etc.)
    """

    # Mapping of version strings to compiler flags
    C_VERSION_FLAGS = {
        'c90': ['-std=c90'],
        'c99': ['-std=c99'],
        'c11': ['-std=c11'],
        'c17': ['-std=c17'],
        'c2x': ['-std=c2x'],  # Experimental C2x standard
        'gnu90': ['-std=gnu90'],
        'gnu99': ['-std=gnu99'],
        'gnu11': ['-std=gnu11'],
        'gnu17': ['-std=gnu17'],
    }

    def __init__(self):
        if not CLANG_AVAILABLE:
            logger.error(
                "libclang is not available. Please install python-clang and libclang.")
            raise ImportError(
                "libclang is not available. Please install python-clang and libclang.")

        # Try to automatically set the libclang library file if not already set
        try:
            # This might already be configured, but if not, we can try to auto-detect
            if not cindex.Config.loaded:
                # Look for common locations of libclang
                possible_paths = [
                    # Ubuntu/Debian specific paths (most recent first)
                    '/usr/lib/x86_64-linux-gnu/libclang-15.so.1',
                    '/usr/lib/x86_64-linux-gnu/libclang-14.so.1',
                    '/usr/lib/x86_64-linux-gnu/libclang-13.so.1',
                    '/usr/lib/x86_64-linux-gnu/libclang-12.so.1',
                    '/usr/lib/x86_64-linux-gnu/libclang-11.so.1',
                    '/usr/lib/x86_64-linux-gnu/libclang-10.so.1',
                    '/usr/lib/x86_64-linux-gnu/libclang-9.so.1',
                    # Generic path
                    '/usr/lib/x86_64-linux-gnu/libclang.so',
                    # LLVM paths (most recent first)
                    '/usr/lib/llvm-15/lib/libclang.so.1',
                    '/usr/lib/llvm-14/lib/libclang.so.1',
                    '/usr/lib/llvm-13/lib/libclang.so.1',
                    '/usr/lib/llvm-12/lib/libclang.so.1',
                    '/usr/lib/llvm-11/lib/libclang.so.1',
                    '/usr/lib/llvm-10/lib/libclang.so.1',
                    # Homebrew on macOS
                    '/opt/homebrew/lib/libclang.dylib',
                    '/usr/local/opt/llvm/lib/libclang.dylib',
                    # Other possible locations
                    '/usr/local/lib/libclang.so',
                    '/usr/local/lib/libclang.dylib',
                ]

                for path in possible_paths:
                    if os.path.exists(path):
                        cindex.Config.set_library_file(path)
                        logger.info(f"Set libclang library file to: {path}")
                        break
        except Exception as e:
            logger.warning(
                f"Could not automatically set libclang library file: {e}")
            logger.info(
                "Make sure libclang library is installed and accessible")

        try:
            self.index = Index.create()
        except Exception as e:
            logger.error(f"Failed to create Clang Index: {e}")
            logger.info(
                "Make sure libclang development libraries are installed (e.g., libclang-12-dev on Ubuntu)")
            raise

    def parse_c_code(self, code: str, version: Optional[str] = None) -> Optional['TranslationUnit']:
        """
        Parse C code with specific language version
        """
        if version is None:
            version = 'c11'  # Default to C11

        version_lower = version.lower()
        if version_lower not in self.C_VERSION_FLAGS:
            raise ValueError(f"Unsupported C version: {version}. Supported versions: {
                             list(self.C_VERSION_FLAGS.keys())}")

        # Write code to a temporary file as libclang requires a file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
            f.write(code)
            temp_file_path = f.name

        try:
            # Get the compilation flags
            args = self.C_VERSION_FLAGS[version_lower]

            # Parse the translation unit
            tu = self.index.parse(
                temp_file_path,
                args=args,
                options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
            )

            # Check for parsing errors
            diagnostics = list(tu.diagnostics)
            if diagnostics:
                for diag in diagnostics:
                    if diag.severity >= 3:  # Error level
                        logger.error(f"Parsing error: {
                                     diag.spelling} at {diag.location}")
                        return None
                    else:
                        # Log warnings but don't fail
                        logger.warning(f"Parsing warning: {
                                       diag.spelling} at {diag.location}")

            return tu

        except TranslationUnitLoadError as e:
            logger.error(f"Failed to parse C code: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during C parsing: {e}")
            return None
        finally:
            # Clean up the temporary file
            import os
            os.unlink(temp_file_path)

    def get_ast_nodes(self, tu: 'TranslationUnit'):
        """
        Generator that yields AST nodes from the translation unit
        """
        if tu is None:
            return

        def traverse_ast(cursor, level=0):
            yield cursor
            for child in cursor.get_children():
                yield from traverse_ast(child, level + 1)

        yield from traverse_ast(tu.cursor)

    def extract_functions(self, tu: 'TranslationUnit') -> list:
        """
        Extract function definitions from the C code
        """
        from clang.cindex import CursorKind

        functions = []
        for node in self.get_ast_nodes(tu):
            if node.kind == CursorKind.FUNCTION_DECL:
                func_info = {
                    'name': node.spelling,
                    'line': node.location.line,
                    'column': node.location.column,
                    'file': node.location.file.name if node.location.file else 'unknown',
                    'is_definition': node.is_definition(),
                    'return_type': str(node.result_type.spelling),
                    'parameters': []
                }

                # Get parameters
                for child in node.get_children():
                    if child.kind == CursorKind.PARM_DECL:
                        param_info = {
                            'name': child.spelling,
                            'type': str(child.type.spelling),
                            'line': child.location.line
                        }
                        func_info['parameters'].append(param_info)

                functions.append(func_info)

        return functions

    def extract_variables(self, tu: 'TranslationUnit') -> list:
        """
        Extract variable declarations from the C code
        """
        from clang.cindex import CursorKind

        variables = []
        for node in self.get_ast_nodes(tu):
            if node.kind in (CursorKind.VAR_DECL, CursorKind.PARM_DECL):
                var_info = {
                    'name': node.spelling,
                    'type': str(node.type.spelling),
                    'line': node.location.line,
                    'column': node.location.column,
                    'file': node.location.file.name if node.location.file else 'unknown',
                    'is_local': node.semantic_parent.kind == CursorKind.FUNCTION_DECL
                }
                variables.append(var_info)

        return variables

    def extract_includes(self, tu: 'TranslationUnit') -> list:
        """
        Extract include statements from the C code
        """
        from clang.cindex import CursorKind

        includes = []
        for node in self.get_ast_nodes(tu):
            if node.kind == CursorKind.INCLUSION_DIRECTIVE:
                include_info = {
                    'file': node.spelling,
                    'line': node.location.line,
                    'is_angled': '<' in node.spelling  # Indicates #include <...> vs #include "..."
                }
                includes.append(include_info)

        return includes

# Example usage and test function


def test_c_parsing():
    """
    Test the C parser with different versions
    """
    sample_c_code = """
#include <stdio.h>

int global_var = 42;

int add(int a, int b) {
    int result = a + b;
    return result;
}

int main() {
    int x = 10;
    int y = 20;
    int sum = add(x, y);
    printf("Sum: %d\\n", sum);
    return 0;
}
"""

    if not CLANG_AVAILABLE:
        logger.info("Cannot test C parsing - libclang not available")
        return

    parser = CParser()

    # Test different C versions
    versions = ['c90', 'c99', 'c11']
    for version in versions:
        logger.info(f"\nTesting C parsing with version {version}:")
        try:
            tu = parser.parse_c_code(sample_c_code, version)
            if tu:
                logger.info(f"  Successfully parsed with {version}")

                # Extract functions
                functions = parser.extract_functions(tu)
                logger.info(f"  Found {len(functions)} functions:")
                for func in functions:
                    params = ', '.join([p['type'] for p in func['parameters']])
                    logger.info(f"    - {func['name']}({params}) at line {func['line']}")

                # Extract variables
                variables = parser.extract_variables(tu)
                logger.info(f"  Found {len(variables)} variables:")
                for var in variables[:3]:  # Just show first 3
                    logger.info(f"    - {var['name']} ({var['type']}) at line {var['line']}")

            else:
                logger.info(f"  Failed to parse with {version}")
        except Exception as e:
            logger.info(f"  Error parsing with {version}: {e}")


if __name__ == "__main__":
    test_c_parsing()
