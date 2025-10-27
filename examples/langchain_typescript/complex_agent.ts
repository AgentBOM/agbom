/**
 * Complex LangChain TypeScript agent with multiple tools
 */

import { AgentExecutor } from "langchain/agents";
import { ChatOpenAI } from "@langchain/openai";
import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { BufferMemory } from "langchain/memory";

// Define comprehensive tool set
const webSearch = tool({
  name: "web_search",
  description: "Search the web for information",
  schema: z.object({
    query: z.string().describe("Search query"),
  }),
  func: async ({ query }) => {
    return `Web search results for: ${query}`;
  },
});

const sendEmail = tool({
  name: "send_email",
  description: "Send an email to a recipient",
  schema: z.object({
    recipient: z.string().describe("Email recipient"),
    subject: z.string().describe("Email subject"),
    body: z.string().describe("Email body"),
  }),
  func: async ({ recipient, subject, body }) => {
    return `Email sent to ${recipient} with subject: ${subject}`;
  },
});

const createCalendarEvent = tool({
  name: "create_calendar_event",
  description: "Create a calendar event",
  schema: z.object({
    title: z.string().describe("Event title"),
    date: z.string().describe("Event date"),
    time: z.string().describe("Event time"),
  }),
  func: async ({ title, date, time }) => {
    return `Calendar event created: ${title} on ${date} at ${time}`;
  },
});

const analyzeSentiment = tool({
  name: "analyze_sentiment",
  description: "Analyze the sentiment of a given text",
  schema: z.object({
    text: z.string().describe("Text to analyze"),
  }),
  func: async ({ text }) => {
    return "Sentiment analysis: The text appears to be positive";
  },
});

const summarizeText = tool({
  name: "summarize_text",
  description: "Summarize a long text into a shorter version",
  schema: z.object({
    text: z.string().describe("Text to summarize"),
    maxWords: z.number().optional().describe("Maximum words in summary"),
  }),
  func: async ({ text, maxWords = 100 }) => {
    return `Summary (max ${maxWords} words): Key points extracted`;
  },
});

const translateText = tool({
  name: "translate_text",
  description: "Translate text to a target language",
  schema: z.object({
    text: z.string().describe("Text to translate"),
    targetLanguage: z.string().describe("Target language"),
  }),
  func: async ({ text, targetLanguage }) => {
    return `Translation to ${targetLanguage}: [translated text]`;
  },
});

const extractEntities = tool({
  name: "extract_entities",
  description: "Extract named entities from text",
  schema: z.object({
    text: z.string().describe("Text to extract entities from"),
  }),
  func: async ({ text }) => {
    return "Entities found: Person: John Doe, Organization: Acme Corp";
  },
});

// Initialize the language model with custom settings
const llm = new ChatOpenAI({
  modelName: "gpt-4",
  temperature: 0.3,
  maxTokens: 2000,
});

// Initialize memory
const memory = new BufferMemory({
  memoryKey: "chat_history",
  returnMessages: true,
});

// Create the tools array
const tools = [
  webSearch,
  sendEmail,
  createCalendarEvent,
  analyzeSentiment,
  summarizeText,
  translateText,
  extractEntities,
];

// Create the complex agent executor
const complexAgent = new AgentExecutor({
  tools: tools,
  agent: llm,
  verbose: true,
  memory: memory,
  maxIterations: 15,
});

// Example usage
async function main() {
  const result = await complexAgent.invoke({
    input: "Search for information about AI trends, summarize the findings, and schedule a meeting"
  });
  console.log(result);
}

if (require.main === module) {
  main();
}

export { complexAgent };

