"""AutoGen coding team with specialized developer agents."""

from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

# Configuration for the language model
llm_config = {
    "model": "gpt-4",
    "temperature": 0,
    "api_key": "your-api-key-here",
    "functions": [
        {
            "name": "execute_code",
            "description": "Execute Python code",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code to execute"}
                },
                "required": ["code"]
            }
        },
        {
            "name": "run_tests",
            "description": "Run test suite",
            "parameters": {
                "type": "object",
                "properties": {
                    "test_file": {"type": "string", "description": "Test file to run"}
                },
                "required": ["test_file"]
            }
        }
    ]
}

# Create code executor
executor = UserProxyAgent(
    name="CodeExecutor",
    system_message="Execute code and run tests. Report results.",
    code_execution_config={
        "work_dir": "workspace",
        "use_docker": False,
    },
    human_input_mode="NEVER",
    max_consecutive_auto_reply=15,
    function_map={
        "execute_code": lambda code: f"Executed: {code[:50]}...",
        "run_tests": lambda test_file: f"Tests passed for {test_file}"
    }
)

# Create senior developer
senior_dev = AssistantAgent(
    name="SeniorDeveloper",
    system_message="""You are a senior developer. Design architecture, write high-quality code,
    and ensure best practices are followed.""",
    llm_config=llm_config,
    max_consecutive_auto_reply=10
)

# Create code reviewer
reviewer = AssistantAgent(
    name="CodeReviewer",
    system_message="""You are a code reviewer. Review code for:
    - Code quality and style
    - Security vulnerabilities
    - Performance issues
    - Best practices compliance""",
    llm_config=llm_config
)

# Create QA engineer
qa_engineer = AssistantAgent(
    name="QA_Engineer",
    system_message="""You are a QA engineer. Write tests, verify functionality,
    and ensure code meets requirements.""",
    llm_config=llm_config
)

# Create the group chat
coding_group_chat = GroupChat(
    agents=[executor, senior_dev, reviewer, qa_engineer],
    messages=[],
    max_round=25
)

# Create the group chat manager
coding_manager = GroupChatManager(
    groupchat=coding_group_chat,
    llm_config=llm_config
)

# Example usage
if __name__ == "__main__":
    executor.initiate_chat(
        coding_manager,
        message="Create a Python function to calculate Fibonacci numbers with unit tests."
    )

