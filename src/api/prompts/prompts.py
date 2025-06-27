from src.api.prompts.types import Prompt
from src.api.responses import prompt_response


@prompt_response
def sql_optimization_prompt(query: str, database_type: str = "singlestore") -> str:
    """
    Generate a prompt for SQL query optimization analysis.

    Args:
        query: The SQL query to optimize
        database_type: The type of database (default: singlestore)
    """
    return f"""
    Please analyze and optimize the following {database_type.upper()} SQL query:

    ```sql
    {query}
    ```

    Consider the following optimization strategies:
    1. Index usage and recommendations
    2. Query structure improvements
    3. JOIN optimization
    4. WHERE clause efficiency
    5. SingleStore-specific optimizations (if applicable)

    Provide:
    - Optimized query version
    - Explanation of changes
    - Performance impact estimation
    - Index recommendations
    """


@prompt_response
def data_modeling_prompt(
    table_description: str, use_case: str = "analytics", scale: str = "medium"
) -> str:
    """
    Generate a prompt for SingleStore data modeling guidance.

    Args:
        table_description: Description of the data to model
        use_case: The primary use case (analytics, transactional, hybrid)
        scale: Expected data scale (small, medium, large, enterprise)
    """
    return f"""
    Design an optimal SingleStore data model for the following requirements:

    **Data Description:** {table_description}
    **Use Case:** {use_case}
    **Scale:** {scale}

    Please provide:
    1. **Table Schema Design**
       - Column definitions with appropriate data types
       - Primary key strategy
       - Distribution key recommendations
       - Sort key optimization

    2. **SingleStore-Specific Optimizations**
       - Columnstore vs Rowstore recommendations
       - Partitioning strategy
       - Shard key selection
       - Reference table considerations

    3. **Performance Considerations**
       - Query pattern optimization
       - Index strategy
       - Memory usage optimization
       - Scaling recommendations

    4. **Best Practices**
       - Data ingestion patterns
       - ETL considerations
       - Monitoring and maintenance

    Ensure the design leverages SingleStore's distributed architecture and hybrid transactional/analytical capabilities.
    """


prompts_definitions = [
    {
        "title": "SQL Query Optimization Assistant",
        "func": sql_optimization_prompt,
    },
    {
        "title": "SingleStore Data Modeling Guide",
        "func": data_modeling_prompt,
    },
]

# Export the prompts using create_from_dict for consistency
prompts = [Prompt.create_from_dict(prompt) for prompt in prompts_definitions]
