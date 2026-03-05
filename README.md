# SYConv

SYConv is a vocabulary extraction and translation tool for English test papers. It identifies highlighted regions, extracts text using OCR, and provides contextual translations using LLMs (Ollama, Gemini, or OpenAI).

## 🚀 Quick Start

### 1. Automatic Setup (Recommended)
This script will check for prerequisites, install `uv` if missing, and set up both Backend and Frontend.

- **Windows**:
  ```powershell
  ./setup.ps1
  ```
- **macOS/Linux**:
  ```bash
  chmod +x setup.sh start.sh
  ./setup.sh
  ```

### 2. Running the App
- **Windows**:
  ```powershell
  ./start.ps1
  ```
- **macOS/Linux**:
  ```bash
  ./start.sh
  ```

---

### 3. Prerequisites
- **Python 3.9+**
- **Node.js 18+**
- **Ollama** (Optional, for local LLM)

---

## 🛠️ Key Features
- **OCR Engine**: Powered by EasyOCR.
- **2-Pass LLM Logic**: Extracts and verifies meanings to ensure consistency and naturalness.
- **Multilingual Suffixes**: Specifically tuned for Korean grammar (POS-specific suffixes).
- **Interactive Review**: Manually adjust OCR results before translation.
