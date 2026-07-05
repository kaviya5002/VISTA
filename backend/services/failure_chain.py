def predict_failure_chain(vehicle):
    root_causes = vehicle["root_cause"]
    chain = []

    # Build chain from all root causes
    if "Battery Degradation" in root_causes:
        chain.append("Battery Degradation")
    if "Low Battery Voltage" in root_causes:
        chain.append("Low Battery Voltage")
    if "Battery Below Optimal" in root_causes:
        chain.append("Battery Below Optimal")
    if "Thermal Stress" in root_causes:
        chain.append("Thermal Stress")
    if "Cooling System Stress" in root_causes:
        chain.append("Cooling System Stress")
    if "Elevated Temperature" in root_causes:
        chain.append("Elevated Temperature")
    if "Engine Stress" in root_causes:
        chain.append("Engine Stress")
    if "High RPM" in root_causes:
        chain.append("High RPM")

    # Add progression based on what's in chain
    if "Battery Degradation" in chain or "Low Battery Voltage" in chain:
        chain.append("Motor Efficiency Loss")
    if "Thermal Stress" in chain or "Cooling System Stress" in chain:
        chain.append("Component Wear")
    if "Engine Stress" in chain or "High RPM" in chain:
        chain.append("Performance Loss")

    if chain:
        chain.append("Vehicle Breakdown")
    else:
        chain = ["System Healthy"]

    vehicle["failure_chain"] = chain
    vehicle["risk_level"] = "High" if len(chain) > 3 else "Medium" if len(chain) > 1 else "Low"

    return vehicle
