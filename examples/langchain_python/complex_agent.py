"""Complex LangChain agent with multiple tools and advanced configuration."""

from langchain.agents import initialize_agent, AgentType
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory


@tool
def web_search(query: str) -> str:
    """Search the web for information."""
    return f"Web search results for: {query}"


@tool
def send_email(recipient: str, subject: str, body: str) -> str:
    """Send an email to a recipient."""
    return f"Email sent to {recipient} with subject: {subject}"


@tool
def create_calendar_event(title: str, date: str, time: str) -> str:
    """Create a calendar event."""
    return f"Calendar event created: {title} on {date} at {time}"


@tool
def analyze_sentiment(text: str) -> str:
    """Analyze the sentiment of a given text."""
    return "Sentiment analysis: The text appears to be positive"


@tool
def summarize_text(text: str, max_words: int = 100) -> str:
    """Summarize a long text into a shorter version."""
    return f"Summary (max {max_words} words): Key points extracted"


@tool
def translate_text(text: str, target_language: str) -> str:
    """Translate text to a target language."""
    return f"Translation to {target_language}: [translated text]"


@tool
def extract_entities(text: str) -> str:
    """Extract named entities from text."""
    return "Entities found: Person: John Doe, Organization: Acme Corp"


# Initialize the language model with custom settings
llm = ChatOpenAI(model="gpt-4", temperature=0.3, max_tokens=2000)

# Initialize memory for conversation history
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# Create the tools list
tools = [
    web_search,
    send_email,
    create_calendar_event,
    analyze_sentiment,
    summarize_text,
    translate_text,
    extract_entities,
]

# Initialize the complex agent
complex_agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    agent_name="Executive Assistant Agent",
    verbose=True,
    memory=memory,
    handle_parsing_errors=True,
    max_iterations=10,
)

# Example usage
if __name__ == "__main__":
    response = complex_agent.run(
        "Search for information about AI trends, summarize the findings, and schedule a meeting"
    )
    print(response)
