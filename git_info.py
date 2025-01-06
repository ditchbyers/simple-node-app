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
            latest_commit = collection.find_one(sort=[("_id", pymongo.ASCENDING)], limit=1)["commit_info"]["commit_hash"]
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
            os.system(r'rmdir /s /q "node_modules"')

        # Delete package-lock
        if os.path.exists("package-lock.json"):
            os.system(r'del "package-lock.json"')

        # Install all dependencies
        os.system(r'npm install --silent')
        # os.system(r'npm audit fix --force --silent')


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

def main():
    try:
        # Open the repository
        repo = Repo(repo_path)
        print(f"Processing data for {repo.remotes.origin.url.split('.git')[0].split('/')[-1]}", end="\n\n")

        print("Checking for last commit hash in database...")
        # Get the last commit hash from the database
        last_commit_hash = get_last_commit_hash()
        last_commit_hash = None

        if last_commit_hash:
            print(f"\tLast commit hash in database: {last_commit_hash}")
            commit_range = f"{last_commit_hash}..HEAD"
            commits = list(repo.iter_commits(commit_range))
        else:
            print("\tNo previous commit found in database. \n\tLoading all commits from repository.")
            commits = list(repo.iter_commits("HEAD"))

        print(f"\tFound {len(commits)} commits to process.", end="\n\n")
        for commit in reversed(commits):
            print(f"Processing commit: {commit.hexsha}")
            repo.git.checkout(commit.hexsha)

            git_info = get_git_info(commit)
            print(f"Git Info: {git_info}", end="\n\n")

            print(f"Checking for package.json changes...")
            npm_change = npm_changes(commit)
            print(f"NPM Changed: {npm_change}", end="\n\n")

            if npm_change:
                print(f"Processing package.json changes...")
                npm_info = get_npm_info(commit)
                print(f"NPM Info: {npm_info}", end="\n\n")



    except Exception as e:
        print("An error occurred during execution:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        raise

if __name__ == "__main__":
    main()