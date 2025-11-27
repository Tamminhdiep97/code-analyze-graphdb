"""
Test script for the graph-based code review experiment
"""
from pathlib import Path
from review_algorithm import ReviewAlgorithm
from graph_builder import GraphBuilder
from signals_extractor import SignalsExtractor
from query_system import QuerySystem
import tempfile


def test_python_code():
    # Test code with various elements
    python_code = '''
def calculate_total(items):
    """Calculate total from a list of items."""
    total = 0
    for item in items:
        total += item.price
    return total

def process_user_data(user_input):
    """Process user data with potential security issue."""
    import os
    os.system("echo " + user_input)  # Potential security issue
    return user_input

class DataProcessor:
    """A simple data processor class."""

    def __init__(self, config):
        self.config = config
        self.data = []

    def add_data(self, item):
        self.data.append(item)
        return len(self.data)

    def process(self):
        result = []
        for item in self.data:
            result.append(item * 2)
        return result

def connect_to_db(password="hardcoded_password123"):
    """Function with hardcoded credential."""
    db_password = password
    return "connected"

def sql_query(user_id):
    """Function with potential SQL injection."""
    query = "SELECT * FROM users WHERE id = " + str(user_id)
    return query
'''

    # Create a temporary file
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

        print(f"Found {len(result.signals)} signals:")
        for signal in result.signals:
            print(f"  - Line {signal.line_no}: [{signal.severity.upper()} {
                  signal.signal_type.value}] {signal.message}")

        print(f"\nFound {len(result.context)} related components:")
        for ctx in result.context:
            print(f"  - {ctx.get('type', 'Unknown')} {ctx.get('name',
                  'Unknown')} at line {ctx.get('line_start', 'Unknown')}")

        # Test query system functionality
        query_system = QuerySystem()

        print(f"\nFunctions called by 'calculate_total':")
        deps = query_system.get_function_dependencies(
            'calculate_total', temp_file_path)
        for dep in deps:
            print(f"  - {dep['name']} in {dep['file_path']
                                          } at line {dep['line_start']}")

        print(f"\nFunctions that call 'calculate_total':")
        callers = query_system.get_function_callers(
            'calculate_total', temp_file_path)
        for caller in callers:
            print(f"  - {caller['name']} in {caller['file_path']
                                             } at line {caller['line_start']}")

        # Test security vulnerability detection
        security_vulns = query_system.get_security_vulnerability_patterns()
        print(f"\nFound {len(security_vulns)
                         } security vulnerability patterns:")
        for vuln in security_vulns:
            print(f"  - Function {vuln['function_name']} in {
                  vuln['file_path']} uses {vuln['dangerous_function']}")

    finally:
        # Clean up the temporary file
        Path(temp_file_path).unlink()


def test_signals_extractor():
    """Test the signals extractor with the same code"""
    python_code = '''
def dangerous_function(user_input):
    eval(user_input)  # Security issue
    
def complex_function(a, b, c, d, e, f, g):
    """Function with too many parameters"""
    return a + b + c + d + e + f + g

def bad_exception_handling():
    try:
        pass
    except:  # Bare except clause
        pass
'''

    extractor = SignalsExtractor()
    signals = extractor.extract_signals(python_code, "/test.py", "python")

    print(f"\nSignals extractor test - found {len(signals)} signals:")
    for signal in signals:
        print(f"  - Line {signal.line_no}: [{signal.severity.upper()} {
              signal.signal_type.value}] {signal.message}")


if __name__ == '__main__':
    test_python_code()
    test_signals_extractor()
