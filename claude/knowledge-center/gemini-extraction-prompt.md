# Gemini YouTube Extraction Prompt

Use this prompt with the **Gemini icon** on any YouTube video to extract structured knowledge.

## How to Use

1. Open the YouTube video
2. Click the **Gemini icon**
3. Paste the prompt below
4. Copy the response and send it to Claude to save in the knowledge center

## Prompt

```
Analyze this video and provide the following in markdown format:

# [Video Title]
**Channel:** [channel name]
**URL:** [video URL]
**Date:** [publish date]

## Summary
A 2-3 sentence overview of what this video covers.

## Key Concepts
- Bullet list of main ideas, techniques, or features demonstrated

## Code Snippets / Prompts
Any code examples, prompts, or configurations shown in the video.
Use code blocks with language tags.

## Step-by-Step Instructions
If the video demonstrates a workflow or tutorial, list the steps.

## Tips & Best Practices
Any tips, warnings, or best practices mentioned.

## Tags
Comma-separated tags for categorization (e.g., claude-code, MCP, prompt-engineering, API)
```
