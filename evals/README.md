# LLM Prompt Evaluations

This directory contains promptfoo configurations for evaluating the LLM prompts used in Habit Bot.

## Setup

Ensure you have the required models downloaded in Ollama:

```bash
sudo -u ollama ollama pull gemma3:12b
sudo -u ollama ollama pull qwen3:8b
```

## Running Evaluations

All evaluations run sequentially (maxConcurrency: 1) to avoid GPU memory thrashing when switching between models.

### Run all evaluations
```bash
npm run eval:all
```

### Run specific evaluation sets
```bash
# Category detection (classifies user log entries)
npm run eval:category

# Structured data extraction (extracts JSON from responses)
npm run eval:extraction

# Question generation (generates health-related questions)
npm run eval:questions
```

### View results
```bash
npm run eval:view
```

### Clear cache
```bash
npm run eval:cache-clear
```

## Evaluation Types

### 1. Category Detection (`promptfooconfig.yaml`)
Tests the ability to correctly categorize free-form user log entries into health categories:
- nutrition, sleep, substances, physical_activity
- mental_state, stress_anxiety, physical_symptoms
- social_interaction, work_productivity, environment

### 2. Structured Extraction (`extraction.yaml`)
Tests extraction of structured JSON data from conversational responses:
- Sleep: duration, quality, times
- Nutrition: food items, quantities, times
- Physical activity: type, duration, intensity
- etc.

### 3. Question Generation (`questions.yaml`)
Tests generation of relevant health-tracking questions for each category.

## Models Being Evaluated

- **Gemma3-12B**: Google's Gemma 3 12B parameter model
- **Qwen3-8B**: Alibaba's Qwen 3 8B parameter model

## Adding New Tests

1. Add test cases to the appropriate YAML config file
2. Use `assert` with `contains-json` for JSON output validation
3. Use JavaScript assertions for complex validation logic

Example:
```yaml
- vars:
    log_entry: "Went for a morning run"
  assert:
    - type: contains-json
    - type: javascript
      value: |
        try {
          const data = JSON.parse(output);
          return data.category === "physical_activity";
        } catch { return false; }
```
