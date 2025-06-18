import singlestoredb as s2
from src.config.config import get_settings
import src.version as version

# Deployment can be local or remote
MCP_PROGRAM_NAME = "{deployment} MCP Server"


class S2Manager:
    """
    Manages SingleStore database connections with custom connection attributes for tracking.
    """

    def __init__(self, host, user, password, database=None, **kwargs):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.extra_kwargs = kwargs

        settings = get_settings()

        deployment = "Remote" if settings.is_remote else "Local"

        conn_attrs = {
            "program_name": MCP_PROGRAM_NAME.format(deployment=deployment),
            "program_version": getattr(version, "__version__", "unknown"),
        }
        if "conn_attrs" in self.extra_kwargs:
            conn_attrs.update(self.extra_kwargs.pop("conn_attrs"))
        self.connection = s2.connect(
            user=self.user,
            host=self.host,
            password=self.password,
            database=self.database,
            conn_attrs=conn_attrs,
            **self.extra_kwargs,
        )
        self.cursor = self.connection.cursor()

    def execute(self, query, params=None):
        if params:
            return self.cursor.execute(query, params)
        return self.cursor.execute(query)

    def fetchall(self):
        return self.cursor.fetchall()

    def close(self):
        """
        Closes the cursor and the connection safely.
        """
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
