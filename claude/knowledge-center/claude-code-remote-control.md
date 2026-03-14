# I Tried Claude Code Remote Control So You Don't Have To

**Channel:** Mark Kashef
**URL:** https://www.youtube.com/watch?v=kY31Wn6Jj7k
**Date:** December 13, 2024

## Summary

This video walks through the setup and usage of the new Remote Control feature in Claude Code, which allows developers to manage terminal sessions from mobile devices or browsers. The host explains how this feature acts as a secure mirror for monitoring long-running tasks and demonstrates how to MacGyver it into a personalized AI assistant using specific file configurations.

## Key Concepts

- **Remote Control Setup:** Executing terminal sessions remotely via `claude /remote control` (1:57)
- **Task Monitoring:** Using mobile devices to check on long-running agent tasks (3:10)
- **Security:** Remote control operates via outbound HTTPS requests without exporting credentials (3:51)
- **Pseudo Personal Assistant:** Creating a customized experience using soul files, memory, and skills (7:48)
- **Context Limitation:** Remote Control is currently scoped to one project/terminal at a time (5:50)

## Code Snippets / Prompts

### Updating Claude Code

```bash
claude update
```

### Activating Remote Control

```bash
claude /remote control
```

### Creating a Personal Assistant (Soul File)

```markdown
<!-- soul.md -->
I want you to be a warm and fuzzy experience in our back and forths.
I don't want you to be very corporate.
I want to talk to you about anything from my business to what's bothering me.
```

## Step-by-Step Instructions

1. **Update Claude Code:** Ensure you are on the latest version by running `claude update` or using an agent mode in your terminal (1:04)
2. **Initialize Remote Control:** Type `claude /remote control` in your terminal to generate a QR code or connection link (1:57)
3. **Connect Mobile/Browser:** Scan the QR code or click the link on your phone to open the mirrored session (2:43)
4. **Create Assistant Files:** Within your project folder, create `soul.md` for personality, a memory file for personal preferences, and a `claude.md` to define instructions (8:05)
5. **Import Skills:** Use Claude Code to import necessary skills, such as PowerPoint or CSV manipulation, into the current context (9:00)

## Tips & Best Practices

- **Monitor Permissions:** If using accept edits mode, use remote control to approve plans for long tasks so they don't pause for hours (3:31)
- **Session Management:** The remote session closes automatically when you shut down the primary Claude instance on your desktop (3:01)
- **Buggy QR Scanning:** If the scan doesn't take you directly to the active session, refresh your browser or chat on the mobile app to confirm it is active (2:43)

## Tags

claude-code, remote-control, anthropic, ai-assistant, terminal, productivity, developer-tools
