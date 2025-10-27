"""LangChain SQL agent for database queries."""

from langchain.agents import initialize_agent, AgentType
from langchain.tools import tool
from langchain_openai import ChatOpenAI


@tool
def query_database(query: str) -> str:
    """Execute a SQL query on the database."""
    # Mock implementation
    return "Query results: [{'id': 1, 'name': 'John'}, {'id': 2, 'name': 'Jane'}]"


@tool
def get_table_schema(table_name: str) -> str:
    """Get the schema of a database table."""
    # Mock implementation
    return f"Schema for {table_name}: id (INT), name (VARCHAR), email (VARCHAR)"


@tool
def list_tables() -> str:
    """List all tables in the database."""
    # Mock implementation
    return "Available tables: users, orders, products, customers"


@tool
def generate_sql(description: str) -> str:
    """Generate SQL query from natural language description."""
    # Mock implementation
    return f"SELECT * FROM users WHERE {description}"


# Initialize the language model
llm = ChatOpenAI(model="gpt-4", temperature=0)

# Create the tools list
tools = [query_database, get_table_schema, list_tables, generate_sql]

# Initialize the SQL agent
sql_agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    agent_name="SQL Database Agent",
    verbose=True,
    max_iterations=5,
)

# Example usage
if __name__ == "__main__":
    response = sql_agent.run(
        "Find all active users who placed orders in the last 30 days"
    )
    print(response)
