# How to Embed the MBC Gyeongnam Video on Your Google Site Home Page

This guide explains how to add the **MBC Gyeongnam (MBC경남) News Broadcast** video to your Google Site home page (`https://sites.google.com/view/rwer/home`) with a modern, responsive, and well-aligned layout.

---

## ⚡ Option 1: High-Tech HTML Embed Widget (Recommended)

This gives you a branded, modern broadcast card with a cyan-neon glowing border, TV news badge, metadata cards, and full interactive controls.

### ⏱️ Takes less than 1 minute:

1. **Open your Google Site editor**:
   - Go to: **[https://sites.google.com/view/rwer/home](https://sites.google.com/view/rwer/home)** (or open your Google Sites editor and navigate to the **Home** page).

2. **Click Embed**:
   - In the right-hand panel, click the **Insert** tab.
   - Click **Embed** (the `< >` icon).
   - Select the **Embed code** tab (not "By URL").

3. **Copy & Paste the Widget Code**:
   - Open [`google_sites_widgets/widget_mbc_broadcast.html`](file:///c:/Users/USER/Desktop/Modeling%20work/AI_Water_Guard_Dashboard_All_Files/google_sites_widgets/widget_mbc_broadcast.html).
   - Copy **everything** inside that file (`Ctrl+A`, then `Ctrl+C`).
   - Paste it into the Google Sites **Embed code** text area.
   - Click **Next**, preview the player, and click **Insert**.

4. **Align & Resize**:
   - Click on the newly inserted box.
   - Drag the blue sizing circles on the left and right edges so the card fills the full width of your page.
   - Drag the bottom handle downward until the video, metadata cards, and buttons are fully visible without any internal scrollbars (recommended height: ~780px to 850px).
   - Position it right below your hero section or research highlights.

5. **Publish**:
   - Click the purple/blue **Publish** button at the top right of Google Sites!

---

## 📁 Option 2: Direct Google Drive Video Upload

If you prefer using Google's native video player:

1. **Upload to Google Drive**:
   - Open [Google Drive](https://drive.google.com/).
   - Upload `MBC경남).mp4` (or `mbc_gyeongnam_news.mp4`).
   - Right-click the uploaded video > **Share** > **Share** > change General Access to **"Anyone with the link can view"**.

2. **Insert into Google Sites**:
   - In Google Sites editor, go to **Insert** > **Drive**.
   - Select your uploaded MBC video and click **Insert**.
   - Drag the corners to align it centered on the page.

---

## 🌐 Public CDN Video URLs

The video has been uploaded and pushed to your GitHub repositories, meaning it is permanently hosted with high-speed CDN delivery:

- **Primary Streaming URL:**  
  `https://muhammadwaqas07171991-tech.github.io/rwesl-/assets/videos/mbc_gyeongnam_news.mp4`
- **Secondary Backup URL:**  
  `https://muhammadwaqas07171991-tech.github.io/k-waterguard-dashboard/assets/videos/mbc_gyeongnam_news.mp4`

Both URLs support HTTP Range requests for instant scrubbing, playback, and high-definition mobile streaming.
