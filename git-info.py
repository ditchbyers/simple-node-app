import os
import json
import subprocess
from git import Repo
from pymongo import MongoClient

# Get the path of the repository (working directory where Jenkins is running)
repo_path = os.getenv("WORKSPACE", ".")

# Get Git information in a safe method with try-except
def get_git_info(repo_path):
    try:
        # Open the repository
        repo = Repo(repo_path)

        # Get the latest commit (HEAD)
        commit = repo.head.commit

        # Get commit information
        commit_info = {
            "commit_hash": commit.hexsha,
            "author": commit.author.name,
            "committer": str(commit.committer),
            "date": commit.committed_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            "message": commit.message.strip(),
            "stats": {
                "total": commit.stats.total,
                "files": commit.stats.files
            }
        }

        # Get branches containing the latest commit
        branches_containing_commit = [
            branch.name for branch in repo.branches if commit in branch.commit.iter_items(repo, branch.name)
        ]
        commit_info["branches"] = branches_containing_commit

        return commit_info
    
    except Exception as e:
        return {
            "error": "Error retrieving Git information",
            "details": str(e)
        }

# Run npm audit and capture dependencies information
def run_npm_ls():
    try:
        os.system("npm -v")
        os.system("npm install")

        result = subprocess.run(
            ["npm", "ls", "--depth=4", "--json"],
            text=True,
            capture_output=True,
            check=True,
            # shell=True
        )
        

        # Parse JSON output
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        return {
            "error": "Error running npm commands" ,
            "details": e.stderr.strip()
        }

def count_lines_of_code(repo_path):
    # List to store the number of lines in each file
    lines_of_code_info = {}

    # Walk through the repo directory
    for root, dirs, files in os.walk(repo_path):
        # Skip node_modules or any other directories you want to ignore
        if 'node_modules' in dirs:
            dirs.remove('node_modules')  # This will exclude 'node_modules' from being walked

        for file_name in files:
            file_path = os.path.join(root, file_name)
            
            # Only count lines for source code files (e.g., .js, .py, etc.)
            if file_name.endswith(('.js', '.py', '.html', '.css', '.ts')):  # Add more extensions as needed
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                        lines_of_code_info[file_path] = len(lines)
                except Exception as e:
                    print(f"Could not read file {file_path}: {e}")
    
    return lines_of_code_info

# Main Execution
def main():
    git_info = get_git_info(repo_path)
    npm_info = run_npm_ls()

    lines_of_code_info = count_lines_of_code(repo_path)

    # Combine all information into a single JSON
    combined_info = {
        "commit_info": git_info,
        "npm_info": npm_info,
        "lines_of_code": lines_of_code_info
    }

    # Output the JSON
    output_json = json.dumps(combined_info, indent=4)
    print(output_json)
# Run the main function
if __name__ == "__main__":
    main()