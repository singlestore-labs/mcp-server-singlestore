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


def create_and_upload_notebook(
    filename: str = "singlestore_analysis",
    title: str = "SingleStore Data Analysis",
    subject: str = "data analysis and exploration",
    upload_location: str = "shared",
) -> list:
    """
    Guide users through creating a Jupyter notebook and uploading it to SingleStore Helios Platform.
    This prompt helps users:
    1. Create a new notebook with customized content based on the subject and title
    2. Upload it to their SingleStore workspace with the specified filename and location

    Args:
        filename: Name for the notebook file (without .ipynb extension, e.g., "sales_analysis")
        title: The main title to display in the notebook (e.g., "Sales Performance Analysis")
        subject: Description of the notebook's purpose/content (e.g., "quarterly sales performance analysis")
        upload_location: Where to upload ("shared" or "personal")
    """
    return [
        AssistantMessage(
            f"🚀 Let's create a professional Jupyter notebook for {subject}!"
        ),
        AssistantMessage(
            f"I'll create a well-structured notebook titled '{title}' using the SingleStore notebook format. "
            "This will include professional documentation, connection setup with error handling, "
            "sample queries tailored to your use case, and best practices."
        ),
        UserMessage(
            f"Use the create_notebook_file tool to create a notebook with the following JSON structure:\n\n"
            f"```json\n"
            f"{{\n"
            f'  "cells": [\n'
            f'    {{ "type": "markdown", "content": "# {title}" }},\n'
            f'    {{ "type": "markdown", "content": "## Overview\\nThis notebook is designed for {subject} using SingleStore. It provides a foundation for connecting to your SingleStore database and performing various data operations." }},\n'
            f'    {{ "type": "markdown", "content": "## Getting Started\\nTo use this notebook effectively:\\n1. Ensure you have access to a SingleStore database\\n2. Install the required dependencies: `pip install singlestoredb pandas`\\n3. Update the connection parameters below with your database credentials" }},\n'
            f'    {{ "type": "code", "content": "# Import required libraries\\nimport singlestoredb as s2\\nimport pandas as pd\\nfrom datetime import datetime\\nimport warnings\\nwarnings.filterwarnings(\'ignore\')\\n\\nprint(\\"Libraries imported successfully!\\")" }},\n'
            f"    {{ \"type\": \"code\", \"content\": \"# SingleStore connection configuration\\n# Replace these with your actual database credentials\\nconnection_params = {{\\n    'host': 'your-host.singlestore.com',\\n    'port': 3306,\\n    'user': 'your-username',\\n    'password': 'your-password',\\n    'database': 'your-database'\\n}}\\n\\n# Establish connection\\ntry:\\n    conn = s2.connect(**connection_params)\\n    print(\\\"✅ Successfully connected to SingleStore!\\\")\\nexcept Exception as e:\\n    print(f\\\"❌ Connection failed: {{e}}\\\")\\n    print(\\\"Please verify your connection parameters\\\")\" }},\n"
            f'    {{ "type": "code", "content": "# Example query for {subject}\\n# Modify this query based on your specific data and analysis needs\\nsample_query = \\"\\"\\"\\nSELECT\\n    COUNT(*) as total_records,\\n    \'Sample data exploration for {subject}\' as description\\n\\"\\"\\"\\n\\ntry:\\n    result_df = pd.read_sql(sample_query, conn)\\n    print(\\"Query executed successfully!\\")\\n    display(result_df)\\nexcept Exception as e:\\n    print(f\\"Query error: {{e}}\\")\\n    print(\\"Please ensure your database has the required tables and permissions\\")" }},\n'
            f'    {{ "type": "markdown", "content": "## Next Steps for {title}\\n1. **Data Exploration**: Examine your table schemas and available data\\n2. **Custom Queries**: Replace the sample query with your specific analysis requirements\\n3. **Visualization**: Add data visualization using matplotlib, seaborn, or plotly\\n4. **Analysis**: Implement your specific {subject} logic\\n5. **Documentation**: Add markdown cells to document your findings and methodology" }},\n'
            f'    {{ "type": "code", "content": "# Don\'t forget to close the connection when done\\nif \'conn\' in locals():\\n    conn.close()\\n    print(\\"Database connection closed.\\")" }}\n'
            f"  ]\n"
            f"}}\n"
            f"```"
        ),
        AssistantMessage(
            f"Excellent! Your '{title}' notebook has been created using the proper SingleStore format. "
            f"The notebook includes 8 well-structured cells with professional documentation and error handling."
        ),
        AssistantMessage(
            f"Now let's upload this notebook to your SingleStore Helios Platform. "
            f"I'll upload it with the filename '{filename}.ipynb' to your {upload_location} space using upload_notebook_file tool"
        ),
        UserMessage(
            f"Use the upload_notebook_file tool to upload the notebook with filename '{filename}' and upload_location '{upload_location}'"
        ),
        AssistantMessage(
            f"Perfect! Your notebook '{filename}.ipynb' has been uploaded to your {upload_location} space. "
            "Would you like me to create a schedule job for this notebook or upload it as a cloud function?"
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
        "title": "Create and Upload Notebook",
        "func": create_and_upload_notebook,
    },
    {
        "title": "Help",
        "func": help,
    },
]

# Export the prompts using create_from_dict for consistency
prompts = [Prompt.create_from_dict(prompt) for prompt in prompts_definitions]
