import os
import json
import subprocess

import pymongo
from git import Repo
from pymongo import MongoClient
# Get the path of the repository (working directory where Jenkins is running)
repo_path = os.getenv("WORKSPACE", ".")

# Get last commit hash from MongoDB
def get_last_commit_hash():
    try:
        with MongoClient('mongodb://admin:pass@localhost:27017/') as client:
            db = client['jenkins']
            collection = db["pipeline_data"]

            # Find the latest commit by sorting by commit date
            latest_commit = collection.find_one(sort=[("_id", pymongo.DESCENDING)], limit=1)["commit_info"]["commit_hash"]
            return latest_commit
    except Exception as e:
        print(f"Error retrieving last commit hash: {e}")
        return None

def get_git_info(commit):
    return {
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

# NPM Dependency Check

def npm_changes(commit):
    try:
        for file in commit.stats.files:
            if "package.json" in file:
                return True
        return False
    except Exception as e:
        print(f"Error checking for package.json changes: {e}")
        return False

def get_npm_info(commit):
    try:
        # Delete Node Modules folder
        if os.path.exists("node_modules"):
            # Windows
            os.system(r'rmdir /s /q "node_modules"')
            # Linux
            # os.system(r'rm -rf "node_modules"')

        # Delete package-lock
        if os.path.exists("package-lock.json"):
            # Windows
            os.system(r'del "package-lock.json"')
            # Linux
            # os.system(r'rm "package-lock.json"')

        # Install all dependencies
        os.system(r'npm install')

        # Create list of all dependencies no matter the depth
        result = subprocess.run(
            ["npm", "ls", "--depth=Infinity", "--json"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            shell=True
        )

        os.system(f'git reset --hard {commit}')

        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Command: {e.cmd}")
        print(f"Return code: {e.returncode}")
        print(f"Output: {e.output}")
        print(f"Error: {e.stderr}")

def parse_dependencies(dependencies, path_prefix="", parent_name=None, layer=0):
    """
    Parses the dependency tree and collects all dependencies along with their paths, details, and layer information.

    Args:
        dependencies (dict): The dependency tree to parse.
        path_prefix (str): The path to the current node in the dependency tree.
        parent_name (str): The parent dependency name.
        layer (int): The current layer of the dependency.

    Returns:
        tuple: A tuple containing:
            - dict: A flat dictionary with dependency names as keys and their paths and details as values.
            - dict: A dictionary with first-layer dependencies and their detailed information including child layer counts.
    """
    dependency_paths = {}
    first_layer_dependencies = {}

    for dep_name, dep_info in dependencies.items():
        current_path = f"{path_prefix}/{dep_name}" if path_prefix else dep_name
        dep_details = {
            "version": dep_info.get("version", "unknown"),
            "resolved": dep_info.get("resolved", None),
            "overridden": dep_info.get("overridden", False),
            "paths": [current_path],
            "parent": [parent_name] if parent_name else [],
            "children": list(dep_info.get("dependencies", {}).keys()),
            "layer": layer
        }

        if layer == 0:
            # Initialize layer counts for first-layer dependencies
            dep_details["layer_counts"] = {}

            def count_children(dep_tree, dimension=1):
                if not dep_tree:
                    return
                str_dimension = str(dimension)  # Convert dimension to string
                if str_dimension not in dep_details["layer_counts"]:
                    dep_details["layer_counts"][str_dimension] = 0

                for child_name, child_info in dep_tree.items():
                    dep_details["layer_counts"][str_dimension] += 1
                    if "dependencies" in child_info:
                        count_children(child_info["dependencies"], dimension + 1)

            count_children(dep_info.get("dependencies", {}))

            first_layer_dependencies[dep_name] = dep_details

        if dep_name not in dependency_paths:
            dependency_paths[dep_name] = dep_details
        else:
            dependency_paths[dep_name]["paths"].append(current_path)
            if parent_name and parent_name not in dependency_paths[dep_name]["parent"]:
                dependency_paths[dep_name]["parent"].append(parent_name)

        if "dependencies" in dep_info:
            child_dependencies, _ = parse_dependencies(dep_info["dependencies"], current_path, dep_name, layer + 1)
            for child_name, child_details in child_dependencies.items():
                if child_name not in dependency_paths:
                    dependency_paths[child_name] = child_details
                else:
                    dependency_paths[child_name]["paths"].extend(child_details["paths"])
                    dependency_paths[child_name]["parent"] = list(set(dependency_paths[child_name]["parent"] + child_details["parent"]))

    return dependency_paths, first_layer_dependencies


# Check Lines of Code

def count_lines_of_code(repo_path):
    # List to store the number of lines in each file
    lines_of_code_info = {}

    # Walk through the repo directory
    for root, dirs, files in os.walk(repo_path):
        # Skip node_modules or any other directories you want to ignore
        if 'node_modules' in dirs:
            dirs.remove('node_modules')  # This will exclude 'node_modules' from being walked

        if '.venv' in dirs:
            dirs.remove('.venv')  # This will exclude '.venv' from being walked

        if '.git' in dirs:
            dirs.remove('.git')  # This will exclude '.git' from being walked

        if '.idea' in dirs:
            dirs.remove('.idea') # this will exclude '.idea' from being walked

        for file_name in files:
            file_path = os.path.join(root, file_name)

            # Only count lines for source code files (e.g., .js, .py, etc.)
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    lines_of_code_info[file_path] = len(lines)
            except Exception as e:
                print(f"Could not read file {file_path}: {e}")

    return lines_of_code_info

def save_json_to_db(json_data):
    with MongoClient('mongodb://admin:pass@localhost:27017/') as client:
        db = client['jenkins']

        collection = db["pipeline_data"]

        result = collection.insert_many(json_data)

        print(f"Inserted {len(result.inserted_ids)} documents into 'users' collection.")

def main():
    try:
        # Open the repository
        repo = Repo(repo_path)
        print(f"Processing data for {repo.remotes.origin.url.split('.git')[0].split('/')[-1]}", end="\n\n")

        print("Checking for last commit hash in database...")
        last_commit_hash = get_last_commit_hash()
        # last_commit_hash = None
        npm_info = {}

        if last_commit_hash:
            print(f"\tLast commit hash in database: {last_commit_hash}")
            commit_range = f"{last_commit_hash}..HEAD"
            commits = list(repo.iter_commits(commit_range))
        else:
            print("\tNo previous commit found in database. \n\tLoading all commits from repository.")
            commits = list(repo.iter_commits("HEAD"))

        first_iteration = True

        print(f"\tFound {len(commits)} commits to process.", end="\n\n")
        for commit in reversed(commits):
            repo.git.checkout(commit.hexsha)
            print(f"Processing commit: {commit.hexsha}")

            git_info = get_git_info(commit)
            print(f"Git Info: {git_info}", end="\n\n")

            print(f"Checking for package.json changes...")
            npm_change = npm_changes(commit)
            print(f"NPM Changed: {npm_change}", end="\n\n")

            if first_iteration or npm_change:
                print(f"Processing package.json changes...")
                npm_info = get_npm_info(commit)
                dependencies = npm_info.get("dependencies", {})
                print(f"Original NPM Info: {npm_info}", end="\n\n")

                # Parse the dependencies
                parsed_dependencies, first_layer_dependencies = parse_dependencies(dependencies)
                print(f"Parsed Dependencies: {parsed_dependencies}", end="\n\n")

                npm_info["dependencies"] = parsed_dependencies
                npm_info["first_layer_dependencies"] = first_layer_dependencies

            first_iteration = False

            lines_of_code_info = count_lines_of_code(repo_path)
            print(f"Lines of Code Info: {lines_of_code_info}", end="\n\n")

            combined_info = [{
                "commit_info": git_info,
                "npm_info": npm_info,
                "lines_of_code": lines_of_code_info
            }]

            save_json_to_db(combined_info)
            print(f"Saved Info: {combined_info}", end="\n\n")

        repo.git.checkout("main")

    except Exception as e:
        print("An error occurred during execution:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        raise

if __name__ == "__main__":
    main()