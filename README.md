# 🤖 FlibustaUserAssistBot

[![Python Version](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Version](https://img.shields.io/badge/version-v0.2.0-green.svg)](https://github.com/holyshithappens/flibusta_ass_bot/releases/tag/v0.2.0)
[![Coverage](https://img.shields.io/badge/coverage-86%25-brightgreen.svg)](htmlcov/index.html)

**AI-powered Telegram assistant bot** that helps users interact with [@FlibustaRuBot](https://t.me/FlibustaRuBot) by providing intelligent suggestions and generating reply buttons with appropriate commands.

---

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Development](#development)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

---

## ✨ Features

### ✅ Implemented (v0.2.0)
- **Core Configuration** - Pydantic-based config with environment variable support
- **Structured Logging** - Multi-output logging with rotation and multiple log levels
- **Type Safety** - Complete type definitions with mypy strict mode
- **Comprehensive Tests** - 86.57% coverage with 59 unit tests
- **Quality Assurance** - All quality checks passing (mypy, black, isort, pytest)

### 🚧 Coming Soon (v0.3.0+)
- **Intelligent Assistance** - AI-powered suggestions using DeepSeek v3.1
- **Context-Aware Analysis** - Conversation history understanding
- **Smart Buttons** - Reply keyboard buttons for Flibusta commands
- **Hot-Reloadable Config** - Runtime configuration changes
- **Docker Deployment** - Production-ready containerization
- **Telegram Integration** - Message handlers and middleware

---

## 🏗️ Architecture

The bot is built with a modular, layered architecture:

```
┌─────────────────────────────────────────┐
│          Telegram Layer                 │
│  (Handlers & Middleware)                │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│       Business Logic Layer              │
│  (AI Assistant, Message Analyzer)       │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         External Services               │
│  (OpenRouter API, FlibustaRuBot)        │
└─────────────────────────────────────────┘
```

### Core Components

- **Config Manager** - Loads and validates configuration from multiple sources
- **Logger** - Structured logging with rotation and multiple outputs
- **OpenRouter Client** - Async HTTP client for AI API calls
- **AI Assistant Service** - Generates context-aware responses
- **Message Analyzer** - Extracts conversation context
- **Button Generator** - Creates Telegram reply keyboards
- **Handlers** - Process Telegram messages and events
- **Middleware** - Logging, error handling, and security

For detailed architecture documentation, see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## 📦 Installation

### Prerequisites

- **Python 3.13** or higher
- **Docker** (optional, for containerized deployment)
- **Telegram Bot Token** (get from [@BotFather](https://t.me/BotFather))
- **OpenRouter API Key** (get from [OpenRouter.ai](https://openrouter.ai/keys))

### Method 1: Local Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/holyshithappens/flibusta_ass_bot.git
   cd flibusta_ass_bot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **For development**
   ```bash
   pip install -r requirements-dev.txt
   ```

### Method 2: Docker Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/holyshithappens/flibusta_ass_bot.git
   cd flibusta_ass_bot
   ```

2. **Build Docker image**
   ```bash
   docker build -t flibusta_ass_bot .
   ```

3. **Run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

---

## ⚙️ Configuration

### Step 1: Environment Variables

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```bash
# Telegram Bot Token
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# OpenRouter API Key
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Bot Configuration
TARGET_BOT_USERNAME=FlibustaRuBot
BOT_USERNAME=FlibustaAssBot

# Logging
LOG_LEVEL=INFO
LOG_FILE_PATH=logs/bot.log
```

### Step 2: Bot Configuration

Copy the example configuration file:

```bash
cp config/bot_config.example.yaml config/bot_config.yaml
```

Edit `config/bot_config.yaml` to customize bot behavior:

```yaml
bot:
  name: "FlibustaUserAssistBot"
  username: "@FlibustaAssBot"
  target_bot_username: "@FlibustaRuBot"

telegram:
  group_chat_ids: []  # Leave empty for all groups
  admin_user_ids: []

openrouter:
  model: "nex-agi/deepseek-v3.1-nex-n1:free"
  temperature: 0.7
  max_tokens: 500
```

### Step 3: AI Instructions

Copy the example AI instruction file:

```bash
cp config/ai_instruction.example.md config/ai_instruction.md
```

Edit `config/ai_instruction.md` to customize AI assistant behavior:

```markdown
# AI Assistant Instructions

You are FlibustaAssistant, an intelligent AI assistant that helps users 
interact with the @FlibustaRuBot Telegram bot...

[Customize the instructions as needed]
```

---

## 🚀 Usage

### Local Development

1. **Start the bot**
   ```bash
   python -m src.bot.main
   ```

2. **With hot-reload (development)**
   ```bash
   python -m src.bot.main --dev
   ```

### Docker

1. **Production deployment**
   ```bash
   docker-compose up -d
   ```

2. **Development deployment**
   ```bash
   docker-compose --profile dev up -d
   ```

3. **View logs**
   ```bash
   docker-compose logs -f flibusta-assist-bot
   ```

4. **Stop the bot**
   ```bash
   docker-compose down
   ```

### Bot Interaction

Once the bot is running:

1. **Add the bot to your Telegram group**
2. **Mention the bot** in a message, for example:
   - "Посоветуй что-нибудь почитать"
   - "Ищу книги по программированию"
   - "Хочу почитать Толстого"

3. **The bot will respond** with:
   - A helpful message
   - Suggestions (bullet points)
   - Reply buttons with commands

4. **Click a button** to send the command to FlibustaRuBot

---

## 💻 Development

### Project Structure

```
flibusta-assist-bot/
├── src/
│   └── bot/
│       ├── core/           # Configuration, logging, types
│       ├── clients/        # External API clients
│       ├── services/       # Business logic
│       ├── handlers/       # Telegram message handlers
│       ├── middleware/     # Logging, error handling
│       └── main.py         # Entry point
├── tests/                  # Test suites
├── config/                 # Configuration files
├── docs/                   # Documentation
├── logs/                   # Log files
├── Dockerfile              # Container definition
├── docker-compose.yml      # Orchestration
├── pyproject.toml          # Project metadata
└── requirements.txt        # Dependencies
```

### Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**

3. **Run tests**
   ```bash
   pytest tests/ -v
   ```

4. **Check code style**
   ```bash
   black --check src/ tests/
   isort --check src/ tests/
   flake8 src/ tests/
   mypy src/
   ```

5. **Format code**
   ```bash
   black src/ tests/
   isort src/ tests/
   ```

6. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: your feature description"
   ```

7. **Push and create pull request**
   ```bash
   git push origin feature/your-feature-name
   ```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/bot --cov-report=html

# Run specific test file
pytest tests/test_core/test_config.py -v

# Run with markers
pytest tests/ -m unit
pytest tests/ -m integration
```

### Code Quality

```bash
# Type checking
mypy src/

# Linting
flake8 src/ tests/
pylint src/bot/

# Formatting
black --check src/ tests/
isort --check src/ tests/

# Security audit
bandit -r src/
```

---

## 🐳 Deployment

### Docker Deployment

1. **Build production image**
   ```bash
   docker build -t flibusta-assist-bot:latest .
   ```

2. **Deploy to VPS**
   ```bash
   docker-compose up -d
   ```

3. **Verify deployment**
   ```bash
   docker-compose ps
   docker-compose logs -f
   ```

### Environment-Specific Configuration

Create environment-specific files:

- `.env.production` - Production settings
- `.env.staging` - Staging settings
- `.env.dev` - Development settings

Use with Docker Compose:

```bash
docker-compose --env-file .env.production up -d
```

### Health Checks

The bot includes health check endpoints:

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' flibusta-assist-bot

# View health check logs
docker logs flibusta-assist-bot 2>&1 | grep health
```

---

## 📚 Documentation

- **[Architecture](docs/ARCHITECTURE.md)** - System design and component architecture
- **[Development Plan](docs/DEVELOPMENT_PLAN.md)** - Development stages and roadmap
- **[Changelog](docs/CHANGELOG.md)** - Version history and changes

---

## 🤝 Contributing

We welcome contributions! Please read our contributing guidelines:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/AmazingFeature`)
3. **Commit your changes** (`git commit -m 'Add some AmazingFeature'`)
4. **Push to the branch** (`git push origin feature/AmazingFeature`)
5. **Open a Pull Request**

### Development Guidelines

- Follow **PEP 8** style guidelines
- Use **type hints** for all function parameters
- Write **comprehensive tests** for new features
- Update **documentation** for API changes
- Use **conventional commits** for commit messages

### Code Review Process

All pull requests must:
- Pass all automated tests
- Meet code coverage requirements (>80%)
- Pass code style checks
- Be reviewed by at least one maintainer

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **[FlibustaRuBot](https://t.me/FlibustaRuBot)** - The target bot we assist
- **[OpenRouter.ai](https://openrouter.ai/)** - AI API provider
- **[DeepSeek](https://deepseek.com/)** - AI model provider
- **[aiogram](https://docs.aiogram.dev/)** - Telegram bot framework
- **[Pydantic](https://docs.pydantic.dev/)** - Data validation

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/holyshithappens/flibusta_ass_bot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/holyshithappens/flibusta_ass_bot/discussions)
- **Documentation**: [docs/](docs/)

---

## 🗺️ Roadmap

### v1.0.0 (Current)
- ✅ Initial release with core functionality
- ✅ AI-powered suggestions
- ✅ Reply button generation
- ✅ Hot-reloadable configuration
- ✅ Docker deployment

### v1.1.0 (Planned)
- Rate limiting per user
- AI response caching
- Prometheus metrics
- Health check endpoints

### v1.2.0 (Future)
- Multi-language support (i18n)
- Web admin panel
- Per-group instruction customization
- Analytics dashboard

### v2.0.0 (Future)
- Redis integration
- PostgreSQL for logging
- Load balancing
- Microservices architecture

---

**Project Status**: ✅ Stage 1 Complete (v0.2.0)
**Last Updated**: 2026-01-09
**Maintainer**: Development Team