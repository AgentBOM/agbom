"""Edge cases CrewAI crew to test various detection patterns."""

from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from typing import List

# Edge case 1: Tool with no parameters
@tool
def get_random_fact() -> str:
    """Get a random interesting fact."""
    return "Random fact: The sky is blue"

# Edge case 2: Tool with optional parameters
@tool
def format_text(text: str, style: str = "markdown", uppercase: bool = False) -> str:
    """Format text with various styles and options."""
    return f"Formatted text in {style}: {text.upper() if uppercase else text}"

# Edge case 3: Tool with complex return type
@tool
def get_statistics(dataset: str) -> str:
    """Calculate statistics for a dataset."""
    return "Statistics: mean=10, median=8, std=2.5"

# Edge case 4: Agent with minimal configuration
minimal_agent = Agent(
    role="Minimalist",
    goal="Do the minimum required",
    backstory="You do only what is asked."
)

# Edge case 5: Agent with all options
maximal_agent = Agent(
    role="Maximalist",
    goal="Explore all possibilities",
    backstory="You are thorough and detail-oriented, exploring every option.",
    tools=[get_random_fact, format_text, get_statistics],
    verbose=True,
    allow_delegation=True,
    max_iter=20,
    memory=True,
    cache=True
)

# Edge case 6: Agent with inline tools
researcher_with_tools = Agent(
    role="Researcher",
    goal="Research thoroughly",
    backstory="Expert researcher",
    tools=[get_random_fact, format_text],
    verbose=False
)

# Edge case 7: Task with tools override
task_with_tools = Task(
    description="Research and format findings",
    agent=minimal_agent,
    expected_output="Formatted research report",
    tools=[get_random_fact, format_text, get_statistics]
)

# Edge case 8: Task without assigned agent
unassigned_task = Task(
    description="Do something without assignment",
    expected_output="Some output"
)

# Edge case 9: Sequential process
task1 = Task(
    description="Step 1: Gather facts",
    agent=researcher_with_tools,
    expected_output="List of facts"
)

task2 = Task(
    description="Step 2: Format facts",
    agent=maximal_agent,
    expected_output="Formatted facts"
)

task3 = Task(
    description="Step 3: Finalize",
    agent=minimal_agent,
    expected_output="Final report"
)

# Create crew with various configurations
edge_case_crew = Crew(
    agents=[minimal_agent, maximal_agent, researcher_with_tools],
    tasks=[task_with_tools, task1, task2, task3],
    process=Process.sequential,
    verbose=True,
    memory=True,
    cache=True,
    max_rpm=10
)

# Example usage
if __name__ == "__main__":
    result = edge_case_crew.kickoff()
    print(result)

