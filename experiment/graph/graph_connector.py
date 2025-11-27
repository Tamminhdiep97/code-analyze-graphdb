import os

from loguru import logger
from nebula3.gclient.net import ConnectionPool
from nebula3.Config import Config

class NebulaConnector:
    """
    A connector class to manage connections to Nebula Graph
    """

    def __init__(self,
                 graph_host: str = "localhost",
                 graph_port: int = 9669,
                 user: str = "root",
                 password: str = "password",
                 space: str = "code_graph"):
        """
        Initialize the Nebula connector with connection parameters
        """
        self.graph_host = graph_host
        self.graph_port = graph_port
        self.user = user
        self.password = password
        self.space = space

        # Initialize connection pool
        self.config = Config()
        self.config.max_connection_pool_size = 10
        self.connection_pool = ConnectionPool()

        if not self.connection_pool.init([(self.graph_host, self.graph_port)], self.config):
            raise Exception("Failed to initialize connection pool")

        # Get a session and ensure the space exists
        self.session = self.connection_pool.get_session(self.user, self.password)
        self._ensure_space_exists()

    def _ensure_space_exists(self):
        """
        Ensure the code_graph space exists and use it
        """
        # Create space if it doesn't exist
        create_space_query = f'''
        CREATE SPACE IF NOT EXISTS {self.space} (
            partition_num = 1,
            replica_factor = 1,
            vid_type = FIXED_STRING(32)
        );
        '''
        self.session.execute(create_space_query)

        # Use the space
        self.session.execute(f'USE {self.space};')

    def execute_query(self, query: str):
        """
        Execute a query and return the result
        """
        return self.session.execute(query)

    def close(self):
        """
        Close the connection
        """
        if hasattr(self, 'session'):
            self.session.release()
        if hasattr(self, 'connection_pool'):
            self.connection_pool.close()


def main():
    """
    Example usage of the Nebula connector
    """
    # Use environment variables or default values
    graph_host = os.getenv('GRAPH_HOST', 'localhost')
    graph_port = int(os.getenv('GRAPH_PORT', 9669))
    user = os.getenv('GRAPH_USER', 'root')
    password = os.getenv('GRAPH_PASSWORD', 'password')
    space = os.getenv('GRAPH_SPACE', 'code_graph')

    logger.info(f"graph_host: {graph_host}")
    logger.info(f"graph_port: {graph_port}")
    logger.info(f"user: {user}")
    logger.info(f"pass: {password}")
    logger.info(f"space: {space}")

    # Create connector instance
    connector = NebulaConnector(
        graph_host=graph_host,
        graph_port=graph_port,
        user=user,
        password=password,
        space=space
    )

    try:
        # Example queries - replace with your actual queries
        result = connector.execute_query('SHOW TAGS')
        print("Available tags in the graph:")
        print(result)

        # You can execute any nGQL query here:
        # result = connector.execute_query('MATCH (n) RETURN n LIMIT 10')
        # print(result)

    except Exception as e:
        print(f"Error executing query: {e}")
    finally:
        # Always close the connection
        connector.close()


if __name__ == '__main__':
    main()
