# 🗺️ FlibustaUserAssistBot - Development Plan

## 📦 Git Strategy and Versioning

### Branching Strategy
- `main` — Stable production code (PR required)
- `develop` — Main development branch
- `feature/*` — New functionality development
- `fix/*` — Bug fixes and patches
- `release/*` — Release preparation
- `hotfix/*` — Critical production fixes

### Semantic Versioning (SemVer)
- **v0.x.x** — Alpha versions (unstable, breaking changes allowed)
- **v1.0.0** — First stable production release
- **vX.Y.Z** — MAJOR.MINOR.PATCH
  - MAJOR: Incompatible API changes
  - MINOR: Backward-compatible functionality additions
  - PATCH: Backward-compatible bug fixes

### Tags and Releases
- Each development stage = git tag (v0.1.0, v0.2.0, ..., v1.0.0)
- GitHub Releases with detailed changelog
- Release notes include migration guides for breaking changes

---

## 🚀 Development Stages

### **STAGE 0: Project Initialization** → `v0.1.0`
**Goal:** Create basic project structure and configure infrastructure.

#### Tasks:
1. ✅ Create GitHub repository
2. ✅ Initialize directory structure
3. ✅ Configure `.gitignore`, `.dockerignore`
4. ✅ Create `requirements.txt` and `requirements-dev.txt`
5. ✅ Set up `pyproject.toml` (black, isort, mypy, pytest)
6. ✅ Create `.env.example` with environment variables
7. ✅ Create `config/bot_config.example.yaml` with configuration example
8. ✅ Create `config/ai_instruction.example.md` with AI instruction example
9. ✅ Write basic `README.md` with instructions
10. ✅ Create `Dockerfile` and `docker-compose.yml`

#### Checkpoint:
- ✅ Project builds locally
- ✅ Docker image builds without errors
- ✅ `mypy .` passes without errors (empty modules)
- ✅ `black --check .` and `isort --check .` pass
- ✅ All example files are properly formatted

#### Git Commands:
```bash
git init
git checkout -b develop
git add .
git commit -m "chore: initial project structure (v0.1.0)"
git tag v0.1.0
git remote add origin https://github.com/username/flibusta-assist-bot.git
git push -u origin develop --tags
```

**Estimated Time:** 1-2 days  
**Assigned:** 1 developer

---

### **STAGE 1: Core Layer & Configuration** → `v0.2.0`
**Goal:** Implement configuration loading, logging, and base types.

#### Tasks:
1. Implement `src/bot/core/config.py`:
   - Load environment variables using `os.getenv()`
   - Parse YAML using `PyYAML`
   - Create `Config` class with typed fields (Pydantic)
   - Load AI instruction from file (path specified in YAML)
   - Thread-safe configuration access
   - Configuration loaded once at startup
   
2. Implement `src/bot/core/logger.py`:
   - Configure `logging` (stdout + file with rotation)
   - Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
   - Structured logging with context
   - Log formatting and color output
   
3. Create `src/bot/core/types.py`:
   - TypedDict for Telegram messages
   - Pydantic models for OpenRouter API
   - Internal data models (ChatContext, AIResponse, ButtonCommand)
   - Type aliases and constants
   
4. Write `tests/test_core/`:
   - `test_config.py` — Test environment variables, YAML, and instruction loading
   - `test_logger.py` — Test log writing and rotation
   - `test_types.py` — Test data model validation

#### Checkpoint:
- ✅ Configuration loads from environment variables and YAML at startup
- ✅ AI instruction loads from file at startup
- ✅ Logs write to file and stdout
- ✅ All tests pass: `pytest tests/test_core/ -v`
- ✅ `mypy src/bot/core/` passes without errors
- ✅ Code coverage > 80% for core module (86.57%)

#### Git Commands:
```bash
git checkout -b feature/core-layer
# ... development work ...
git add src/bot/core/ tests/test_core/
git commit -m "feat(core): implement config, logger and types

- Add Config class with hot-reload support
- Implement structured logging with rotation
- Define core types and data models
- Add comprehensive test coverage"
git checkout develop
git merge feature/core-layer
git tag v0.2.0
git push origin develop --tags
```

**Estimated Time:** 2-3 days  
**Assigned:** 1 developer

---

