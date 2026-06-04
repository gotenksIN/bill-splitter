# bill-splitter

A small utility to split bills amongst friends

## Running the App

### Configuration

Before running the application, you need to set up environment variables:

1. Copy the example environment file

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and configure the variables as described in the example file.

### Spin up the services

To run the bill-splitter application, use Docker Compose:

```bash
docker compose up
```

This will start all necessary services for the application.

### Accessing the Frontend

Once the app is running, you can access the frontend at http://localhost:5173. This provides a user-friendly interface where you can split bills amongst friends.

### Accessing Backend Documentation

Once the app is running, you can access the interactive API documentation at http://localhost:8000/docs. This provides a Swagger UI interface where you can explore and test all available API endpoints.

## Performance & Accuracy Benchmarks

We run automated benchmarks comparing Google (using `google-genai`) and OpenAI (using `litellm`) models on complex visual OCR receipts, measuring accuracy (successful extraction of items/prices/totals), cost, and latency.

### 📊 Google Models Benchmark
*Configured with the lowest reliable thinking/reasoning settings for maximum speed and cost efficiency.*

| Model | Avg Time (s) | Avg Cost ($) | Accuracy | Config Details |
| :--- | :---: | :---: | :---: | :--- |
| **`gemini-2.5-flash`** | 3.33s | $0.000788 | **100%** | `thinking_budget`: 0 (Disabled) |
| **`gemini-3.1-pro-preview`** | 5.37s | $0.005985 | **100%** | `thinking_level`: `'low'` |
| **`gemini-3.5-flash`** | 8.01s | $0.004510 | **100%** | `thinking_level`: `'low'` |

### 📊 OpenAI Models Benchmark
*Configured with the lowest reliable reasoning/thinking effort settings.*

| Model | Avg Time (s) | Avg Cost ($) | Accuracy | Config Details |
| :--- | :---: | :---: | :---: | :--- |
| **`gpt-4o`** | 4.28s | $0.004378 | **100%** | Standard autoregressive (No thinking support) |
| **`gpt-4o-mini`** | 6.17s | $0.003970 | **100%** | Standard autoregressive (No thinking support) |
| **`gpt-5.4`** | 5.72s | $0.010489 | **100%** | `reasoning_effort`: `'low'` |
