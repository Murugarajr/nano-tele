# Heartbeat Tasks

This file is checked every 30 minutes by your nanobot agent.
Add tasks below that you want the agent to work on periodically.

If this file has no tasks (only headers and comments), the agent will skip the heartbeat.

## Active Tasks

<!-- Add your periodic tasks below this line -->

- Morning SOTD reminder: if the owner asks for it, create a cron job that runs `python tools/perfume_tool.py recommend --occasion today` and sends the output to Telegram.
- Weather-change check: for active travel mode or Sheffield, compare morning and evening conditions before proactive recommendations so picks account for humidity, rain risk, and daily high.


## Completed

<!-- Move completed tasks here or delete them -->
