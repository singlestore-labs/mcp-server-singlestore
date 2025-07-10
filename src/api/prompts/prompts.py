from src.api.prompts.types import Prompt
from mcp.server.fastmcp.prompts.base import AssistantMessage, UserMessage


def onboarding_prompt() -> list:
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
            "Step 3: Load sample data into your new database. Try running this SQL in your virtual workspace:"
        ),
        AssistantMessage(
            """\
CREATE TABLE IF NOT EXISTS sample_customers (
    id INT NOT NULL,
    name VARCHAR(100),
    email VARCHAR(100),
    country VARCHAR(50),
    PRIMARY KEY (id)
);

INSERT INTO sample_customers VALUES
    (1, 'John Doe', 'john@example.com', 'USA'),
    (2, 'Jane Smith', 'jane@example.com', 'Canada'),
    (3, 'Alice Johnson', 'alice@example.com', 'UK');
"""
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


prompts_definitions = [
    {
        "title": "New User Onboarding",
        "func": onboarding_prompt,
    }
]

# Export the prompts using create_from_dict for consistency
prompts = [Prompt.create_from_dict(prompt) for prompt in prompts_definitions]
