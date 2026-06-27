# Demo Script — Finals Week Simulation

## Setup
1. Seed the backend with `data/demo_scenarios.csv`
2. Start backend (`uvicorn app.main:app --reload`) and both frontend apps
3. Open professor dashboard on one screen, student kiosk on another

## Script
1. Submit 3-5 simulated student requests via the kiosk (mix of anonymous/identified, mix of categories)
2. Show requests appearing + being clustered in real time on the dashboard
3. Show recommendation cards generated per cluster
4. Professor approves one action (e.g., schedules a group review session)
5. Wrap up: show before/after comparison (number of individual messages vs. clustered actions)

## Talking Points
- Emphasize student anonymity option
- Emphasize professor remains in control (no auto-actions)
- Emphasize reduction in repeated 1:1 handling during peak load
