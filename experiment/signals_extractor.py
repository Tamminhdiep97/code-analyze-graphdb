"""
Signals Extractor module to identify meaningful patterns in code
"""
import ast
from loguru import logger
from typing import List, Dict, Any, Optional
from enum import Enum

logger = logger  # Use the imported logger


class SignalType(Enum):
    """Types of signals that can be extracted from code"""
    SECURITY = "security"
    PERFORMANCE = "performance"
    CODE_QUALITY = "code_quality"
    BEST_PRACTICE = "best_practice"
    DESIGN = "design"


class Signal:
    """Represents a signal extracted from code"""

    def __init__(self, signal_type: SignalType, message: str, line_no: int, severity: str = "medium"):
        self.signal_type = signal_type
        self.message = message
        self.line_no = line_no
        self.severity = severity  # low, medium, high, critical


class SignalsExtractor:
    """
    Extracts meaningful signals from code based on patterns and rules
    """

    def __init__(self):
        self.signals = []

    def extract_signals(self, code: str, file_path: str, language: str, version: Optional[str] = None) -> List[Signal]:
        """
        Extract signals from the code
        """
        if language.lower() == 'python':
            return self._extract_python_signals(code, file_path)
        elif language.lower() == 'c':
            return self._extract_c_signals(code, file_path, version)
        else:
            logger.warning(
                f"Signals extraction not implemented for language: {language}")
            return []

    def _extract_python_signals(self, code: str, file_path: str) -> List[Signal]:
        """
        Extract signals from Python code
        """
        self.signals = []
        try:
            tree = ast.parse(code)
            self._analyze_tree(tree, file_path)
        except SyntaxError as e:
            logger.error(f"Could not parse Python code: {e}")

        return self.signals

    def _extract_c_signals(self, code: str, file_path: str, version: Optional[str] = None) -> List[Signal]:
        """
        Extract signals from C code using libclang
        """
        self.signals = []

        try:
            from experiment.c_parser import CParser
            from clang.cindex import CursorKind
            c_parser = CParser()
            tu = c_parser.parse_c_code(code, version)

            if tu is None:
                logger.error(f"Could not parse C code: {file_path}")
                return self.signals

            self._analyze_c_ast(tu, file_path)
        except Exception as e:
            logger.error(f"Error extracting signals from C code: {e}")

        return self.signals

    def _analyze_tree(self, tree: ast.AST, file_path: str):
        """
        Analyze the AST to extract signals
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                self._check_function_calls(node)
            elif isinstance(node, ast.BinOp):
                self._check_binary_operations(node)
            elif isinstance(node, ast.Assign):
                self._check_assignments(node)
            elif isinstance(node, ast.Import):
                self._check_imports(node)
            elif isinstance(node, ast.ImportFrom):
                self._check_imports_from(node)
            elif isinstance(node, ast.FunctionDef):
                self._check_function_definition(node)
            elif isinstance(node, ast.Try):
                self._check_exception_handling(node)

    def _check_function_calls(self, call_node: ast.Call):
        """
        Check function calls for potential issues
        """
        if isinstance(call_node.func, ast.Name):
            func_name = call_node.func.id

            # Check for potentially dangerous function calls
            dangerous_functions = {
                'eval': 'Use of eval() is dangerous',
                'exec': 'Use of exec() is dangerous',
                'input': 'Unvalidated user input may pose security risks',
                'compile': 'Dynamically compiled code may pose security risks',
                'open': 'File operation without proper validation',
            }

            if func_name in dangerous_functions:
                self.signals.append(
                    Signal(
                        SignalType.SECURITY,
                        dangerous_functions[func_name],
                        call_node.lineno,
                        "high" if func_name in ['eval', 'exec'] else "medium"
                    )
                )
        elif isinstance(call_node.func, ast.Attribute):
            # Check for attribute function calls like os.system, subprocess calls
            if isinstance(call_node.func.value, ast.Name):
                module_name = call_node.func.value.id
                func_attr = call_node.func.attr

                if (module_name, func_attr) in [('os', 'system'), ('os', 'popen'), ('subprocess', 'call'),
                                                ('subprocess', 'run'), ('subprocess', 'Popen')]:
                    self.signals.append(
                        Signal(
                            SignalType.SECURITY,
                            f"Use of {module_name}.{func_attr}() with potential command injection", call_node.lineno, "high"
                        )
                    )

        # Check for SQL injection patterns
        if self._is_sql_query_pattern(call_node):
            self.signals.append(
                Signal(
                    SignalType.SECURITY,
                    "Potential SQL injection vulnerability detected",
                    call_node.lineno,
                    "high"
                )
            )

    def _is_sql_query_pattern(self, call_node: ast.Call) -> bool:
        """
        Check if function call looks like a SQL query with string concatenation
        """
        # Look for patterns like cursor.execute("SELECT * FROM table WHERE id = " + user_input)
        if isinstance(call_node.func, ast.Attribute):
            if call_node.func.attr.lower() in ['execute', 'query', 'select']:
                if len(call_node.args) > 0:
                    arg = call_node.args[0]
                    if isinstance(arg, ast.BinOp):
                        # Check if operation involves string concatenation
                        if isinstance(arg.op, ast.Add):
                            # If left or right side is a string literal concatenated with a variable
                            return True
        return False

    def _check_binary_operations(self, binop_node: ast.BinOp):
        """
        Check binary operations for potential issues
        """
        # For now, just check string concatenation patterns that might indicate SQL injection
        if isinstance(binop_node.op, ast.Add):
            # Check if this is string concatenation that might be part of a SQL query
            if self._is_possible_sql_concatenation(binop_node):
                self.signals.append(
                    Signal(
                        SignalType.SECURITY,
                        "Potential SQL injection through string concatenation",
                        binop_node.lineno,
                        "high"
                    )
                )

    def _is_possible_sql_concatenation(self, binop_node: ast.BinOp) -> bool:
        """
        Check if binary operation is a string concatenation that might be related to SQL
        """
        # This is a simplified check - in practice, this would be more sophisticated
        # Look for operations that combine string literals with variables
        left_is_str = isinstance(binop_node.left, ast.Str) if hasattr(ast, 'Str') else isinstance(
            binop_node.left, ast.Constant) and isinstance(binop_node.left.value, str)
        right_is_name = isinstance(binop_node.right, ast.Name)

        # Check if left side contains SQL keywords
        if left_is_str:
            if hasattr(ast, 'Str'):
                sql_keywords = ['SELECT', 'INSERT',
                                'UPDATE', 'DELETE', 'FROM', 'WHERE']
                left_val = binop_node.left.s.upper()
            else:
                # For Python 3.8+, Constant is used instead of Str
                if isinstance(binop_node.left, ast.Constant) and isinstance(binop_node.left.value, str):
                    sql_keywords = ['SELECT', 'INSERT', 'UPDATE',
                                    'DELETE', 'FROM', 'WHERE', 'LIKE']
                    left_val = binop_node.left.value.upper()
                else:
                    return False
            return any(keyword in left_val for keyword in sql_keywords) and right_is_name

        return False

    def _check_assignments(self, assign_node: ast.Assign):
        """
        Check assignments for potential issues
        """
        for target in assign_node.targets:
            if isinstance(target, ast.Name):
                # Check for hardcoded credentials
                var_name = target.id.lower()
                if 'password' in var_name or 'secret' in var_name or 'key' in var_name:
                    # Check if it's a string literal assignment
                    if isinstance(assign_node.value, ast.Str) if hasattr(ast, 'Str') else (isinstance(assign_node.value, ast.Constant) and isinstance(assign_node.value.value, str)):
                        self.signals.append(
                            Signal(
                                SignalType.SECURITY,
                                f"Hardcoded credential in variable {target.id}",
                                assign_node.lineno,
                                "high"
                            )
                        )

    def _check_imports(self, import_node: ast.Import):
        """
        Check imports for potential security or quality issues
        """
        for alias in import_node.names:
            module_name = alias.name
            if module_name in ['pickle', 'marshal']:
                self.signals.append(
                    Signal(
                        SignalType.SECURITY,
                        f"Use of {module_name} module can be unsafe with untrusted data",
                        import_node.lineno,
                        "high"
                    )
                )

    def _check_imports_from(self, import_node: ast.ImportFrom):
        """
        Check from ... import ... statements
        """
        if import_node.module:
            module_name = import_node.module
            if module_name in ['pickle', 'marshal']:
                self.signals.append(
                    Signal(
                        SignalType.SECURITY,
                        f"Use of {module_name} module can be unsafe with untrusted data",
                        import_node.lineno,
                        "high"
                    )
                )

    def _check_function_definition(self, func_node: ast.FunctionDef):
        """
        Check function definitions for potential issues
        """
        # Check function complexity (number of parameters)
        if len(func_node.args.args) > 5:
            self.signals.append(
                Signal(
                    SignalType.CODE_QUALITY,
                    f"Function {func_node.name} has {len(func_node.args.args)} parameters, consider reducing",
                    func_node.lineno,
                    "medium"
                )
            )

        # Check for nested functions - may indicate complex logic
        for item in func_node.body:
            if isinstance(item, ast.FunctionDef):
                self.signals.append(
                    Signal(
                        SignalType.CODE_QUALITY,
                        f"Nested function in {func_node.name} may indicate complex logic",
                        item.lineno,
                        "low"
                    )
                )

    def _check_exception_handling(self, try_node: ast.Try):
        """
        Check exception handling for potential issues
        """
        # Check for bare except clauses
        for handler in try_node.handlers:
            if handler.type is None:  # bare except
                self.signals.append(
                    Signal(
                        SignalType.BEST_PRACTICE,
                        "Bare except clause is discouraged, catch specific exceptions",
                        handler.lineno,
                        "medium"
                    )
                )
            elif isinstance(handler.type, ast.Name) and handler.type.id == 'Exception':
                self.signals.append(
                    Signal(
                        SignalType.BEST_PRACTICE,
                        "Catching general Exception is discouraged, catch specific exceptions",
                        handler.lineno,
                        "medium"
                    )
                )

    def _analyze_c_ast(self, tu, file_path: str):
        """
        Analyze C AST to extract signals
        """
        from clang.cindex import CursorKind

        def traverse_c_ast(cursor):
            # Analyze the current node
            self._analyze_c_cursor(cursor, file_path)

            # Recursively analyze children
            for child in cursor.get_children():
                traverse_c_ast(child)

        traverse_c_ast(tu.cursor)

    def _analyze_c_cursor(self, cursor, file_path: str):
        """
        Analyze a single C AST cursor for potential issues
        """
        from clang.cindex import CursorKind

        if cursor.kind == CursorKind.FUNCTION_DECL:
            self._check_c_function(cursor, file_path)
        elif cursor.kind == CursorKind.CALL_EXPR:
            self._check_c_function_call(cursor, file_path)
        elif cursor.kind == CursorKind.BINARY_OPERATOR:
            self._check_c_binary_op(cursor, file_path)
        elif cursor.kind == CursorKind.DECL_STMT and cursor.get_children():
            # Check declarations for unsafe functions
            for child in cursor.get_children():
                if child.kind == CursorKind.VAR_DECL:
                    self._check_c_variable_decl(child, file_path)

    def _check_c_function(self, cursor, file_path: str):
        """
        Check C function for potential issues
        """
        from clang.cindex import CursorKind
        func_name = cursor.spelling
        line_no = cursor.location.line

        # Check for functions with too many parameters
        param_count = 0
        dangerous_params = 0
        for child in cursor.get_children():
            if hasattr(child, 'kind') and child.kind == CursorKind.PARM_DECL:
                param_count += 1
                param_type = str(child.type.spelling).lower()
                # Check for unsafe parameter types
                if 'char *' in param_type or 'char*' in param_type:
                    dangerous_params += 1

        if param_count > 5:
            self.signals.append(
                Signal(
                    SignalType.CODE_QUALITY,
                    f"Function {func_name} has {param_count} parameters, consider reducing",
                    line_no,
                    "medium"
                )
            )

    def _check_c_function_call(self, cursor, file_path: str):
        """
        Check C function calls for potential security issues
        """
        from clang.cindex import CursorKind
        func_name = cursor.spelling
        line_no = cursor.location.line

        # Check for dangerous functions that indicate security vulnerabilities
        dangerous_functions = {
            'gets': ('Use of gets() is dangerous and deprecated', 'critical'),
            'strcpy': ('Use of strcpy() can cause buffer overflows', 'high'),
            'sprintf': ('Use of sprintf() can cause buffer overflows', 'high'),
            'scanf': ('Use of scanf() can cause buffer overflows', 'high'),
            'printf': ('Potential format string vulnerability', 'high'),
            'fprintf': ('Potential format string vulnerability', 'high'),
            'snprintf': ('Potential buffer overflow if size is not properly checked', 'medium'),
            'strcat': ('Use of strcat() can cause buffer overflows', 'high'),
            'realpath': ('Use of realpath() without proper buffer management', 'medium'),
            'getenv': ('Use of getenv() may expose sensitive information', 'medium'),
            'system': ('Use of system() can lead to command injection', 'high'),
            'exec': ('Use of exec() can lead to command injection', 'high'),
        }

        if func_name in dangerous_functions:
            message, severity = dangerous_functions[func_name]
            self.signals.append(
                Signal(
                    SignalType.SECURITY,
                    message,
                    line_no,
                    severity
                )
            )

        # Check for potentially unsafe functions with string arguments
        unsafe_string_funcs = ['strcpy', 'strcat',
                               'sprintf', 'gets', 'scanf', 'fscanf', 'sscanf']
        if func_name in unsafe_string_funcs:
            # Check if the call has string literals that might be unsafe
            for arg in cursor.get_children():
                if hasattr(arg, 'kind') and arg.kind == CursorKind.STRING_LITERAL:
                    # If it's a format string function, check for format issues
                    if func_name in ['printf', 'fprintf', 'sprintf', 'snprintf']:
                        # Check if the string is being used as a format string directly
                        self._check_c_format_string_vulnerability(
                            cursor, arg, line_no)

    def _check_c_format_string_vulnerability(self, cursor, format_arg, line_no: int):
        """
        Check for C format string vulnerabilities
        """
        from clang.cindex import CursorKind
        # Check if the format string is not a literal (vulnerable case)
        if not hasattr(format_arg, 'kind') or format_arg.kind != CursorKind.STRING_LITERAL:
            self.signals.append(
                Signal(
                    SignalType.SECURITY,
                    "Potential format string vulnerability - format string from non-literal source",
                    line_no,
                    "high"
                )
            )

    def _check_c_binary_op(self, cursor, file_path: str):
        """
        Check C binary operations for potential issues
        """
        # This is where we'd check for potential buffer overflows, etc.
        # For now, we'll look for common dangerous patterns
        if str(cursor.kind).endswith('ASSIGNMENT_OPERATOR'):
            # Check for assignment operations that might lead to buffer overflows
            op_str = cursor.displayname
            if op_str in ['+=', '-=', '*=', '/=']:
                # Check for potential integer overflow/underflow
                pass  # Implementation would depend on more complex analysis

    def _check_c_variable_decl(self, cursor, file_path: str):
        """
        Check C variable declarations for potential security issues
        """
        from clang.cindex import CursorKind
        var_name = cursor.spelling
        line_no = cursor.location.line
        var_type = str(cursor.type.spelling)

        # Check for hardcoded credentials in variable names
        var_name_lower = var_name.lower()
        if any(cred in var_name_lower for cred in ['password', 'secret', 'key', 'token', 'passwd']):
            # Check if the variable is assigned a string literal value
            for child in cursor.get_children():
                if hasattr(child, 'kind') and child.kind == CursorKind.STRING_LITERAL:
                    self.signals.append(
                        Signal(
                            SignalType.SECURITY,
                            f"Hardcoded credential in variable {var_name}",
                            line_no,
                            "high"
                        )
                    )
                    break
