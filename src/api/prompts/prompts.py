from src.api.prompts.types import Prompt
from mcp.server.fastmcp.prompts.base import AssistantMessage, UserMessage


def onboarding_helios_user() -> list:
    """
    Guide new users through SingleStore setup process:
    1. Account setup and organization selection
    2. Workspace creation with sample data
    3. Basic SQL tutorial
    """
    return [
        AssistantMessage("Welcome to SingleStore! Let's get you started."),
        AssistantMessage(
            "Step 1: Make sure you are authenticated and have access to an organization. If you haven't, please run the login command or use the authentication flow in your client."
        ),
        AssistantMessage(
            "Step 2: Create a starter workspace and database. You can do this by running the following command or using the UI:"
        ),
        UserMessage(
            "Let's create a starter workspace if I don't have one yet. Then, populate the database with sample data.",
        ),
        AssistantMessage(
            "Step 3: First, let's create a table to store our sample customer data:"
        ),
        AssistantMessage(
            """\
CREATE TABLE IF NOT EXISTS sample_customers (
    id INT NOT NULL,
    name VARCHAR(100),
    email VARCHAR(100),
    country VARCHAR(50),
    PRIMARY KEY (id)
);"""
        ),
        AssistantMessage("Great! Now let's add some sample data to our table:"),
        AssistantMessage(
            """\
INSERT INTO sample_customers VALUES
    (1, 'John Doe', 'john@example.com', 'USA'),
    (2, 'Jane Smith', 'jane@example.com', 'Canada'),
    (3, 'Alice Johnson', 'alice@example.com', 'UK');"""
        ),
        AssistantMessage("Step 4: Try your first query!"),
        UserMessage("Let's run a simple select query to see our data."),
        AssistantMessage(
            """Here are some ways to explore your SingleStore database:

1. Performance Monitoring & Analysis:
   - View query history and performance metrics in SingleStore Helios Portal
   - Try EXPLAIN before queries to analyze execution plans

2. Data Management:
   - Experiment with different table types (rowstore vs. columnstore)
   - Try bulk data loading with LOAD DATA
   - Explore JSON and geospatial data types

3. Optimization Features:
   - Create indexes for better query performance
   - Use window functions for analytics
   - Try full-text search capabilities

4. Development Integration:
   - Connect using various client libraries (Python, Drizzle ORM)
   - Explore SingleStore Notebooks for interactive analysis

Which area would you like to explore first?"""
        ),
    ]


def help() -> list:
    """
    Provides an overview of the SingleStore MCP server capabilities,
    available tools, resources, and prompts.
    """
    return [
        AssistantMessage(
            "Welcome to the SingleStore Model Context Protocol (MCP) Server! 👋\nDo not call any tools! The user only wnat's to list them, not perform any action"
        ),
        AssistantMessage(
            "Let me show you what tools , resources, and prompts are available to you."
        ),
        AssistantMessage(
            "Organize the response in the following format:\n"
            "- **Tools**: List of available tools with brief descriptions\n"
            "- **Resources**: Links to documentation, tutorials, and guides\n"
            "- **Prompts**: List of available prompts with their titles and descriptions"
        ),
        UserMessage("List all the MCP tools, resources, and prompts available to me."),
        AssistantMessage(
            "Need help with something specific? Just ask and I'll guide you through it!"
        ),
    ]


prompts_definitions = [
    {
        "title": "Helios User Onboarding",
        "func": onboarding_helios_user,
    },
    {
        "title": "Help",
        "func": help,
    },
]

# Export the prompts using create_from_dict for consistency
prompts = [Prompt.create_from_dict(prompt) for prompt in prompts_definitions]
