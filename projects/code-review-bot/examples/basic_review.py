"""Example: Basic code review with diff input."""

from bot.code_reviewer import CodeReviewer
from bot.report_generator import ReportGenerator

# Sample diff with intentional issues
SAMPLE_DIFF = """--- a/app/auth.py
+++ b/app/auth.py
@@ -10,6 +10,15 @@
 import hashlib
 import random

+DB_PASSWORD = "admin123"
+
+def authenticate(username, password):
+    query = "SELECT * FROM users WHERE username='" + username + "'"
+    cursor.execute(query)
+    user = cursor.fetchone()
+    if user and user.password == password:
+        return True
+    return False

 def generate_token():
     return random.randint(100000, 999999)
"""


def main():
    reviewer = CodeReviewer(model="qwen-plus")

    print("🔍 Starting code review...\n")

    result = reviewer.review_diff(
        diff_text=SAMPLE_DIFF,
        language="python",
        rules=["security", "performance", "best-practices"],
    )

    # Print as markdown
    print(ReportGenerator.generate(result, fmt="markdown"))

    # Save as HTML
    html = ReportGenerator.generate(result, fmt="html")
    with open("review_report.html", "w") as f:
        f.write(html)
    print("\n📄 HTML report saved to review_report.html")


if __name__ == "__main__":
    main()
