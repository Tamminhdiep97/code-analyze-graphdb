"""
Example to demonstrate the graph-based code review system
"""
from review_algorithm import ReviewAlgorithm
from loguru import logger
import tempfile
import os

def main():
    # Example Python code to review
    python_code = '''
def calculate_total(items):
    """Calculate total from a list of items."""
    total = 0
    for item in items:
        total += item.price
    return total

def process_user_input(user_data):
    """Process user data with potential security issue."""
    query = "SELECT * FROM users WHERE id = " + str(user_data)
    return query

def complex_function(a, b, c, d, e, f, g, h):
    """Function with too many parameters."""
    return a + b + c + d + e + f + g + h

def bad_exception_handling():
    """Function with bad exception handling."""
    try:
        risky_operation()
    except:  # Bare except
        pass

def risky_operation():
    import os
    os.system("echo Hello")  # Potential security issue
'''
    
    logger.info("Running graph-based code review for Python...")
    logger.info("-" * 50)
    
    # Write to a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(python_code)
        temp_file_path = f.name
    
    try:
        # Initialize the review algorithm
        review_algo = ReviewAlgorithm()
        
        # Perform the review
        result = review_algo.review_code(
            code=python_code,
            file_path=temp_file_path,
            language='python'
        )
        
        logger.info(f"Found {len(result.signals)} issues:")
        for signal in result.signals:
            logger.info(f"  - Line {signal.line_no}: [{signal.severity.upper()} {signal.signal_type.value}] {signal.message}")
        
        logger.info(f"\nFound {len(result.context)} related components:")
        for ctx in result.context:
            logger.info(f"  - {ctx.get('type', 'Unknown')} {ctx.get('name', 'Unknown')} at line {ctx.get('line_start', 'Unknown')}")
        
        logger.info(f"\nFound {len(result.relationships)} relationships:")
        for rel in result.relationships:
            logger.info(f"  - Function {rel.get('name', 'Unknown')} in {rel.get('file_path', 'Unknown')} at line {rel.get('line_start', 'Unknown')}")
        
    finally:
        # Clean up
        os.unlink(temp_file_path)

    logger.info("\n" + "="*50)
    
    # Example C code to review
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
    
    logger.info("\nRunning graph-based code review for C...")
    logger.info("-" * 50)
    
    # Write C code to a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
        f.write(c_code)
        temp_c_file_path = f.name
    
    try:
        # Perform the review for C code
        result = review_algo.review_code(
            code=c_code,
            file_path=temp_c_file_path,
            language='c',
            version='c99'
        )
        
        logger.info(f"Found {len(result.signals)} issues:")
        for signal in result.signals:
            logger.info(f"  - Line {signal.line_no}: [{signal.severity.upper()} {signal.signal_type.value}] {signal.message}")
        
        logger.info(f"\nFound {len(result.context)} related components:")
        for ctx in result.context:
            logger.info(f"  - {ctx.get('type', 'Unknown')} {ctx.get('name', 'Unknown')} at line {ctx.get('line_start', 'Unknown')}")
        
        logger.info(f"\nFound {len(result.relationships)} relationships:")
        for rel in result.relationships:
            logger.info(f"  - Function {rel.get('name', 'Unknown')} in {rel.get('file_path', 'Unknown')} at line {rel.get('line_start', 'Unknown')}")
        
    finally:
        # Clean up
        os.unlink(temp_c_file_path)

if __name__ == '__main__':
    main()