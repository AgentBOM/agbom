"""AutoGen research team with specialized agents."""

from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

# Configuration for the language model
llm_config = {
    "model": "gpt-4-turbo",
    "temperature": 0.7,
    "api_key": "your-api-key-here",
}

# Create user proxy for human interaction
user_proxy = UserProxyAgent(
    name="UserProxy",
    system_message="A human user providing input and feedback.",
    code_execution_config={
        "last_n_messages": 3,
        "work_dir": "research",
        "use_docker": False,
    },
    human_input_mode="TERMINATE",
    max_consecutive_auto_reply=5
)

# Create researcher agent
researcher = AssistantAgent(
    name="Researcher",
    system_message="""You are a research specialist. Your role is to:
    - Find relevant information and sources
    - Conduct thorough research on topics
    - Cite sources and verify facts
    - Provide comprehensive research summaries""",
    llm_config=llm_config
)

# Create writer agent
writer = AssistantAgent(
    name="Writer",
    system_message="""You are a professional writer. Your role is to:
    - Write clear and engaging content
    - Structure information logically
    - Adapt tone for the target audience
    - Create polished final drafts""",
    llm_config=llm_config
)

# Create critic agent
critic = AssistantAgent(
    name="Critic",
    system_message="""You are a critical reviewer. Your role is to:
    - Review content for accuracy and quality
    - Identify gaps or weaknesses
    - Suggest improvements
    - Ensure consistency and clarity""",
    llm_config=llm_config
)

# Create editor agent
editor = AssistantAgent(
    name="Editor",
    system_message="""You are an editor. Your role is to:
    - Finalize content structure
    - Ensure proper formatting
    - Make final revisions
    - Approve the final output""",
    llm_config=llm_config
)

# Create the group chat
research_group_chat = GroupChat(
    agents=[user_proxy, researcher, writer, critic, editor],
    messages=[],
    max_round=20,
    speaker_selection_method="auto"
)

# Create the group chat manager
research_manager = GroupChatManager(
    groupchat=research_group_chat,
    llm_config=llm_config
)

# Example usage
if __name__ == "__main__":
    user_proxy.initiate_chat(
        research_manager,
        message="Create a comprehensive article about the impact of AI on healthcare."
    )

