"""Example LangChain agent for testing AgentBOM."""

from langchain.agents import initialize_agent, AgentType
from langchain.tools import tool
from langchain_openai import ChatOpenAI

@tool
def search_documentation(query: str) -> str:
    """Search the product documentation for relevant information."""
    # This would normally search actual documentation
    return f"Documentation results for: {query}"

@tool
def fetch_database_info(table_name: str) -> str:
    """Fetch information about a database table."""
    # This would normally query database metadata
    return f"Schema information for table: {table_name}"

@tool
def generate_sql_query(description: str) -> str:
    """Generate a SQL query based on natural language description."""
    # This would normally use an LLM to generate SQL
    return f"SELECT * FROM users WHERE {description}"

# Initialize the language model
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0
)

# Create the tools list
tools = [
    search_documentation,
    fetch_database_info,
    generate_sql_query
]

# Initialize the agent
sales_support_agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    agent_name="Sales Support Agent",
    verbose=True,
    handle_parsing_errors=True
)

# Example usage
if __name__ == "__main__":
    # Example query
    response = sales_support_agent.run(
        "Find documentation about user authentication and generate a SQL query to get all active users"
    )
    print(response)