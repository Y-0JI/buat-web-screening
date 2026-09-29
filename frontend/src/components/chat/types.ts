export interface UITool {
  name: string;
  ok?: boolean;
  running?: boolean;
}

export interface UIMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  reasoning?: string;
  tools?: UITool[];
  streaming?: boolean;
}
