# CursorBoost

CursorBoost is a CLI tool designed to dynamically generate and maintain an accurate `.cursorrules` file for improved integration with **Cursor**, a VSCode fork powered by GPT-4. By automating system and project environment analysis, CursorBoost ensures that `.cursorrules` stays up-to-date, reducing errors and enhancing coding assistance in complex development environments.

## Features
- **System Snapshot**: Collects real-time system information (e.g., Docker status, disk usage, memory stats, network ports).
- **Project Analysis**: Scans project directories and dependencies to provide detailed context.
- **LLM Integration**: Uses OpenAI's GPT-4 to generate `.cursorrules` based on collected data.
- **Docker Logs**: Includes logs from running Docker containers for debugging.
- **Continuous Updates**: Periodically refreshes `.cursorrules` and system snapshots.

## Installation
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd .cursorboost
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   - Create a `.env` file in the `.cursorboost` directory.
   - Add your OpenAI API key:
     ```
     OPENAI_API_KEY=your_openai_api_key
     ```

## Usage
1. **Run CursorBoost**:
   ```bash
   python index.py
   ```
   The tool will continuously monitor and update `.cursorrules` every 60 seconds.

2. **Configuration**:
   - Modify `config.json` to customize settings like directory depth, ignored patterns, and disk usage thresholds.

3. **Project List**:
   - Add project directories to `containers-list.md` in the following format:
     ```
     - project_name_1
     - project_name_2
     ```

## Output
- **`.cursorrules`**: Generated in the parent directory of `.cursorboost`.
- **`snapshot.txt`**: Contains the latest system and project snapshots for reference.

## Troubleshooting
- **Missing `config.json`**: Default settings will be used if the file is not found.
- **Docker Errors**: Ensure Docker is installed and running.
- **OpenAI API Key Missing**: Add your API key to the `.env` file.
