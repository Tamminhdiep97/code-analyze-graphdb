"""
Review Algorithm module that performs code review using graph relationships
"""
from typing import List, Dict, Any, Optional
from experiment.ast_parser import ASTParser
from experiment.graph_builder import GraphBuilder
from experiment.signals_extractor import SignalsExtractor, Signal
from experiment.query_system import QuerySystem
from loguru import logger


class ReviewResult:
    """
    Represents the result of a code review
    """

    def __init__(self, file_path: str, signals: List[Signal], context: List[Dict[str, Any]], relationships: List[Dict[str, Any]]):
        self.file_path = file_path
        self.signals = signals  # Issues found in the code
        self.context = context  # Relevant code context
        self.relationships = relationships  # Relationship information


class ReviewAlgorithm:
    """
    Performs code review using graph-based analysis instead of raw code chunks
    """

    def __init__(self,
                 graph_host: str = "localhost",
                 graph_port: int = 9669,
                 user: str = "root",
                 password: str = "password",
                 space: str = "code_graph"):
        self.ast_parser = ASTParser()
        self.graph_builder = GraphBuilder(
            graph_host, graph_port, user, password, space
        )
        self.signals_extractor = SignalsExtractor()
        self.query_system = QuerySystem(
            graph_host, graph_port, user, password, space
        )

    def review_code(self,
                    code: str,
                    file_path: str,
                    language: str,
                    version: Optional[str] = None,
                    changed_functions: Optional[List[str]] = None) -> ReviewResult:
        """
        Perform code review using graph relationships
        """
        # Step 1: Parse the code and build graph representation
        logger.info(f"Building graph for {file_path}")
        self.graph_builder.build_graph_from_ast(
            code, file_path, language, version)

        # Step 2: Extract signals from the code
        logger.info(f"Extracting signals from {file_path}")
        signals = self.signals_extractor.extract_signals(
            code, file_path, language, version)

        # Step 3: Get relevant context based on graph relationships
        logger.info(f"Getting context for {file_path}")
        if changed_functions:
            # If we know specific changed functions, get impacted functions
            context = self.query_system.get_impacted_functions(
                file_path, changed_functions)
        else:
            # Otherwise, get related components
            context = self.query_system.get_related_components(file_path)

        # Step 4: Get function dependencies and callers for relationship analysis
        relationships = []
        if changed_functions:
            for func in changed_functions:
                # Get functions this function calls
                deps = self.query_system.get_function_dependencies(
                    func, file_path)
                # Get functions that call this function
                callers = self.query_system.get_function_callers(
                    func, file_path)
                relationships.extend(deps)
                relationships.extend(callers)
        else:
            # When no specific changed functions are provided, get all relationships for the file
            # Get all functions in the file and their dependencies/callers
            related_components = self.query_system.get_related_components(file_path)
            function_names = [comp.get('name') for comp in related_components if comp.get('type') == 'Function']

            for func_name in function_names:
                # Get functions this function calls
                deps = self.query_system.get_function_dependencies(func_name, file_path)
                # Get functions that call this function
                callers = self.query_system.get_function_callers(func_name, file_path)
                relationships.extend(deps)
                relationships.extend(callers)

        logger.info(f"Review completed for {file_path}")
        return ReviewResult(file_path, signals, context, relationships)

    def review_file_changes(self,
                            file_path: str,
                            old_code: str,
                            new_code: str,
                            language: str,
                            version: Optional[str] = None) -> ReviewResult:
        """
        Review changes in a file by comparing old and new code
        """
        # Determine what functions have changed
        old_ast = self.ast_parser.parse_code(old_code, language, version)
        new_ast = self.ast_parser.parse_code(new_code, language, version)

        changed_functions = self._get_changed_functions(old_ast, new_ast)

        # Perform review on new code with knowledge of changed functions
        return self.review_code(new_code, file_path, language, version, changed_functions)

    def _get_changed_functions(self, old_ast: Any, new_ast: Any) -> List[str]:
        """
        Determine which functions have changed between two ASTs
        Note: This is a simplified implementation
        """
        if old_ast is None or new_ast is None:
            return []

        old_funcs = set()
        new_funcs = set()

        # Extract function names from old AST
        for node in old_ast.body if hasattr(old_ast, 'body') else []:
            if isinstance(node, (old_ast.FunctionDef, getattr(old_ast, 'AsyncFunctionDef', type))):
                if hasattr(node, 'name'):
                    old_funcs.add(node.name)

        # Extract function names from new AST
        for node in new_ast.body if hasattr(new_ast, 'body') else []:
            if isinstance(node, (new_ast.FunctionDef, getattr(new_ast, 'AsyncFunctionDef', type))):
                if hasattr(node, 'name'):
                    new_funcs.add(node.name)

        # Return functions that exist in new AST but not in old AST
        # or that exist in both but have different structure (simplified)
        # For now, return all new functions as potentially changed
        return list(new_funcs)

    def get_security_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get security recommendations based on vulnerability patterns in the codebase
        """
        return self.query_system.get_security_vulnerability_patterns()
