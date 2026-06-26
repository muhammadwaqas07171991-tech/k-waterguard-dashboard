# Hourly Google Sites Dashboard Setup

This project is ready for this flow:

GitHub Actions runs `Claude.py` every hour, GitHub Pages publishes the generated dashboard, and Google Sites embeds the GitHub Pages URL.

## 1. Push These Files To GitHub

Push the whole project folder to this repository:

```text
https://github.com/muhammadwaqas07171991-tech/k-waterguard-dashboard
```

The important new files are:

```text
.github/workflows/update-dashboard-pages.yml
requirements.txt
```

## 2. Enable GitHub Pages

In GitHub:

1. Open the repository.
2. Go to `Settings`.
3. Go to `Pages`.
4. Under `Build and deployment`, set `Source` to `GitHub Actions`.
5. Save.

## 3. Run The First Update

In GitHub:

1. Go to `Actions`.
2. Open `Update Water Dashboard Pages`.
3. Click `Run workflow`.

After it finishes, your dashboard URL should be:

```text
https://muhammadwaqas07171991-tech.github.io/k-waterguard-dashboard/
```

The workflow also runs automatically every hour at minute 7 UTC.

## 4. Embed In Google Sites

In Google Sites:

1. Open your site editor.
2. Choose `Insert`.
3. Choose `Embed`.
4. Paste the GitHub Pages URL:

```text
https://muhammadwaqas07171991-tech.github.io/k-waterguard-dashboard/
```

5. Insert it and publish the Google Site.

After this, you do not need to manually update Google Sites. The embedded page will show the latest GitHub Pages dashboard after each hourly workflow run.
