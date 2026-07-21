import os
import json
import urllib.request
import urllib.error

username = "bangjc"
token = os.environ.get("GITHUB_TOKEN")

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "Accept": "application/vnd.github+json"
}

# Query GraphQL untuk mengambil data menyeluruh (termasuk private & organisasi jika token mendukung)
graphql_query = {
    "query": """
    query {
      user(login: "%s") {
        followers {
          totalCount
        }
        following {
          totalCount
        }
        repositories(first: 100, ownerAffiliations: [OWNER, ORGANIZATION_MEMBER, COLLABORATOR]) {
          totalCount
          nodes {
            isPrivate
            stargazerCount
          }
        }
        contributionsCollection {
          totalCommitContributions
          totalPullRequestContributions
          totalPullRequestReviewContributions
          totalIssueContributions
        }
      }
    }
    """ % username
}

req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps(graphql_query).encode("utf-8"),
    headers=headers,
    method="POST"
)

try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode())
        
        if "errors" in result:
            print("GraphQL Errors:", result["errors"])
            exit(1)
            
        data = result["data"]["user"]
        
        # Ekstraksi metrik
        repos = data["repositories"]["nodes"]
        total_repos_count = data["repositories"]["totalCount"]
        public_repos_count = sum(1 for r in repos if not r["isPrivate"])
        private_repos_count = sum(1 for r in repos if r["isPrivate"])
        total_stars = sum(r["stargazerCount"] for r in repos)
        
        contributions = data["contributionsCollection"]
        
        # Susun struktur data JSON lengkap
        stats = {
            "profile": {
                "username": username,
                "followers": data["followers"]["totalCount"],
                "following": data["following"]["totalCount"]
            },
            "repositories": {
                "total_repos": total_repos_count,
                "public_repos": public_repos_count,
                "private_repos": private_repos_count
            },
            "contributions": {
                "total_commits": contributions["totalCommitContributions"],
                "total_stars_received": total_stars,
                "total_pull_requests": contributions["totalPullRequestContributions"],
                "pull_request_reviews": contributions["totalPullRequestReviewContributions"],
                "total_issues": contributions["totalIssueContributions"]
            }
        }

        # Simpan ke file stats.json
        with open("stats.json", "w") as f:
            json.dump(stats, f, indent=4)
            
        print("stats.json successfully updated with comprehensive data (Public, Private, & Organization context)!")

except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} - {e.reason}")
    print(e.read().decode())
except Exception as e:
    print(f"An error occurred: {e}")