### **STAGE 2: OpenRouter Client** → `v0.3.0`
**Goal:** Implement async client for OpenRouter.ai API.

#### Tasks:
1. Implement `src/bot/clients/openrouter_client.py`:
   - Async `OpenRouterClient` class (aiohttp)
   - Method `async def chat_completion(...) -> str`
   - Error handling (retry logic, timeout, rate limiting)
   - Request/response typing
   - Support for model: "nex-agi/deepseek-v3.1-nex-n1:free"
   - Request deduplication
   - Optional response caching
   
2. Write `tests/test_clients/test_openrouter_client.py`:
   - Mock HTTP requests using `aioresponses`
   - Test successful responses
   - Test error handling (429, 500, timeout, network errors)
   - Test retry logic
   - Test timeout scenarios

#### Checkpoint:
- ✅ Client successfully makes requests to OpenRouter API
- ✅ Error handling works correctly
- ✅ Retry logic functions as expected
- ✅ All tests pass: `pytest tests/test_clients/ -v`
- ✅ `mypy src/bot/clients/` passes without errors
- ✅ Code coverage > 80% for clients module (80.32%)

#### Git Commands:
```bash
git checkout -b feature/openrouter-client
# ... development work ...
git add src/bot/clients/ tests/test_clients/
git commit -m "feat(clients): implement OpenRouter API client

- Add async OpenRouterClient with aiohttp
- Implement retry logic and error handling
- Add comprehensive test coverage
- Support for DeepSeek v3.1 model"
git checkout develop
git merge feature/openrouter-client
git tag v0.3.0
git push origin develop --tags
```

**Estimated Time:** 2-3 days  
**Assigned:** 1 developer

---

### **STAGE 3: Services - Business Logic** → `v0.4.0`
**Goal:** Implement service layer for AI processing and button generation.

#### Tasks:
1. Implement `src/bot/services/ai_assistant.py`:
   - `AIAssistantService` class
   - Method `async def get_ai_response(context: str) -> str`
   - Prompt formatting: instruction from file + context
   - Call OpenRouterClient
   - Cache AI instructions at startup
   - Response validation and sanitization
   
2. Implement `src/bot/services/message_analyzer.py`:
   - `MessageAnalyzer` class
   - Method `async def extract_context(chat_id: int) -> str`
   - Retrieve message history from Telegram
   - Context building and filtering
   - Conversation thread detection
   
3. Implement `src/bot/services/button_generator.py`:
   - `ButtonGenerator` class
   - Method `generate_reply_buttons(ai_response: str) -> ReplyKeyboardMarkup`
   - Parse commands/requests from AI response
   - Format buttons for target bot:
     * Commands: `/command@FlibustaRuBot`
     * Requests: `@FlibustaRuBot request`
   - Adaptive button layout (2-3 per row)
   
4. Write tests for all services:
   - Mock external dependencies
   - Test edge cases
   - Validate button formatting
   - Test context extraction

#### Checkpoint:
- [x] `AIAssistantService` generates responses via OpenRouter ✅
- [x] AI instruction loads from file at startup ✅
- [x] `MessageAnalyzer` extracts context from chat ✅
- [x] `ButtonGenerator` creates reply buttons in correct format ✅
- [x] Buttons properly target @FlibustaRuBot ✅
- [x] All tests pass: `pytest tests/test_services/ -v` ✅
- [x] `mypy src/bot/services/` passes without errors ✅
- [x] Code coverage > 80% for services module ✅

#### Git Commands:
```bash
git checkout -b feature/services
# ... development work ...
git add src/bot/services/ tests/test_services/
git commit -m "feat(services): implement AI assistant, message analyzer and button generator

- Add AIAssistantService with instruction caching
- Implement MessageAnalyzer for context extraction
- Add ButtonGenerator with FlibustaRuBot formatting
- Comprehensive test coverage"
git checkout develop
git merge feature/services
git tag v0.4.0
git push origin develop --tags
```

**Estimated Time:** 3-5 days  
**Assigned:** 1 developer

---

### **STAGE 4: Handlers & Middleware** → `v0.5.0`
**Goal:** Implement Telegram event handlers and middleware.

#### Tasks:
1. Implement `src/bot/middleware/logging.py`:
   - Middleware for logging all incoming events
   - Request/response timing
   - Error tracking
   - Performance metrics
   
