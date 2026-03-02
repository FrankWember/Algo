# SIUE Campus Routing - Manual Data Collection Checklist

## 🎯 QUICK START GUIDE

**Goal:** Get your routing algorithm working with real data
**Minimum Data Needed:** Buildings coordinates + paths between them
**Estimated Time:** 4-6 hours for MVP

---

## ✅ STEP-BY-STEP COLLECTION PROCESS

### STEP 1: Get Building Coordinates (2-3 hours)
**Priority:** 🔴 DO THIS FIRST

#### Method A: Using OpenStreetMap (Recommended)
1. Go to https://www.openstreetmap.org/
2. Search "SIUE Edwardsville Illinois"
3. Zoom into campus
4. For EACH building in buildings.json:
   - Find the building on map
   - Right-click the building → "Show address" or "Query features"
   - Copy latitude and longitude
   - Paste into buildings.json

#### Method B: Using Google Maps
1. Go to https://www.google.com/maps
2. Search "SIUE Edwardsville"
3. For EACH building:
   - Search the building name (e.g., "Lovejoy Library SIUE")
   - Right-click on the building marker
   - Click the coordinates to copy them
   - Format: First number = latitude, Second = longitude

**Example Entry:**
```json
{
  "id": "lovejoy_library",
  "name": "Lovejoy Library",
  "latitude": 38.7897,
  "longitude": -89.9873,
  ...
}
```

**Checklist:**
- [ ] Lovejoy Library
- [ ] Morris University Center
- [ ] Engineering Building
- [ ] Rendleman Hall
- [ ] Founders Hall
- [ ] Alumni Hall
- [ ] Peck Hall
- [ ] Dunham Hall
- [ ] Science Building East
- [ ] Science Building West
- [ ] Art and Design
- [ ] Student Fitness Center
- [ ] Vadalabene Center
- [ ] Woodland Hall
- [ ] Prairie Hall
- [ ] Bluff Hall
- [ ] Evergreen Hall
- [ ] Student Success Center
- [ ] Birger Hall

---

### STEP 2: Map Walking Paths (3-4 hours)
**Priority:** 🔴 CRITICAL

#### What You're Looking For:
Which buildings can you walk directly to from each building?

#### Method:
1. Open Google Maps satellite view of SIUE
2. Zoom in close enough to see sidewalks
3. For EACH building, identify which OTHER buildings it connects to via sidewalk
4. Use Google Maps "Measure distance" tool:
   - Right-click on start point → "Measure distance"
   - Click on end point
   - Read distance at bottom of screen

**Example:** From Lovejoy Library, you can probably walk to:
- Morris University Center
- Peck Hall
- Dunham Hall
- Founders Hall

#### Fill in paths.json:
```json
{
  "id": "path_001",
  "from_building_id": "lovejoy_library",
  "to_building_id": "morris_university_center",
  "distance_meters": 450,
  "estimated_time_seconds": 321,
  "path_type": "outdoor_sidewalk",
  "slope_percent": 2,
  "stairs_count": 0
}
```

**Quick Time Calculation:**
- Average walking speed = 1.4 meters/second
- Time (seconds) = Distance (meters) / 1.4
- Example: 450m / 1.4 = 321 seconds ≈ 5.4 minutes

**Minimum Paths to Map (Start Here):**
- [ ] Lovejoy ↔ MUC
- [ ] Lovejoy ↔ Peck
- [ ] Lovejoy ↔ Dunham
- [ ] MUC ↔ Engineering
- [ ] MUC ↔ Science East
- [ ] Science East ↔ Science West
- [ ] Engineering ↔ Science East
- [ ] Peck ↔ Founders
- [ ] Founders ↔ Alumni

**Note:** You need BOTH directions if path characteristics differ
- Path A→B might have uphill slope of +5%
- Path B→A would have downhill slope of -5%

---

### STEP 3: Elevation Data (2-3 hours)
**Priority:** 🟡 HIGH (but can start testing without this)

#### Method A: Google Earth Pro (Best)
1. Download Google Earth Pro (free)
2. Navigate to SIUE campus
3. Use elevation tool:
   - Tools → Ruler → Path
   - Draw path between buildings
   - See elevation profile

#### Method B: USGS Elevation Viewer
1. Go to https://apps.nationalmap.gov/epqs/
2. Enter SIUE coordinates
3. Click on building locations
4. Record elevation

#### Method C: Approximate (Quick & Dirty)
1. Use satellite view to identify obvious hills
2. Estimate slopes:
   - Flat = 0%
   - Gentle = 2-3%
   - Noticeable = 5-7%
   - Steep = 8-12%
   - Very steep = 15%+

**Buildings to Check First:**
- [ ] Science Building East (likely on hill)
- [ ] Science Building West (likely on hill)
- [ ] Engineering Building
- [ ] Lovejoy Library (reference point)

---

### STEP 4: Accessibility Features (2-3 hours)
**Priority:** 🟡 HIGH

#### Best Method: Campus Visit
Walk around and note:
- Which entrances have stairs
- Where ramps are located
- Which buildings have elevators

#### Alternative: Google Street View
1. Use Google Maps Street View
2. "Walk" around campus virtually
3. Look for:
   - Wheelchair ramps
   - Stairs at entrances
   - Accessibility signage

