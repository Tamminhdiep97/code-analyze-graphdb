"""
Graph Builder module to create graph representations from AST
"""
import ast
from typing import Dict, List, Any, Optional
from nebula3.gclient.net import ConnectionPool
from nebula3.Config import Config
from nebula3.common import ttypes
from nebula3.graph import ttypes as graph_ttypes
from loguru import logger
from clang.cindex import CursorKind

class GraphBuilder:
    """
    Builds a graph representation from parsed code ASTs
    """

    @staticmethod
    def _sanitize_vertex_id(file_path: str) -> str:
        """
        Sanitize file path to create safe vertex IDs for Nebula Graph
        Replace special characters that could interfere with queries
        """
        import re
        # Replace path separators with underscores
        safe_id = file_path.replace('/', '_').replace('\\', '_')
        # Remove or replace any characters that could cause issues in queries
        # Only allow alphanumeric characters and underscore to prevent syntax errors
        safe_id = re.sub(r'[^a-zA-Z0-9_]', '_', safe_id)
        return safe_id

    def __init__(self, graph_host: str = "localhost", graph_port: int = 9669, user: str = "root", password: str = "password", space: str = "code_graph"):
        """
        Initialize the graph builder with connection to Nebula Graph
        """
        self.space = space
        logger.info(f"Initializing GraphBuilder with host={graph_host}, port={graph_port}, space={space}")

        # Initialize connection pool
        self.config = Config()
        self.config.max_connection_pool_size = 10
        self.connection_pool = ConnectionPool()
        logger.info("Attempting to initialize connection pool...")
        if not self.connection_pool.init([(graph_host, graph_port)], self.config):
            logger.error("Failed to initialize connection pool")
            raise Exception("Failed to initialize connection pool")
        logger.info("Connection pool initialized successfully")

        logger.info(f"Attempting to get session with user {user}...")
        self.session = self.connection_pool.get_session(user, password)
        logger.info("Session obtained successfully")

        # Create space if it doesn't exist
        logger.info("Creating space if it doesn't exist...")
        self._create_space()

        # Use the space
        logger.info(f"Using space {space}")
        use_result = self.session.execute(f'USE {space};')
        if use_result.is_succeeded():
            logger.info(f"Successfully switched to space {space}")
        else:
            logger.error(f"Failed to switch to space {space}: {use_result.error_msg()}")
            raise Exception(f"Failed to switch to space {space}: {use_result.error_msg()}")

    def _create_space(self):
        """
        Create the graph space if it doesn't exist
        """
        try:
            logger.info(f"Creating space {self.space} if it doesn't exist")
            # Create space for code graph with larger vertex ID size to accommodate longer vertex IDs
            create_space_query = f'''
            CREATE SPACE IF NOT EXISTS {self.space} (
                partition_num = 1,
                replica_factor = 1,
                vid_type = FIXED_STRING(256)
            );
            '''
            logger.info(f"Executing space creation query: {create_space_query}...")
            result = self.session.execute(create_space_query)
            if result.is_succeeded():
                logger.info(f"Successfully created or verified space {self.space}")
            else:
                logger.error(f"Failed to create space: {result.error_msg()}")
                raise Exception(f"Failed to create space: {result.error_msg()}")

            # Wait a bit for space creation to complete
            import time
            logger.info("Waiting for space creation to complete...")
            time.sleep(5)  # Increased wait time to ensure space is fully ready

            # Verify that the space exists before creating schema
            logger.info("Verifying space exists before schema creation...")
            try:
                # Try to switch to the space to verify it's ready
                verify_result = self.session.execute(f"USE {self.space};")
                if verify_result.is_succeeded():
                    logger.info(f"Successfully verified and switched to space {self.space}")
                    # Switch back to the original context
                    self.session.execute("USE system;")  # Switch back to system space
                else:
                    logger.error(f"Could not access space {self.space}: {verify_result.error_msg()}")
                    raise Exception(f"Space {self.space} was not created properly: {verify_result.error_msg()}")
            except Exception as e:
                logger.warning(f"Could not verify space exists due to: {e}, continuing with schema creation...")
                # If verification fails, still continue with schema creation since space was created

            # Now create the schema (tags and edges)
            logger.info("Creating schema (tags and edges)...")
            self._create_schema()
        except Exception as e:
            logger.error(f"Error creating space: {e}")
            raise

    def _create_schema(self):
        """
        Create tags and edges for efficient querying in Nebula
        """
        try:
            logger.info(f"Using space {self.space} for schema creation")
            # Use the space first - with retry logic in case space is not fully ready
            use_result = None
            for attempt in range(5):  # Try up to 5 times
                use_result = self.session.execute(f'USE {self.space};')
                if use_result.is_succeeded():
                    logger.info("Successfully switched to space for schema creation")
                    break
                else:
                    logger.warning(f"Attempt {attempt + 1} to use space failed: {use_result.error_msg()}")
                    import time
                    time.sleep(2)  # Wait before retry
            else:
                # If all attempts failed
                logger.error(f"Failed to use space {self.space} after 5 attempts: {use_result.error_msg()}")
                raise Exception(f"Failed to use space {self.space} after 5 attempts: {use_result.error_msg()}")

            # Create tags for different code entities
            logger.info("Creating File tag...")
            file_tag_query = '''CREATE TAG IF NOT EXISTS File (`path` string);'''
            result = self.session.execute(file_tag_query)
            if result.is_succeeded():
                logger.info("Successfully created File tag")
            else:
                logger.error(f"Failed to create File tag: {result.error_msg()}")
                raise Exception(f"Failed to create File tag: {result.error_msg()}")

            logger.info("Creating Function tag...")
            function_tag_query = '''
            CREATE TAG IF NOT EXISTS Function (name string, file_path string, line_start int, line_end int, docstring string);
            '''
            result = self.session.execute(function_tag_query)
            if result.is_succeeded():
                logger.info("Successfully created Function tag")
            else:
                logger.error(f"Failed to create Function tag: {result.error_msg()}")
                raise Exception(f"Failed to create Function tag: {result.error_msg()}")

            logger.info("Creating Variable tag...")
            variable_tag_query = '''
            CREATE TAG IF NOT EXISTS Variable (name string, scope string, function_name string, file_path string, type string, line_start int);
            '''
            result = self.session.execute(variable_tag_query)
            if result.is_succeeded():
                logger.info("Successfully created Variable tag")
            else:
                logger.error(f"Failed to create Variable tag: {result.error_msg()}")
                raise Exception(f"Failed to create Variable tag: {result.error_msg()}")

            logger.info("Creating Class tag...")
            class_tag_query = '''
            CREATE TAG IF NOT EXISTS Class (name string, file_path string, line_start int, line_end int);
            '''
            result = self.session.execute(class_tag_query)
            if result.is_succeeded():
                logger.info("Successfully created Class tag")
            else:
                logger.error(f"Failed to create Class tag: {result.error_msg()}")
                raise Exception(f"Failed to create Class tag: {result.error_msg()}")

            logger.info("Creating Method tag...")
            method_tag_query = '''
            CREATE TAG IF NOT EXISTS Method (name string, class_name string, file_path string, line_start int, line_end int);
            '''
            result = self.session.execute(method_tag_query)
            if result.is_succeeded():
                logger.info("Successfully created Method tag")
            else:
                logger.error(f"Failed to create Method tag: {result.error_msg()}")
                raise Exception(f"Failed to create Method tag: {result.error_msg()}")

            logger.info("Creating Parameter tag...")
            parameter_tag_query = '''
            CREATE TAG IF NOT EXISTS Parameter (name string, type string, function_name string, file_path string);
            '''
            result = self.session.execute(parameter_tag_query)
            if result.is_succeeded():
                logger.info("Successfully created Parameter tag")
            else:
                logger.error(f"Failed to create Parameter tag: {result.error_msg()}")
                raise Exception(f"Failed to create Parameter tag: {result.error_msg()}")

            logger.info("Creating Module tag...")
            module_tag_query = '''
            CREATE TAG IF NOT EXISTS Module (name string, as_name string, file_path string);
            '''
            result = self.session.execute(module_tag_query)
            if result.is_succeeded():
                logger.info("Successfully created Module tag")
            else:
                logger.error(f"Failed to create Module tag: {result.error_msg()}")
                raise Exception(f"Failed to create Module tag: {result.error_msg()}")

            logger.info("Creating Import tag...")
            import_tag_query = '''
            CREATE TAG IF NOT EXISTS Import (name string, as_name string, module string, file_path string);
            '''
            result = self.session.execute(import_tag_query)
            if result.is_succeeded():
                logger.info("Successfully created Import tag")
            else:
                logger.error(f"Failed to create Import tag: {result.error_msg()}")
                raise Exception(f"Failed to create Import tag: {result.error_msg()}")

            logger.info("Creating Struct tag...")
            struct_tag_query = '''
            CREATE TAG IF NOT EXISTS Struct (name string, file_path string, line int, column int);
            '''
            result = self.session.execute(struct_tag_query)
            if result.is_succeeded():
                logger.info("Successfully created Struct tag")
            else:
                logger.error(f"Failed to create Struct tag: {result.error_msg()}")
                raise Exception(f"Failed to create Struct tag: {result.error_msg()}")

            logger.info("Creating Include tag...")
            include_tag_query = '''
            CREATE TAG IF NOT EXISTS Include (file string, file_path string, line int);
            '''
            result = self.session.execute(include_tag_query)
            if result.is_succeeded():
                logger.info("Successfully created Include tag")
            else:
                logger.error(f"Failed to create Include tag: {result.error_msg()}")
                raise Exception(f"Failed to create Include tag: {result.error_msg()}")

            # Create edge types for relationships
            logger.info("Creating CONTAINS edge...")
            contains_edge_query = '''
            CREATE EDGE IF NOT EXISTS CONTAINS ();
            '''
            result = self.session.execute(contains_edge_query)
            if result.is_succeeded():
                logger.info("Successfully created CONTAINS edge")
            else:
                logger.error(f"Failed to create CONTAINS edge: {result.error_msg()}")
                raise Exception(f"Failed to create CONTAINS edge: {result.error_msg()}")

            logger.info("Creating HAS_PARAMETER edge...")
            has_parameter_edge_query = '''
            CREATE EDGE IF NOT EXISTS HAS_PARAMETER ();
            '''
            result = self.session.execute(has_parameter_edge_query)
            if result.is_succeeded():
                logger.info("Successfully created HAS_PARAMETER edge")
            else:
                logger.error(f"Failed to create HAS_PARAMETER edge: {result.error_msg()}")
                raise Exception(f"Failed to create HAS_PARAMETER edge: {result.error_msg()}")

            logger.info("Creating CALLS edge...")
            calls_edge_query = '''
            CREATE EDGE IF NOT EXISTS CALLS ();
            '''
            result = self.session.execute(calls_edge_query)
            if result.is_succeeded():
                logger.info("Successfully created CALLS edge")
            else:
                logger.error(f"Failed to create CALLS edge: {result.error_msg()}")
                raise Exception(f"Failed to create CALLS edge: {result.error_msg()}")

            logger.info("Creating IMPORTS edge...")
            imports_edge_query = '''
            CREATE EDGE IF NOT EXISTS IMPORTS ();
            '''
            result = self.session.execute(imports_edge_query)
            if result.is_succeeded():
                logger.info("Successfully created IMPORTS edge")
            else:
                logger.error(f"Failed to create IMPORTS edge: {result.error_msg()}")
                raise Exception(f"Failed to create IMPORTS edge: {result.error_msg()}")

            logger.info("Creating IMPORTS_FROM edge...")
            imports_from_edge_query = '''
            CREATE EDGE IF NOT EXISTS IMPORTS_FROM ();
            '''
            result = self.session.execute(imports_from_edge_query)
            if result.is_succeeded():
                logger.info("Successfully created IMPORTS_FROM edge")
            else:
                logger.error(f"Failed to create IMPORTS_FROM edge: {result.error_msg()}")
                raise Exception(f"Failed to create IMPORTS_FROM edge: {result.error_msg()}")

            logger.info("Creating INCLUDES edge...")
            includes_edge_query = '''
            CREATE EDGE IF NOT EXISTS INCLUDES ();
            '''
            result = self.session.execute(includes_edge_query)
            if result.is_succeeded():
                logger.info("Successfully created INCLUDES edge")
            else:
                logger.error(f"Failed to create INCLUDES edge: {result.error_msg()}")
                raise Exception(f"Failed to create INCLUDES edge: {result.error_msg()}")

            logger.info("Schema creation completed successfully")
        except Exception as e:
            logger.error(f"Error creating schema: {e}")
            raise

    def build_graph_from_ast(self, code: str, file_path: str, language: str, version: Optional[str] = None):
        """
        Build graph representation from AST of the code using two-pass approach
        """
        if language.lower() == 'python':
            self._build_graph_from_python_ast_two_pass(code, file_path)
        elif language.lower() == 'c':
            from experiment.c_parser import CParser
            self._build_graph_from_c_ast_two_pass(code, file_path, version)
        else:
            logger.error(
                f"Graph building not implemented for language: {language}")
            return

    def _build_graph_from_python_ast(self, code: str, file_path: str):
        """
        Build graph representation from Python AST
        """
        try:
            tree = ast.parse(code)
            self._process_ast_node(tree, file_path)
        except SyntaxError as e:
            logger.error(f"Could not parse Python code: {e}")

    def _build_graph_from_c_ast(self, code: str, file_path: str, version: Optional[str] = None):
        """
        Build graph representation from C AST using libclang
        """
        try:
            # Import CParser locally to avoid circular imports
            from experiment.c_parser import CParser
            from clang.cindex import CursorKind
            c_parser = CParser()
            tu = c_parser.parse_c_code(code, version)

            if tu is None:
                logger.error(f"Could not parse C code: {file_path}")
                return

            # Process C AST nodes
            self._process_c_ast_nodes(tu, file_path)
        except Exception as e:
            logger.error(f"Error building graph from C AST: {e}")

    def _build_graph_from_python_ast_two_pass(self, code: str, file_path: str):
        """
        Build graph representation from Python AST using two-pass approach
        """
        try:
            tree = ast.parse(code)

            # First pass: collect all information in memory
            vertices_info, relationships = self._collect_vertices_and_relationships_from_python_ast(tree, file_path)

            # Second pass: create all vertices in database
            self._create_vertices_in_database(vertices_info)

            # Third pass: create all relationships in database
            self._create_relationships_in_database(relationships)

        except SyntaxError as e:
            logger.error(f"Could not parse Python code: {e}")

    def _build_graph_from_c_ast_two_pass(self, code: str, file_path: str, version: Optional[str] = None):
        """
        Build graph representation from C AST using two-pass approach
        """
        # try:
        # Import CParser locally to avoid circular imports
        from experiment.c_parser import CParser
        c_parser = CParser()
        tu = c_parser.parse_c_code(code, version)

        if tu is None:
            logger.error(f"Could not parse C code: {file_path}")
            return

        # First pass: collect all information in memory
        logger.info("First pass")
        vertices_info, relationships = self._collect_vertices_and_relationships_from_c_ast(tu, file_path)

        # Second pass: create all vertices in database
        logger.info("Second pass")
        self._create_vertices_in_database(vertices_info)

        # Third pass: create all relationships in database
        logger.info("Third pass")
        self._create_relationships_in_database(relationships)

        # except Exception as e:
        #     logger.error(f"Error building graph from C AST: {e}")

    def _collect_vertices_and_relationships_from_python_ast(self, tree: ast.AST, file_path: str):
        """
        First pass: collect all vertices and relationships information from Python AST
        """
        vertices_info = {
            'functions': [],
            'classes': [],
            'variables': [],
            'parameters': [],
            'files': [],
            'modules': [],
            'imports': []
        }

        relationships = {
            'contains': [],  # (file_id, entity_id)
            'has_parameter': [],  # (function_id, parameter_id)
            'calls': [],  # (caller_id, callee_id) - stored as function names initially
            'imports': [],  # (file_id, module_id)
            'imports_from': []  # (file_id, import_id)
        }

        # Maintain mapping of function name to vertex ID for relationship creation
        function_vertex_map = {}

        # Add file vertex
        sanitized_file_path = self._sanitize_vertex_id(file_path)
        file_vertex_id = f"file_{sanitized_file_path}"
        vertices_info['files'].append({
            'vertex_id': file_vertex_id,
            'file_path': file_path
        })

        # Process the AST to collect information
        self._collect_python_ast_nodes(tree, file_path, file_vertex_id, vertices_info, relationships, function_vertex_map)

        # Store the mapping for later use
        relationships['function_vertex_map'] = function_vertex_map

        return vertices_info, relationships

    def _collect_python_ast_nodes(self, node: ast.AST, file_path: str, file_vertex_id: str, vertices_info: dict, relationships: dict, function_vertex_map: dict):
        """
        Collect information from Python AST nodes
        """
        # Process the AST and track current function context for calls
        self._traverse_python_ast(node, file_path, file_vertex_id, vertices_info, relationships, function_vertex_map, current_function=None)

    def _traverse_python_ast(self, node: ast.AST, file_path: str, file_vertex_id: str, vertices_info: dict, relationships: dict, function_vertex_map: dict, current_function: str = None):
        """
        Traverse Python AST nodes recursively, tracking the current function context
        """
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef) or isinstance(child, ast.AsyncFunctionDef):
                # Process function definition and enter its context
                func_name = child.name
                vertex_id = self._collect_function_info(child, file_path, file_vertex_id, vertices_info, relationships)
                # Store the mapping of function name to vertex ID
                if vertex_id:
                    function_vertex_map[f"{func_name}@{file_path}"] = vertex_id
                # Process the function body with the function as context
                self._traverse_python_ast(child, file_path, file_vertex_id, vertices_info, relationships, function_vertex_map, current_function=func_name)
            elif isinstance(child, ast.ClassDef):
                self._collect_class_info(child, file_path, file_vertex_id, vertices_info, relationships)
                # Process class body with the current function context maintained
                for item in child.body:
                    self._traverse_python_ast(item, file_path, file_vertex_id, vertices_info, relationships, function_vertex_map, current_function)
            elif isinstance(child, ast.Assign):
                self._collect_assignment_info(child, file_path, file_vertex_id, vertices_info, relationships)
            elif isinstance(child, ast.Import):
                self._collect_import_info(child, file_path, file_vertex_id, vertices_info, relationships)
            elif isinstance(child, ast.ImportFrom):
                self._collect_import_from_info(child, file_path, file_vertex_id, vertices_info, relationships)
            elif isinstance(child, ast.Call):
                # Process call with current function context
                self._collect_call_info(child, file_path, current_function, vertices_info, relationships)
            # For other statements, continue traversal with current context
            else:
                self._traverse_python_ast(child, file_path, file_vertex_id, vertices_info, relationships, function_vertex_map, current_function)

    def _collect_function_info(self, func_node: ast.FunctionDef, file_path: str, file_vertex_id: str, vertices_info: dict, relationships: dict):
        """
        Collect function information
        """
        func_name = func_node.name
        sanitized_file_path = self._sanitize_vertex_id(file_path)
        vertex_id = f"function_{func_name}_{sanitized_file_path}_{func_node.lineno}"

        # Add function vertex
        vertices_info['functions'].append({
            'vertex_id': vertex_id,
            'name': func_name,
            'file_path': file_path,
            'line_start': func_node.lineno,
            'line_end': getattr(func_node, 'end_lineno', func_node.lineno),
            'docstring': ast.get_docstring(func_node) or ''
        })

        # Add CONTAINS relationship between file and function
        relationships['contains'].append({
            'from_vertex': file_vertex_id,
            'to_vertex': vertex_id
        })

        # Add parameters
        args = []
        if hasattr(func_node.args, 'args'):
            for arg in func_node.args.args:
                if isinstance(arg, ast.arg):
                    arg_name = arg.arg
                    sanitized_file_path = self._sanitize_vertex_id(file_path)
                    arg_vertex_id = f"variable_{arg_name}_{sanitized_file_path}_{func_node.lineno}"

                    # Add parameter vertex
                    vertices_info['parameters'].append({
                        'vertex_id': arg_vertex_id,
                        'name': arg_name,
                        'scope': 'parameter',
                        'function_name': func_name,
                        'file_path': file_path
                    })

                    # Add HAS_PARAMETER relationship
                    relationships['has_parameter'].append({
                        'from_vertex': vertex_id,
                        'to_vertex': arg_vertex_id
                    })

        # The function calls are now handled by the traversal method with proper function context

        # Return the vertex ID for mapping
        return vertex_id

    def _collect_class_info(self, class_node: ast.ClassDef, file_path: str, file_vertex_id: str, vertices_info: dict, relationships: dict):
        """
        Collect class information
        """
        class_name = class_node.name
        sanitized_file_path = self._sanitize_vertex_id(file_path)
        class_vertex_id = f"class_{class_name}_{sanitized_file_path}_{class_node.lineno}"

        # Add class vertex
        vertices_info['classes'].append({
            'vertex_id': class_vertex_id,
            'name': class_name,
            'file_path': file_path,
            'line_start': class_node.lineno,
            'line_end': getattr(class_node, 'end_lineno', class_node.lineno)
        })

        # Add CONTAINS relationship
        relationships['contains'].append({
            'from_vertex': file_vertex_id,
            'to_vertex': class_vertex_id
        })

        # Process class body for methods
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef):
                # For methods, we'll process them separately
                method_name = item.name
                sanitized_file_path = self._sanitize_vertex_id(file_path)
                method_vertex_id = f"method_{method_name}_{sanitized_file_path}_{item.lineno}"

                # Add method vertex
                vertices_info['functions'].append({  # Treat methods as functions for simplicity
                    'vertex_id': method_vertex_id,
                    'name': method_name,
                    'file_path': file_path,
                    'line_start': item.lineno,
                    'line_end': getattr(item, 'end_lineno', item.lineno),
                    'docstring': ast.get_docstring(item) or ''
                })

                # Add CONTAINS relationship from class to method
                relationships['contains'].append({
                    'from_vertex': class_vertex_id,
                    'to_vertex': method_vertex_id
                })

    def _collect_assignment_info(self, assign_node: ast.Assign, file_path: str, file_vertex_id: str, vertices_info: dict, relationships: dict):
        """
        Collect assignment information
        """
        for target in assign_node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                sanitized_file_path = self._sanitize_vertex_id(file_path)
                var_vertex_id = f"variable_{var_name}_{sanitized_file_path}_{assign_node.lineno}"

                # Add variable vertex
                vertices_info['variables'].append({
                    'vertex_id': var_vertex_id,
                    'name': var_name,
                    'scope': 'local',
                    'file_path': file_path,
                    'line_start': assign_node.lineno
                })

                # Add CONTAINS relationship
                relationships['contains'].append({
                    'from_vertex': file_vertex_id,
                    'to_vertex': var_vertex_id
                })

    def _collect_import_info(self, import_node: ast.Import, file_path: str, file_vertex_id: str, vertices_info: dict, relationships: dict):
        """
        Collect import information
        """
        for alias in import_node.names:
            module_name = alias.name
            as_name = alias.asname or module_name
            sanitized_file_path = self._sanitize_vertex_id(file_path)
            module_vertex_id = f"module_{module_name}_{sanitized_file_path}_{import_node.lineno}"

            # Add module vertex
            vertices_info['modules'].append({
                'vertex_id': module_vertex_id,
                'name': module_name,
                'as_name': as_name,
                'file_path': file_path
            })

            # Add IMPORTS relationship
            relationships['imports'].append({
                'from_vertex': file_vertex_id,
                'to_vertex': module_vertex_id
            })

    def _collect_import_from_info(self, import_node: ast.ImportFrom, file_path: str, file_vertex_id: str, vertices_info: dict, relationships: dict):
        """
        Collect import from information
        """
        module_name = import_node.module or ""
        for alias in import_node.names:
            import_name = alias.name
            as_name = alias.asname or import_name
            sanitized_file_path = self._sanitize_vertex_id(file_path)
            import_vertex_id = f"import_{import_name}_{sanitized_file_path}_{import_node.lineno}"

            # Add import vertex
            vertices_info['imports'].append({
                'vertex_id': import_vertex_id,
                'name': import_name,
                'as_name': as_name,
                'module': module_name,
                'file_path': file_path
            })

            # Add IMPORTS_FROM relationship
            relationships['imports_from'].append({
                'from_vertex': file_vertex_id,
                'to_vertex': import_vertex_id
            })

    def _collect_call_info(self, call_node: ast.Call, file_path: str, current_function: str, vertices_info: dict, relationships: dict):
        """
        Collect function call information (for CALLS relationships)
        """
        if isinstance(call_node.func, ast.Name):
            # Direct function call: func_name()
            func_name = call_node.func.id

            # Store the function call information with proper caller context
            relationships['calls'].append({
                'caller_function_name': current_function,
                'caller_file_path': file_path,
                'callee_name': func_name,
                'callee_file_path': file_path
            })
        elif isinstance(call_node.func, ast.Attribute):
            # Method call: obj.method_name()
            attr_name = call_node.func.attr
            # Store method call information
            relationships['calls'].append({
                'caller_function_name': current_function,
                'caller_file_path': file_path,
                'callee_name': attr_name,
                'callee_file_path': file_path
            })

    def _collect_vertices_and_relationships_from_c_ast(self, tu, file_path: str):
        """
        First pass: collect all vertices and relationships information from C AST
        """
        from clang.cindex import CursorKind

        vertices_info = {
            'functions': [],
            'variables': [],
            'structs': [],
            'includes': [],
            'parameters': [],
            'files': []
        }

        relationships = {
            'contains': [],  # (file_id, entity_id)
            'has_parameter': [],  # (function_id, parameter_id)
            'calls': [],  # (caller_id, callee_id) - stored as function names initially
            'includes': []  # (file_id, include_id)
        }

        # Maintain mapping of function name to vertex ID for relationship creation
        function_vertex_map = {}

        # Use the sanitize method to ensure safe vertex IDs
        sanitized_file_path = self._sanitize_vertex_id(file_path)
        # Add file vertex
        file_vertex_id = f"file_{sanitized_file_path}"
        vertices_info['files'].append({
            'vertex_id': file_vertex_id,
            'file_path': file_path
        })

        # Process C AST nodes with current function context
        def traverse_c_ast(cursor, current_function=None):
            self._collect_c_cursor_info(cursor, file_path, file_vertex_id, vertices_info, relationships, current_function, function_vertex_map)
            for child in cursor.get_children():
                # If this is a function declaration, update the current function for its children
                if cursor.kind == CursorKind.FUNCTION_DECL:
                    traverse_c_ast(child, cursor.spelling)
                else:
                    traverse_c_ast(child, current_function)

        traverse_c_ast(tu.cursor)

        # Store the mapping for later use
        relationships['function_vertex_map'] = function_vertex_map

        return vertices_info, relationships

    def _collect_c_cursor_info(self, cursor, file_path: str, file_vertex_id: str, vertices_info: dict, relationships: dict, current_function: str = None, function_vertex_map: dict = None):
        """
        Collect information from a single C AST cursor
        """
        from clang.cindex import CursorKind

        if cursor.kind == CursorKind.FUNCTION_DECL:
            vertex_id = self._collect_c_function_info(cursor, file_path, file_vertex_id, vertices_info, relationships)
            # Store the mapping of function name to vertex ID
            func_name = cursor.spelling
            sanitized_file_path = self._sanitize_vertex_id(file_path)
            if vertex_id and function_vertex_map is not None:
                function_vertex_map[f"{func_name}@{file_path}"] = vertex_id  # Keep original file path for lookup
        elif cursor.kind == CursorKind.VAR_DECL:
            self._collect_c_variable_info(cursor, file_path, file_vertex_id, vertices_info, relationships)
        elif (cursor.kind == CursorKind.CLASS_DECL or cursor.kind == CursorKind.STRUCT_DECL):
            self._collect_c_struct_info(cursor, file_path, file_vertex_id, vertices_info, relationships)
        elif cursor.kind == CursorKind.CALL_EXPR:
            self._collect_c_function_call_info(cursor, file_path, current_function, vertices_info, relationships)
        elif cursor.kind == CursorKind.INCLUSION_DIRECTIVE:
            self._collect_c_include_info(cursor, file_path, file_vertex_id, vertices_info, relationships)

    def _collect_c_function_info(self, cursor, file_path: str, file_vertex_id: str, vertices_info: dict, relationships: dict):
        """
        Collect C function information
        """
        func_name = cursor.spelling
        if not func_name:
            return

        sanitized_file_path = self._sanitize_vertex_id(file_path)
        func_vertex_id = f"c_function_{func_name}_{sanitized_file_path}_{cursor.location.line}"

        # Add function vertex
        vertices_info['functions'].append({
            'vertex_id': func_vertex_id,
            'name': func_name,
            'file_path': file_path,
            'line_start': cursor.location.line,
            'line_end': cursor.location.line,
            'docstring': ''  # C functions don't have Python-style docstrings
        })

        # Add CONTAINS relationship
        relationships['contains'].append({
            'from_vertex': file_vertex_id,
            'to_vertex': func_vertex_id
        })

        # Process parameters
        for child in cursor.get_children():
            if child.kind == CursorKind.PARM_DECL:
                self._collect_c_parameter_info(child, func_vertex_id, file_path, func_name, vertices_info, relationships)

        # Return the vertex ID for mapping
        return func_vertex_id

    def _collect_c_parameter_info(self, cursor, func_vertex_id: str, file_path: str, func_name: str, vertices_info: dict, relationships: dict):
        """
        Collect C parameter information
        """
        param_name = cursor.spelling
        if not param_name:
            return

        sanitized_file_path = self._sanitize_vertex_id(file_path)
        param_vertex_id = f"parameter_{param_name}_{sanitized_file_path}_{cursor.location.line}"

        # Add parameter vertex
        vertices_info['parameters'].append({
            'vertex_id': param_vertex_id,
            'name': param_name,
            'type': str(cursor.type.spelling),
            'function_name': func_name,
            'file_path': file_path
        })

        # Add HAS_PARAMETER relationship
        relationships['has_parameter'].append({
            'from_vertex': func_vertex_id,
            'to_vertex': param_vertex_id
        })

    def _collect_c_variable_info(self, cursor, file_path: str, file_vertex_id: str, vertices_info: dict, relationships: dict):
        """
        Collect C variable information
        """
        var_name = cursor.spelling
        if not var_name:
            return

        # Use the sanitize method to ensure safe vertex IDs
        sanitized_file_path = self._sanitize_vertex_id(file_path)
        var_vertex_id = f"c_variable_{var_name}_{sanitized_file_path}_{cursor.location.line}"

        # Add variable vertex
        vertices_info['variables'].append({
            'vertex_id': var_vertex_id,
            'name': var_name,
            'scope': 'local',  # Default scope for C variables
            'function_name': '',  # Will be filled if it's a local variable
            'file_path': file_path,
            'type': str(cursor.type.spelling),
            'line_start': cursor.location.line
        })

        # Add CONTAINS relationship
        relationships['contains'].append({
            'from_vertex': file_vertex_id,
            'to_vertex': var_vertex_id
        })

    def _collect_c_struct_info(self, cursor, file_path: str, file_vertex_id: str, vertices_info: dict, relationships: dict):
        """
        Collect C struct information
        """
        struct_name = cursor.spelling
        if not struct_name:
            return

        sanitized_file_path = self._sanitize_vertex_id(file_path)
        struct_vertex_id = f"struct_{struct_name}_{sanitized_file_path}_{cursor.location.line}"

        # Add struct vertex
        vertices_info['structs'].append({
            'vertex_id': struct_vertex_id,
            'name': struct_name,
            'file_path': file_path,
            'line': cursor.location.line,
            'column': cursor.location.column
        })

        # Add CONTAINS relationship
        relationships['contains'].append({
            'from_vertex': file_vertex_id,
            'to_vertex': struct_vertex_id
        })

    def _collect_c_function_call_info(self, cursor, file_path: str, current_function: str, vertices_info: dict, relationships: dict):
        """
        Collect C function call information
        """
        called_func_name = cursor.spelling
        if not called_func_name:
            return

        # Store function call information with proper caller context
        relationships['calls'].append({
            'caller_function_name': current_function,
            'caller_file_path': file_path,
            'callee_name': called_func_name,
            'callee_file_path': file_path
        })

    def _collect_c_include_info(self, cursor, file_path: str, file_vertex_id: str, vertices_info: dict, relationships: dict):
        """
        Collect C include information
        """
        include_file = cursor.spelling
        if not include_file:
            return

        # Use the sanitize method to ensure safe vertex IDs
        sanitized_include_file = self._sanitize_vertex_id(include_file)
        include_vertex_id = f"include_{sanitized_include_file}_{cursor.location.line}"

        # Add include vertex
        vertices_info['includes'].append({
            'vertex_id': include_vertex_id,
            'file': include_file,
            'file_path': file_path,
            'line': cursor.location.line
        })

        # Add INCLUDES relationship
        relationships['includes'].append({
            'from_vertex': file_vertex_id,
            'to_vertex': include_vertex_id
        })

    def _create_vertices_in_database(self, vertices_info: dict):
        """
        Second pass: create all vertices in the database
        """
        # Add logging to see what data we have
        logger.info(f"Vertices info contains: {list(vertices_info.keys())}")
        for key, value in vertices_info.items():
            logger.info(f"Number of {key}: {len(value) if value else 0}")

        # Create functions (always present for both Python and C)
        logger.info("Creating Functions")
        for func in vertices_info.get('functions', []):
            insert_function_query = f'''
            INSERT VERTEX Function(name, file_path, line_start, line_end, docstring)
            VALUES "{func['vertex_id']}":("{func['name']}", "{func['file_path']}", {func['line_start']}, {func['line_end']}, "{func.get('docstring', '')}");
            '''
            try:
                logger.info(f"Executing function insertion query: INSERT VERTEX Function(name, file_path...) VALUES \"{func['vertex_id']}\":(\"{func['name']}\", \"{func['file_path']}\"...")
                result = self.session.execute(insert_function_query)
                if result.is_succeeded():
                    logger.info(f"Successfully inserted function {func['name']} with ID {func['vertex_id']}")
                else:
                    logger.error(f"Failed to insert function {func['name']}: {result.error_msg()}")
            except Exception as e:
                logger.error(f"Exception when inserting function {func['name']}: {e}")

        # Create classes (only for Python)
        logger.info("Creating Classes")
        for cls in vertices_info.get('classes', []):
            insert_class_query = f'''
            INSERT VERTEX Class(name, file_path, line_start, line_end)
            VALUES "{cls['vertex_id']}":("{cls['name']}", "{cls['file_path']}", {cls['line_start']}, {cls['line_end']});
            '''
            try:
                logger.info(f"Executing class insertion query: INSERT VERTEX Class(name, file_path...) VALUES \"{cls['vertex_id']}\":(\"{cls['name']}\"...")
                result = self.session.execute(insert_class_query)
                if result.is_succeeded():
                    logger.info(f"Successfully inserted class {cls['name']} with ID {cls['vertex_id']}")
                else:
                    logger.error(f"Failed to insert class {cls['name']}: {result.error_msg()}")
            except Exception as e:
                logger.error(f"Exception when inserting class {cls['name']}: {e}")

        # Create variables
        logger.info("Creating Variables")
        for var in vertices_info.get('variables', []):
            insert_var_query = f'''
            INSERT VERTEX Variable(name, scope, function_name, file_path, type, line_start)
            VALUES "{var['vertex_id']}":("{var['name']}", "{var.get('scope', '')}", "{var.get('function_name', '')}", "{var['file_path']}", "{var.get('type', '')}", {var['line_start']});
            '''
            try:
                logger.info(f"Executing variable insertion query: INSERT VERTEX Variable(name, scope...) VALUES \"{var['vertex_id']}\":(\"{var['name']}\"...")
                result = self.session.execute(insert_var_query)
                if result.is_succeeded():
                    logger.info(f"Successfully inserted variable {var['name']} with ID {var['vertex_id']}")
                else:
                    logger.error(f"Failed to insert variable {var['name']}: {result.error_msg()}")
            except Exception as e:
                logger.error(f"Exception when inserting variable {var['name']}: {e}")

        # Create parameters
        logger.info("Creating Parameters")
        for param in vertices_info.get('parameters', []):
            insert_param_query = f'''
            INSERT VERTEX Parameter(name, type, function_name, file_path)
            VALUES "{param['vertex_id']}":("{param['name']}", "{param['type']}", "{param['function_name']}", "{param['file_path']}");
            '''
            try:
                logger.info(f"Executing parameter insertion query: INSERT VERTEX Parameter(name, type...) VALUES \"{param['vertex_id']}\":(\"{param['name']}\"...")
                result = self.session.execute(insert_param_query)
                if result.is_succeeded():
                    logger.info(f"Successfully inserted parameter {param['name']} with ID {param['vertex_id']}")
                else:
                    logger.error(f"Failed to insert parameter {param['name']}: {result.error_msg()}")
            except Exception as e:
                logger.error(f"Exception when inserting parameter {param['name']}: {e}")

        # Create files
        logger.info("Creating Files")
        for file_info in vertices_info.get('files', []):
            insert_file_query = f'''INSERT VERTEX File(`path`) VALUES "{file_info['vertex_id']}":("{file_info['file_path']}");'''
            try:
                logger.info(f"Executing file insertion query: INSERT VERTEX File(path) VALUES \"{file_info['vertex_id']}\":(\"{file_info['file_path']}\"...")
                result = self.session.execute(insert_file_query)
                if result.is_succeeded():
                    logger.info(f"Successfully inserted file {file_info['file_path']} with ID {file_info['vertex_id']}")
                else:
                    logger.error(f"Failed to insert file {file_info['file_path']}: {result.error_msg()}")
            except Exception as e:
                logger.error(f"Exception when inserting file {file_info['file_path']}: {e}")

        # Create modules (only for Python)
        logger.info("Creating Modules")
        for module in vertices_info.get('modules', []):
            insert_module_query = f'''
            INSERT VERTEX Module(name, as_name, file_path)
            VALUES "{module['vertex_id']}":("{module['name']}", "{module['as_name']}", "{module['file_path']}");
            '''
            try:
                logger.info(f"Executing module insertion query: INSERT VERTEX Module(name, as_name...) VALUES \"{module['vertex_id']}\":(\"{module['name']}\"...")
                result = self.session.execute(insert_module_query)
                if result.is_succeeded():
                    logger.info(f"Successfully inserted module {module['name']} with ID {module['vertex_id']}")
                else:
                    logger.error(f"Failed to insert module {module['name']}: {result.error_msg()}")
            except Exception as e:
                logger.error(f"Exception when inserting module {module['name']}: {e}")

        # Create imports (only for Python)
        logger.info("Creating Imports")
        for imp in vertices_info.get('imports', []):
            insert_import_query = f'''
            INSERT VERTEX Import(name, as_name, module, file_path)
            VALUES "{imp['vertex_id']}":("{imp['name']}", "{imp['as_name']}", "{imp['module']}", "{imp['file_path']}");
            '''
            try:
                logger.info(f"Executing import insertion query: INSERT VERTEX Import(name, as_name...) VALUES \"{imp['vertex_id']}\":(\"{imp['name']}\"...")
                result = self.session.execute(insert_import_query)
                if result.is_succeeded():
                    logger.info(f"Successfully inserted import {imp['name']} with ID {imp['vertex_id']}")
                else:
                    logger.error(f"Failed to insert import {imp['name']}: {result.error_msg()}")
            except Exception as e:
                logger.error(f"Exception when inserting import {imp['name']}: {e}")

        # Create structs (only for C)
        logger.info("Creating Structs")
        for struct in vertices_info.get('structs', []):
            insert_struct_query = f'''
            INSERT VERTEX Struct(name, file_path, line, column)
            VALUES "{struct['vertex_id']}":("{struct['name']}", "{struct['file_path']}", {struct['line']}, {struct['column']});
            '''
            try:
                logger.info(f"Executing struct insertion query: INSERT VERTEX Struct(name, file_path...) VALUES \"{struct['vertex_id']}\":(\"{struct['name']}\"...")
                result = self.session.execute(insert_struct_query)
                if result.is_succeeded():
                    logger.info(f"Successfully inserted struct {struct['name']} with ID {struct['vertex_id']}")
                else:
                    logger.error(f"Failed to insert struct {struct['name']}: {result.error_msg()}")
            except Exception as e:
                logger.error(f"Exception when inserting struct {struct['name']}: {e}")

        # Create includes (only for C)
        logger.info("Creating Includes")
        for include in vertices_info.get('includes', []):
            insert_include_query = f'''
            INSERT VERTEX Include(file, file_path, line)
            VALUES "{include['vertex_id']}":("{include['file']}", "{include['file_path']}", {include['line']});
            '''
            try:
                logger.info(f"Executing include insertion query: INSERT VERTEX Include(file, file_path...) VALUES \"{include['vertex_id']}\":(\"{include['file']}\"...")
                result = self.session.execute(insert_include_query)
                if result.is_succeeded():
                    logger.info(f"Successfully inserted include {include['file']} with ID {include['vertex_id']}")
                else:
                    logger.error(f"Failed to insert include {include['file']}: {result.error_msg()}")
            except Exception as e:
                logger.error(f"Exception when inserting include {include['file']}: {e}")

    def _create_relationships_in_database(self, relationships: dict):
        """
        Third pass: create all relationships in the database
        """
        logger.info(f"Creating relationships: {list(relationships.keys())}")
        for key, value in relationships.items():
            if key != 'function_vertex_map':
                logger.info(f"Number of {key} relationships: {len(value) if value else 0}")

        # Create CONTAINS relationships
        for rel in relationships.get('contains', []):
            # contains_rel_query = f'''INSERT EDGE CONTAINS VALUES "{rel['from_vertex']}" -> "{rel['to_vertex']}";'''
            contains_rel_query = f'''INSERT EDGE CONTAINS () VALUES '{rel["from_vertex"]}' -> '{rel["to_vertex"]}':();'''
            try:
                logger.info(f"Executing CONTAINS relationship query: {contains_rel_query[:100]}...")
                result = self.session.execute(contains_rel_query)
                if result.is_succeeded():
                    logger.info(f"Successfully created CONTAINS relationship: {rel['from_vertex']} -> {rel['to_vertex']}")
                else:
                    logger.error(f"Failed to create CONTAINS relationship: {result.error_msg()}")
            except Exception as e:
                logger.error(f"Error creating CONTAINS relationship: {e}")

        # Create HAS_PARAMETER relationships
        for rel in relationships.get('has_parameter', []):
            param_rel_query = f'''INSERT EDGE HAS_PARAMETER () VALUES '{rel["from_vertex"]}' -> '{rel["to_vertex"]}':();'''
            try:
                logger.info(f"Executing HAS_PARAMETER relationship query: {param_rel_query[:100]}...")
                result = self.session.execute(param_rel_query)
                if result.is_succeeded():
                    logger.info(f"Successfully created HAS_PARAMETER relationship: {rel['from_vertex']} -> {rel['to_vertex']}")
                else:
                    logger.error(f"Failed to create HAS_PARAMETER relationship: {result.error_msg()}")
            except Exception as e:
                logger.error(f"Error creating HAS_PARAMETER relationship: {e}")

        # Get the function vertex map that was stored during collection
        function_vertex_map = relationships.get('function_vertex_map', {})
        logger.info(f"Function vertex map has {len(function_vertex_map)} entries")

        # Create CALLS relationships (this uses the in-memory function vertex mapping)
        for rel in relationships.get('calls', []):
            logger.info(f"Processing call relationship: {rel}")
            self._create_calls_relationship(rel, function_vertex_map)

        # Create IMPORTS relationships
        for rel in relationships.get('imports', []):
            imports_rel_query = f'''
            INSERT EDGE IMPORTS VALUES '{rel["from_vertex"]}' -> '{rel["to_vertex"]}':();
            '''
            try:
                logger.info(f"Executing IMPORTS relationship query: {imports_rel_query[:100]}...")
                result = self.session.execute(imports_rel_query)
                if result.is_succeeded():
                    logger.info(f"Successfully created IMPORTS relationship: {rel['from_vertex']} -> {rel['to_vertex']}")
                else:
                    logger.error(f"Failed to create IMPORTS relationship: {result.error_msg()}")
            except Exception as e:
                logger.error(f"Error creating IMPORTS relationship: {e}")

        # Create IMPORTS_FROM relationships
        for rel in relationships.get('imports_from', []):
            imports_from_rel_query = f'''INSERT EDGE IMPORTS_FROM () VALUES "{rel['from_vertex']}" -> "{rel['to_vertex']}";'''
            try:
                logger.info(f"Executing IMPORTS_FROM relationship query: {imports_from_rel_query[:100]}...")
                result = self.session.execute(imports_from_rel_query)
                if result.is_succeeded():
                    logger.info(f"Successfully created IMPORTS_FROM relationship: {rel['from_vertex']} -> {rel['to_vertex']}")
                else:
                    logger.error(f"Failed to create IMPORTS_FROM relationship: {result.error_msg()}")
            except Exception as e:
                logger.error(f"Error creating IMPORTS_FROM relationship: {e}")

        # Create INCLUDES relationships
        for rel in relationships.get('includes', []):
            includes_rel_query = "INSERT EDGE `INCLUDES` VALUES '{}' -> '{}':();".format(rel['from_vertex'], rel['to_vertex'])
            try:
                logger.info(f"Executing INCLUDES relationship query: {includes_rel_query[:100]}...")
                result = self.session.execute(includes_rel_query)
                if result.is_succeeded():
                    logger.info(f"Successfully created INCLUDES relationship: {rel['from_vertex']} -> {rel['to_vertex']}")
                else:
                    logger.error(f"Failed to create INCLUDES relationship: {result.error_msg()}")
            except Exception as e:
                logger.error(f"Error creating INCLUDES relationship: {e}")

    def _create_calls_relationship(self, call_info: dict, function_vertex_map: dict = None):
        """
        Special method to create CALLS relationship by using the in-memory function vertex mapping
        """
        if function_vertex_map is None:
            function_vertex_map = {}

        logger.info(f"Processing call_info: {call_info}")
        logger.info(f"Function vertex map keys: {list(function_vertex_map.keys())}")

        # Get caller and callee function names from the call info
        caller_function_name = call_info.get('caller_function_name')
        callee_name = call_info['callee_name']
        callee_file_path = call_info['callee_file_path']

        # Skip system/library functions that won't be in our database
        system_functions = {
            'printf', 'scanf', 'fprintf', 'fscanf', 'sprintf', 'sscanf',
            'snprintf', 'vprintf', 'vfprintf', 'vsprintf', 'getline',
            'malloc', 'free', 'calloc', 'realloc', 'fopen', 'fclose',
            'fread', 'fwrite', 'fgetc', 'fgets', 'fputc', 'fputs',
            'getc', 'getchar', 'gets', 'putc', 'putchar', 'puts',
            'system', 'exit', 'abort', 'atof', 'atoi', 'atol', 'atoll',
            'itoa', 'strlen', 'strcmp', 'strcpy', 'strncpy', 'strcat',
            'strncat', 'memcpy', 'memmove', 'memset', 'memcmp',
            'time', 'ctime', 'localtime', 'strftime'
        }

        if callee_name in system_functions:
            logger.debug(f"Skipping system function call: {callee_name}")
            return

        # Look up the callee function in our in-memory map
        callee_key = f"{callee_name}@{callee_file_path}"
        logger.info(f"Looking up callee key: {callee_key}")
        if callee_key not in function_vertex_map:
            logger.warning(f"Could not find user-defined callee function: {callee_name} in file {callee_file_path}")
            logger.warning(f"Available callee keys: {list(function_vertex_map.keys())}")
            return

        callee_vertex_id = function_vertex_map[callee_key]
        logger.info(f"Found callee vertex ID: {callee_vertex_id}")

        # Look up the caller function in our in-memory map
        if caller_function_name:
            caller_file_path = call_info['caller_file_path']
            caller_key = f"{caller_function_name}@{caller_file_path}"
            logger.info(f"Looking up caller key: {caller_key}")

            if caller_key not in function_vertex_map:
                logger.debug(f"Could not find caller function: {caller_function_name}")
                logger.debug(f"Available caller keys: {list(function_vertex_map.keys())}")
                return

            caller_vertex_id = function_vertex_map[caller_key]
            logger.info(f"Found caller vertex ID: {caller_vertex_id}")

            # Create CALLS relationship
            calls_rel_query = f"INSERT EDGE CALLS () VALUES '{caller_vertex_id}' -> '{callee_vertex_id}':()";
            try:
                logger.info(f"Executing CALLS relationship query: {calls_rel_query[:100]}...")
                result = self.session.execute(calls_rel_query)
                if result.is_succeeded():
                    logger.info(f"Successfully created CALLS relationship: {caller_function_name} -> {callee_name}")
                else:
                    logger.error(f"Failed to create CALLS relationship: {result.error_msg()}")
            except Exception as e:
                logger.error(f"Error creating CALLS relationship between {caller_vertex_id} and {callee_vertex_id}: {e}")
        else:
            # No specific caller function (e.g., call from global scope)
            logger.debug(f"Call from global scope calling: {callee_name}")

    def _process_ast_node(self, node: ast.AST, file_path: str, parent_node: Optional[None] = None):
        """
        Recursively process AST nodes and create graph entities
        """
        for child in ast.walk(node):
            if isinstance(child, ast.FunctionDef):
                self._process_function(child, file_path, parent_node)
            elif isinstance(child, ast.AsyncFunctionDef):
                self._process_function(child, file_path, parent_node)
            elif isinstance(child, ast.ClassDef):
                self._process_class(child, file_path, parent_node)
            elif isinstance(child, ast.Assign):
                self._process_assignment(child, file_path, parent_node)
            elif isinstance(child, ast.Import):
                self._process_import(child, file_path, parent_node)
            elif isinstance(child, ast.ImportFrom):
                self._process_import_from(child, file_path, parent_node)

    def _process_function(self, func_node: ast.FunctionDef, file_path: str, parent_node: Optional[None]):
        """
        Process a function definition and create graph nodes/relationships
        """
        # Create function node
        func_name = func_node.name
        # In Nebula, vertex IDs need to be strings. We'll use the function name as the ID
        sanitized_file_path = self._sanitize_vertex_id(file_path)
        vertex_id = f"function_{func_name}_{sanitized_file_path}_{func_node.lineno}"

        # Insert the function as a vertex with the Function tag
        insert_function_query = f'''
        INSERT VERTEX Function(name, file_path, line_start, line_end, docstring)
        VALUES "{vertex_id}":("{func_name}", "{file_path}", {func_node.lineno}, {getattr(func_node, 'end_lineno', func_node.lineno)}, "{ast.get_docstring(func_node) or ''}");
        '''
        try:
            self.session.execute(insert_function_query)
        except Exception as e:
            logger.error(f"Error inserting function {func_name}: {e}")

        # Add parameters as variables
        args = []
        if hasattr(func_node.args, 'args'):
            for arg in func_node.args.args:
                if isinstance(arg, ast.arg):
                    arg_name = arg.arg
                    sanitized_file_path = self._sanitize_vertex_id(file_path)
                    arg_vertex_id = f"variable_{arg_name}_{sanitized_file_path}_{func_node.lineno}"

                    insert_arg_query = f'''
                    INSERT VERTEX Variable(name, scope, function_name, file_path)
                    VALUES "{arg_vertex_id}":("{arg_name}", "parameter", "{func_name}", "{file_path}");
                    '''
                    try:
                        self.session.execute(insert_arg_query)
                        # Create relationship: Function -> Parameter
                        insert_rel_query = f'''
                        INSERT EDGE HAS_PARAMETER () VALUES "{vertex_id}" -> "{arg_vertex_id}":();
                        '''
                        self.session.execute(insert_rel_query)
                    except Exception as e:
                        logger.error(f"Error inserting parameter {arg_name}: {e}")

        # Create relationship to file
        sanitized_file_path = self._sanitize_vertex_id(file_path)
        file_vertex_id = f"file_{sanitized_file_path}"
        insert_file_query = f'''
        INSERT VERTEX File(`path`) VALUES "{file_vertex_id}":("{file_path}");
        '''
        try:
            self.session.execute(insert_file_query)
            # Create relationship: File -> Function
            insert_contains_rel_query = f'''
            INSERT EDGE CONTAINS () VALUES "{file_vertex_id}" -> "{vertex_id}":();
            '''
            self.session.execute(insert_contains_rel_query)
        except Exception as e:
            logger.error(f"Error inserting file {file_path} or relationship: {e}")

        # Process function body for variable usage and function calls
        self._process_function_body(func_node, vertex_id, file_path)

    def _process_class(self, class_node: ast.ClassDef, file_path: str, parent_node: Optional[None]):
        """
        Process a class definition and create graph nodes/relationships
        """
        class_name = class_node.name
        sanitized_file_path = self._sanitize_vertex_id(file_path)
        class_vertex_id = f"class_{class_name}_{sanitized_file_path}_{class_node.lineno}"

        # Insert the class as a vertex with the Class tag
        insert_class_query = f'''
        INSERT VERTEX Class(name, file_path, line_start, line_end)
        VALUES "{class_vertex_id}":("{class_name}", "{file_path}", {class_node.lineno}, {getattr(class_node, 'end_lineno', class_node.lineno)});
        '''
        try:
            self.session.execute(insert_class_query)

            # Use the sanitize method to ensure safe vertex IDs
            sanitized_file_path = self._sanitize_vertex_id(file_path)
            # Create relationship to file
            file_vertex_id = f"file_{sanitized_file_path}"
            insert_file_query = f'''
            INSERT VERTEX File(path) VALUES "{file_vertex_id}":("{file_path}");
            '''
            self.session.execute(insert_file_query)

            # Create relationship: File -> Class
            insert_contains_rel_query = f'''
            INSERT EDGE CONTAINS () VALUES "{file_vertex_id}" -> "{class_vertex_id}":();
            '''
            self.session.execute(insert_contains_rel_query)

            # Process class body
            for item in class_node.body:
                if isinstance(item, ast.FunctionDef):
                    self._process_method(
                        item, class_name, file_path, class_vertex_id)
        except Exception as e:
            logger.error(f"Error processing class {class_name}: {e}")

    def _process_method(self, method_node: ast.FunctionDef, class_name: str, file_path: str, class_node: str):
        """
        Process a method definition within a class
        """
        method_name = method_node.name
        method_vertex_id = f"method_{method_name}_{file_path}_{method_node.lineno}"

        # Insert the method as a vertex with the Method tag
        insert_method_query = f'''
        INSERT VERTEX Method(name, class_name, file_path, line_start, line_end)
        VALUES "{method_vertex_id}":("{method_name}", "{class_name}", "{file_path}", {method_node.lineno}, {getattr(method_node, 'end_lineno', method_node.lineno)});
        '''
        try:
            self.session.execute(insert_method_query)

            # Create relationship: Class -> Method
            insert_contains_rel_query = f'''
            INSERT EDGE CONTAINS () VALUES "{class_node}" -> "{method_vertex_id}":();
            '''
            self.session.execute(insert_contains_rel_query)

            # Process method body - pass the vertex_id instead of the Node object
            self._process_function_body(method_node, method_vertex_id, file_path)
        except Exception as e:
            logger.error(f"Error processing method {method_name}: {e}")

    def _process_assignment(self, assign_node: ast.Assign, file_path: str, parent_node: Optional[None]):
        """
        Process assignment statements and create variable nodes
        """
        for target in assign_node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                sanitized_file_path = self._sanitize_vertex_id(file_path)
                var_vertex_id = f"variable_{var_name}_{sanitized_file_path}_{assign_node.lineno}"

                # Insert the variable as a vertex with the Variable tag
                insert_var_query = f'''
                INSERT VERTEX Variable(name, scope, file_path, line_start)
                VALUES "{var_vertex_id}":("{var_name}", "local", "{file_path}", {assign_node.lineno});
                '''
                try:
                    self.session.execute(insert_var_query)

                    # Add to containing scope (file, function, class)
                    if parent_node:
                        contains_rel_query = f'''
                        INSERT EDGE CONTAINS () VALUES "{parent_node}" -> "{var_vertex_id}":();
                        '''
                        self.session.execute(contains_rel_query)
                except Exception as e:
                    logger.error(f"Error processing assignment for variable {var_name}: {e}")

    def _process_import(self, import_node: ast.Import, file_path: str, parent_node: Optional[None]):
        """
        Process import statements
        """
        for alias in import_node.names:
            module_name = alias.name
            as_name = alias.asname or module_name
            sanitized_file_path = self._sanitize_vertex_id(file_path)
            module_vertex_id = f"module_{module_name}_{sanitized_file_path}_{import_node.lineno}"

            # Insert the module as a vertex with the Module tag
            insert_module_query = f'''
            INSERT VERTEX Module(name, as_name, file_path)
            VALUES "{module_vertex_id}":("{module_name}", "{as_name}", "{file_path}");
            '''
            try:
                self.session.execute(insert_module_query)

                # Create relationship: File -> Imports
                file_vertex_id = f"file_{sanitized_file_path}"

                # Create relationship: File -> Module import
                imports_rel_query = f'''
                INSERT EDGE IMPORTS () VALUES "{file_vertex_id}" -> "{module_vertex_id}":();
                '''
                self.session.execute(imports_rel_query)
            except Exception as e:
                logger.error(f"Error processing import for module {module_name}: {e}")

    def _process_import_from(self, import_node: ast.ImportFrom, file_path: str, parent_node: Optional[None]):
        """
        Process from ... import ... statements
        """
        module_name = import_node.module or ""
        for alias in import_node.names:
            import_name = alias.name
            as_name = alias.asname or import_name
            sanitized_file_path = self._sanitize_vertex_id(file_path)
            import_vertex_id = f"import_{import_name}_{sanitized_file_path}_{import_node.lineno}"

            # Insert the import as a vertex with the Import tag
            insert_import_query = f'''
            INSERT VERTEX Import(name, as_name, module, file_path)
            VALUES "{import_vertex_id}":("{import_name}", "{as_name}", "{module_name}", "{file_path}");
            '''
            try:
                self.session.execute(insert_import_query)

                # Create relationship: File -> ImportsFrom
                file_vertex_id = f"file_{sanitized_file_path}"

                # Create relationship: File -> Import
                imports_rel_query = f'''
                INSERT EDGE IMPORTS_FROM () VALUES "{file_vertex_id}" -> "{import_vertex_id}":();
                '''
                self.session.execute(imports_rel_query)
            except Exception as e:
                logger.error(f"Error processing import from for {import_name}: {e}")

    def _process_function_body(self, func_node: ast.AST, func_node_graph: str, file_path: str):
        """
        Process the body of a function to identify variable usage and function calls
        """
        for stmt in func_node.body:
            if isinstance(stmt, ast.Expr):
                # Could be a function call in expression context
                if isinstance(stmt.value, ast.Call):
                    self._process_call(stmt.value, func_node_graph, file_path)
            elif isinstance(stmt, ast.Assign):
                # Assignment with potential function call on right side
                if isinstance(stmt.value, ast.Call):
                    self._process_call(stmt.value, func_node_graph, file_path)
            elif isinstance(stmt, ast.Call):
                # Direct function call statement
                self._process_call(stmt, func_node_graph, file_path)

    def _process_call(self, call_node: ast.Call, parent_node: str, file_path: str):
        """
        Process function calls to identify relationships
        """
        if isinstance(call_node.func, ast.Name):
            # Direct function call: func_name()
            func_name = call_node.func.id
            # In Nebula, we'll create an edge from the calling function to the called function
            # The called function vertex ID would typically match the pattern used in _process_function
            called_vertex_id = f"function_{func_name}_%"  # Use % as a wildcard to match any file path and line

            # Try to find the called function vertex - if it exists, create the CALLS relationship
            # Use a query to check if the function exists in the graph
            check_function_query = f'''
            MATCH (n:Function) WHERE n.name == "{func_name}"
            RETURN id(n) AS vertex_id LIMIT 1
            '''
            result = self.session.execute(check_function_query)

            if result.is_succeeded() and result.row_size() > 0:
                # Get the actual vertex ID from the result
                for row in result.rows():
                    actual_called_vertex_id = row.values[0].as_string()
                    # Create CALLS relationship
                    calls_rel_query = f'''
                    INSERT EDGE CALLS () VALUES "{parent_node}" -> "{actual_called_vertex_id}":();
                    '''
                    self.session.execute(calls_rel_query)
        elif isinstance(call_node.func, ast.Attribute):
            # Method call: obj.method_name()
            attr_name = call_node.func.attr
            # Try to find the method vertex
            check_method_query = f'''
            MATCH (n:Method) WHERE n.name == "{attr_name}"
            RETURN id(n) AS vertex_id LIMIT 1
            '''
            result = self.session.execute(check_method_query)

            if result.is_succeeded() and result.row_size() > 0:
                # Get the actual vertex ID from the result
                for row in result.rows():
                    actual_called_vertex_id = row.values[0].as_string()
                    # Create CALLS relationship
                    calls_rel_query = f'''
                    INSERT EDGE CALLS () VALUES "{parent_node}" -> "{actual_called_vertex_id}":();
                    '''
                    self.session.execute(calls_rel_query)

    def _process_c_ast_nodes(self, tu, file_path: str):
        """
        Process C AST nodes from libclang translation unit and create graph entities
        """
        from clang.cindex import CursorKind

        def traverse_c_ast(cursor, parent_node=None):
            # Process the current node
            self._process_c_cursor(cursor, file_path, parent_node)

            # Recursively process children
            for child in cursor.get_children():
                traverse_c_ast(child, parent_node)

        traverse_c_ast(tu.cursor)

    def _process_c_cursor(self, cursor, file_path: str, parent_node=None):
        """
        Process a single C AST cursor and create appropriate graph nodes/relationships
        """
        from clang.cindex import CursorKind

        # Use the sanitize method to ensure safe vertex IDs
        sanitized_file_path = self._sanitize_vertex_id(file_path)
        # Create file node if it doesn't exist
        file_vertex_id = f"file_{sanitized_file_path}"
        insert_file_query = f'''
        INSERT VERTEX File(path) VALUES "{file_vertex_id}":("{file_path}");
        '''
        try:
            self.session.execute(insert_file_query)
        except Exception:
            # File might already exist, which is fine
            pass

        if hasattr(cursor, 'kind') and cursor.kind == CursorKind.FUNCTION_DECL:
            self._process_c_function(cursor, file_path, file_vertex_id)
        elif hasattr(cursor, 'kind') and cursor.kind == CursorKind.VAR_DECL:
            self._process_c_variable(cursor, file_path, file_vertex_id)
        elif (hasattr(cursor, 'kind') and
              (cursor.kind == CursorKind.CLASS_DECL or cursor.kind == CursorKind.STRUCT_DECL)):
            self._process_c_struct(cursor, file_path, file_vertex_id)
        elif hasattr(cursor, 'kind') and cursor.kind == CursorKind.CALL_EXPR:
            self._process_c_function_call(cursor, file_path)
        elif hasattr(cursor, 'kind') and cursor.kind == CursorKind.INCLUSION_DIRECTIVE:
            self._process_c_include(cursor, file_path, file_vertex_id)

    def _process_c_function(self, cursor, file_path: str, file_vertex_id: str):
        """
        Process a C function declaration/definition
        """
        from clang.cindex import CursorKind
        func_name = cursor.spelling
        if not func_name:  # Skip anonymous functions/cursors
            return

        # Create function vertex
        sanitized_file_path = self._sanitize_vertex_id(file_path)
        func_vertex_id = f"c_function_{func_name}_{sanitized_file_path}_{cursor.location.line}"

        insert_function_query = f'''
        INSERT VERTEX Function(name, file_path, line_start, line_end, return_type, is_definition)
        VALUES "{func_vertex_id}":("{func_name}", "{file_path}", {cursor.location.line}, {cursor.location.line}, "{str(cursor.result_type.spelling)}", {1 if cursor.is_definition() else 0});
        '''
        try:
            self.session.execute(insert_function_query)

            # Create relationship to file
            contains_rel_query = f'''
            INSERT EDGE CONTAINS () VALUES "{file_vertex_id}" -> "{func_vertex_id}":();
            '''
            self.session.execute(contains_rel_query)

            # Process parameters
            for child in cursor.get_children():
                if hasattr(child, 'kind') and child.kind == CursorKind.PARM_DECL:
                    self._process_c_parameter(child, func_vertex_id, file_path)
        except Exception as e:
            logger.error(f"Error processing C function {func_name}: {e}")

    def _process_c_parameter(self, cursor, func_vertex_id: str, file_path: str):
        """
        Process a C function parameter
        """
        param_name = cursor.spelling
        if not param_name:
            return

        sanitized_file_path = self._sanitize_vertex_id(file_path)
        param_vertex_id = f"parameter_{param_name}_{sanitized_file_path}_{cursor.location.line}"

        insert_param_query = f'''
        INSERT VERTEX Parameter(name, type, function_name, file_path)
        VALUES "{param_vertex_id}":("{param_name}", "{str(cursor.type.spelling)}", "{func_vertex_id}", "{file_path}");
        '''
        try:
            self.session.execute(insert_param_query)

            # Create relationship: Function -> Parameter
            rel_query = f'''
            INSERT EDGE HAS_PARAMETER () VALUES "{func_vertex_id}" -> "{param_vertex_id}":();
            '''
            self.session.execute(rel_query)
        except Exception as e:
            logger.error(f"Error processing C parameter {param_name}: {e}")

    def _process_c_variable(self, cursor, file_path: str, file_vertex_id: str):
        """
        Process a C variable declaration
        """
        var_name = cursor.spelling
        if not var_name:
            return

        sanitized_file_path = self._sanitize_vertex_id(file_path)
        var_vertex_id = f"c_variable_{var_name}_{sanitized_file_path}_{cursor.location.line}"

        insert_var_query = f'''
        INSERT VERTEX Variable(name, type, file_path, line_start, line_end)
        VALUES "{var_vertex_id}":("{var_name}", "{str(cursor.type.spelling)}", "{file_path}", {cursor.location.line}, {cursor.location.line});
        '''
        try:
            self.session.execute(insert_var_query)

            # Create relationship to file
            contains_rel_query = f'''
            INSERT EDGE CONTAINS () VALUES "{file_vertex_id}" -> "{var_vertex_id}":();
            '''
            self.session.execute(contains_rel_query)
        except Exception as e:
            logger.error(f"Error processing C variable {var_name}: {e}")

    def _is_c_local_variable(self, cursor) -> bool:
        """
        Determine if a C variable is local to a function
        """
        from clang.cindex import CursorKind
        # A variable is local if its semantic parent is a function
        parent = cursor.semantic_parent
        return hasattr(parent, 'kind') and parent.kind in [CursorKind.FUNCTION_DECL, CursorKind.CXX_METHOD]

    def _process_c_struct(self, cursor, file_path: str, file_vertex_id: str):
        """
        Process a C struct/class declaration
        """
        struct_name = cursor.spelling
        if not struct_name:
            return

        sanitized_file_path = self._sanitize_vertex_id(file_path)
        struct_vertex_id = f"struct_{struct_name}_{sanitized_file_path}_{cursor.location.line}"

        insert_struct_query = f'''
        INSERT VERTEX Struct(name, file_path, line, column)
        VALUES "{struct_vertex_id}":("{struct_name}", "{file_path}", {cursor.location.line}, {cursor.location.column});
        '''
        try:
            self.session.execute(insert_struct_query)

            # Create relationship to file
            contains_rel_query = f'''
            INSERT EDGE CONTAINS () VALUES "{file_vertex_id}" -> "{struct_vertex_id}":();
            '''
            self.session.execute(contains_rel_query)
        except Exception as e:
            logger.error(f"Error processing C struct {struct_name}: {e}")

    def _process_c_function_call(self, cursor, file_path: str):
        """
        Process a C function call expression
        """
        from clang.cindex import CursorKind
        called_func_name = cursor.spelling
        if not called_func_name:
            return

        # Find the containing function
        caller_func = self._find_containing_function(cursor, file_path)
        if caller_func:
            # Look for the caller function vertex in the graph
            check_caller_query = f'''
            MATCH (n:Function) WHERE n.name == "{caller_func}"
            RETURN id(n) AS vertex_id LIMIT 1
            '''
            result = self.session.execute(check_caller_query)

            if result.is_succeeded() and result.row_size() > 0:
                for row in result.rows():
                    caller_vertex_id = row.values[0].as_string()

                    # Look for the called function vertex
                    check_called_query = f'''
                    MATCH (n:Function) WHERE n.name == "{called_func_name}"
                    RETURN id(n) AS vertex_id LIMIT 1
                    '''
                    called_result = self.session.execute(check_called_query)

                    if called_result.is_succeeded() and called_result.row_size() > 0:
                        for called_row in called_result.rows():
                            called_vertex_id = called_row.values[0].as_string()

                            # Create CALLS relationship
                            calls_rel_query = f'''
                            INSERT EDGE CALLS () VALUES "{caller_vertex_id}" -> "{called_vertex_id}":();
                            '''
                            self.session.execute(calls_rel_query)

    def _find_containing_function(self, cursor, file_path: str) -> Optional[str]:
        """
        Find the function that contains the given cursor
        """
        from clang.cindex import CursorKind
        parent = cursor.semantic_parent
        while parent and hasattr(parent, 'kind') and parent.kind != CursorKind.TRANSLATION_UNIT:
            if hasattr(parent, 'kind') and parent.kind == CursorKind.FUNCTION_DECL:
                return parent.spelling
            parent = parent.semantic_parent
        return None

    def _process_c_include(self, cursor, file_path: str, file_vertex_id: str):
        """
        Process a C include directive
        """
        include_file = cursor.spelling
        if not include_file:
            return

        # Use the sanitize method to ensure safe vertex IDs
        sanitized_include_file = self._sanitize_vertex_id(include_file)
        include_vertex_id = f"include_{sanitized_include_file}_{cursor.location.line}"

        insert_include_query = f'''
        INSERT VERTEX Include(file, file_path, line)
        VALUES "{include_vertex_id}":("{include_file}", "{file_path}", {cursor.location.line});
        '''
        try:
            self.session.execute(insert_include_query)

            # Create relationship to file
            includes_rel_query = f'''
            INSERT EDGE INCLUDES () VALUES "{file_vertex_id}" -> "{include_vertex_id}":();
            '''
            self.session.execute(includes_rel_query)
        except Exception as e:
            logger.error(f"Error processing C include {include_file}: {e}")
