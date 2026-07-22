import os
import json
import urllib.request
import urllib.error
import re

token = os.environ.get("GITHUB_TOKEN")

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

def fetch_rest(url):
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP Error on {url}: {e.code} - {e.read().decode()}")
        return None

try:
    # 1. Ambil data User info (followers, following, login) via REST
    user_data = fetch_rest("https://api.github.com/user")
    if not user_data:
        exit(1)
    
    username = user_data["login"]
    followers = user_data["followers"]
    following = user_data["following"]

    # 2. Ambil data Repositories (untuk hitung total repo & stars)
    repos_data = fetch_rest("https://api.github.com/user/repos?per_page=100&affiliation=owner,organization_member,collaborator")
    total_repos_count = len(repos_data) if repos_data else 0
    public_repos_count = sum(1 for r in repos_data if not r.get("private", False)) if repos_data else 0
    private_repos_count = sum(1 for r in repos_data if r.get("private", True)) if repos_data else 0
    total_stars = sum(r.get("stargazers_count", 0) for r in repos_data) if repos_data else 0

    # 3. Hitung akurat Issue & PR menggunakan GitHub Search API (Mendukung ribuan data & private org!)
    # q=type:issue author:USERNAME
    issues_search = fetch_rest(f"https://api.github.com/search/issues?q=type:issue+author:{username}")
    total_issues_count = issues_search.get("total_count", 0) if issues_search else 0

    prs_search = fetch_rest(f"https://api.github.com/search/issues?q=type:pr+author:{username}")
    script_total_prs = prs_search.get("total_count", 0) if prs_search else 0

    # 4. Susun data JSON
    stats = {
        "profile": {
            "username": username,
            "followers": followers,
            "following": following
        },
        "repositories": {
            "total_repos": total_repos_count,
            "public_repos": public_repos_count,
            "private_repos": private_repos_count
        },
        "contributions": {
            "total_commits": 0, # Bisa disesuaikan jika ingin pakai kontribusi lain
            "total_stars_received": total_stars,
            "total_pull_requests": script_total_prs,
            "pull_request_reviews": 0,
            "total_issues": total_issues_count
        }
    }

    # Simpan ke stats.json
    with open("stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4)
    print(f"stats.json updated successfully! Issues found: {total_issues_count}")

    # Otomatis update angka di dalam URL badge README.md
    readme_path = "README.md"
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()

        content = re.sub(r'(badge/Stars-)\d+(-)', r'\g<1>' + str(stats["contributions"]["total_stars_received"]) + r'\2', content)
        content = re.sub(r'(badge/Repos-)\d+(-)', r'\g<1>' + str(stats["repositories"]["total_repos"]) + r'\2', content)
        content = re.sub(r'(badge/PRs-)\d+(-)', r'\g<1>' + str(stats["contributions"]["total_pull_requests"]) + r'\2', content)
        content = re.sub(r'(badge/Issues-)\d+(-)', r'\g<1>' + str(stats["contributions"]["total_issues"]) + r'\2', content)

        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("README.md badges updated successfully!")

except Exception as e:
    print(f"An error occurred: {e}")