"""
Query System module to extract relevant code context from the graph database
"""
from typing import List, Dict, Any
from nebula3.gclient.net import ConnectionPool
from nebula3.Config import Config
from loguru import logger


class QuerySystem:
    """
    System to query the graph database for relevant code context
    """

    def __init__(self, graph_host: str = "localhost", graph_port: int = 9669, user: str = "root", password: str = "password", space: str = "code_graph"):
        """
        Initialize the query system with connection to Nebula Graph
        """
        self.space = space
        # Initialize connection pool
        self.config = Config()
        self.config.max_connection_pool_size = 10
        self.connection_pool = ConnectionPool()
        if not self.connection_pool.init([(graph_host, graph_port)], self.config):
            raise Exception("Failed to initialize connection pool")
        self.session = self.connection_pool.get_session(user, password)

        # Use the space
        self.session.execute(f'USE {space};')

    def get_function_dependencies(self, function_name: str, file_path: str = None) -> List[Dict[str, Any]]:
        """
        Get all functions called by a specific function
        """
        if file_path:
            query = f"""
            MATCH (f:Function) WHERE f.name == "{function_name}" AND f.file_path == "{file_path}"
            -[:CALLS]->(called:Function)
            RETURN called.name as name, called.file_path as file_path, called.line_start as line_start
            """
        else:
            query = f"""
            MATCH (f:Function) WHERE f.name == "{function_name}"
            -[:CALLS]->(called:Function)
            RETURN called.name as name, called.file_path as file_path, called.line_start as line_start
            """
        try:
            result = self.session.execute(query)
            if result.is_succeeded():
                records = []
                for row in result.rows():
                    record = {
                        'name': row.values[0].as_string(),
                        'file_path': row.values[1].as_string(),
                        'line_start': row.values[2].as_int() if row.values[2].is_int() else row.values[2].as_string()
                    }
                    records.append(record)
                return records
            else:
                logger.error(f"Query failed: {result.error_msg()}")
                return []
        except Exception as e:
            logger.error(f"Error getting function dependencies: {e}")
            return []

    def get_function_callers(self, function_name: str, file_path: str = None) -> List[Dict[str, Any]]:
        """
        Get all functions that call a specific function
        """
        if file_path:
            query = f"""
            MATCH (caller:Function)-[:CALLS]->(f:Function) WHERE f.name == "{function_name}" AND f.file_path == "{file_path}"
            RETURN caller.name as name, caller.file_path as file_path, caller.line_start as line_start
            """
        else:
            query = f"""
            MATCH (caller:Function)-[:CALLS]->(f:Function) WHERE f.name == "{function_name}"
            RETURN caller.name as name, caller.file_path as file_path, caller.line_start as line_start
            """
        try:
            result = self.session.execute(query)
            if result.is_succeeded():
                records = []
                for row in result.rows():
                    record = {
                        'name': row.values[0].as_string(),
                        'file_path': row.values[1].as_string(),
                        'line_start': row.values[2].as_int() if row.values[2].is_int() else row.values[2].as_string()
                    }
                    records.append(record)
                return records
            else:
                logger.error(f"Query failed: {result.error_msg()}")
                return []
        except Exception as e:
            logger.error(f"Error getting function callers: {e}")
            return []

    def get_variable_usage(self, variable_name: str, file_path: str = None) -> List[Dict[str, Any]]:
        """
        Get all places where a variable is used
        """
        if file_path:
            query = f"""
            MATCH (v:Variable) WHERE v.name == "{variable_name}" AND v.file_path == "{file_path}"
            RETURN v.scope as scope, v.line_start as line_start, v.function_name as function_name
            """
        else:
            query = f"""
            MATCH (v:Variable) WHERE v.name == "{variable_name}"
            RETURN v.scope as scope, v.line_start as line_start, v.function_name as function_name, v.file_path as file_path
            """
        try:
            result = self.session.execute(query)
            if result.is_succeeded():
                records = []
                for row in result.rows():
                    record = {
                        'scope': row.values[0].as_string() if row.values[0].is_string() else None,
                        'line_start': row.values[1].as_int() if row.values[1].is_int() else row.values[1].as_string(),
                        'function_name': row.values[2].as_string() if row.values[2].is_string() else None,
                        'file_path': row.values[3].as_string() if len(row.values) > 3 and row.values[3].is_string() else None
                    }
                    records.append(record)
                return records
            else:
                logger.error(f"Query failed: {result.error_msg()}")
                return []
        except Exception as e:
            logger.error(f"Error getting variable usage: {e}")
            return []

    def get_impacted_functions(self, changed_file_path: str, changed_functions: List[str]) -> List[Dict[str, Any]]:
        """
        Get all functions that might be impacted by changes in specific functions
        """
        # Construct the query with the function names list in Nebula format
        functions_str = '", "'.join(changed_functions)
        query = f"""
        MATCH (changed_func:Function) WHERE changed_func.file_path == "{changed_file_path}" AND changed_func.name IN ["{functions_str}"]
        MATCH (changed_func)<-[:CALLS*1..5]-(impacted:Function)
        RETURN DISTINCT impacted.name as name, impacted.file_path as file_path, impacted.line_start as line_start
        """
        try:
            result = self.session.execute(query)
            if result.is_succeeded():
                records = []
                for row in result.rows():
                    record = {
                        'name': row.values[0].as_string(),
                        'file_path': row.values[1].as_string(),
                        'line_start': row.values[2].as_int() if row.values[2].is_int() else row.values[2].as_string()
                    }
                    records.append(record)
                return records
            else:
                logger.error(f"Query failed: {result.error_msg()}")
                return []
        except Exception as e:
            logger.error(f"Error getting impacted functions: {e}")
            return []

    # def get_related_components(self, file_path: str) -> List[Dict[str, Any]]:
    #     """
    #     Get all components related to a specific file
    #     """
    #     query = f"""
    #     MATCH (f:File)-[:CONTAINS]->(comp) WHERE f.path == "{file_path}"
    #     AND (comp:Function OR comp:Class OR comp:Variable OR comp:Method OR comp:Struct)
    #     RETURN tags(comp)[0] as type, comp.name as name, comp.line_start as line_start
    #     """
    #     try:
    #         result = self.session.execute(query)
    #         if result.is_succeeded():
    #             records = []
    #             for row in result.rows():
    #                 record = {
    #                     'type': row.values[0].as_string(),
    #                     'name': row.values[1].as_string(),
    #                     'line_start': row.values[2].as_int() if row.values[2].is_int() else row.values[2].as_string()
    #                 }
    #                 records.append(record)
    #             return records
    #         else:
    #             logger.error(f"Query failed: {result.error_msg()}")
    #             return []
    #     except Exception as e:
    #         logger.error(f"Error getting related components: {e}")
    #         return []
    def get_related_components(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Get all components related to a specific file
        """
        # Get all possible component types separately to avoid the tags() function error
        components = []

        # Query for Functions
        query_func = f"""
        MATCH (f:File)-[:CONTAINS]->(comp:Function) WHERE f.path == "{file_path}"
        RETURN "Function" as type, comp.name as name, comp.line_start as line_start
        """
        try:
            result = self.session.execute(query_func)
            if result.is_succeeded():
                for row in result.rows():
                    record = {
                        'type': row.values[0].as_string(),
                        'name': row.values[1].as_string(),
                        'line_start': row.values[2].as_int() if row.values[2].is_int() else row.values[2
                                                                                                       ].as_string()
                    }
                    components.append(record)
        except Exception as e:
            logger.error(f"Error getting function components: {e}")

        # Query for Classes
        query_class = f"""
        MATCH (f:File)-[:CONTAINS]->(comp:Class) WHERE f.path == "{file_path}"
        RETURN "Class" as type, comp.name as name, comp.line_start as line_start
        """
        try:
            result = self.session.execute(query_class)
            if result.is_succeeded():
                for row in result.rows():
                    record = {
                        'type': row.values[0].as_string(),
                        'name': row.values[1].as_string(),
                        'line_start': row.values[2].as_int() if row.values[2].is_int() else row.values[2
                                                                                                       ].as_string()
                    }
                    components.append(record)
        except Exception as e:
            logger.error(f"Error getting class components: {e}")

        # Query for Variables
        query_var = f"""
        MATCH (f:File)-[:CONTAINS]->(comp:Variable) WHERE f.path == "{file_path}"
        RETURN "Variable" as type, comp.name as name, comp.line_start as line_start
        """
        try:
            result = self.session.execute(query_var)
            if result.is_succeeded():
                for row in result.rows():
                    record = {
                        'type': row.values[0].as_string(),
                        'name': row.values[1].as_string(),
                        'line_start': row.values[2].as_int() if row.values[2].is_int() else row.values[2
                                                                                                       ].as_string()
                    }
                    components.append(record)
        except Exception as e:
            logger.error(f"Error getting variable components: {e}")

        # Query for Methods
        query_meth = f"""
        MATCH (f:File)-[:CONTAINS]->(comp:Method) WHERE f.path == "{file_path}"
        RETURN "Method" as type, comp.name as name, comp.line_start as line_start
        """
        try:
            result = self.session.execute(query_meth)
            if result.is_succeeded():
                for row in result.rows():
                    record = {
                        'type': row.values[0].as_string(),
                        'name': row.values[1].as_string(),
                        'line_start': row.values[2].as_int() if row.values[2].is_int() else row.values[2
                                                                                                       ].as_string()
                    }
                    components.append(record)
        except Exception as e:
            logger.error(f"Error getting method components: {e}")

        # Query for Structs
        query_struct = f"""
        MATCH (f:File)-[:CONTAINS]->(comp:Struct) WHERE f.path == "{file_path}"
        RETURN "Struct" as type, comp.name as name, comp.line_start as line_start
        """
        try:
            result = self.session.execute(query_struct)
            if result.is_succeeded():
                for row in result.rows():
                    record = {
                        'type': row.values[0].as_string(),
                        'name': row.values[1].as_string(),
                        'line_start': row.values[2].as_int() if row.values[2].is_int() else row.values[2
                                                                                                       ].as_string()
                    }
                    components.append(record)
        except Exception as e:
            logger.error(f"Error getting struct components: {e}")

        return components

    def get_data_flow_from_variable(self, variable_name: str, file_path: str) -> List[Dict[str, Any]]:
        """
        Get the flow of data from a specific variable
        """
        query = f"""
        MATCH (v:Variable)-[:HAS_PARAMETER|CONTAINS*]-(func:Function) WHERE v.name == "{variable_name}" AND v.file_path == "{file_path}"
        OPTIONAL MATCH (func)-[:CALLS]->(called:Function)
        RETURN v.name as var_name, func.name as function_name, called.name as called_function
        """
        try:
            result = self.session.execute(query)
            if result.is_succeeded():
                records = []
                for row in result.rows():
                    record = {
                        'var_name': row.values[0].as_string(),
                        'function_name': row.values[1].as_string() if row.values[1].is_string() else None,
                        'called_function': row.values[2].as_string() if row.values[2].is_string() else None
                    }
                    records.append(record)
                return records
            else:
                logger.error(f"Query failed: {result.error_msg()}")
                return []
        except Exception as e:
            logger.error(f"Error getting data flow from variable: {e}")
            return []

    def get_security_vulnerability_patterns(self) -> List[Dict[str, Any]]:
        """
        Find common security vulnerability patterns in the codebase
        """
        patterns = []

        # Find uses of dangerous functions (eval, exec)
        query = """
        MATCH (f:Function)-[:CALLS]->(danger:Function)
        WHERE danger.name IN ["eval", "exec", "compile"]
        RETURN f.name as function_name, f.file_path as file_path, f.line_start as line_start, danger.name as dangerous_function
        """
        try:
            result = self.session.execute(query)
            if result.is_succeeded():
                for row in result.rows():
                    record = {
                        'function_name': row.values[0].as_string(),
                        'file_path': row.values[1].as_string(),
                        'line_start': row.values[2].as_int() if row.values[2].is_int() else row.values[2].as_string(),
                        'dangerous_function': row.values[3].as_string()
                    }
                    patterns.append(record)
        except Exception as e:
            logger.error(f"Error getting dangerous function patterns: {e}")

        # Find SQL-related string concatenations (simplified pattern)
        query = """
        MATCH (f:Function)-[:CALLS]->(db_func:Function)
        WHERE db_func.name IN ["execute", "query", "select"]
        RETURN f.name as function_name, f.file_path as file_path, f.line_start as line_start, db_func.name as db_operation
        """
        try:
            result = self.session.execute(query)
            if result.is_succeeded():
                for row in result.rows():
                    record = {
                        'function_name': row.values[0].as_string(),
                        'file_path': row.values[1].as_string(),
                        'line_start': row.values[2].as_int() if row.values[2].is_int() else row.values[2].as_string(),
                        'db_operation': row.values[3].as_string()
                    }
                    patterns.append(record)
        except Exception as e:
            logger.error(f"Error getting SQL vulnerability patterns: {e}")

        return patterns
