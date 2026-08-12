---
name: playwright-testing
description: Commands and setup for executing backend PDF rendering tests and frontend E2E web application tests using Playwright.
---

# Playwright Testing Guide — ResumeAI

This guide details how to set up, run, and troubleshoot Playwright tests for both the backend PDF engine and the frontend web app.

---

## 1. Backend PDF Generation Tests

The backend uses headless Chromium via the `playwright` python package to render resume HTML templates to PDFs.

### Prerequisites (Python environment)
If running for the first time, install playwright and its Chromium dependency:
```bash
pip install -r backend/requirements.txt
playwright install chromium
playwright install-deps
```

### Run PDF Tests
From the project root directory, run:
```bash
pytest backend/tests/test_pdf_generator.py
```

### Troubleshoot
- **Uvicorn SelectorEventLoop reload conflict (Windows):** The codebase uses a custom Uvicorn reload mechanism to avoid Windows reload loop issues when running Playwright async loops.
- **Async loop overlap:** Ensure `await BrowserManager.close_all()` is executed in pytest cleanup fixtures to prevent unclosed browser contexts.

---

## 2. Frontend E2E Web Application Tests

The frontend uses `@playwright/test` for browser E2E testing of the react application interface.

### Setup (Node environment)
Ensure frontend dependencies and browser binaries are installed:
```bash
cd frontend
npm install
npx playwright install
```

### Run Web E2E Tests
To execute all UI tests:
```bash
cd frontend
npm run test:e2e
```

To run tests in interactive UI mode:
```bash
npx playwright test --ui
```
