Here is the complete README.md updated with a Mermaid flowchart. GitHub natively supports Mermaid, so when you upload this, it will automatically render a beautiful visual map of your architecture directly on your repository page.

Markdown
# Ruko AI Email-to-WhatsApp Agent

An automated, local AI agent that monitors a Gmail inbox, summarizes incoming emails using a local Large Language Model (Qwen 2.5 via Ollama), and forwards the summary directly to a WhatsApp number.

## System Flow

```mermaid
graph TD
    A[Gmail Inbox] -->|IMAP Fetch| B(Python Email Agent)
    B -->|HTTP Request| C{Ollama: Qwen 2.5}
    C -->|AI Summary| B
    B -->|HTTP POST| D[Node.js WhatsApp Bridge]
    D -->|whatsapp-web.js| E[WhatsApp Phone Client]
Architecture & Tech Stack
AI Engine: Ollama running locally with the qwen2.5 model.

Email Processing: Python script using IMAP to fetch emails and HTTP requests to interface with Ollama.

WhatsApp Bridge: Node.js application utilizing whatsapp-web.js.

Containerization: Docker & Docker Compose.

Environment: Designed for Windows running Ubuntu via WSL2, utilizing local GPU resources (RTX 5050).

Prerequisites
Docker Desktop installed and configured to integrate with WSL2.

Ubuntu (WSL2) installed on Windows.

Ollama installed directly inside the Ubuntu (WSL2) environment.

A dedicated Gmail account with an App Password generated for IMAP access.

Local Setup & Installation
1. Configure Ollama (WSL2)
Since Docker containers run in an isolated network, Ollama must be configured to accept connections from the Docker host.

Run these commands in your Ubuntu terminal to expose Ollama:

Bash
sudo mkdir -p /etc/systemd/system/ollama.service.d
echo -e "[Service]\nEnvironment=\"OLLAMA_HOST=0.0.0.0\"" | sudo tee /etc/systemd/system/ollama.service.d/override.conf
sudo systemctl daemon-reload
sudo systemctl restart ollama
2. Configure Network Settings in Python
To ensure the Dockerized Python agent can reach both Ollama and the WhatsApp bridge, ensure the email_agent.py script points to the correct local IPs.

Because we use network_mode: "host" for the Python container, standard localhost works for the bridge, but Ollama might require the explicit Ubuntu IP:

Ollama URL: http://<YOUR_UBUNTU_IP>:11434/api/chat

WhatsApp Bridge URL: http://127.0.0.1:3000/send

3. Docker Compose Configuration
Ensure your docker-compose.yml uses host networking for the email agent so it bypasses Docker's internal virtual network bridge to reach Ollama:

YAML
services:
  assistant-email-agent:
    build: .
    restart: unless-stopped
    network_mode: "host"

  assistant-wa-bridge:
    build: ./wa-bridge
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - ./wa-session:/app/.wwebjs_auth  # Persists WhatsApp login
4. Build and Run
Start the environment using Docker Compose:

Bash
docker compose up -d --build
5. Authenticate WhatsApp
The WhatsApp bridge requires you to scan a QR code on the first run. Make your terminal window large (to prevent the QR code from wrapping) and check the logs:

Bash
docker compose logs -f assistant-wa-bridge
Open WhatsApp on your phone, navigate to Linked Devices, and scan the QR code displayed in the terminal.

6. Verify Operation
Monitor the email agent to watch it process incoming messages:

Bash
docker compose logs -f assistant-email-agent
Send a test email to the configured Gmail address. The agent will detect it, summarize it using Ollama, and send the final output to your connected WhatsApp account.

CI/CD Pipeline
This repository includes a GitHub Actions workflow (ci.yml). Every push to the main branch automatically builds the latest Docker image and pushes it to Docker Hub.


To push this exact file to your GitHub repository, run the following commands in your Ubuntu terminal:

```bash
cd ~/assistant
nano README.md
# Paste the updated text above, then save (Ctrl+O, Enter, Ctrl+X)
git add README.md
git commit -m "Update README with system architecture flowchart"
git push origin main
