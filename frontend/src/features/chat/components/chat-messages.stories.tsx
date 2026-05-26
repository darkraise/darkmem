import type { Meta, StoryObj } from "@storybook/react"
import { ChatMessages } from "./chat-messages"
import type { ChatMessage } from "@/hooks/api"

const meta: Meta<typeof ChatMessages> = {
  title: "Chat/ChatMessages",
  component: ChatMessages,
  parameters: { layout: "fullscreen" },
  decorators: [
    (Story) => (
      <div className="bg-background flex h-[500px] flex-col">
        <Story />
      </div>
    ),
  ],
}
export default meta

type S = StoryObj<typeof ChatMessages>

const userMsg: ChatMessage = {
  id: "u1",
  role: "user",
  content: "How does FastAPI handle authentication?",
  context: null,
  created_at: new Date().toISOString(),
}

const assistantMsg: ChatMessage = {
  id: "a1",
  role: "assistant",
  content:
    "FastAPI handles authentication via dependency injection. You define a dependency that reads from the `Authorization` header and validates the token. [1] Common approaches include OAuth2 with Bearer tokens and API keys.",
  context: {
    memories: [
      {
        id: "m1",
        score: 0.92,
        content:
          "FastAPI uses dependency injection for auth middleware via Depends()",
        source: "claude-code",
        tags: ["python", "fastapi"],
        created_at: new Date().toISOString(),
      },
    ],
    entities: [
      { id: "e1", name: "FastAPI", entity_type: "tool" },
      { id: "e2", name: "OAuth2", entity_type: "concept" },
    ],
  },
  created_at: new Date().toISOString(),
}

export const Empty: S = {
  args: {
    messages: [],
    isStreaming: false,
  },
}

export const WithMessages: S = {
  args: {
    messages: [userMsg, assistantMsg],
    isStreaming: false,
  },
}

export const Streaming: S = {
  args: {
    messages: [userMsg],
    isStreaming: true,
    pendingUserMessage: "Can you show me an example?",
    streamingContent:
      "Sure! Here's how you'd write a basic auth dependency in FastAPI:\n\n```python\nfrom fastapi import Depends, HTTPException\n```",
    streamingSources: {
      memories: [
        {
          id: "m2",
          index: 1,
          score: 0.88,
          content: "FastAPI auth example with OAuth2PasswordBearer",
          source: "api",
        },
      ],
      entities: [{ id: "e1", name: "FastAPI", entity_type: "tool" }],
    },
  },
}

export const StreamingThinking: S = {
  args: {
    messages: [userMsg],
    isStreaming: true,
    pendingUserMessage: "Explain JWT validation",
    streamingContent: "",
    streamingSources: null,
  },
}

export const ErrorState: S = {
  args: {
    messages: [
      userMsg,
      {
        id: "a-err",
        role: "assistant",
        content:
          "I'm sorry, I encountered an error processing your request. Please try again.",
        context: null,
        created_at: new Date().toISOString(),
      },
    ],
    isStreaming: false,
  },
}
