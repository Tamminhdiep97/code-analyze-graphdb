from loguru import logger

from core.database.connection_manager import ConnectionManager


class SchemaManager:
    """
    Manages Nebula Graph schema (spaces, tags, edges)
    """

    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager

    def create_space(self, space_name: str) -> bool:
        """
        Create a graph space if it doesn't exist
        """
        try:
            logger.info(f"Creating space {space_name} if it doesn't exist")

            # Create space for code graph with larger vertex ID size to accommodate longer vertex IDs
            create_space_query = f'''
            CREATE SPACE IF NOT EXISTS {space_name} (
                partition_num = 1,
                replica_factor = 1,
                vid_type = FIXED_STRING(256)
            );
            '''

            logger.info(f"Executing space creation query: {create_space_query}...")
            result = self.connection_manager.execute_query(create_space_query)

            if result.is_succeeded():
                logger.info(f"Successfully created or verified space {space_name}")

                # Wait a bit for space creation to complete
                import time
                logger.info("Waiting for space creation to complete...")
                time.sleep(2)

                # Verify that the space exists before creating schema
                logger.info("Verifying space exists...")
                verify_result = self.connection_manager.execute_query(f"USE {space_name};")
                if verify_result.is_succeeded():
                    logger.info(f"Successfully verified and switched to space {space_name}")
                    return True
                else:
                    logger.error(f"Could not access space {space_name}: {
                                 verify_result.error_msg()}")
                    return False
            else:
                logger.error(f"Failed to create space: {result.error_msg()}")
                return False

        except Exception as e:
            logger.error(f"Error creating space {space_name}: {e}")
            return False

    def create_schema(self, space_name: str) -> bool:
        """
        Create tags and edges schema in the specified space
        """
        try:
            logger.info(f"Creating schema in space {space_name}")

            # Use the space
            use_result = self.connection_manager.execute_query(
                f'USE {space_name};')
            if not use_result.is_succeeded():
                logger.error(f"Failed to use space {space_name}: {use_result.error_msg()}")
                return False

            # Create tags for different code entities
            tag_queries = {
                'File': "CREATE TAG IF NOT EXISTS File (`path` string);",
                'Function': "CREATE TAG IF NOT EXISTS Function (name string, file_path string, line_start int, line_end int, docstring string);",
                'Variable': "CREATE TAG IF NOT EXISTS Variable (name string, scope string, function_name string, file_path string, type string, line_start int);",
                'Class': "CREATE TAG IF NOT EXISTS Class (name string, file_path string, line_start int, line_end int);",
                'Method': "CREATE TAG IF NOT EXISTS Method (name string, class_name string, file_path string, line_start int, line_end int);",
                'Parameter': "CREATE TAG IF NOT EXISTS Parameter (name string, type string, function_name string, file_path string);",
                'Module': "CREATE TAG IF NOT EXISTS Module (name string, as_name string, file_path string);",
                'Import': "CREATE TAG IF NOT EXISTS Import (name string, as_name string, module string, file_path string);",
                'Struct': "CREATE TAG IF NOT EXISTS Struct (name string, file_path string, line int, column int);",
                'Include': "CREATE TAG IF NOT EXISTS Include (file string, file_path string, line int);"
            }

            for tag_name, query in tag_queries.items():
                logger.info(f"Creating {tag_name} tag...")
                result = self.connection_manager.execute_query(query)
                if result.is_succeeded():
                    logger.info(f"Successfully created {tag_name} tag")
                else:
                    logger.error(f"Failed to create {tag_name} tag: {result.error_msg()}")
                    return False

            # Create edge types for relationships
            edge_queries = {
                'CONTAINS': "CREATE EDGE IF NOT EXISTS CONTAINS ();",
                'HAS_PARAMETER': "CREATE EDGE IF NOT EXISTS HAS_PARAMETER ();",
                'CALLS': "CREATE EDGE IF NOT EXISTS CALLS ();",
                'IMPORTS': "CREATE EDGE IF NOT EXISTS IMPORTS ();",
                'IMPORTS_FROM': "CREATE EDGE IF NOT EXISTS IMPORTS_FROM ();",
                'INCLUDES': "CREATE EDGE IF NOT EXISTS INCLUDES ();"
            }

            for edge_name, query in edge_queries.items():
                logger.info(f"Creating {edge_name} edge...")
                result = self.connection_manager.execute_query(query)
                if result.is_succeeded():
                    logger.info(f"Successfully created {edge_name} edge")
                else:
                    logger.error(f"Failed to create {edge_name} edge: {result.error_msg()}")
                    return False

            logger.info("Schema creation completed successfully")
            return True

        except Exception as e:
            logger.error(f"Error creating schema: {e}")
            return False

    def setup_space_with_schema(self, space_name: str) -> bool:
        """
        Create space and schema in one go
        """
        # Create space
        if not self.create_space(space_name):
            logger.error(f"Failed to create space {space_name}")
            return False

        # Create schema
        if not self.create_schema(space_name):
            logger.error(f"Failed to create schema in space {space_name}")
            return False
        return True
