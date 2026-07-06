# VISTA – Vehicle Intelligence System for Telemetry Analytics

> **An AI-Powered Digital Twin Platform for Real-Time Vehicle Health Monitoring, Predictive Maintenance, Explainable AI, and Fleet Intelligence.**

---

# Overview

**VISTA (Vehicle Intelligence System for Telemetry Analytics)** is an end-to-end AI-powered Digital Twin platform that combines **real-time OBD-II telemetry, machine learning, predictive maintenance, explainable AI (XAI), and immersive 3D visualization** to monitor vehicle health and forecast failures before they occur.

Unlike traditional vehicle diagnostic systems that only display sensor values or fault codes, VISTA creates a **living digital replica of every vehicle**, continuously analyzing telemetry to predict failures, estimate Remaining Useful Life (RUL), explain AI decisions, and assist technicians with intelligent maintenance recommendations.

The platform demonstrates how **Edge AI**, **Digital Twin Technology**, and **Predictive Analytics** can transform modern fleet maintenance from reactive repairs into intelligent predictive maintenance.

---

# Key Features

## Real-Time OBD-II Integration

- Live telemetry acquisition from workshop vehicles
- Launch X431 PAD V3.0 Integration
- Bluetooth OBD-II Scanner Integration
- Multi-vehicle monitoring
- Live vehicle status updates

---

## AI Digital Twin

- Interactive 3D Digital Twin
- Component-wise health monitoring
- Battery Twin
- Motor Twin
- Cooling Twin
- Brake Twin
- Transmission Twin
- Electrical Twin
- Interactive component inspection
- Live telemetry visualization

---

## Predictive AI

- Vehicle Health Prediction
- Failure Probability Prediction
- Remaining Useful Life (RUL)
- Root Cause Analysis
- Maintenance Recommendation Engine
- AI Confidence Score

---

## Timeline Prediction

- Day 0
- Day 7
- Day 15
- Day 30

Future vehicle degradation is simulated using AI-powered predictive analytics.

---

## Failure Chain Analysis

Visualizes how one component failure propagates across interconnected vehicle systems, helping technicians identify cascading failures before they occur.

---

## Fleet Intelligence

- Fleet Health Dashboard
- Vehicle Prioritization
- Risk Ranking
- Executive Insights
- Maintenance Planning
- Fleet Analytics

---

## Professional Reports

Downloadable AI-generated reports including:

- Vehicle Summary
- Live OBD Telemetry
- AI Predictions
- Diagnostic Trouble Codes
- Maintenance Recommendations
- Executive Summary

---

# Technology Stack

## Frontend

- React
- TypeScript
- Vite
- Three.js
- React Three Fiber
- React Drei
- Zustand
- Framer Motion
- Chart.js

---

## Backend

- Python
- FastAPI
- SQLite
- WebSocket
- REST APIs

---

## Artificial Intelligence

- Scikit-learn
- AutoML Training Pipeline
- Health Prediction
- Failure Prediction
- Remaining Useful Life Prediction
- Root Cause Analysis
- Explainable AI (SHAP)

---

## Hardware

- Launch X431 PAD V3.0
- Bluetooth OBD-II Scanner
- Android Car Scanner Application

---

# Project Showcase

## System Workflow

<img width="1408" height="716" alt="flow chart innovent " src="https://github.com/user-attachments/assets/a1456be5-eda2-40b6-84e5-dc8dcf1b945c" />

The system workflow illustrates the complete pipeline from **real-time OBD-II data acquisition**, backend AI processing, Digital Twin synchronization, predictive analytics, and interactive dashboard visualization.

---

## AI Digital Twin

<img width="1918" height="906" alt="15 digital twin" src="https://github.com/user-attachments/assets/f8d20a8f-379c-4ed0-a573-26039d78742e" />

The interactive Digital Twin visualizes the vehicle in 3D while displaying component-wise health, AI insights, real-time telemetry, and predictive maintenance information.

---

## AI Timeline Forecast

<img width="1917" height="905" alt="13 ai timeline" src="https://github.com/user-attachments/assets/c9fb2542-f45b-4bd7-bfc5-c4450fff5091" />

