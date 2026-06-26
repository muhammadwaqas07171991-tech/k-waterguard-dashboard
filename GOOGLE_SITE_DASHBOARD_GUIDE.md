# K-Water Guard AI Dashboard on Google Sites

Google Sites cannot directly show a local file such as `C:\Users\USER\water_quality_data\dashboard.html` to other users. The dashboard must first be available at a public HTTPS URL, then that URL can be embedded in Google Sites.

## Generated Files

Each run of `Claude.py` creates this online-ready static bundle:

`C:\Users\USER\water_quality_data\google_site_dashboard\`

Important files:

- `index.html` - dashboard page to host online
- `assets\` - logo and cover image
- `plots\` - dashboard charts and spatial maps
- `data\` - latest daily CSV

## Recommended Publishing Flow

### Option A: GitHub Pages

1. On GitHub, create a new public repository.
   Suggested name:

   `k-waterguard-dashboard`

2. On your computer, open this folder:

   `C:\Users\USER\water_quality_data\google_site_dashboard\`

3. Upload the files inside that folder to the GitHub repository root.

   - `index.html`
   - `.nojekyll`
   - all `.png` files in the root of the generated folder
   - the latest `water_quality_records_YYYY-MM-DD.csv` file

   The generator also creates `assets`, `plots`, and `data` subfolders for local organization, but the GitHub Pages version now references the root-level files because GitHub web upload often places files this way.

4. In the GitHub repository, open **Settings**.

5. In the left sidebar, click **Pages**.

6. Under **Build and deployment**, set:

   - **Source**: `Deploy from a branch`
   - **Branch**: `main`
   - **Folder**: `/ (root)`

7. Click **Save**.

8. Wait a few minutes. GitHub will publish the dashboard at a URL like:

   `https://YOUR_GITHUB_USERNAME.github.io/k-waterguard-dashboard/`

9. Open that URL in your browser and confirm the dashboard loads.

10. If the page loads but images do not display, check these URLs directly in the browser:

   - `https://YOUR_GITHUB_USERNAME.github.io/k-waterguard-dashboard/quality_summary.png`
   - `https://YOUR_GITHUB_USERNAME.github.io/k-waterguard-dashboard/station_coverage_map.png`
   - `https://YOUR_GITHUB_USERNAME.github.io/k-waterguard-dashboard/ph_map_2026_06_26.png`

   If any of these show a 404 page, the corresponding file was not uploaded to the repository root.

### Add It To Google Sites

1. Open your Google Site:
   `https://sites.google.com/view/rwer/k-waterguard-ai`

2. Click **Edit**.

3. Click **Insert** > **Embed**.

4. Choose **By URL**.

5. Paste your GitHub Pages URL.

6. Resize the embedded frame to fill the page width.

7. Publish the Google Site.

### Option B: Other Static Hosting

You can also host the full `google_site_dashboard` folder on Netlify, Firebase Hosting, or Google Cloud Storage. Use the public HTTPS URL the same way in Google Sites.

## Daily Updates

After the dashboard is hosted, the daily agent run will refresh the local `google_site_dashboard` folder. To update the Google Site content automatically, sync or upload that folder to the same hosting location after each run.

Google Sites will then show the latest dashboard through the embedded URL.

## If Images Show On GitHub Pages But Not Google Sites

Use absolute GitHub Pages asset URLs in the generated dashboard.

1. Open `Claude.py`.

2. Find:

   `GITHUB_PAGES_BASE_URL = ""`

3. Set it to your real GitHub Pages URL. Example:

   `GITHUB_PAGES_BASE_URL = "https://YOUR_GITHUB_USERNAME.github.io/k-waterguard-dashboard/"`

4. Run `Claude.py` or regenerate the dashboard.

5. Re-upload the refreshed `google_site_dashboard` folder to GitHub.

6. Confirm the generated `index.html` contains URLs like:

   `https://YOUR_GITHUB_USERNAME.github.io/k-waterguard-dashboard/quality_summary.png`

7. In Google Sites, remove the old embed and add it again with:

   `https://YOUR_GITHUB_USERNAME.github.io/k-waterguard-dashboard/`
