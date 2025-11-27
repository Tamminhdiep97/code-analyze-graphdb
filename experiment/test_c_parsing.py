"""
Test script for C parsing functionality in the graph-based code review experiment
"""
from pathlib import Path
from review_algorithm import ReviewAlgorithm
from graph_builder import GraphBuilder
from signals_extractor import SignalsExtractor
from ast_parser import ASTParser
from loguru import logger
import tempfile


def test_c_parsing():
    # Test C code with various elements
    c_code = '''
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

char global_password[] = "hardcoded_secret123";  // Security issue: hardcoded credential

int add_numbers(int a, int b) {
    return a + b;
}

int unsafe_function(char *input) {
    char buffer[10];
    strcpy(buffer, input);  // Security issue: buffer overflow
    return 0;
}

int main() {
    char user_input[100];
    gets(user_input);  // Security issue: dangerous function
    printf(user_input);  // Security issue: format string vulnerability

    int result = add_numbers(5, 10);
    system("echo Hello");  // Security issue: command injection

    return 0;
}
'''

    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write(c_code)
        temp_file_path = f.name

    try:
        logger.info("Testing C parsing functionality...")

        # Test AST parser with C code
        parser = ASTParser()
        ast_result = parser.parse_code(c_code, 'c', 'c99')
        if ast_result:
            logger.success("✓ C code parsing successful")
        else:
            logger.error("✗ C code parsing failed")
            return

        # Test signals extractor with C code
        extractor = SignalsExtractor()
        signals = extractor.extract_signals(c_code, temp_file_path, 'c', 'c99')
        logger.success(f"✓ Found {len(signals)} signals in C code:")
        for signal in signals:
            logger.info(f"  - Line {signal.line_no}: [{signal.severity.upper()} {
                        signal.signal_type.value}] {signal.message}")

        # Test graph builder with C code
        graph_builder = GraphBuilder()
        graph_builder.build_graph_from_ast(c_code, temp_file_path, 'c', 'c99')
        logger.success("✓ C code graph building completed")

        # Test full review algorithm with C code
        review_algo = ReviewAlgorithm()
        result = review_algo.review_code(
            code=c_code,
            file_path=temp_file_path,
            language='c',
            version='c99'
        )

        logger.success(f"✓ C code review completed:")
        logger.info(f"  - Found {len(result.signals)} signals")
        logger.info(f"  - Found {len(result.context)} related components")
        logger.info(f"  - Found {len(result.relationships)} relationships")

        for signal in result.signals:
            logger.info(f"    - Line {signal.line_no}: [{signal.severity.upper()} {
                        signal.signal_type.value}] {signal.message}")

    except Exception as e:
        logger.error(f"✗ Error during C parsing test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up the temporary file
        Path(temp_file_path).unlink()


def test_different_c_versions():
    """Test C parsing with different language versions"""
    simple_c_code = '''
#include <stdio.h>

int main() {
    int x = 10;
    printf("Hello, World! %d\\n", x);
    return 0;
}
'''

    versions = ['c90', 'c99', 'c11']

    logger.info("Testing different C language versions:")
    for version in versions:
        try:
            parser = ASTParser()
            ast_result = parser.parse_code(simple_c_code, 'c', version)
            if ast_result:
                logger.success(f"  ✓ Successfully parsed with {version}")
            else:
                logger.error(f"  ✗ Failed to parse with {version}")
        except Exception as e:
            logger.error(f"  ✗ Error parsing with {version}: {e}")


if __name__ == '__main__':
    test_c_parsing()
    test_different_c_versions()
