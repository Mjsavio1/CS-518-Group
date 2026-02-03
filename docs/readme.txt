3. End of Lab: Sharing the "Winning" Code
Once the instructor chooses a version to keep, the "chosen" student will push their branch and merge it.
The Chosen Student runs:

# 1. Push your branch to the cloud
git push origin your-name/lab-3-1 #<--Example

# 2. Move to the main branch and merge your work
git checkout main
git merge your-name/lab-3-1 #<--Example

# 3. Update the shared repo for everyone else
git push origin main




4. Everyone Else: Syncing Up
Once the chosen code is pushed to main, everyone else needs to grab it to stay in sync:

# Switch back to the main branch
git checkout main

# Pull the new "official" code
git pull origin main