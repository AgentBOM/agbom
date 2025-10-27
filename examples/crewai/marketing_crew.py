"""CrewAI marketing team with specialized agents."""

from crewai import Agent, Task, Crew
from crewai.tools import tool

@tool
def analyze_market(market_segment: str) -> str:
    """Analyze a specific market segment."""
    return f"Market analysis for {market_segment}: Size, trends, and opportunities"

@tool
def generate_content(topic: str, format: str) -> str:
    """Generate marketing content."""
    return f"Generated {format} content about {topic}"

@tool
def analyze_competitors(company: str) -> str:
    """Analyze competitors."""
    return f"Competitor analysis for {company}: Strengths, weaknesses, and positioning"

@tool
def create_campaign(campaign_details: str) -> str:
    """Create a marketing campaign."""
    return f"Campaign created: {campaign_details}"

# Create marketing strategist
strategist = Agent(
    role="Marketing Strategist",
    goal="Develop effective marketing strategies",
    backstory="""You are a senior marketing strategist with 15 years of experience.
    You excel at identifying market opportunities and creating winning strategies.""",
    tools=[analyze_market, analyze_competitors],
    verbose=True,
    allow_delegation=True
)

# Create content creator
content_creator = Agent(
    role="Content Creator",
    goal="Create engaging marketing content",
    backstory="""You are a creative content writer who knows how to craft compelling
    messages that resonate with target audiences.""",
    tools=[generate_content],
    verbose=True,
    allow_delegation=False
)

# Create campaign manager
campaign_manager = Agent(
    role="Campaign Manager",
    goal="Execute and manage marketing campaigns",
    backstory="""You are an experienced campaign manager who ensures campaigns are
    executed flawlessly and deliver results.""",
    tools=[create_campaign],
    verbose=True,
    allow_delegation=True,
    max_iter=10
)

# Create tasks
strategy_task = Task(
    description="Analyze the market for electric vehicles and develop a marketing strategy",
    agent=strategist,
    expected_output="A comprehensive marketing strategy document"
)

content_task = Task(
    description="Create blog posts and social media content for the EV marketing campaign",
    agent=content_creator,
    expected_output="A content calendar with 10 pieces of content"
)

campaign_task = Task(
    description="Launch and manage the EV marketing campaign across all channels",
    agent=campaign_manager,
    expected_output="Campaign execution plan and timeline"
)

# Create the marketing crew
marketing_crew = Crew(
    agents=[strategist, content_creator, campaign_manager],
    tasks=[strategy_task, content_task, campaign_task],
    verbose=True,
    process="sequential"
)

# Execute the crew
if __name__ == "__main__":
    result = marketing_crew.kickoff()
    print(result)

