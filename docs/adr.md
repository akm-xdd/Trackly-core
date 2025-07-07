# Architectural Decision Record

**Date:** 2025-07-05  

## 1. Server-Sent Events vs WebSockets for Real-time Updates

### Problem
Users need to see real-time notifications when issues are created, updated, or deleted without refreshing the page.

### Decision
Use **Server-Sent Events (SSE)** instead of WebSockets.

### Why SSE?
- ✅ **Simple implementation**: Built on standard HTTP responses
- ✅ **Perfect fit**: We only need server→client updates (not bidirectional)
- ✅ **Auto-reconnect**: Browser handles reconnection automatically
- ✅ **Easy debugging**: Visible in browser dev tools
- ✅ **No special setup**: Works with our existing FastAPI/SvelteKit stack

### Why not WebSockets?
- ❌ **Unnecessary complexity**: Don't need bidirectional communication
- ❌ **Extra work**: Would need custom connection management and reconnection logic
- ❌ **Overkill**: Our use case is simple notifications, not chat or gaming

### Authorization for SSE
- The JWT based auth for normal API requests is not compatible with SSE.
- Use the `token` query parameter for SSE connections
- This token is generated during user login and can be used to authenticate SSE connections separately when establishing the connection.

### Result
Real-time issue notifications work reliably with minimal code and complexity using SSE, fitting our needs perfectly.

---

## 2. Multi-repo vs Monorepo Architecture

### Problem
Project has separate frontend (SvelteKit) and backend (FastAPI) but the requirement was to use a single `docker-compose up` command to deploy the full stack. Should we use a monorepo or separate repositories?

### Decision
Use **separate repositories** for frontend and backend, with Docker Compose orchestration.

### Why Multi-repo?
- ✅ **Technology separation**: Python and Node.js have different tooling
- ✅ **Independent development**: Frontend and backend teams don't interfere
- ✅ **Focused testing**: Backend achieved 83% test coverage without frontend complexity
- ✅ **Clear ownership**: Each repo has focused responsibility
- ✅ **Commit history clarity**: Changes are easier to track in separate repos

### Why not Monorepo?
- ❌ **Mixed tooling**: Python linting + Node.js builds in same repo gets messy
- ❌ **Workflow conflicts**: Frontend changes trigger backend CI and vice versa
- ❌ **Complexity**: Single CI pipeline handling multiple technologies

### Implementation
```
trackly-server/     # This repo - FastAPI backend
trackly-frontend/   # Separate repo - SvelteKit app
```

**Deployment:** Docker Compose in `trackly-server` and `trackly-frontend` directories to orchestrate both services. Each service has its own Dockerfile and can be built independently.

### Trade-offs
- **Good**: Clean separation, focused development, optimal tooling per technology
- **Bad**: Must coordinate API changes across repositories due to incompatible health checks
- **Acceptable**: Single machine can run both services with individual `docker-compose up` commands

### Result
Clean architecture with independent development while meeting deployment requirements.

---

## 3. No Public Registration Endpoint

### Problem
Should users be able to self-register accounts, or should account creation be restricted to administrators?

### Decision
**No public registration endpoint** - only administrators can create user accounts.

### Why No Public Registration?
- ✅ **Controlled access**: Prevents random users from creating accounts and spam issues
- ✅ **Organization control**: Only intended team members can access the system
- ✅ **Role management**: Admins can assign appropriate roles (REPORTER, MAINTAINER, ADMIN) from the start
- ✅ **Security**: Reduces attack surface by eliminating open registration
- ✅ **Data quality**: Ensures only legitimate users create issues

### Why not Public Registration?
- ❌ **Spam potential**: Anyone could create accounts and flood the system with fake issues
- ❌ **Role confusion**: New users wouldn't know which role to select
- ❌ **Moderation overhead**: Would need systems to manage unwanted accounts

### Implementation
- **Signup endpoint exists** but requires ADMIN authentication
- **Default admin account** created during app initialization (`admin@trackly.com`)
- **Google OAuth** available but only for existing users (no auto-account creation)
- **User creation flow**: Admin logs in → Creates accounts → Shares credentials with team


### Trade-offs
- **Good**: Clean, controlled user base with appropriate roles
- **Bad**: Initial setup requires manual account creation by admin
- **Acceptable**: Fits organizational use case where user list is known

### Result
Secure, controlled access system where admins manage the user base appropriately.