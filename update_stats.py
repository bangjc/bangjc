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
    # 1. Ambil data User info
    user_data = fetch_rest("https://api.github.com/user")
    if not user_data:
        exit(1)
    
    username = user_data["login"]
    followers = user_data["followers"]
    following = user_data["following"]

    # 2. Ambil data Repositories
    repos_data = fetch_rest("https://api.github.com/user/repos?per_page=100&affiliation=owner,organization_member,collaborator")
    total_repos_count = len(repos_data) if repos_data else 0
    public_repos_count = sum(1 for r in repos_data if not r.get("private", False)) if repos_data else 0
    private_repos_count = sum(1 for r in repos_data if r.get("private", True)) if repos_data else 0
    total_stars = sum(r.get("stargazers_count", 0) for r in repos_data) if repos_data else 0

    # 3. Hitung Total Issue & PR secara keseluruhan vs yang berstatus OPEN
    # Total keseluruhan issue buatan user
    all_issues_search = fetch_rest(f"https://api.github.com/search/issues?q=type:issue+author:{username}")
    total_issues = all_issues_search.get("total_count", 0) if all_issues_search else 0

    # Total issue buatan user yang statusnya OPEN saja
    open_issues_search = fetch_rest(f"https://api.github.com/search/issues?q=type:issue+author:{username}+state:open")
    open_issues = open_issues_search.get("total_count", 0) if open_issues_search else 0

    # Format string Open / Total (misal: "5/1900" atau tersimpan sebagai teks/angka)
    issues_display = f"{open_issues}/{total_issues}"

    # Sama halnya untuk PR jika ingin format serupa (opsional, di sini kita ambil total PR biasa)
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
            "total_commits": 0,
            "total_stars_received": total_stars,
            "total_pull_requests": script_total_prs,
            "pull_request_reviews": 0,
            "total_issues": issues_display  # Format "Open/Total"
        },
        "languages": language_percentages
    }
    
    # 5. Ambil data Bahasa Pemrograman dari semua Repositories
    language_counts = {}
    
    if repos_data:
        for repo in repos_data:
            # Lewatkan jika repo fork atau kosong (opsional, sesuaikan kebutuhan)
            langs_url = repo.get("languages_url")
            if langs_url:
                langs_data = fetch_rest(langs_url)
                if langs_data:
                    for lang, bytes_count in langs_data.items():
                        language_counts[lang] = language_counts.get(lang, 0) + bytes_count

    # Hitung total bytes semua bahasa untuk dijadikan persentase
    total_bytes = sum(language_counts.values())
    language_percentages = {}
    
    if total_bytes > 0:
        # Urutkan dari bahasa yang paling banyak digunakan ke yang paling sedikit
        sorted_langs = sorted(language_counts.items(), key=lambda x: x[1], reverse=True)
        for lang, bytes_count in sorted_langs:
            percentage = (bytes_count / total_bytes) * 100
            language_percentages[lang] = round(percentage, 2) # Dibulatkan 2 desimal

    # Simpan ke stats.json
    with open("stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4)
    print(f"stats.json updated successfully! Issues (Open/Total): {issues_display}")

    # Otomatis update angka di dalam URL badge README.md
    readme_path = "README.md"
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()

        content = re.sub(r'(badge/Stars-)\d+(-)', r'\g<1>' + str(stats["contributions"]["total_stars_received"]) + r'\2', content)
        content = re.sub(r'(badge/Repos-)\d+(-)', r'\g<1>' + str(stats["repositories"]["total_repos"]) + r'\2', content)
        content = re.sub(r'(badge/PRs-)\d+(-)', r'\g<1>' + str(stats["contributions"]["total_pull_requests"]) + r'\2', content)
        
        # Untuk badge Issues yang berupa teks gabungan (Open/Total), sesuaikan penggantian registernya:
        content = re.sub(r'(badge/Issues-)[^?-]+(-)', r'\g<1>' + str(issues_display).replace('/', '%2F') + r'\2', content)

        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("README.md badges updated successfully!")

except Exception as e:
    print(f"An error occurred: {e}")