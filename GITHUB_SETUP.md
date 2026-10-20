# Put the project on GitHub and run the CI gate (about 20 minutes)

1. Create an empty repository on github.com (New repository, no README), e.g. `api-testing-platform`.
2. In PowerShell, from the unzipped project folder:
       git init
       git add .
       git commit -m "AI-powered API testing platform: Review 3"
       git branch -M main
       git remote add origin https://github.com/<your-username>/api-testing-platform.git
       git push -u origin main
3. Open the repository on GitHub > Actions tab. If asked, click "I understand my workflows, enable them".
4. Pick "API quality gate" > "Run workflow" > main. It runs two jobs (httpbin, chroma), about 5 minutes each.
5. A green run = the gate passed (no NEW actionable findings against ci/accepted_findings.json). Take a screenshot.
6. Show a FAILING run too: edit ci/accepted_findings.json, delete one fingerprint line under "chroma", commit, push.
   The "chroma" job turns red and lists the finding as NEW. Screenshot it, then restore the file.
If a job fails for another reason (install or startup error), open the job log and send me the red lines.
