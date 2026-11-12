FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

# Usuário sem privilégios: um comprometimento da API não vira root no contêiner.
RUN useradd --system --uid 1001 app
USER app

EXPOSE 8000
CMD ["uvicorn", "src.presentation.api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