2. Implement `src/bot/middleware/error_handler.py`:
   - Global exception handling
   - User-friendly error messages
   - Detailed error logging
   - Graceful degradation
   
3. Implement `src/bot/handlers/group_messages.py`:
   - Router for group messages
   - Handle bot mentions
   - Call `AIAssistantService`
   - Send messages with reply buttons
   
4. Implement `src/bot/handlers/channel_comments.py`:
   - Router for channel post comments
   - Context-aware suggestions
   - Button generation
   
5. Create `src/bot/main.py`:
   - Initialize aiogram Bot and Dispatcher
   - Register middleware and handlers
   - Start polling
   - Graceful shutdown handling

#### Checkpoint:
- [ ] Bot starts and responds to group messages
- [ ] Middleware logs events correctly
- [ ] Error handling works properly
- [ ] Reply buttons are generated and functional
- [ ] Integration tests in test group pass
- [ ] All tests pass: `pytest tests/ -v`
- [ ] `mypy src/bot/` passes without errors

#### Git Commands:
```bash
git checkout -b feature/handlers-middleware
# ... development work ...
git add src/bot/middleware/ src/bot/handlers/ src/bot/main.py tests/
git commit -m "feat(handlers): implement message handlers and middleware

- Add logging and error handling middleware
- Implement group message and channel comment handlers
- Create main bot entry point
- Add integration tests"
git checkout develop
git merge feature/handlers-middleware
git tag v0.5.0
git push origin develop --tags
```

**Estimated Time:** 3-4 days  
**Assigned:** 1 developer

---

### **STAGE 5: Integration Testing** → `v0.6.0`
**Goal:** Conduct comprehensive testing of all components.

#### Tasks:
1. Create test Telegram group
2. Add bot as administrator
3. Add target bot (@FlibustaRuBot) to the same group
4. Test scenarios:
   - Bot mention in group
   - Response with reply buttons
   - Button click sends command to target bot
   - Target bot processes command from button
   - API error handling
   - Rate limiting scenarios
   - Multiple concurrent users
   
5. Perform load testing (high message volume)
6. Verify logging (files, stdout, rotation)
7. Write E2E tests using aiogram testing tools
8. Performance profiling and optimization

#### Checkpoint:
- [ ] All scenarios work correctly
- [ ] Buttons send commands to target bot
- [ ] Target bot processes button commands
- [ ] No critical bugs found
- [ ] Logs are readable and informative
- [ ] Test coverage > 80%: `pytest --cov=src/bot --cov-report=html`
- [ ] Performance benchmarks meet requirements (<2s response time)
- [ ] Load testing successful (100+ concurrent users)

#### Git Commands:
```bash
git checkout -b feature/integration-tests
# ... testing and fixes ...
git add tests/e2e/ docs/test_results/
git commit -m "test: add integration and E2E tests

- Complete integration testing with FlibustaRuBot
- Add E2E test suite
- Performance optimization
- Bug fixes from testing"
git checkout develop
git merge feature/integration-tests
git tag v0.6.0
git push origin develop --tags
```

**Estimated Time:** 2-3 days  
**Assigned:** 1-2 developers

---

### **STAGE 6: Docker & Deployment** → `v0.7.0`
**Goal:** Prepare bot for VPS deployment.

#### Tasks:
1. Optimize `Dockerfile` (multi-stage build):
   - Use python:3.13-slim base
   - Install dependencies efficiently
   - Minimize image size
   - Security hardening
   
2. Configure `docker-compose.yml`:
   - Mount config/ (YAML + instruction) and logs/
   - Environment variables from .env
   - Restart policy
   - Health checks
   - Network configuration
   
3. Create `deploy.sh` automation script:
   - Pull latest changes
   - Build Docker image
   - Deploy to VPS
   - Run migrations (if any)
   - Health check validation
   
4. Document deployment process in README
5. Test local Docker build and run
6. Test deployment to staging environment

#### Checkpoint:
- [ ] Docker image builds without errors
- [ ] Bot runs correctly in container
- [ ] Logs accessible via `docker logs`
- [ ] Configuration loads correctly in container
- [ ] Health checks pass
- [ ] Deployment script works
- [ ] Staging deployment successful

