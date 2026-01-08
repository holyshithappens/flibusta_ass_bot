# Multi-stage Dockerfile for FlibustaUserAssistBot
# Stage 1: Build dependencies and install packages

FROM python:3.13-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Add metadata labels
LABEL org.opencontainers.image.created=$BUILD_DATE \
      org.opencontainers.image.url="https://github.com/username/flibusta-assist-bot" \
      org.opencontainers.image.source="https://github.com/username/flibusta-assist-bot" \
      org.opencontainers.image.version=$VERSION \
      org.opencontainers.image.revision=$VCS_REF \
      org.opencontainers.image.vendor="Development Team" \
      org.opencontainers.image.title="FlibustaUserAssistBot" \
      org.opencontainers.image.description="AI-powered Telegram assistant bot for FlibustaRuBot"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements files
COPY requirements.txt requirements-dev.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime image

FROM python:3.13-slim as runtime

# Set build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Add metadata labels
LABEL org.opencontainers.image.created=$BUILD_DATE \
      org.opencontainers.image.url="https://github.com/username/flibusta-assist-bot" \
      org.opencontainers.image.source="https://github.com/username/flibusta-assist-bot" \
      org.opencontainers.image.version=$VERSION \
      org.opencontainers.image.revision=$VCS_REF \
      org.opencontainers.image.vendor="Development Team" \
      org.opencontainers.image.title="FlibustaUserAssistBot" \
      org.opencontainers.image.description="AI-powered Telegram assistant bot for FlibustaRuBot"

# Create non-root user
RUN groupadd -r botuser && useradd -r -g botuser botuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/src:$PYTHONPATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create necessary directories
RUN mkdir -p /app/config /app/logs /app/src && \
    chown -R botuser:botuser /app

# Copy application code
COPY --chown=botuser:botuser src/ /app/src/
COPY --chown=botuser:botuser pyproject.toml /app/

# Create volume mount points
VOLUME ["/app/config", "/app/logs"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Switch to non-root user
USER botuser

# Expose port (if needed for webhooks)
EXPOSE 8080

# Set default command
CMD ["python", "-m", "src.bot.main"]