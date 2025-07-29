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
    # Create structured content based on the subject
    notebook_structure = f"""Create a notebook file with the following content:

**Cell 1 (Markdown):**
# {title}

**Cell 2 (Markdown):**
## Overview
This notebook is designed for {subject} using SingleStore. It provides a foundation for connecting to your SingleStore database and performing various data operations.

**Cell 3 (Markdown):**
## Getting Started
To use this notebook effectively:
1. Ensure you have access to a SingleStore database
2. Install the required dependencies: `pip install singlestoredb pandas`
3. Update the connection parameters below with your database credentials

**Cell 4 (Code - Python):**
# Import required libraries
import singlestoredb as s2
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("Libraries imported successfully!")

**Cell 5 (Code - Python):**
# SingleStore connection configuration
# Replace these with your actual database credentials
connection_params = {{
    'host': 'your-host.singlestore.com',
    'port': 3306,
    'user': 'your-username',
    'password': 'your-password',
    'database': 'your-database'
}}

# Establish connection
try:
    conn = s2.connect(**connection_params)
    print("✅ Successfully connected to SingleStore!")
except Exception as e:
    print(f"❌ Connection failed: {{e}}")
    print("Please verify your connection parameters")

**Cell 6 (Code - Python):**
# Example query for {subject}
# Modify this query based on your specific data and analysis needs
sample_query = \"\"\"
SELECT
    COUNT(*) as total_records,
    'Sample data exploration for {subject}' as description
\"\"\"

try:
    result_df = pd.read_sql(sample_query, conn)
    print("Query executed successfully!")
    display(result_df)
except Exception as e:
    print(f"Query error: {{e}}")
    print("Please ensure your database has the required tables and permissions")

**Cell 7 (Markdown):**
## Next Steps for {title}
1. **Data Exploration**: Examine your table schemas and available data
2. **Custom Queries**: Replace the sample query with your specific analysis requirements
3. **Visualization**: Add data visualization using matplotlib, seaborn, or plotly
4. **Analysis**: Implement your specific {subject} logic
5. **Documentation**: Add markdown cells to document your findings and methodology

**Cell 8 (Code - Python):**
# Don't forget to close the connection when done
if 'conn' in locals():
    conn.close()
    print("Database connection closed.")"""

    return [
        AssistantMessage(
            f"Let's create a professional Jupyter notebook for {subject}!"
        ),
        AssistantMessage(
            f"I'll create a well-structured notebook titled '{title}' that includes:\n"
            "• Professional documentation and overview\n"
            "• SingleStore connection setup with error handling\n"
            "• Sample queries tailored to your use case\n"
            "• Next steps and best practices\n"
            "• Proper connection management"
        ),
        UserMessage(notebook_structure),
        AssistantMessage(
            f"Excellent! Your '{title}' notebook has been created with a professional structure. "
            f"Now let's upload it to your SingleStore Helios Platform for easy access and collaboration."
        ),
        AssistantMessage(
            f"I'll upload this notebook with the filename '{filename}.ipynb' to your {upload_location} space. "
            f"This ensures {'your team can collaborate on it' if upload_location == 'shared' else 'it remains in your personal workspace'}."
        ),
        UserMessage(
            f"Upload the notebook to my SingleStore workspace with the filename '{filename}' in the {upload_location} space."
        ),
        AssistantMessage(
            f"Perfect! Your notebook '{filename}.ipynb' has been uploaded to your {upload_location} space. "
            "Here's what you can do next:"
        ),
        AssistantMessage(
            f"**Access Options:**\n"
            f"• **Helios Portal**: Open through your SingleStore Helios dashboard\n"
            f"• **Direct Link**: Access via the SingleStore Notebooks interface\n"
            f"• **{'Team Collaboration' if upload_location == 'shared' else 'Personal Workspace'}**: "
            f"{'Available to all team members in shared space' if upload_location == 'shared' else 'Secure in your personal space'}\n\n"
            f"**⚡ Features Available:**\n"
            f"• **Live Database Connections**: Execute queries against real-time data\n"
            f"• **Auto-save**: Your work is automatically saved\n"
            f"• **Version Control**: Track changes and collaborate safely\n"
            f"• **Performance Insights**: Built-in query performance monitoring\n\n"
            f"**Ready to customize for your specific {subject}!**"
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