#### Alternative: SIUE Accessibility Office
- Call or email SIUE Disability Support Services
- They likely have this information documented
- Ask for accessibility map or building entrance info

**Quick Checklist per Building:**
- [ ] Main entrance: stairs? ramp? automatic doors?
- [ ] Accessible entrance location (if different)
- [ ] Elevator present? (yes/no)
- [ ] Number of stairs at main entrance

---

### STEP 5: Building Hours (30 minutes)
**Priority:** 🟠 MEDIUM

#### Method:
1. Go to https://www.siue.edu/
2. Search for each building
3. Find hours of operation
4. Or call: (618) 650-2000 and ask

**Critical Buildings:**
- [ ] Lovejoy Library
- [ ] Morris University Center
- [ ] Engineering Building
- [ ] Student Fitness Center

**Why This Matters:**
If a building closes at 10 PM, you can't use indoor shortcuts through it after hours.

---

### STEP 6: Crowd Data (1 hour - Synthetic)
**Priority:** 🟢 LOW (use defaults)

You can GENERATE this rather than collect it:

**Assumptions:**
- Classes change every hour (50-minute classes + 10-minute passing)
- Rush hours: 10 minutes before and after each hour
- Peak times: 10 AM, 11 AM (most scheduled classes)
- Quiet times: Before 8 AM, after 5 PM

**Just use the rush_hours in schedules.json as-is**

---

## 🎯 PRIORITY ORDER FOR YOUR PROJECT

### Week 1: Minimum Viable Product
**Goal:** Get basic routing working

1. ✅ Building list (DONE)
2. ⏳ Building coordinates (2-3 hours) ← START HERE
3. ⏳ Major walking paths (3-4 hours)
4. ⏳ Basic distance estimates

**Deliverable:** Dijkstra's algorithm can find shortest path

---

### Week 2: Multi-Objective Routing
**Goal:** Add preferences and trade-offs

5. ⏳ Elevation data (2-3 hours)
6. ⏳ Stairs count (1-2 hours)
7. ⏳ Accessibility features (2-3 hours)

**Deliverable:** Dynamic programming returns multiple route options

---

### Week 3: Time-Dependent Routing
**Goal:** Account for schedules

8. ⏳ Building hours (30 minutes)
9. ⏳ Class schedule (use synthetic data)
10. ⏳ Rush hour definitions (use defaults)

**Deliverable:** Divide & Conquer handles time windows

---

### Week 4: Polish & Testing
11. ⏳ Validate all data
12. ⏳ Test edge cases
13. ⏳ (Optional) Add shuttle data

---

## 📝 DATA VALIDATION CHECKLIST

Before running your algorithms, verify:

- [ ] All 19 buildings have coordinates
- [ ] Coordinates are in correct format (latitude, longitude)
- [ ] All buildings have at least 2 connecting paths
- [ ] Path distances are reasonable (100m - 1000m typically)
- [ ] Paths are bidirectional where appropriate
- [ ] No isolated buildings (all connected to graph)
- [ ] Elevation data makes sense (no building at -50m)
- [ ] Stairs counts are integers >= 0

---

## 🚀 QUICK TEST DATA

Can't collect everything yet? Use this minimal dataset to test:

```json
{
  "buildings": [
    {"id": "a", "name": "Lovejoy Library", "lat": 38.7897, "lon": -89.9873},
    {"id": "b", "name": "MUC", "lat": 38.7902, "lon": -89.9868},
    {"id": "c", "name": "Engineering", "lat": 38.7905, "lon": -89.9863}
  ],
  "paths": [
    {"from": "a", "to": "b", "distance": 450, "time": 321, "stairs": 0},
    {"from": "b", "to": "a", "distance": 450, "time": 321, "stairs": 0},
    {"from": "b", "to": "c", "distance": 380, "time": 271, "stairs": 12},
    {"from": "c", "to": "b", "distance": 380, "time": 271, "stairs": 0}
  ]
}
```

This gives you enough to:
- Test graph construction
- Test Dijkstra's algorithm
- Test path finding
- Test accessibility routing (note the stairs difference)

---

## 💡 PRO TIPS

1. **Start Small:** Get 3-5 buildings working first, then expand
2. **Focus on Academic Core:** Lovejoy, MUC, Engineering, Science buildings
3. **Estimate When Stuck:** Better to have approximate data than no data
4. **Verify with Reality:** Do the walking times make sense?
5. **Document Assumptions:** Note where you estimated vs measured
6. **Version Control:** Save incremental versions of JSON files

---

## 📊 CURRENT STATUS TRACKER

Update this as you complete each section:

| Task | Status | Completion % | Hours Spent | Notes |
|------|--------|--------------|-------------|-------|
| Building coordinates | ⏳ Not Started | 0% | 0 | |
| Walking paths | ⏳ Not Started | 0% | 0 | |
| Elevation data | ⏳ Not Started | 0% | 0 | |
| Accessibility | ⏳ Not Started | 0% | 0 | |
| Building hours | ⏳ Not Started | 0% | 0 | |
| Crowd data | ⏳ Not Started | 0% | 0 | |

**Overall Project Completion: 5%**

Last Updated: 2026-02-03

