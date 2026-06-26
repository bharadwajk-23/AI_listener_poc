from pathlib import Path

project_dir = Path.cwd()

service_content = f"""[Unit]
Description=Backend FastAPI Service
After=network.target

[Service]
Type=simple
User=plareaiuser
WorkingDirectory={project_dir}
ExecStart={project_dir}/start.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

with open("ai_listener_backend.service", "w") as f:
    f.write(service_content)

print("ai_listener_backend.service created successfully")
