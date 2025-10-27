"""CrewAI software development crew with multiple specialized agents."""

from crewai import Agent, Task, Crew
from crewai.tools import tool

@tool
def write_code(specification: str) -> str:
    """Write code based on specification."""
    return f"Code written for: {specification}"

@tool
def review_code(code_snippet: str) -> str:
    """Review code for quality and issues."""
    return f"Code review complete: Found 3 suggestions for improvement"

@tool
def write_tests(component: str) -> str:
    """Write unit tests for a component."""
    return f"Tests written for {component}: 15 test cases"

@tool
def design_architecture(requirements: str) -> str:
    """Design system architecture."""
    return f"Architecture designed for: {requirements}"

@tool
def create_documentation(component: str) -> str:
    """Create technical documentation."""
    return f"Documentation created for {component}"

# Create architect
architect = Agent(
    role="Software Architect",
    goal="Design scalable and maintainable system architecture",
    backstory="""You are a principal software architect with deep expertise in
    distributed systems, microservices, and cloud architecture.""",
    tools=[design_architecture],
    verbose=True,
    allow_delegation=True
)

# Create senior developer
senior_developer = Agent(
    role="Senior Developer",
    goal="Write high-quality, efficient code",
    backstory="""You are a senior software engineer with 10+ years of experience.
    You write clean, efficient, and well-tested code.""",
    tools=[write_code, write_tests],
    verbose=True,
    allow_delegation=False
)

# Create code reviewer
code_reviewer = Agent(
    role="Code Reviewer",
    goal="Ensure code quality and best practices",
    backstory="""You are a meticulous code reviewer who catches bugs and ensures
    code follows best practices and standards.""",
    tools=[review_code],
    verbose=True,
    allow_delegation=False
)

# Create tech writer
tech_writer = Agent(
    role="Technical Writer",
    goal="Create clear and comprehensive documentation",
    backstory="""You are a technical writer who creates documentation that
    developers actually want to read.""",
    tools=[create_documentation],
    verbose=True,
    allow_delegation=False
)

# Create tasks
architecture_task = Task(
    description="""Design the architecture for a real-time chat application with
    support for 1 million concurrent users""",
    agent=architect,
    expected_output="Detailed architecture document with diagrams"
)

development_task = Task(
    description="""Implement the message queue system and WebSocket handler
    based on the architecture""",
    agent=senior_developer,
    expected_output="Working code with unit tests",
    tools=[write_code, write_tests]
)

review_task = Task(
    description="Review the implemented code and provide feedback",
    agent=code_reviewer,
    expected_output="Code review report with recommendations"
)

documentation_task = Task(
    description="Create API documentation and deployment guide",
    agent=tech_writer,
    expected_output="Complete technical documentation"
)

# Create the development crew
development_crew = Crew(
    agents=[architect, senior_developer, code_reviewer, tech_writer],
    tasks=[architecture_task, development_task, review_task, documentation_task],
    verbose=True,
    process="sequential"
)

# Execute the crew
if __name__ == "__main__":
    result = development_crew.kickoff()
    print(result)

