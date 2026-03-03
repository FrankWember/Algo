# SIUE Campus Routing - Data Inventory & Collection Guide

## 📊 CURRENT DATA STATUS

### ✅ DATA YOU HAVE RIGHT NOW

#### 1. **Building List** (From your React code)
**Status:** ✅ COMPLETE
**Source:** Extracted from your application code
**Count:** 19 buildings

```
- Lovejoy Library
- Morris University Center
- Engineering Building
- Rendleman Hall
- Founders Hall
- Alumni Hall
- Peck Hall
- Dunham Hall
- Science Building East
- Science Building West
- Art and Design
- Student Fitness Center
- Vadalabene Center
- Woodland Hall
- Prairie Hall
- Bluff Hall
- Evergreen Hall
- Student Success Center
- Birger Hall
```

#### 2. **Parking Lots** (From campus map PDF)
**Status:** ✅ PARTIAL
**Source:** Campus Core Map PDF
**Data Available:**
- Lot identifiers: A, B, C, D, E, F, G, P1-P12, BH, EH, PH, WH
- Parking tag requirements (Green, Orange, Yellow, Brown, Blue)
- Pay-by-space information
- Visitor parking locations (Lots B, C)

#### 3. **Campus Map Reference Points** (From PDF)
**Status:** ✅ PARTIAL - Need coordinates
**Known Locations:**
- Swimming Pool
- Outdoor Recreational Sports Complex
- Physics Observatory
- The Gardens
- "The 'e' Sculpture"
- Dental Clinic
- Technology and Management Center
- Chamber of Commerce
- School of Pharmacy Lab
- Research Drive addresses (100, 95, 47, 110, 200 University Park)

---

## ❌ DATA YOU NEED TO COLLECT MANUALLY

### 🎯 CRITICAL (Must Have for Basic Functionality)

#### 1. **Building Coordinates (Lat/Long)**
**Status:** ❌ MISSING
**Priority:** 🔴 CRITICAL
**Method:** Manual extraction from OpenStreetMap or Google Maps
**Format Needed:**
```json
{
  "building_name": "Lovejoy Library",
  "latitude": 38.XXXX,
  "longitude": -89.XXXX
}
```
**Progress:** 0/19 buildings
**Estimated Time:** 2-3 hours

---

#### 2. **Walking Paths Between Buildings**
**Status:** ❌ MISSING
**Priority:** 🔴 CRITICAL
**What to Collect:**
- Path connections (which buildings connect to which)
- Distance in meters for each path
- Path type (outdoor sidewalk, indoor hallway, covered walkway)

**Format Needed:**
```json
{
  "from": "Lovejoy Library",
  "to": "Morris University Center",
  "distance_meters": 450,
  "path_type": "outdoor_sidewalk",
  "estimated_time_seconds": 360
}
```
**Progress:** 0/??? paths
**Estimated Time:** 4-6 hours

---

#### 3. **Elevation Data for Each Building/Path**
**Status:** ❌ MISSING
**Priority:** 🟡 HIGH
**What to Collect:**
- Elevation in meters for each building entrance
- Slope/incline for each path (percentage or degrees)

**Format Needed:**
```json
{
  "building": "Engineering Building",
  "elevation_meters": 140,
  "entrance_points": [
    {"name": "main", "elevation": 140},
    {"name": "east", "elevation": 138}
  ]
}
```
**Source:** Google Earth, USGS elevation data, or manual site survey
**Estimated Time:** 3-4 hours

---

### 🎯 IMPORTANT (Needed for Core Features)

#### 4. **Accessibility Features**
**Status:** ❌ MISSING
**Priority:** 🟡 HIGH
**What to Collect for Each Building:**
- Number of stairs at each entrance
- Elevator availability (yes/no)
- Ramp availability and slope
- Accessible entrances (which ones)
- Automatic doors

**Format Needed:**
```json
{
  "building": "Lovejoy Library",
  "elevators": 2,
  "accessible_entrances": ["west", "main"],
  "stairs_at_main": 12,
  "ramps": [
    {"location": "west", "slope_percent": 5}
  ]
}
```
**Progress:** 0/19 buildings
**Estimated Time:** 6-8 hours (may require campus visit)

---

#### 5. **Building Operating Hours**
**Status:** ❌ MISSING
**Priority:** 🟠 MEDIUM
**What to Collect:**
- Opening/closing times for each building
- Weekend hours
- Special hours during breaks

**Format Needed:**
```json
{
  "building": "Morris University Center",
  "weekday_hours": {"open": "06:00", "close": "23:00"},
  "weekend_hours": {"open": "08:00", "close": "20:00"},
  "indoor_path_available": true
}
```
**Source:** SIUE website
**Estimated Time:** 1-2 hours

