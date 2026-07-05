"""
Repair templates — parts, tools, checklist, technician instructions per component.
"""

TEMPLATES = {
    "battery": {
        "label":    "Battery Replacement",
        "duration": 2,
        "skill":    "Electrical / HV Systems",
        "parts": [
            "Battery Pack (OEM)",
            "HV Wiring Harness",
            "Battery Connector Kit",
            "Main Fuse (200A)",
            "Thermal Pad",
            "Mounting Bolts (M10×6)",
        ],
        "tools": [
            "Digital Multimeter",
            "Insulated Socket Set",
            "Torque Wrench (20–80 Nm)",
            "HV Insulation Tester",
            "Battery Diagnostic Scanner",
        ],
        "checklist": [
            "Disconnect HV supply and verify isolation",
            "Wear PPE — insulated gloves and face shield",
            "Remove battery cover panels",
            "Disconnect negative terminal first",
            "Remove old battery pack",
            "Inspect battery tray for corrosion",
            "Install new battery pack",
            "Reconnect terminals — positive first",
            "Torque connectors to spec (45 Nm)",
            "Reinstall cover panels",
            "Perform voltage test (target: 12.6–13.2V)",
            "Run charging cycle test",
            "Verify BMS communication",
            "Final inspection and sign-off",
        ],
        "instructions": {
            "before": [
                "Disconnect HV supply and lock out / tag out",
                "Wear full PPE — insulated gloves, face shield",
                "Verify battery isolation with HV tester",
                "Allow 10 min discharge before handling",
            ],
            "during": [
                "Handle battery pack with two-person lift",
                "Torque all connectors to manufacturer spec",
                "Reconnect fuse only after all connections verified",
                "Check polarity before energising",
            ],
            "after": [
                "Run BMS diagnostic scan",
                "Perform 30-min charging cycle",
                "Verify voltage under load",
                "Update Digital Twin record",
            ],
        },
    },

    "cooling": {
        "label":    "Cooling System Service",
        "duration": 3,
        "skill":    "Thermal / Mechanical",
        "parts": [
            "Coolant (5L OEM spec)",
            "Coolant Pump",
            "Radiator Hose Set",
            "Hose Clamps (×4)",
            "Thermostat",
            "Coolant Reservoir Cap",
        ],
        "tools": [
            "Coolant Pressure Tester",
            "Hose Clamp Pliers",
            "Drain Pan (10L)",
            "Funnel",
            "Torque Wrench",
            "Infrared Thermometer",
        ],
        "checklist": [
            "Allow engine to cool completely (min 30 min)",
            "Drain existing coolant into drain pan",
            "Inspect hoses for cracks or swelling",
            "Replace coolant pump if worn",
            "Replace thermostat",
            "Flush cooling circuit with clean water",
            "Install new hoses and clamps",
            "Fill with fresh OEM coolant",
            "Bleed air from system",
            "Run engine to operating temperature",
            "Pressure test — hold 1.2 bar for 10 min",
            "Check for leaks at all joints",
            "Verify temperature stabilises at 85–95°C",
            "Final inspection and sign-off",
        ],
        "instructions": {
            "before": [
                "Ensure engine is cold before opening system",
                "Place drain pan under vehicle",
                "Wear chemical-resistant gloves",
                "Check coolant type compatibility",
            ],
            "during": [
                "Do not mix coolant types",
                "Tighten hose clamps evenly",
                "Bleed air pockets from highest point",
                "Monitor temperature during warm-up",
            ],
            "after": [
                "Pressure test for minimum 10 minutes",
                "Road test and recheck coolant level",
                "Dispose of old coolant per regulations",
                "Update service record",
            ],
        },
    },

    "motor": {
        "label":    "Motor / Engine Overhaul",
        "duration": 5,
        "skill":    "Powertrain Specialist",
        "parts": [
            "Motor Bearing Set",
            "Motor Seal Kit",
            "Drive Belt",
            "Lubricant (Synthetic 5W-40, 4L)",
            "Oil Filter",
            "Gasket Set",
        ],
        "tools": [
            "Engine Hoist",
            "Bearing Puller Set",
            "Torque Wrench (20–200 Nm)",
            "Feeler Gauge",
            "Compression Tester",
            "OBD-II Scanner",
        ],
        "checklist": [
            "Drain engine oil completely",
            "Disconnect all electrical connectors",
            "Remove drive belt and tensioner",
            "Extract motor / engine assembly",
            "Disassemble and inspect all bearings",
            "Replace worn bearings and seals",
            "Clean all mating surfaces",
            "Install new gasket set",
            "Reassemble motor to spec",
            "Install new drive belt",
            "Fill with fresh synthetic lubricant",
            "Reconnect all electrical connectors",
            "Run engine — check for abnormal noise",
            "Perform OBD-II diagnostic scan",
            "Road test under load",
            "Final inspection and sign-off",
        ],
        "instructions": {
            "before": [
                "Drain all fluids before disassembly",
                "Label all connectors and hoses",
                "Photograph assembly for reference",
                "Prepare clean work surface",
            ],
            "during": [
                "Follow torque sequence for head bolts",
                "Use new fasteners where specified",
                "Keep components organised by assembly order",
                "Check clearances with feeler gauge",
            ],
            "after": [
                "Run engine at idle for 15 min",
                "Check for oil leaks under load",
                "Perform full OBD-II scan",
                "Update Digital Twin and service log",
            ],
        },
    },

    "brake": {
        "label":    "Brake System Service",
        "duration": 2,
        "skill":    "Brake / Safety Systems",
        "parts": [
            "Brake Pad Set (Front + Rear)",
            "Brake Disc (if worn beyond limit)",
            "Brake Fluid (DOT 4, 500ml)",
            "Caliper Slide Pin Kit",
            "Brake Cleaner Spray",
        ],
        "tools": [
            "Brake Caliper Wind-Back Tool",
            "Torque Wrench",
            "Brake Bleeding Kit",
            "Vernier Caliper",
            "Jack and Axle Stands",
        ],
        "checklist": [
            "Lift vehicle and secure on axle stands",
            "Remove wheels",
            "Measure disc thickness — replace if below limit",
            "Remove caliper and inspect for leaks",
            "Wind back caliper piston",
            "Install new brake pads",
            "Lubricate slide pins",
            "Reinstall caliper — torque to spec (35 Nm)",
            "Bleed brake circuit — remove air bubbles",
            "Top up brake fluid to MAX mark",
            "Reinstall wheels — torque to spec (110 Nm)",
            "Pump brake pedal until firm",
            "Test brakes at low speed",
            "Final inspection and sign-off",
        ],
        "instructions": {
            "before": [
                "Ensure vehicle is on level ground",
                "Engage parking brake before lifting",
                "Wear safety glasses",
                "Check brake fluid level before bleeding",
            ],
            "during": [
                "Never reuse old brake fluid",
                "Keep caliper supported — do not hang by hose",
                "Apply copper grease to pad backing only",
                "Bleed furthest caliper first",
            ],
            "after": [
                "Bed in new pads — 10 moderate stops from 50 km/h",
                "Recheck fluid level after bedding",
                "Inspect for fluid leaks",
                "Update service record",
            ],
        },
    },

    "transmission": {
        "label":    "Transmission Service",
        "duration": 6,
        "skill":    "Drivetrain Specialist",
        "parts": [
            "Transmission Fluid (ATF, 6L)",
            "Transmission Filter",
            "Gasket / Sump Pan Seal",
            "Shift Solenoid (if faulty)",
            "Torque Converter Seal",
        ],
        "tools": [
            "Transmission Jack",
            "Torque Wrench",
            "Fluid Pump",
            "Drain Pan (10L)",
            "Transmission Diagnostic Tool",
        ],
        "checklist": [
            "Warm transmission to operating temperature",
            "Drain transmission fluid",
            "Remove sump pan and inspect for debris",
            "Replace transmission filter",
            "Clean sump pan thoroughly",
            "Install new sump pan gasket",
            "Reinstall sump pan — torque to spec",
            "Fill with correct ATF to spec level",
            "Check shift solenoids",
            "Run transmission through all gear ranges",
            "Check for leaks at all seals",
            "Perform transmission diagnostic scan",
            "Road test — verify smooth gear changes",
            "Recheck fluid level when hot",
            "Final inspection and sign-off",
        ],
        "instructions": {
            "before": [
                "Warm transmission before draining",
                "Use correct ATF specification",
                "Prepare large drain pan",
                "Check for fault codes before disassembly",
            ],
            "during": [
                "Note position of all solenoids before removal",
                "Do not overtighten sump pan bolts",
                "Fill fluid slowly to avoid overfill",
                "Check fluid colour — dark/burnt = deeper inspection",
            ],
            "after": [
                "Road test through all gear ranges",
                "Recheck fluid level when at operating temp",
                "Clear fault codes and rescan",
                "Update Digital Twin and service log",
            ],
        },
    },

    "electrical": {
        "label":    "Electrical System Inspection",
        "duration": 2,
        "skill":    "Auto Electrician",
        "parts": [
            "Wiring Loom Section (if damaged)",
            "Fuse Set (assorted)",
            "Relay Kit",
            "Electrical Tape / Heat Shrink",
            "Terminal Connector Kit",
        ],
        "tools": [
            "Digital Multimeter",
            "Oscilloscope",
            "Wire Stripper / Crimper",
            "OBD-II Scanner",
            "Circuit Tester",
        ],
        "checklist": [
            "Disconnect battery before inspection",
            "Inspect main wiring harness for damage",
            "Test all fuses — replace blown fuses",
            "Check relay operation",
            "Inspect connector pins for corrosion",
            "Test voltage at key circuits",
            "Repair or replace damaged wiring",
            "Reconnect battery",
            "Run OBD-II scan — clear fault codes",
            "Test all electrical systems",
            "Verify charging system output",
            "Final inspection and sign-off",
        ],
        "instructions": {
            "before": [
                "Disconnect battery — negative first",
                "Wear insulated gloves",
                "Document all fault codes before clearing",
                "Inspect visually for burn marks or melted insulation",
            ],
            "during": [
                "Never probe live HV circuits without proper PPE",
                "Use correct fuse ratings only",
                "Solder and heat-shrink all repairs",
                "Test each circuit after repair",
            ],
            "after": [
                "Run full OBD-II diagnostic",
                "Test all accessories and safety systems",
                "Verify no new fault codes",
                "Update Digital Twin record",
            ],
        },
    },

    "general": {
        "label":    "General Inspection",
        "duration": 1,
        "skill":    "General Technician",
        "parts": [
            "Engine Oil (if due)",
            "Air Filter",
            "Wiper Blades",
            "Cabin Filter",
        ],
        "tools": [
            "OBD-II Scanner",
            "Torque Wrench",
            "Tyre Pressure Gauge",
            "Inspection Light",
        ],
        "checklist": [
            "Check all fluid levels",
            "Inspect tyre condition and pressure",
            "Test all lights",
            "Run OBD-II diagnostic scan",
            "Inspect brake pads visually",
            "Check battery terminals",
            "Inspect belts and hoses",
            "Test horn and wipers",
            "Final inspection and sign-off",
        ],
        "instructions": {
            "before": [
                "Park on level ground",
                "Allow engine to cool before checking fluids",
                "Gather inspection checklist",
            ],
            "during": [
                "Document all findings",
                "Flag any items requiring further attention",
                "Do not clear fault codes without noting them",
            ],
            "after": [
                "Provide written inspection report",
                "Advise on any upcoming service items",
                "Update service record",
            ],
        },
    },
}


def get_template(root_causes: list) -> dict:
    """Pick the most relevant template from root causes."""
    cause_str = " ".join(root_causes).lower()
    if any(k in cause_str for k in ("battery", "voltage", "charging")):
        return TEMPLATES["battery"]
    if any(k in cause_str for k in ("thermal", "cooling", "temperature", "overheat")):
        return TEMPLATES["cooling"]
    if any(k in cause_str for k in ("engine", "motor", "rpm", "stress")):
        return TEMPLATES["motor"]
    if any(k in cause_str for k in ("brake", "braking")):
        return TEMPLATES["brake"]
    if any(k in cause_str for k in ("transmission", "gear")):
        return TEMPLATES["transmission"]
    if any(k in cause_str for k in ("electrical", "wiring", "fuse", "relay")):
        return TEMPLATES["electrical"]
    return TEMPLATES["general"]
