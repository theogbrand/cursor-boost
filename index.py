import subprocess
import datetime
from dotenv import load_dotenv
import os
import json
import time
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

def load_config():
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(script_dir, 'config.json')
        with open(config_file, 'r') as f:
            config = json.load(f)
            
            # Validate required keys
            if 'tree' not in config or 'system_commands' not in config:
                raise KeyError("Missing required keys in config.json")
            
            return config
    except (FileNotFoundError, KeyError):
        print("⚠️ config.json not found or invalid, using default settings")
        return {
            "tree": {
                "max_depth": 3,
                "ignore_patterns": ["venv", "__pycache__", "node_modules", "build", "public", "dist", ".git"],
                "ignore_extensions": ["*.pyc", "*.pyo", "*.pyd", "*.so", "*.dll", "*.class"]
            },
            "system_commands": {
                "disk_usage_threshold": 80
            }
        }

# Load config at the module level, before defining the commands
config = load_config()

# Convert ignore patterns and extensions to string
ignore_patterns = '|'.join(config['tree']['ignore_patterns'])
ignore_extensions = '|'.join(config['tree']['ignore_extensions'])
combined_ignore = f"{ignore_patterns}|{ignore_extensions}"

system_commands = [
    # System information
    "uname -a",  # Operating system details
    "python --version",
    "pip list",  # Installed Python packages
    "python -c 'import sys; print(sys.path)'",  # Python path information
    
    # Docker status
    "docker ps",  # Running containers
    
    # System resources
    f"df -h | awk '(NR==1) || ($5+0 >= {config['system_commands']['disk_usage_threshold']})'",
    "vm_stat | awk '/Pages free:|Pages active:|Pages inactive:|Pages wired down:/ {print}'",  # Key memory stats
    
    # Network
    "netstat -an | grep LISTEN | awk '{print $4}' | sort -u",  # Unique listening ports only
    
    # Environment variables (excluding sensitive data)
    "printenv | grep -v 'KEY\\|SECRET\\|PASS\\|TOKEN'",
]

project_commands = [
    # Project structure (directories only)
    f"tree -d -L {config['tree']['max_depth']} -I '{combined_ignore}'",
]

def get_project_directories():
    try:
        # Look for containers-list.md in the same directory as the script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        projects_file = os.path.join(script_dir, 'containers-list.md')
        
        with open(projects_file, 'r') as f:
            # Read projects from markdown list and clean up
            projects = [
                line.strip('- \n') 
                for line in f.readlines() 
                if line.strip().startswith('-')
            ]
        return projects
    except FileNotFoundError:
        print("❌ Error: containers-list.md not found in .cursorboost directory")
        return []

def run_commands(commands_list, project_dir=None):
    print(f"📊 Collecting {'project' if project_dir else 'system'} information...")
    output = []
    output.append(f"Timestamp: {datetime.utcnow().isoformat()}Z\n")
    
    if project_dir:
        # Change to project directory
        original_dir = os.getcwd()
        project_path = os.path.expanduser(f"~/work/{project_dir}")
        try:
            os.chdir(project_path)
            output.append(f"\n### Project: {project_dir} ###\n")
        except FileNotFoundError:
            print(f"  ❌ Project directory not found: {project_path}")
            return ""

    for command in commands_list:
        print(f"  ⚡ Running: {command}")
        try:
            result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
            output.append(f"{command}:\n{result.decode('utf-8')}\n")
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed: {command}")
            output.append(f"{command} (FAILED):\n{e.output.decode('utf-8')}\n")
    
    if project_dir:
        # Change back to original directory
        os.chdir(original_dir)
    
    return "\n".join(output)

def write_snapshot(snapshot):
    print("💾 Saving system snapshot to snapshot.txt...")
    with open("snapshot.txt", "w") as f:
        f.write(snapshot)


import openai

def generate_cursorrules(snapshot):
    print("🤖 Generating .cursorrules using OpenAI API...")
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        return None
    
    client = openai.OpenAI(api_key=api_key)
    
    response = client.chat.completions.create(
        model="chatgpt-4o-latest",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that injects a user's system information and parses out the most important details. Only respond with the complete file contents, without any additional explanation or commentary."},
            {"role": "user", "content": f"You are a coding assistant optimizing text files for LLM-based applications. Using the following system snapshot, generate a text file that highlights the most relevant details for coding context. Only output the complete file contents, without explanations or extra text:\n\n{snapshot}"}
        ],
        temperature=1,
    )
    return response.choices[0].message.content

