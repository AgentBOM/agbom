"""Basic CrewAI crew with simple agents and tasks."""

from crewai import Agent, Task, Crew
from crewai.tools import tool

@tool
def search_internet(query: str) -> str:
    """Search the internet for information."""
    return f"Search results for: {query}"

@tool
def analyze_data(data: str) -> str:
    """Analyze the provided data."""
    return f"Analysis complete: Key findings from {data}"

# Create agents
researcher = Agent(
    role="Researcher",
    goal="Find and gather relevant information",
    backstory="You are an experienced researcher skilled at finding accurate information.",
    tools=[search_internet],
    verbose=True
)

analyst = Agent(
    role="Data Analyst",
    goal="Analyze information and extract insights",
    backstory="You are a data analyst with expertise in interpreting complex information.",
    tools=[analyze_data],
    verbose=True
)

# Create tasks
research_task = Task(
    description="Research the latest trends in artificial intelligence",
    agent=researcher,
    expected_output="A comprehensive report on AI trends"
)

analysis_task = Task(
    description="Analyze the research findings and identify key insights",
    agent=analyst,
    expected_output="An analysis report with actionable insights"
)

# Create the crew
basic_crew = Crew(
    agents=[researcher, analyst],
    tasks=[research_task, analysis_task],
    verbose=True
)

# Execute the crew
if __name__ == "__main__":
    result = basic_crew.kickoff()
    print(result)