#### Git Commands:
```bash
git checkout -b feature/docker-deploy
# ... deployment setup ...
git add Dockerfile docker-compose.yml deploy.sh
git commit -m "feat(docker): optimize Dockerfile and add deploy script

- Multi-stage Docker build for minimal image size
- Docker Compose for easy orchestration
- Automated deployment script
- Health check endpoints"
git checkout develop
git merge feature/docker-deploy
git tag v0.7.0
git push origin develop --tags
```

**Estimated Time:** 1-2 days  
**Assigned:** 1 DevOps/developer

---

### **STAGE 7: Documentation & Code Review** → `v0.8.0`
**Goal:** Complete documentation and conduct final code review.

#### Tasks:
1. Update `README.md`:
   - Feature description
   - Installation and setup instructions
   - Configuration examples (YAML + instruction)
   - Interaction format with target bot
   - Deployment guide
   - Troubleshooting FAQ
   - Contributing guidelines
   
2. Add docstrings to all functions and classes:
   - Google-style docstrings
   - Type annotations in docstrings
   - Usage examples
   - Parameter descriptions
   
3. Create `CONTRIBUTING.md`:
   - Development setup
   - Code style guidelines
   - Pull request process
   - Issue reporting
   
4. Conduct code review:
   - SOLID principles compliance
   - Remove code duplication
   - Check type annotations (mypy --strict)
   - Performance optimization
   - Security audit
   
5. Update `CHANGELOG.md`:
   - All changes from v0.1.0 to v0.8.0
   - Breaking changes highlighted
   - Migration guides

#### Checkpoint:
- [ ] Documentation is complete and current
- [ ] All functions have docstrings
- [ ] `mypy --strict` passes without errors
- [ ] Code follows standards (black, isort, flake8)
- [ ] No critical security issues
- [ ] CHANGELOG is comprehensive
- [ ] README examples are tested and working

#### Git Commands:
```bash
git checkout -b docs/finalize
# ... documentation and review ...
git add README.md CONTRIBUTING.md CHANGELOG.md src/
git commit -m "docs: finalize README and add docstrings

- Complete project documentation
- Add comprehensive docstrings
- Code review and refactoring
- Update CHANGELOG"
git checkout develop
git merge docs/finalize
git tag v0.8.0
git push origin develop --tags
```

**Estimated Time:** 2-3 days  
**Assigned:** 1 developer

---

### **STAGE 8: Release v1.0.0** → `v1.0.0` 🎉
**Goal:** Stable version for production deployment.

#### Tasks:
1. Create `release/1.0.0` branch
2. Conduct final testing on VPS:
   - All features working
   - Performance acceptable
   - No critical bugs
   - Security validation
   
3. Fix critical bugs (if found)
4. Update `CHANGELOG.md` with complete change list
5. Create GitHub Release with description:
   - Feature highlights
   - Breaking changes
   - Upgrade guide
   - Known issues
   
6. Merge to `main` and `develop`
7. Deploy to production
8. Monitor for issues

#### Checkpoint:
- [ ] All tests pass
- [ ] Bot runs stably in production
- [ ] Buttons correctly send commands to target bot
- [ ] Documentation is current
- [ ] GitHub Release published
- [ ] Production monitoring active
- [ ] No critical issues in first 24 hours

#### Git Commands:
```bash
git checkout -b release/1.0.0
# ... final fixes and preparation ...
git commit -m "chore: prepare release v1.0.0

- Final bug fixes
- Update CHANGELOG
- Version bump to 1.0.0
- Release preparation"

git checkout main
git merge release/1.0.0
git tag v1.0.0
git push origin main --tags

git checkout develop
git merge main
git push origin develop
```

**Estimated Time:** 1-2 days  
**Assigned:** Full team

---

## 🧪 Testing Strategy

### Unit Tests (Every Stage)
- Coverage of individual functions and classes
- Mock external dependencies
- Run: `pytest tests/unit/`
- Target: >80% code coverage

### Integration Tests (Stage 5)
- Test component interactions
- Real OpenRouter API calls (staging environment)
- Test Telegram group with target bot
- Run: `pytest tests/integration/`

### E2E Tests (Stage 5)
- Full bot workflow scenarios
- Automation via aiogram testing tools
- Test interaction with target bot
- Run: `pytest tests/e2e/`

