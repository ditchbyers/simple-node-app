import os
import json
import subprocess
from git import Repo
from pymongo import MongoClient

# Get the path of the repository (working directory where Jenkins is running)
repo_path = os.getenv("WORKSPACE", ".")
print("Current PATH:", os.environ["PATH"])
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
        test1 = subprocess.run(
            ["npm", "-v"],
            text=True,
            capture_output=True,
            check=True,
            shell=True
        )
        print(test1.stdout)
        test2 = subprocess.run(
            ["npm", "install"],
            text=True,
            capture_output=True,
            check=True,
            shell=True
        )
        print(test2.stdout)
        result = subprocess.run(
            ["npm", "ls", "--depth=4", "--json"],
            text=True,
            capture_output=True,
            check=True,
            shell=True
        )
        

        # Parse JSON output
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        return {
            "error": "Error running npm commands" ,
            "details": e.stderr.strip()
        }

# Count total lines of code in each file
def count_lines_of_code(repo_path):
    loc_info = {}
    try:
        for root, _, files in os.walk(repo_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    # Only count lines for text-based files
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        loc_info[file_path] = sum(1 for _ in f)
                except Exception as e:
                    # Handle any errors (e.g., binary files)
                    loc_info[file_path] = f"Error reading file: {str(e)}"
        return loc_info
    except Exception as e:
        return {
            "error": "Error counting lines of code",
            "details": str(e)
        }

# Main Execution
def main():
    git_info = get_git_info(repo_path)
    npm_info = run_npm_ls()
    test1 = subprocess.run(
                ["npm", "-v"],
                text=True,
                capture_output=True,
                check=True,
                shell=True
            )
    print(test1)

    lines_of_code_info = count_lines_of_code(repo_path)

    # Combine all information into a single JSON
    combined_info = {
        "commit_info": git_info,
        "npm_info": npm_info,
        "lines_of_code": lines_of_code_info
    }

    # Output the JSON
    output_json = json.dumps(combined_info, indent=4)
# Run the main function
if __name__ == "__main__":
    main()