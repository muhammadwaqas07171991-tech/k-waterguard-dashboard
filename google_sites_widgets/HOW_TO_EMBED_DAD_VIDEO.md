# How to Upload and Embed the DAD Analysis Video on Your Google Site

This guide provides step-by-step instructions to embed the **Depth–Area–Duration (DAD) Analysis** video animation along with the **interactive high-definition keyframe screens gallery (with click-to-enlarge lightbox modal)** on your Google Site (`https://sites.google.com/view/rwer/home` or any research page).

---

## ⚡ Option 1: Interactive HTML Embed Widget (Recommended)

This widget embeds:
1. **The 50-second scientific animation** with high-definition video player, controls, and HUD overlay.
2. **7 Keyframe Stage Cards** demonstrating each stage of the analysis.
3. **Interactive Click-to-Enlarge Lightbox Modal**: When any screen is clicked, it opens in full resolution (1080p) with in-depth captions, next/previous buttons, and keyboard navigation (`←`, `→`, `Esc`).
4. **Hydrological principles summary** and topic tags.

### ⏱️ Quick Setup (Takes ~1 minute):

1. **Open your Google Site editor**:
   - Navigate to: **[https://sites.google.com/view/rwer/home](https://sites.google.com/view/rwer/home)** (or open your Google Sites editor and choose your desired page).

2. **Click Embed**:
   - In the right-hand panel, select the **Insert** tab.
   - Click the **Embed** button (`< >` icon).
   - Select the **Embed code** tab (not "By URL").

3. **Copy & Paste the Widget Code**:
   - Open [`google_sites_widgets/widget_dad_analysis.html`](file:///c:/Users/USER/Desktop/Modeling%20work/AI_Water_Guard_Dashboard_All_Files/google_sites_widgets/widget_dad_analysis.html).
   - Select everything (`Ctrl + A`) and copy (`Ctrl + C`).
   - Paste it into the Google Sites **Embed code** text box.
   - Click **Next**, verify the preview, and click **Insert**.

4. **Adjust Width and Height**:
   - Click on the newly inserted widget box.
   - Drag the blue circles on the left and right borders so it spans the **full width** of your page.
   - Drag the bottom handle downward to give enough vertical space so the video, screens grid, and details fit smoothly without an awkward internal scrollbar (recommended height: ~950px to 1100px).

5. **Publish**:
   - Click the purple/blue **Publish** button at the top right of Google Sites!

---

## 📁 Option 2: Direct Google Drive Video Upload

If you also want Google's native video player directly inside Google Sites:

1. **Upload `DAD.mp4` to Google Drive**:
   - Open [Google Drive](https://drive.google.com/).
   - Upload `DAD.mp4` (located on your Desktop: `C:\Users\USER\Desktop\DAD.mp4` or in `AI_Water_Guard_Dashboard_All_Files`).
   - Once uploaded, right-click the video > **Share** > change General Access to **"Anyone with the link can view"**.

2. **Insert via Google Sites**:
   - In your Google Sites editor, go to **Insert** > **Drive**.
   - Select your uploaded `DAD.mp4` file and click **Insert**.
   - Resize and position it where you want on the page.

---

## 🖼️ Screens Gallery Included in the Widget

The widget features 7 keyframe screens extracted directly from the animation. Users can click any screen to view it in full screen / large view:

1. **Stage 01: Spatial Rainfall Variation across Watershed**  
   Peak precipitation intensity ($140\text{ mm/hr}$), runoff flow ($115\text{ m}^3\text{/s}$), and topographic storm core.
2. **Stage 02: Concentric Isohyetal Monitoring Zones**  
   Isohyetal delineation radiating outward: Zone I ($100\text{ km}^2$), Zone II ($200\text{ km}^2$), Zone III ($2,100\text{ km}^2$).
3. **Stage 03: Telemetric Rain Gauge Sensor Array**  
   Optical digital rain gauges logging spot rain depths ($59\text{ mm}$, $157\text{ mm}$, $159\text{ mm}$).
4. **Stage 04: Watershed Hydrology & Area-Weighted Averaging**  
   Spatial distribution model computing areal weighted mean depth over expanding catchment boundaries.
5. **Stage 05: 3D DAD Analysis Results Matrix**  
   Glassmorphic 3D matrix table showing maximum rainfall depth across durations ($2\text{h}$, $4\text{h}$, $6\text{h}$) and areas ($100$, $300$, $600\text{ km}^2$).
6. **Stage 06: Depth–Area–Duration (DAD) Curves Formulation**  
   Semi-logarithmic curves demonstrating rainfall attenuation across expanding catchment area ($1\text{ to }20,000\text{ km}^2$).
7. **Stage 07: Watershed Telemetry & Field Validation**  
   Field telemetry observation over the Namgang basin ($4\text{h}$, $300\text{ km}^2$) validating empirical curves.

---

## 🌐 Public CDN Video & Image URLs

Once the repository is pushed to GitHub, all media is available via high-speed CDN:

- **Optimized 1080p Video Stream:**  
  `https://muhammadwaqas07171991-tech.github.io/k-waterguard-dashboard/assets/videos/dad_analysis_animation.mp4`
- **Screens Directory:**  
  `https://muhammadwaqas07171991-tech.github.io/k-waterguard-dashboard/assets/images/dad_screens/`