### Regression Testing (Before Each Release)
- Ensure old functionality still works
- Run full test suite
- Performance benchmarks
- Security scans

---

## 📊 Quality Control

### On Every Commit (Git Hooks):
```bash
# pre-commit hook
black --check src/ tests/
isort --check src/ tests/
flake8 src/ tests/
mypy src/
pytest tests/ --cov=src/bot --cov-fail-under=80
```

### CI/CD (GitHub Actions) - Optional:
- Automatic test run on every PR
- Code style checks
- Docker image build
- Security scanning
- Staging deployment

---

## 📅 Time Estimation

| Stage | Time | Team |
|-------|------|------|
| Stage 0 | 1-2 days | 1 developer |
| Stage 1 | 2-3 days | 1 developer |
| Stage 2 | 2-3 days | 1 developer |
| Stage 3 | 3-5 days | 1 developer |
| Stage 4 | 3-4 days | 1 developer |
| Stage 5 | 2-3 days | 1-2 developers |
| Stage 6 | 1-2 days | 1 DevOps/developer |
| Stage 7 | 2-3 days | 1 developer |
| Stage 8 | 1-2 days | Full team |
| **TOTAL** | **~3-4 weeks** | 1-2 people |

---

## 🎯 Success Criteria

- ✅ Bot works correctly in groups and comments
- ✅ AI assistant provides relevant suggestions
- ✅ Reply buttons generate in correct format
- ✅ Buttons send commands to target bot (@FlibustaRuBot)
- ✅ Target bot processes button commands
- ✅ Test coverage > 80%
- ✅ Type checking (mypy --strict) without errors
- ✅ Docker deployment to VPS works stably
- ✅ Documentation is complete and current

---

## 📌 Post v1.0.0 Roadmap

### v1.1.0 — Improvements
- Rate limiting to prevent spam
- AI response caching
- Metrics and monitoring (Prometheus)
- Health check endpoints

### v1.2.0 — New Features
- Multi-language support (i18n)
- Web admin panel
- Per-group instruction customization
- Analytics dashboard

### v2.0.0 — Scaling
- Redis for context storage
- PostgreSQL for request logging
- Load balancing (multiple instances)
- Microservices architecture

---

## 📝 Development Log

### 2026-01-12
- ✅ **STAGE 3 COMPLETE (v0.4.0)**
- ✅ Implemented AIAssistantService with OpenRouter integration
- ✅ Added comprehensive AI response parsing and categorization
- ✅ Implemented MessageAnalyzer for context extraction and validation
- ✅ Added ButtonGenerator with adaptive layout and FlibustaRuBot formatting
- ✅ Created comprehensive test suite for all services
- ✅ Implemented response sanitization and Telegram compatibility
- ✅ Added context filtering, validation, and chat type detection
- ✅ Implemented button categorization and layout validation
- ✅ All tests passing: `pytest tests/test_services/ -v`
- ✅ Code coverage exceeds 80% requirement
- ✅ Type checking passes: `mypy src/bot/services/`
- ✅ Updated architecture documentation with implementation details
- ✅ Updated changelog and development plan
- 🔄 **Next: Stage 4 - Handlers & Middleware (v0.5.0)**

### 2026-01-09
- ✅ **STAGE 1 COMPLETE (v0.2.0)**
- ✅ Implemented Config class with Pydantic validation
- ✅ Implemented BotLogger with structured logging and rotation
- ✅ Implemented core types (ChatContext, AIResponse, ButtonCommand, etc.)
- ✅ Created comprehensive test suite (59 tests, 86.57% coverage)
- ✅ Fixed all type annotation issues (mypy --strict passes)
- ✅ Applied code formatting (black, isort)
- ✅ Merged to main and tagged v0.2.0
- ✅ Pushed to origin with tags

### 2026-01-08
- ✅ Reviewed existing architecture and planning documents
- ✅ Created comprehensive ARCHITECTURE.md
- ✅ Created detailed DEVELOPMENT_PLAN.md
- ✅ Established clear documentation structure
- ✅ **STAGE 0 COMPLETE (v0.1.0)**

---

**Plan Version:** 1.1
**Last Updated:** 2026-01-12
**Status:** Stage 3 Complete (v0.4.0) - Ready for Handlers & Middleware Implementation