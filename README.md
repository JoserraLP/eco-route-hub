# EcoRouteHub: Speed Profile Simulator & Energy Consumption Estimator

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Framework-Flask-green.svg)](https://flask.palletsprojects.com/)
[![API Spec](https://img.shields.io/badge/OpenAPI-3.0.3-brightgreen.svg)](openapi.yaml)
[![License](https://img.shields.io/badge/license-MIT-informational.svg)](LICENSE)

**EcoRouteHub** (`route_consumption_estimator`) is an open framework and RESTful service designed for simulating vehicle speed profiles, evaluating kinematic energy consumption, and benchmarking route efficiency across physics and data-driven simulation engines (such as `greta` and `fastsim`).

---

## 📋 Table of Contents

1. [Project Objective](#1-project-objective)
2. [Architecture Overview](#2-architecture-overview)
3. [Installation & Setup](#3-installation--setup)
4. [Database Setup](#4-database-setup)
5. [Benchmarking API Usage](#5-benchmarking-api-usage)
6. [How to Add a New Provider](#6-how-to-add-a-new-provider)
7. [Repository Structure](#7-repository-structure)

---

## 1. Project Objective

EcoRouteHub addresses the challenges of eco-routing and vehicle fleet efficiency by providing a standardized, modular platform for route energy estimation. Key objectives include:

* **Standardized Energy & Emissions Modeling:** Calculating precise energy consumption ($kWh$, fuel liters), travel time, and distance based on elevation, speed profiles, and vehicle resistance coefficients ($A, B, C$).
* **Benchmarking Platform:** Enabling side-by-side performance and telemetry comparison between different energy evaluation engines (e.g., `greta`, `fastsim`) under identical route conditions.
* **Extensible Provider Architecture:** Decoupling infrastructure, weather, traffic, driving behavior, and vehicle specs into interface abstractions to allow seamless integration of new data sources and models.

---

## 2. Architecture Overview

EcoRouteHub is built on a modular, provider-driven layered architecture that decouples data ingestion, route enrichment, and kinematic energy simulation. At the heart of the system is the **`RouteModel`** domain entity, which acts as a unified state container throughout the entire processing pipeline.


```mermaid
graph TD
    Client[REST Client / External App] -->|HTTP GET /benchmarking| API[Flask API Layer /app]
    API --> Pipeline[Pipeline Orchestrator]
    
    subgraph Providers ["Provider Abstraction Layer (route_consumption_estimator/interfaces/)"]
        P1[Vehicle Information Provider]
        P2[Road Route Provider]
        P3[Speed Profile Provider]
        P4[Ambient Weather Provider]
        P5[Road Infrastructure Provider]
        P6[Traffic Operation Provider]
    end
    
    Pipeline -->|Fetch Data & Enrich| P1 & P2 & P3 & P4 & P5 & P6
    P1 & P2 & P3 & P4 & P5 & P6 -->|Populate Attributes| Domain[Unified Core Domain: RouteModel]
    
    Domain --> Bench[Benchmarking & Simulation Engine]
    
    subgraph Engines ["Simulation Engines"]
        Bench --> Greta[GRETA Physics Model]
        Bench --> Fastsim[FASTSim Powertrain Model]
        Bench --> Custom[Extensible Energy Models...]
    end
    
    Bench --> Telemetry[Telemetry & Performance Profiler]
    Telemetry -->|Execution Time & Energy Metrics| Response[JSON Response Output]
    Response --> Client
```
---

## 3. Installation & Setup

### 3.1. Prerequisites
* **Python:** 3.10 or higher
* **Database:** MySQL 8.0+ or MariaDB 10.5+

### 3.2. Local Installation

```bash
# Clone the repository
git clone https://github.com/your-username/ecoroutehub.git
cd ecoroutehub

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.3. Environment Configuration (`.env`)

Create a `.env` file in the root directory of the project:

```env
PORT=5001
ENVIRONMENT=development
LOG_LEVEL=INFO
DATABASE_URI=mysql+pymysql://user:password@localhost:3306/greta_app
API_KEY=KEY
```

### 3.4. Running the Application

```bash
# Development server
python main.py

# Production WSGI server
gunicorn --bind 0.0.0.0:5001 route_consumption_estimator.wsgi:app
```

---

## 4. Database Setup

The framework utilizes a MySQL database (`greta_app`) containing vehicle specifications, motor types, unladen mass, and physical resistance coefficients ($A, B, C$).

Initialize the database schema and sample vehicle datasets using the SQL script:

```bash
mysql -u root -p greta_app < vehicles_data/vehicles_db.sql
```

---

## 5. Benchmarking API Usage

The `/benchmarking` endpoint evaluates energy consumption across multiple simulation models simultaneously (e.g., `greta` and `fastsim`).

### cURL Request

```bash
curl --location 'http://127.0.0.1:5001/benchmarking?source=39.556168%2C-6.415368&destination=39.471626%2C-6.387366&vehicle_id=3006&api_key=K4CH0P0-Eco-Traffic-App-Testing&models=greta%2Cfastsim&api_key=K4CH0P0-Eco-Traffic-App-Testing'
```

### JSON Response

```json
{
    "pipelinePreparationMs": 12184.8,
    "simulations": [
        {
            "distance": 11050.583624363573,
            "fuelEnergyKwh": 4.797347641042175,
            "fuelEnergyKwhPer100Km": 43.41261786812156,
            "fuelLiters": 0.5388705131259838,
            "fuelLitersPer100Km": 4.876398672174371,
            "model": "greta",
            "telemetry": {
                "executionCpuTimeMs": 1953.125,
                "executionWallTimeMs": 1929.955,
                "peakMemoryMb": 4.8364
            },
            "time": 957.8063971380233
        },
        {
            "distance": 10979.804698250544,
            "fuelEnergyKwh": 4.270929129501978,
            "fuelEnergyKwhPer100Km": 38.89804278743211,
            "fuelLiters": 0.4797396277580311,
            "fuelLitersPer100Km": 4.369291084334769,
            "model": "fastsim",
            "telemetry": {
                "executionCpuTimeMs": 2406.25,
                "executionWallTimeMs": 2384.698,
                "peakMemoryMb": 4.9904
            },
            "time": 957.8393226416019
        }
    ]
}
```

---

## 6. How to Add a New Provider

Integrating a new data source or energy model into EcoRouteHub follows a structured 4-step process:

### Step 1: Category Identification & Configuration
The integration process begins by identifying the provider category that best matches the information to be incorporated. The available abstractions located in `route_consumption_estimator/interfaces/` include:
* `VehicleInformationProvider`
* `RoadRouteProvider`
* `SpeedProfileProvider`
* `AmbientWeatherProvider`
* `RoadInfrastructureProvider`
* `TrafficOperationProvider`
* `VehicleEnergyModelProvider`

Once the appropriate provider type has been selected, the developer defines the provider-specific configuration parameters required by the target data source or service in `route_consumption_estimator/config.py` or `.env`. Typical parameters may include service endpoints, authentication credentials, supported attributes, refresh policies, filtering criteria, or provider-specific processing options. These configuration elements determine both how the provider acquires information and which data will be exposed to the rest of the framework.

### Step 2: Interface Implementation
After the configuration requirements have been identified, the new provider is implemented by extending the corresponding provider abstraction in `route_consumption_estimator/interfaces/` and conforming to the input and output contracts defined by the associated interfaces.

```python
# Example: Custom Weather Provider implementation
from route_consumption_estimator.interfaces.ambient_weather_provider import AmbientWeatherProvider
from route_consumption_estimator.domain.route_model import RouteModel

class CustomWeatherProvider(AmbientWeatherProvider):
    def __init__(self, api_key: str, endpoint: str):
        self.api_key = api_key
        self.endpoint = endpoint

    def enrich_route_weather(self, route: RouteModel) -> RouteModel:
        # Acquire weather data and bind parameters to route segments
        return route
```

### Step 3: Registration & Auto-Discovery
Once implemented, the provider is registered through the architecture configuration layer (`route_consumption_estimator/config.py` or `plugins.py`) by specifying its identifier, implementation class, execution parameters, and provider-specific configuration values, as represented in `config_base.yaml`. During framework initialization (`create_app()`), the provider is automatically discovered, validated, and instantiated together with the remaining registered components.

### Step 4: Core Domain Integration & Data Availability
After registration, in the case of information providers, the information supplied by the new provider becomes part of the common route representation (`RouteModel`) maintained by the architectural core. Consequently, the newly acquired attributes are immediately available to downstream components, including route-processing services, speed-profile generation modules, and vehicle energy-consumption models. This mechanism enables the architecture to evolve incrementally as new information sources become available, while preserving interoperability, reproducibility, and compatibility with existing experimental workflows.

### Step 5: Optional: Extend speed profile behavior
While dealing with new information, it may affect to the speed profile and resistances calculation. Consider including new information in each required process to be considered for consumption estimation based on your needs.

---

## 7. Repository Structure

```text
.
├── config/                                 # Global configurations and benchmarking examples
│   ├── benchmarking_example.yaml
│   └── config_base.yaml
├── docs/                                   # Technical project documentation
├── route_consumption_estimator/            # Core package/module
│   ├── app/                                # Web application layer and API endpoints
│   │   ├── routes/                         # Flask routes/controllers
│   │   │   ├── app_review.py
│   │   │   ├── benchmarking.py
│   │   │   ├── feature_review.py
│   │   │   ├── routes.py
│   │   │   ├── user_routes.py
│   │   │   ├── user_stats.py
│   │   │   ├── user_vehicles.py
│   │   │   ├── users.py
│   │   │   └── vehicles.py
│   │   ├── security.py                     # Authentication and security
│   │   └── utils.py
│   ├── config/                             # Configuration loaders and internal models
│   │   ├── loader.py
│   │   └── models.py
│   ├── core/                               # Core system logic and processors
│   │   ├── graph/                          # Graph engines and network algorithms
│   │   │   └── graph_engine.py
│   │   ├── visualization/                  # Plotting and visualization utilities
│   │   │   ├── plots.py
│   │   │   └── utils.py
│   │   ├── core.py
│   │   ├── plugin_manager.py               # Dynamic plugin management and registry
│   │   ├── plugin_registry.py
│   │   ├── route_processor.py              # Main route processing
│   │   └── utils.py
│   ├── domain/                             # Domain models, DTOs, DAOs, and constants
│   │   ├── constants.py
│   │   ├── dao_models.py
│   │   ├── dto_models.py
│   │   ├── enums.py
│   │   ├── graph_models.py
│   │   ├── parsers.py
│   │   ├── route_model.py
│   │   └── vehicle_model.py
│   ├── interfaces/                         # Interfaces/Contracts for providers
│   │   ├── ambient_weather_provider.py
│   │   ├── driving_behavior_provider.py
│   │   ├── road_infrastructure_provider.py
│   │   ├── road_route_provider.py
│   │   ├── route_segmentation_provider.py
│   │   ├── speed_profile_provider.py
│   │   ├── traffic_operation_provider.py
│   │   ├── vehicle_energy_model_provider.py
│   │   └── vehicle_information_provider.py
│   ├── plugins/                            # Concrete provider implementations
│   │   ├── ambient_weather_provider/       # Weather (e.g., OpenWeatherAPI)
│   │   │   ├── openweatherapi.py
│   │   │   └── static_pressure_provider.py
│   │   ├── driving_behavior_provider/
│   │   ├── road_infrastructure_provider/    # Elevation and road infrastructure data
│   │   │   ├── nominatim.py
│   │   │   └── opentopodata.py
│   │   ├── road_route_provider/             # Road routing (GraphHopper, ORS, OSRM)
│   │   │   ├── graphhopper.py
│   │   │   ├── ors.py
│   │   │   └── osrm.py
│   │   ├── route_segmentation_provider/    # Route segmentation
│   │   │   └── route_segmentator.py
│   │   ├── speed_profile_provider/          # Speed profiles
│   │   │   └── speed_profile.py
│   │   ├── traffic_operation_provider/
│   │   ├── vehicle_energy_model_provider/  # Energy consumption models (FastSim, Greta)
│   │   │   ├── fastsim/
│   │   │   │   └── fastsim.py
│   │   │   └── greta/
│   │   │       ├── constants.py
│   │   │       ├── greta.py
│   │   │       └── power_energy.py
│   │   └── vehicle_information_provider/  # Vehicle data and technical information
│   │       ├── epa_database_parser_scripts/
│   │       │   ├── constants.py
│   │       │   ├── parse_vehicles_xlsx_sql.py
│   │       │   └── process_all_vehicles_dir.py
│   │       └── vehicle_information_repository.py
│   ├── profiling/                          # Performance profiling tools
│   │   └── workflow_profiler.py
│   ├── extensions.py                       # Global extensions (e.g., SQLAlchemy, Marshmallow)
│   └── wsgi.py                             # WSGI entry point
├── .env                                    # Local environment variables
├── .gitignore                              # Git repository ignore rules
├── main.py                                 # Main application entry point
├── openapi.yaml                            # API specification (OpenAPI/Swagger)
├── README.md                               # Main documentation
├── requirements.txt                        # Python dependencies
└── setup.py                                # Python package setup script
```