def get_docker_logs():
    print("🐳 Collecting Docker container logs...")
    try:
        # Get ignore list from config
        ignore_containers = config.get('docker', {}).get('ignore_containers', [])
        
        # Get list of running containers
        containers = subprocess.check_output(
            "docker ps --format '{{.ID}} {{.Names}}'", 
            shell=True
        ).decode('utf-8').strip().split('\n')
        
        logs = []
        for container in containers:
            if not container:  # Skip empty lines
                continue
                
            container_id, container_name = container.split()
            
            # Skip ignored containers
            if container_name in ignore_containers:
                print(f"  ⏭️  Skipping ignored container: {container_name}")
                continue
                
            try:
                # Get last 25 lines of logs for each container
                container_logs = subprocess.check_output(
                    f"docker logs --tail 25 {container_id}",
                    shell=True
                ).decode('utf-8')
                
                logs.append(f"\nDocker Logs for {container_name} ({container_id}):\n")
                logs.append(container_logs)
            except subprocess.CalledProcessError as e:
                print(f"  ❌ Failed to get logs for container {container_name}")
                logs.append(f"\nError getting logs for {container_name}: {str(e)}\n")
        
        return "\n".join(logs)
    except subprocess.CalledProcessError as e:
        print("  ❌ Failed to get Docker container list")
        return "Error getting Docker container list"

def write_cursorrules(cursorrules):
    print("📝 Writing .cursorrules file...")
    project_description = ""
    try:
        with open("project-description.txt", "r") as f:
            project_description = f"# Project Description:\n{f.read()}\n\n"
    except FileNotFoundError:
        print("Warning: project-description.txt not found")
    
    # Get Docker logs
    docker_logs = get_docker_logs()
    
    # Get parent directory path
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cursorrules_path = os.path.join(parent_dir, '.cursorrules')
    
    # Write combined content to .cursorrules in parent directory
    with open(cursorrules_path, "w") as f:
        f.write(f"{project_description}{cursorrules}\n\n# Docker Container Logs:\n\n{docker_logs}")

def find_requirements_files(root_dir):
    requirements_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip the .cursorboost directory
        if '.cursorboost' in dirpath:
            continue
        
        # Check for requirements.txt in the current directory
        if 'requirements.txt' in filenames:
            requirements_files.append(os.path.join(dirpath, 'requirements.txt'))
    
    return requirements_files

# Example usage
root_directory = os.getcwd()  # Assuming you're running this from the root directory
requirements_files = find_requirements_files(root_directory)
print("Found requirements files:", requirements_files)

if __name__ == "__main__":
    print("🚀 Starting Cursor Boost in continuous mode...")
    
    while True:
        print(f"\n⏰ Running update at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Get all project directories
        projects = get_project_directories()
        if not projects:
            print("⚠️ No projects found in containers-list.md")
        
        # Collect system-wide information first
        system_snapshot = run_commands(system_commands)
        
        # Collect information for each project
        all_snapshots = [system_snapshot]
        for project in projects:
            print(f"📂 Processing project: {project}")
            project_snapshot = run_commands(project_commands, project)
            if project_snapshot:  # Only add if we got some output
                all_snapshots.append(project_snapshot)
        
        # Combine all snapshots
        complete_snapshot = "\n\n".join(all_snapshots)
        
        # Write combined snapshot
        write_snapshot(complete_snapshot)
        
        # Generate and write cursorrules
        cursorrules = generate_cursorrules(complete_snapshot)
        if cursorrules:
            write_cursorrules(cursorrules)
            print("✅ .cursorrules updated successfully")
            print("✅ Snapshot saved to snapshot.txt")
        else:
            print("❌ Failed to generate .cursorrules")
            
        # Wait for 60 seconds before next run
        print("\n⏳ Waiting 60 seconds for next update...")
        time.sleep(60)
