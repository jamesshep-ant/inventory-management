---
name: Debugger Memory Index
description: Index of all debugger memory topics and key findings from this project.
---

# Debugger Memory Index

## Topic Files

- `known-bugs.md` — confirmed bugs found during dashboard investigation and other sessions
- `architecture.md` — key file paths, endpoints, and architecture notes useful for debugging

## Quick Reference

- Backend routes: see `architecture.md` for full list
- Missing components cause silent Vue warns — always check `components/` when seeing "Failed to resolve component"
- `/api/tasks` does NOT exist in main.py — frontend calls it on every page load from App.vue