<img width="1918" height="902" alt="14 ai timeline" src="https://github.com/user-attachments/assets/d10a1934-cfa7-4446-adc6-0c20aaaf5257" />

The AI Timeline Forecast simulates vehicle degradation across Day 0, Day 7, Day 15, and Day 30, enabling proactive maintenance planning.

---

## Failure Chain Analysis

<img width="1918" height="920" alt="17 failure chain" src="https://github.com/user-attachments/assets/223dd38d-06d0-463c-a22b-d6cb7d18c412" />

<img width="1918" height="912" alt="18 failure chain" src="https://github.com/user-attachments/assets/30688bc8-d20d-4145-9a2d-1df8ec2ffced" />

The Failure Chain module demonstrates how failures propagate between interconnected vehicle components, assisting technicians in root cause identification.

---

## Hardware Setup

<img width="962" height="1280" alt="Launch X-431 PAD ENTIRE KIT" src="https://github.com/user-attachments/assets/a57c0121-1201-498a-bfd9-749158169dfa" />

<img width="1280" height="960" alt="OBD Port in vehicle&#39;s interior" src="https://github.com/user-attachments/assets/136aff46-1e5f-43b5-ac9c-568ab24d557a" />

Vehicle telemetry is collected using the Launch X431 PAD V3.0 diagnostic scanner and Bluetooth OBD-II devices connected directly to workshop vehicles.

---

# AI Modules

- Vehicle Health Prediction
- Failure Probability Prediction
- Remaining Useful Life Prediction
- Root Cause Analysis
- Fleet Risk Prioritization
- Confidence Estimation
- Predictive Maintenance Engine

---

# Vehicle Analytics

The platform continuously monitors:

- Engine RPM
- Vehicle Speed
- Engine Load
- Coolant Temperature
- Intake Air Temperature
- Ambient Temperature
- Battery Voltage
- Fuel Level
- Fuel Pressure
- Oil Temperature
- Oil Pressure
- MAF
- MAP
- Throttle Position
- Engine Runtime
- Diagnostic Trouble Codes (DTC)

---

# Digital Twin Capabilities

- Live Digital Twin Synchronization
- Interactive Component Inspection
- AI Timeline Replay
- Failure Simulation
- Predictive Analytics
- Dynamic HUD Overlay
- Component Health Visualization
- Live Telemetry Dashboard
- Failure Propagation Animation

---

# REST APIs

The backend exposes REST APIs for communication between the frontend, AI engine, and Digital Twin.

```http
GET    /fleet
GET    /vehicle/{id}
GET    /digital-twin/{id}
GET    /forecast/{id}
GET    /timeline/{id}
GET    /failure-chain/{id}
GET    /xai/{id}
POST   /simulate
GET    /assistant
```

---

# Project Highlights

- AI-Powered Digital Twin
- Real-Time OBD-II Integration
- Predictive Maintenance
- Explainable AI (XAI)
- Failure Chain Analysis
- Timeline Forecasting
- Fleet Intelligence
- Executive Dashboard
- Interactive 3D Visualization
- Professional Report Generation

---

# Data Source

This prototype utilizes **real telemetry collected from six workshop vehicles** using **Launch X431 PAD V3.0**, **Bluetooth OBD-II Scanners**, and the **Car Scanner Android application**.

As the vehicles were recorded under idle workshop conditions, AI-powered predictive analytics and Digital Twin simulations are applied to demonstrate health forecasting, failure prediction, and maintenance planning.

---

# Future Enhancements

- Live CAN Bus Integration
- MQTT Edge Gateway
- Cloud Fleet Synchronization
- OTA AI Model Updates
- Mobile Technician Application
- Voice-enabled AI Assistant
- Edge AI Deployment
- Fleet-wide Digital Twin Synchronization

---

# Developed By

## Team COSMIC

**Vehicle Intelligence System for Telemetry Analytics**

An AI-powered Digital Twin platform designed to redefine predictive maintenance through intelligent diagnostics, explainable AI, and immersive real-time vehicle visualization.

---

⭐ If you found this project interesting, don't forget to **Star ⭐ the repository!**
