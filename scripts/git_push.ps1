$env:GIT_EDITOR = 'true'
git rebase --quit
git reset --hard HEAD
git pull origin main
git add .
git commit -m "Fix authentication and API integration - resolved conflicts"
git push origin main
