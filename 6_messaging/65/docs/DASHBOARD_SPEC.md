# Dashboard Specification

## Pages
- Overview (stats + recent events)
- Chats (monitoring + config toggles)
- Users (searchable index)
- Events (filterable history)
- Config (toggle controls)

## API Endpoints
GET /api/events
GET /api/recent
GET /api/users
GET /api/chats
POST /api/config/update

## Live Updates
Simple polling every 2 seconds or SSE stream.
