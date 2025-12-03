from nebula3.gclient.net import ConnectionPool
from nebula3.Config import Config
from loguru import logger

from config.config import GRAPH_HOST, GRAPH_PORT, GRAPH_USER, GRAPH_PASSWORD


class ConnectionManager:
    """
    Manages Nebula Graph database connections and sessions
    """

    def __init__(
        self,
        host: str = GRAPH_HOST,
        port: int = GRAPH_PORT,
        user: str = GRAPH_USER,
        password: str = GRAPH_PASSWORD,
        max_connection_pool_size: int = 10
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.max_connection_pool_size = max_connection_pool_size

        # Initialize connection pool
        self.config = Config()
        self.config.max_connection_pool_size = max_connection_pool_size
        self.connection_pool = ConnectionPool()

        if not self.connection_pool.init([(self.host, self.port)], self.config):
            logger.error("Failed to initialize connection pool")
            raise Exception("Failed to initialize connection pool")

        logger.info(f"Connection pool initialized successfully for {
                    self.host}:{self.port}")

    def get_session(self):
        """
        Get a session from the connection pool
        """
        return self.connection_pool.get_session(self.user, self.password)

    def close(self):
        """
        Close the connection pool
        """
        if self.connection_pool:
            self.connection_pool.close()
            logger.info("Connection pool closed")

    def get_session_context(self):
        """
        Context manager for session handling with automatic cleanup
        """
        session = None
        try:
            session = self.get_session()
            yield session
        finally:
            if session:
                session.release()

    def should_create_session(self, session):
        if session is None:
            session = self.get_session_context()
        return session

    def execute_query(self, query: str, space: str, session=None):
        """
        Execute a query in the specified space
        If session is None, creates a new session; otherwise uses the provided session
        """
        session = self.should_create_session(session)
        # Use the specified space
        if 'USE' not in query:
            use_result = session.execute(f'USE {space};')
            if not use_result.is_succeeded():
                raise Exception(f"Failed to switch to space {space}: {use_result.error_msg()}")

        # Execute the query
        result = session.execute(query)
        return result


connection_manager = ConnectionManager()
