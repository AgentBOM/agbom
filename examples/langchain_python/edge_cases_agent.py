"""Edge cases LangChain agent to test various detection patterns."""

from langchain.agents import initialize_agent, AgentType
from langchain.tools import tool, Tool, StructuredTool
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field
from typing import Optional

# Edge case 1: Lambda tool
lambda_tool = Tool(
    name="lambda_calculator",
    description="Calculate using a lambda function",
    func=lambda x: f"Result: {x}",
)


# Edge case 2: Tool with Pydantic schema
class EmailInput(BaseModel):
    """Input schema for sending emails."""

    to: str = Field(description="Recipient email address")
    subject: str = Field(description="Email subject line")
    body: str = Field(description="Email body content")
    cc: Optional[str] = Field(None, description="CC recipients")


def send_email_func(to: str, subject: str, body: str, cc: Optional[str] = None) -> str:
    """Send an email."""
    return f"Email sent to {to}"


email_tool = StructuredTool(
    name="send_email",
    description="Send an email to a recipient with optional CC",
    func=send_email_func,
    args_schema=EmailInput,
)


# Edge case 3: Tool decorator with complex parameters
@tool
def process_json_data(json_string: str, operation: str = "parse") -> str:
    """
    Process JSON data with various operations.

    Args:
        json_string: The JSON string to process
        operation: The operation to perform (parse, validate, transform)

    Returns:
        Processed result as string
    """
    return f"Processed JSON with {operation} operation"


# Edge case 4: Tool with no description
@tool
def mysterious_function(input_data: str) -> str:
    return f"Mystery result: {input_data}"


# Edge case 5: Multiple LLM providers
llm_openai = ChatOpenAI(model="gpt-4", temperature=0)
llm_anthropic = ChatAnthropic(model="claude-3-opus-20240229")

# Create tools list with various types
tools = [lambda_tool, email_tool, process_json_data, mysterious_function]

# Initialize agent with edge cases
edge_case_agent = initialize_agent(
    tools=tools,
    llm=llm_openai,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    agent_name="Edge Case Test Agent",
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=15,
    early_stopping_method="generate",
)

# Example usage
if __name__ == "__main__":
    response = edge_case_agent.run("Send an email and process some JSON data")
    print(response)
