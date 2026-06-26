# Windows Task Scheduler Setup Guide

## How to Schedule Water Quality Agent to Run Automatically

### Step 1: Open Task Scheduler
1. Press `Win + R`
2. Type `taskschd.msc` and press Enter
3. Click "Task Scheduler Library" on the left

### Step 2: Create a New Task
1. Right-click "Task Scheduler Library" → Select "Create Task"
2. Give it a name: "Water Quality Agent"
3. Check: "Run whether user is logged in or not"

### Step 3: Set Triggers (When to Run)
1. Go to the "Triggers" tab
2. Click "New..."
3. Select "At log on" to run when you start your computer
   - Or select "On a schedule" and set to Daily at a specific time
4. Click OK

### Step 4: Set Actions (What to Run)
1. Go to the "Actions" tab
2. Click "New..."
3. Set the following:
   - **Program/script:** `C:\Users\USER\Desktop\AI_Agent_Try\run_water_agent.bat`
   - **Start in:** `C:\Users\USER\Desktop\AI_Agent_Try`
4. Click OK

### Step 5: Additional Settings (Optional)
1. Go to the "Settings" tab
2. Check "If the task fails, restart every:" and set to 1 minute
3. Check "Run task as soon as possible after a scheduled start is missed"

### Step 6: Finish
1. Click OK to create the task
2. You'll be prompted for your Windows password - enter it
3. The task is now scheduled!

## What Happens
- Every time you start your computer, the agent will automatically:
  1. Collect water quality data
  2. Generate visualization plots
  3. Save everything to `C:\Users\USER\{username}\water_quality_data\`
  4. Close automatically when done

## Output Files
- **Data:** `water_quality_records.csv` - Contains all collected data
- **Plots:** 
  - `timeline_parameters.png` - Time series of all parameters
  - `regional_comparison.png` - Comparison across regions
  - `quality_heatmap.png` - Heatmap visualization
  - `distributions.png` - Parameter distributions
  - `quality_summary.png` - Summary dashboard
- **Logs:** `agent_log.txt` - Execution logs

## To Run Manually
Double-click `run_water_agent.bat` or run from PowerShell:
```
python C:\Users\USER\Desktop\AI_Agent_Try\Claude.py
```
