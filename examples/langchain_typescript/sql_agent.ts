/**
 * LangChain TypeScript SQL agent for database queries
 */

import { AgentExecutor } from "langchain/agents";
import { ChatOpenAI } from "@langchain/openai";
import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { SqlDatabase } from "langchain/sql_db";

// Define SQL tools
const queryDatabase = tool({
  name: "query_database",
  description: "Execute a SQL query on the database",
  schema: z.object({
    query: z.string().describe("SQL query to execute"),
  }),
  func: async ({ query }) => {
    // Mock implementation
    return `Query results: [{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]`;
  },
});

const getTableSchema = tool({
  name: "get_table_schema",
  description: "Get the schema of a database table",
  schema: z.object({
    tableName: z.string().describe("Name of the table"),
  }),
  func: async ({ tableName }) => {
    // Mock implementation
    return `Schema for ${tableName}: id (INT), name (VARCHAR), email (VARCHAR)`;
  },
});

const listTables = tool({
  name: "list_tables",
  description: "List all tables in the database",
  schema: z.object({}),
  func: async () => {
    // Mock implementation
    return "Available tables: users, orders, products, customers";
  },
});

const generateSql = tool({
  name: "generate_sql",
  description: "Generate SQL query from natural language description",
  schema: z.object({
    description: z.string().describe("Natural language description of the query"),
  }),
  func: async ({ description }) => {
    // Mock implementation
    return `SELECT * FROM users WHERE ${description}`;
  },
});

// Initialize the language model
const llm = new ChatOpenAI({
  modelName: "gpt-4",
  temperature: 0,
});

// Create the tools array
const tools = [queryDatabase, getTableSchema, listTables, generateSql];

// Create the SQL agent executor
const sqlAgent = new AgentExecutor({
  tools: tools,
  agent: llm,
  verbose: true,
  maxIterations: 10,
});

// Example usage
async function main() {
  const result = await sqlAgent.invoke({
    input: "Find all active users who placed orders in the last 30 days"
  });
  console.log(result);
}

if (require.main === module) {
  main();
}

export { sqlAgent };