---

#### 6. **Class Schedule Data** (For Crowd Prediction)
**Status:** ❌ MISSING
**Priority:** 🟠 MEDIUM
**What to Collect:**
- Typical class start times (e.g., 8:00, 9:00, 10:00, etc.)
- Buildings with high class density
- Peak transition times

**Format Needed:**
```json
{
  "class_times": ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"],
  "high_traffic_buildings": ["Engineering Building", "Science Building East"],
  "rush_windows": [
    {"start": "09:50", "end": "10:10"},
    {"start": "10:50", "end": "11:10"}
  ]
}
```
**Source:** SIUE registrar or synthetic data
**Estimated Time:** 2-3 hours

---

### 🎯 NICE TO HAVE (Enhanced Features)

#### 7. **Shuttle Information**
**Status:** ❌ MISSING
**Priority:** 🟢 LOW (Can add later)
**What to Collect:**
- Shuttle stop locations
- Route numbers
- Schedule/frequency
- Operating hours

**Format Needed:**
```json
{
  "stop_name": "MUC Shuttle Stop",
  "latitude": 38.XXXX,
  "longitude": -89.XXXX,
  "routes": ["Red Line"],
  "schedule": {
    "weekday": ["07:00", "07:15", "07:30"]
  }
}
```
**Source:** SIUE Transportation website
**Estimated Time:** 2-3 hours

---

#### 8. **Weather/Seasonal Factors**
**Status:** ❌ MISSING
**Priority:** 🟢 LOW
**What to Consider:**
- Covered vs exposed paths
- Indoor connection availability

---

#### 9. **Construction/Closure Data**
**Status:** ❌ MISSING
**Priority:** 🟢 LOW
**Note:** This would be real-time data, not needed for initial prototype

---

## 📋 RECOMMENDED DATA COLLECTION WORKFLOW

### Phase 1: Core Graph Structure (Week 1)
1. ✅ Building list (DONE)
2. ❌ Get coordinates for all 19 buildings
3. ❌ Map major walking paths between buildings
4. ❌ Estimate distances for each path

### Phase 2: Physical Characteristics (Week 2)
5. ❌ Collect elevation data
6. ❌ Document stairs/slopes
7. ❌ Note accessibility features

### Phase 3: Temporal Data (Week 3)
8. ❌ Building hours
9. ❌ Class schedule patterns
10. ❌ Synthetic crowd data

### Phase 4: Optional Enhancements (Week 4+)
11. ❌ Shuttle information
12. ❌ Additional points of interest

---

## 🗂️ SUGGESTED FILE STRUCTURE

```
siue_routing_data/
├── buildings.json           # Building coordinates and basic info
├── paths.json              # Walking path connections
├── elevation.json          # Elevation and slope data
├── accessibility.json      # Stairs, elevators, ramps
├── schedules.json          # Building hours and class times
├── shuttle.json            # (Optional) Shuttle stops and routes
└── README.md              # Data sources and update log
```

---

## ⏱️ TOTAL TIME ESTIMATE

- **Minimum Viable Dataset:** 8-12 hours
- **Full Featured Dataset:** 20-25 hours
- **With Campus Visit:** Add 3-5 hours

---

## 🎯 IMMEDIATE NEXT STEPS

1. **START HERE:** Extract building coordinates from OpenStreetMap
   - Use: https://www.openstreetmap.org/
   - Search: "SIUE Edwardsville"
   - Right-click each building → "Show coordinates"

2. **THEN:** Map major paths by looking at satellite view
   - Use Google Maps satellite view
   - Estimate distances using measuring tool

3. **CREATE:** Start filling in the JSON files with collected data

---

## 📊 PROGRESS TRACKER

| Data Category | Status | Priority | Completion % | Est. Hours |
|---------------|--------|----------|--------------|------------|
| Building List | ✅ Done | Critical | 100% | 0 |
| Coordinates | ❌ Missing | Critical | 0% | 2-3 |
| Walking Paths | ❌ Missing | Critical | 0% | 4-6 |
| Elevation | ❌ Missing | High | 0% | 3-4 |
| Accessibility | ❌ Missing | High | 0% | 6-8 |
| Building Hours | ❌ Missing | Medium | 0% | 1-2 |
| Class Schedule | ❌ Missing | Medium | 0% | 2-3 |
| Shuttle Info | ❌ Missing | Low | 0% | 2-3 |

**OVERALL COMPLETION: 5% (1/8 categories)**

