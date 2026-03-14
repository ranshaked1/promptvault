# I Tried Claude Code Remote Control So You Don't Have To

**Channel:** Mark Kashef
**URL:** https://www.youtube.com/watch?v=kY31Wn6Jj7k
**Date:** December 13, 2024

## Summary

Claude Code's Remote Control feature lets you mirror your desktop terminal session to a mobile device or browser. It's not a standalone remote IDE — it's a secure view into an active Claude Code session, useful for monitoring long-running tasks on the go. The video also shows a creative use case: combining Remote Control with soul files, memory, and skills to turn Claude into a pseudo personal assistant you can chat with from your phone.

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

## Action Items

- [ ] Run `claude update` and try `claude /remote control` to test the feature
- [ ] Create a `soul.md` file in a project folder to define Claude's personality for personal assistant use
- [ ] Create a memory file with personal preferences (communication style, interests, context)
- [ ] Set up a `claude.md` with instructions pointing to the soul and memory files
- [ ] Try importing skills (e.g., PowerPoint, CSV) into a remote session for on-the-go productivity
- [ ] Test the mobile workflow: start a long-running task on desktop, monitor/approve from phone

## Related Concepts

- **Soul files** — personality configuration for Claude, worth exploring for other projects
- **Skills** — reusable capabilities that can be imported into Claude Code sessions
- **Accept edits mode** — a permission mode where Claude proposes changes and you approve, pairs well with remote monitoring

## Tags

claude-code, remote-control, anthropic, ai-assistant, terminal, productivity, developer-tools, soul-files, skills
