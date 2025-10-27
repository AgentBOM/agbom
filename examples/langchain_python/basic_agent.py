"""Basic LangChain agent with simple tools."""

from langchain.agents import initialize_agent, AgentType
from langchain.tools import tool
from langchain_openai import ChatOpenAI


@tool
def get_current_weather(location: str) -> str:
    """Get the current weather for a given location."""
    # Mock implementation
    return f"The weather in {location} is sunny, 72°F"


@tool
def calculate_distance(origin: str, destination: str) -> str:
    """Calculate the distance between two locations."""
    # Mock implementation
    return f"Distance from {origin} to {destination}: 150 miles"


@tool
def get_time(timezone: str) -> str:
    """Get the current time in a specific timezone."""
    # Mock implementation
    return f"Current time in {timezone}: 10:30 AM"


# Initialize the language model
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

# Create the tools list
tools = [get_current_weather, calculate_distance, get_time]

# Initialize the agent
basic_agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    agent_name="Basic Travel Assistant",
    verbose=True,
)

# Example usage
if __name__ == "__main__":
    response = basic_agent.run(
        "What's the weather in San Francisco and how far is it from Los Angeles?"
    )
    print(response)
