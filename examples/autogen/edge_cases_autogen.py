"""Edge cases AutoGen system to test various detection patterns."""

from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

# Edge case 1: LLM config with functions
llm_config_with_functions = {
    "model": "gpt-4",
    "temperature": 0.5,
    "api_key": "your-api-key",
    "functions": [
        {
            "name": "calculate",
            "description": "Perform calculations",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
            },
        },
        {
            "name": "search_web",
            "description": "Search the web",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
            },
        },
    ],
}


# Edge case 2: Function map
def execute_calculation(expression: str) -> str:
    """Execute a calculation."""
    return f"Result: {eval(expression)}"


def search_web(query: str) -> str:
    """Search the web."""
    return f"Search results for: {query}"


function_map = {"calculate": execute_calculation, "search_web": search_web}

# Edge case 3: Code execution with Docker
code_executor_docker = UserProxyAgent(
    name="DockerExecutor",
    system_message="Execute code in Docker container",
    code_execution_config={
        "work_dir": "docker_workspace",
        "use_docker": True,
        "timeout": 120,
        "last_n_messages": 5,
    },
    human_input_mode="NEVER",
    max_consecutive_auto_reply=20,
    function_map=function_map,
)

# Edge case 4: Agent with custom system message
specialized_agent = AssistantAgent(
    name="SpecializedAgent",
    system_message="""You are a specialized agent with multiple capabilities:
    1. Code analysis and review
    2. Architecture design
    3. Performance optimization
    4. Security assessment
    
    Always provide detailed explanations and examples.""",
    llm_config=llm_config_with_functions,
    max_consecutive_auto_reply=8,
)

# Edge case 5: Agent with minimal config
minimal_agent = AssistantAgent(
    name="MinimalAgent", llm_config={"model": "gpt-3.5-turbo"}
)

# Edge case 6: Human proxy with termination
human_proxy = UserProxyAgent(
    name="HumanProxy",
    system_message="Human in the loop",
    human_input_mode="TERMINATE",
    max_consecutive_auto_reply=0,
    code_execution_config=False,
)

# Edge case 7: Agent without code execution
assistant_no_code = AssistantAgent(
    name="TheoreticalAssistant",
    system_message="I only provide theoretical advice, no code execution",
    llm_config={"model": "gpt-4", "temperature": 0.9},
)

# Edge case 8: UserProxy with code execution but no Docker
local_executor = UserProxyAgent(
    name="LocalExecutor",
    code_execution_config={
        "work_dir": "local_work",
        "use_docker": False,
    },
    human_input_mode="ALWAYS",
    max_consecutive_auto_reply=1,
)

# Edge case 9: Complex group chat with many agents
all_agents = [
    code_executor_docker,
    specialized_agent,
    minimal_agent,
    human_proxy,
    assistant_no_code,
    local_executor,
]

# Edge case 10: GroupChat with custom speaker selection
complex_group_chat = GroupChat(
    agents=all_agents,
    messages=[],
    max_round=30,
    speaker_selection_method="round_robin",
    allow_repeat_speaker=False,
)

# Create the manager
edge_case_manager = GroupChatManager(
    groupchat=complex_group_chat, llm_config=llm_config_with_functions
)

# Example usage
if __name__ == "__main__":
    code_executor_docker.initiate_chat(
        edge_case_manager,
        message="Analyze system performance and provide optimization recommendations",
    )
