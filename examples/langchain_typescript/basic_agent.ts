/**
 * Basic LangChain TypeScript agent with simple tools
 */

import { AgentExecutor } from "langchain/agents";
import { ChatOpenAI } from "@langchain/openai";
import { tool } from "@langchain/core/tools";
import { z } from "zod";

// Define tools
const getCurrentWeather = tool({
  name: "get_current_weather",
  description: "Get the current weather for a given location",
  schema: z.object({
    location: z.string().describe("The location to get weather for"),
  }),
  func: async ({ location }) => {
    // Mock implementation
    return `The weather in ${location} is sunny, 72°F`;
  },
});

const calculateDistance = tool({
  name: "calculate_distance",
  description: "Calculate the distance between two locations",
  schema: z.object({
    origin: z.string().describe("Starting location"),
    destination: z.string().describe("Destination location"),
  }),
  func: async ({ origin, destination }) => {
    // Mock implementation
    return `Distance from ${origin} to ${destination}: 150 miles`;
  },
});

const getTime = tool({
  name: "get_time",
  description: "Get the current time in a specific timezone",
  schema: z.object({
    timezone: z.string().describe("The timezone to get time for"),
  }),
  func: async ({ timezone }) => {
    // Mock implementation
    return `Current time in ${timezone}: 10:30 AM`;
  },
});

// Initialize the language model
const llm = new ChatOpenAI({
  modelName: "gpt-3.5-turbo",
  temperature: 0,
});

// Create the tools array
const tools = [getCurrentWeather, calculateDistance, getTime];

// Create the agent executor
const basicAgent = new AgentExecutor({
  tools: tools,
  agent: llm,
  verbose: true,
  maxIterations: 5,
});

// Example usage
async function main() {
  const result = await basicAgent.invoke({
    input: "What's the weather in San Francisco and how far is it from Los Angeles?"
  });
  console.log(result);
}

if (require.main === module) {
  main();
}

export { basicAgent };

