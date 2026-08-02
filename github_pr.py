"""
Opens a GitHub Pull Request with a generated fix. Auto-merges if risk is
LOW, leaves it open for human review if risk is HIGH.

Requires:
    - GITHUB_TOKEN environment variable set to your personal access token
      (in cmd: set GITHUB_TOKEN=your_token_here)
    - REPO_NAME below changed to your actual repo, e.g. "victoiren79/lineagepilot"

Run standalone to test (will actually open a real PR on your repo):
    py -3.11 github_pr.py
"""
import os
import time
from github import Github, Auth
from dotenv import load_dotenv

load_dotenv()

REPO_NAME = "victoiren79-hash/lineagepilot"  


def open_pr(file_path: str, fixed_content: str, risk: str, reasoning: str,
            old_column: str, new_column: str) -> dict:
    """
    Opens a PR with the fixed file content on a new branch.
    Returns {"pr_url": "...", "status": "auto-merged" | "pending review"}
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN environment variable is not set.")

    gh = Github(auth=Auth.Token(token))
    repo = gh.get_repo(REPO_NAME)

    base_branch = repo.default_branch
    base_sha = repo.get_branch(base_branch).commit.sha

    branch_name = f"auto-fix-{file_path.replace('/', '-')}-{int(time.time())}"
    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_sha)

    # Try to update the existing file; if it doesn't exist yet in the repo, create it.
    try:
        existing = repo.get_contents(file_path, ref=base_branch)
        repo.update_file(
            path=file_path,
            message=f"Auto-fix: {old_column} -> {new_column} in {file_path}",
            content=fixed_content,
            sha=existing.sha,
            branch=branch_name,
        )
    except Exception:
        repo.create_file(
            path=file_path,
            message=f"Auto-fix: {old_column} -> {new_column} in {file_path}",
            content=fixed_content,
            branch=branch_name,
        )

    pr_body = (
        f"**Automated fix from LineagePilot**\n\n"
        f"Column `{old_column}` was renamed to `{new_column}` upstream.\n\n"
        f"**Risk level:** {risk}\n"
        f"**Reasoning:** {reasoning}\n"
    )

    pr = repo.create_pull(
        title=f"[LineagePilot] Fix {file_path} for {old_column} -> {new_column}",
        body=pr_body,
        head=branch_name,
        base=base_branch,
    )

    if risk == "LOW":
        try:
            pr.merge(merge_method="squash")
            status = "auto-merged"
        except Exception as e:
            status = f"auto-merge failed ({e}), left open for review"
    else:
        pr.create_issue_comment(
            f"This PR needs manual review: {reasoning}"
        )
        status = "pending review"

    return {"pr_url": pr.html_url, "status": status}


if __name__ == "__main__":
    with open("models/stg_orders_v2.sql") as f:
        content = f.read()
    fixed = content.replace("user_id", "customer_id as user_id", 1)
    result = open_pr(
        file_path="models/stg_orders_v2.sql",
        fixed_content=fixed,
        risk="LOW",
        reasoning="Test run from github_pr.py standalone test.",
        old_column="user_id",
        new_column="customer_id",
    )
    print(result)
