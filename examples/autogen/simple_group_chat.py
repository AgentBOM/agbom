"""Simple AutoGen multi-agent system with group chat."""

from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

# Configuration for the language model
llm_config = {
    "model": "gpt-4",
    "temperature": 0,
    "api_key": "your-api-key-here",
}

# Create the code executor agent
code_executor = UserProxyAgent(
    name="CodeExecutor",
    system_message="You are a code executor. Execute code and provide results.",
    code_execution_config={
        "work_dir": "coding",
        "use_docker": False,
    },
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
)

# Create the analyst agent
analyst = AssistantAgent(
    name="DataAnalyst",
    system_message="You are a data analyst. Analyze data and provide insights.",
    llm_config=llm_config,
)

# Create the planner agent
planner = AssistantAgent(
    name="Planner",
    system_message="You are a planner. Create plans and coordinate tasks.",
    llm_config=llm_config,
)

# Create the group chat
group_chat = GroupChat(
    agents=[code_executor, analyst, planner], messages=[], max_round=12
)

# Create the group chat manager
manager = GroupChatManager(groupchat=group_chat, llm_config=llm_config)

# Example usage
if __name__ == "__main__":
    code_executor.initiate_chat(
        manager,
        message="Analyze the sales data for the last quarter and create a report.",
    )
