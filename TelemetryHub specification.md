# IoT Monitoring Platform — System Specification

## 1. Project Overview

### 1.1 Purpose

The goal of this project is to build a production-oriented IoT monitoring platform for companies that use connected devices in environments such as:

- cold-chain transportation
- warehouses
- industrial facilities
- laboratories
- storage facilities
- vehicle fleets

The platform will collect telemetry from IoT devices, process it, store historical measurements, maintain the latest device state, detect abnormal conditions, generate alerts, and provide analytical insights.

The project is primarily intended for learning and practicing:

- backend engineering
- distributed systems
- microservices
- event-driven architecture
- data engineering
- database design
- scalability
- observability
- fault tolerance
- production-oriented software practices

The project will start as a modular monolith and will later evolve into a distributed system.

---

## 2. Main Business Scenario

A company transports temperature-sensitive medicine.

Each shipment contains one or more IoT devices.

The devices periodically send measurements such as:

- temperature
- humidity
- battery level
- GPS location
- signal strength
- device status

Example telemetry event:

```json
{
  "eventId": "evt-123",
  "deviceId": "device-456",
  "timestamp": "2026-09-25T08:30:00Z",
  "temperature": 6.4,
  "humidity": 61,
  "battery": 78,
  "latitude": 45.2671,
  "longitude": 19.8335
}
```

A company can configure rules such as:

```text
Allowed temperature range: 2°C - 8°C
Allowed humidity range: 30% - 70%
Minimum battery level: 15%
Maximum allowed violation duration: 2 minutes
```

If a measurement violates a rule, the system tracks the violation.

If the violation continues long enough, the system creates an alert.

Example:

```text
08:30:00 -> 8.7°C
08:30:30 -> 9.1°C
08:31:00 -> 9.4°C
08:31:30 -> 9.2°C
08:32:00 -> 9.0°C
```

If the rule states that temperature above 8°C for two minutes is critical, the system should generate an alert.

---

# 3. Main System Actors

## 3.1 Platform User

A user represents a person using the platform.

Possible responsibilities:

- manage devices
- view telemetry
- configure monitoring rules
- review alerts
- view analytics
- manage company settings

Future versions may support roles such as:

- administrator
- operator
- analyst
- viewer

---

## 3.2 Company

A company represents a tenant using the platform.

A company owns:

- users
- devices
- device configurations
- locations
- monitoring rules
- alerts
- analytical data

The platform should be designed so that data from one company cannot be accessed by another company.

---

## 3.3 IoT Device

A device represents a physical or simulated IoT sensor.

Examples:

- temperature sensor
- humidity sensor
- GPS tracker
- industrial machine sensor
- cold-storage sensor
- vehicle monitoring device

Devices send telemetry to the platform.

---

## 3.4 Device Simulator

Because the project will not depend on real physical hardware, the system must include a device simulator.

The simulator should be able to:

- create many virtual devices
- send telemetry periodically
- generate normal values
- generate abnormal values
- simulate offline devices
- simulate unstable network behavior
- simulate duplicated events
- simulate delayed events
- simulate out-of-order events
- generate high load

The simulator is an important part of the project because it allows testing scalability and failure scenarios.

---

# 4. Core Domain Objects

The exact database schemas will be designed later.

The initial domain should include at least the following objects.

## 4.1 Company

Represents an organization using the platform.

Possible properties:

- id
- name
- status
- createdAt
- updatedAt

---

## 4.2 User

Represents a platform user.

Possible properties:

- id
- companyId
- email
- passwordHash
- role
- status
- createdAt
- updatedAt

---

## 4.3 Device

Represents an IoT device.

Possible properties:

- id
- companyId
- name
- deviceType
- status
- locationId
- lastSeenAt
- createdAt
- updatedAt

---

## 4.4 DeviceConfiguration

Represents device-specific configuration.

Possible properties:

- deviceId
- samplingInterval
- enabledSensors
- firmwareVersion
- sensorSettings
- metadata
- communicationSettings

This object should support different structures for different device types.

---

## 4.5 Location

Represents a logical or physical device location.

Examples:

- warehouse
- truck
- laboratory
- storage room

Possible properties:

- id
- companyId
- name
- type
- address
- metadata

---

## 4.6 TelemetryEvent

Represents one measurement sent by a device.

Possible properties:

- eventId
- deviceId
- timestamp
- temperature
- humidity
- battery
- latitude
- longitude
- status
- metadata

Not every device needs to send every field.

---

## 4.7 AlertRule

Represents a rule used to detect abnormal conditions.

Possible properties:

- id
- companyId
- deviceId or deviceType
- metric
- comparisonOperator
- threshold
- minimumDuration
- severity
- enabled

Example:

```text
metric: temperature
condition: temperature > 8
duration: 2 minutes
severity: critical
```

---

## 4.8 Alert

Represents a detected problem.

Possible properties:

- id
- companyId
- deviceId
- ruleId
- severity
- status
- startedAt
- resolvedAt
- message

Possible statuses:

- active
- acknowledged
- resolved

---

## 4.9 DeviceState

Represents the latest known state of a device.

Possible properties:

- deviceId
- lastSeenAt
- latestTemperature
- latestHumidity
- latestBattery
- latestLocation
- onlineStatus

This is not necessarily the same as historical telemetry.

---

# 5. Functional Requirements

## 5.1 Authentication and Authorization

The system should allow users to:

- register or be created by an administrator
- log in
- log out
- access protected endpoints
- access only resources belonging to their company

The first version may use simple JWT-based authentication.

Future versions may introduce more advanced authorization.

---

## 5.2 Company Management

The system should allow:

- company creation
- company update
- company status management
- listing company users
- listing company devices

---

## 5.3 Device Management

Users should be able to:

- register a device
- update a device
- deactivate a device
- view device details
- list company devices
- assign a device to a location
- configure device properties
- view device online/offline status

---

## 5.4 Device Configuration

The system should support different configurations for different device types.

Examples:

### Temperature Device

```text
sampling interval
temperature unit
supported range
firmware version
```

### Vehicle Tracker

```text
sampling interval
GPS precision
speed monitoring
battery settings
```

The configuration model should remain flexible.

---

## 5.5 Telemetry Ingestion

Telemetry ingestion means receiving data sent by IoT devices.

The system should:

- receive telemetry events
- authenticate devices
- validate basic event structure
- reject malformed events
- reject unauthorized devices
- assign or validate event identifiers
- validate timestamps
- accept large numbers of events
- forward valid events for further processing

The ingestion layer should avoid performing expensive business logic.

Its main goal is to accept data reliably and quickly.

---

## 5.6 Telemetry Processing

After telemetry is received, the system should process it.

Processing may include:

- validation
- normalization
- deduplication
- enrichment
- historical storage
- updating the latest device state
- forwarding data to alert processing
- forwarding data to analytical processing

### Normalization

Normalization means converting incoming data into a standard internal format.

Example:

```text
Device sends Fahrenheit
System stores Celsius
```

### Enrichment

Enrichment means adding additional information to an event.

Example:

Incoming event:

```text
deviceId = device-123
temperature = 6.5
```

Enriched event:

```text
deviceId = device-123
companyId = company-1
locationId = warehouse-7
deviceType = cold-storage-sensor
temperature = 6.5
```

### Deduplication

The system should recognize repeated events and avoid producing incorrect duplicate results.

---

## 5.7 Latest Device State

The system should maintain the latest known state of each device.

Example:

```text
device-123

temperature = 6.4
humidity = 61
battery = 78
lastSeen = 08:30:00
status = online
```

This allows the dashboard to quickly show the current state without searching the full telemetry history.

---

## 5.8 Historical Telemetry

Users should be able to request historical telemetry.

Example queries:

```text
Get temperature history for device-123
between 10:00 and 12:00.
```

Possible filters:

- device
- time range
- metric
- location

---

## 5.9 Alert Rules

Users should be able to create rules.

Examples:

```text
temperature > 8°C for more than 2 minutes
temperature < 2°C for more than 1 minute
humidity > 75%
battery < 15%
device has not sent telemetry for 5 minutes
```

Rules should support different severity levels.

Example:

```text
warning
high
critical
```

---

## 5.10 Alert Processing

The system should evaluate telemetry against configured rules.

The system should avoid creating a new alert for every single invalid measurement.

Example:

```text
temperature > 8°C
```

may need to remain true for two minutes before generating an alert.

The alert engine should therefore support stateful rule evaluation.

---

## 5.11 Alert Management

Users should be able to:

- list active alerts
- view alert details
- acknowledge an alert
- resolve an alert
- filter alerts
- view alert history

---

## 5.12 Device Online/Offline Detection

A device should be considered offline if it has not sent telemetry for a configured period.

Example:

```text
expected interval = 30 seconds
offline threshold = 2 minutes
```

If no telemetry is received for two minutes, the system may generate:

```text
DeviceOffline
```

When telemetry resumes:

```text
DeviceOnline
```

---

## 5.13 Analytics

The system should provide analytical information based on historical telemetry.

Examples:

- average temperature per hour
- minimum temperature
- maximum temperature
- number of measurements
- number of rule violations
- number of alerts
- average battery level
- device uptime
- device downtime
- number of offline periods
- measurements per device
- measurements per company
- measurements per location

---

# 6. Data Engineering Requirements

The project should contain a separate analytical data flow.

The purpose of the data engineering part is to transform large amounts of raw telemetry into useful analytical data.

High-level flow:

```text
Telemetry Events
      ↓
Kafka
      ↓
Raw Data
      ↓
Data Processing
      ↓
Transformations
      ↓
Aggregations
      ↓
Analytics Storage
      ↓
Dashboard / Reports
```

---

## 6.1 Raw Data

The platform should preserve raw telemetry data for analytical processing.

Raw data represents events as they were originally received or after minimal normalization.

---

## 6.2 Transformations

The data pipeline may:

- remove invalid records
- handle missing values
- normalize units
- detect duplicates
- enrich data
- convert timestamps
- group measurements
- derive additional columns

Example derived fields:

```text
temperature_violation = true
battery_status = low
device_online = true
```

---

## 6.3 Aggregations

The analytical system should create summarized data.

Example:

```text
device_hourly_statistics
```

Possible fields:

- deviceId
- hour
- averageTemperature
- minimumTemperature
- maximumTemperature
- averageHumidity
- measurementCount
- violationCount
- alertCount

The purpose is to avoid scanning millions of raw events for every dashboard request.

---

## 6.4 Batch Processing

The project should include batch processing.

Example:

```text
Every night:
process previous day's telemetry
calculate daily statistics
store analytical results
```

Batch jobs may later be scheduled with Airflow.

---

## 6.5 Stream Processing

The project should also support near real-time processing.

Example:

```text
Telemetry event
    ↓
Kafka
    ↓
Streaming consumer
    ↓
Update hourly statistics
```

The exact technology may evolve during development.

---

# 7. Modular Monolith — Initial Version

The first version of the system should be implemented as a modular monolith.

The monolith is one deployable application, but its internal structure must be separated into clear modules.

Suggested modules:

```text
IoT Platform Monolith
│
├── Identity
├── Companies
├── Devices
├── Device Configuration
├── Telemetry
├── Alerts
├── Analytics
└── Shared Infrastructure
```

---

## 7.1 Monolith Communication

Modules should communicate using internal interfaces or application services.

Do not use:

- gRPC between modules
- network calls between modules
- Kafka for every internal operation

The goal is to keep the first version simple while maintaining clear boundaries.

---

## 7.2 Initial Database Strategy

The first version does not need to introduce every database immediately.

A reasonable initial version may use PostgreSQL for most application data.

Additional storage technologies should be introduced when their need becomes clear.

Possible evolution:

```text
Phase 1
PostgreSQL

Phase 2
Redis

Phase 3
Kafka

Phase 4
ScyllaDB

Phase 5
MongoDB

Phase 6
Analytical storage
```

This sequence may change if implementation requirements justify a different order.

---

# 8. Target Distributed Architecture

The final target system should evolve into multiple independently deployable services.

Approximate architecture:

```text
Frontend
   │
   │ REST
   ▼
API Gateway
   │
   │ gRPC
   ├───────────────┐
   ▼               ▼
Device Service   Alert Service
   │               │
   │               │
   └──────┐   ┌────┘
          │   │
          ▼   ▼
         Kafka
           │
      ┌────┼─────────────┐
      ▼    ▼             ▼
Telemetry  Alert      Data Pipeline
Processor  Processing
   │
   ├──────► ScyllaDB
   │
   └──────► Redis

Data Pipeline
   │
   ▼
Analytics Storage
```

An ingestion service will receive device telemetry and publish it into Kafka.

---

# 9. Target Services

The exact service boundaries may change during development.

The initial target architecture should consider the following services.

## 9.1 API Gateway

Responsibilities:

- expose REST APIs to frontend clients
- authenticate user requests
- route requests
- perform basic request validation
- apply rate limiting
- call backend services using gRPC

The gateway should not contain core business logic.

---

## 9.2 Device Service

Responsibilities:

- company-related device management
- device registration
- device metadata
- device configuration
- device lifecycle
- location assignment

Possible data:

- PostgreSQL
- MongoDB for flexible device configuration

---

## 9.3 Telemetry Ingestion Service

Responsibilities:

- receive device telemetry
- authenticate devices
- validate request format
- apply ingestion rate limits
- publish telemetry into Kafka

The service should be optimized for high throughput.

It should not perform complex analytics or alert evaluation.

---

## 9.4 Telemetry Processing Service

Responsibilities:

- consume telemetry events from Kafka
- normalize events
- enrich events
- deduplicate events
- store historical telemetry
- update latest state
- publish processed telemetry events

Possible storage:

- ScyllaDB
- Redis

---

## 9.5 Alert Service

Responsibilities:

- manage alert rules
- evaluate telemetry against rules
- maintain rule violation state
- create alerts
- acknowledge alerts
- resolve alerts

Possible storage:

- PostgreSQL
- Redis for temporary state if required

---

## 9.6 Analytics / Data Platform

Responsibilities:

- consume telemetry
- store raw analytical data
- transform data
- aggregate data
- prepare analytical datasets
- support dashboards and reports

Possible technologies:

- Python
- Kafka
- Pandas
- PySpark
- Airflow
- dbt
- PostgreSQL or another analytical storage technology

Not all technologies must be introduced immediately.

---

# 10. Communication Strategy

## 10.1 Frontend to Backend

Frontend communication should use:

```text
REST / HTTP
```

Flow:

```text
Frontend
   ↓ REST
API Gateway
```

---

## 10.2 API Gateway to Services

In the final distributed architecture:

```text
API Gateway
   ↓ gRPC
Backend Services
```

gRPC should be used when an immediate response is required.

Example:

```text
Gateway asks Device Service:
"Return device details."
```

---

## 10.3 Service-to-Service Synchronous Communication

Services may use gRPC when one service requires an immediate response from another.

However, unnecessary synchronous dependencies should be avoided.

---

## 10.4 Asynchronous Communication

Kafka should be used for asynchronous events.

Examples:

```text
TelemetryReceived
TelemetryProcessed
AlertCreated
DeviceOffline
DeviceOnline
DeviceConfigurationChanged
```

General rule:

```text
Frontend <-> Gateway = REST

Gateway <-> Services = gRPC

Service <-> Service requiring immediate response = gRPC

Asynchronous events = Kafka
```

---

# 11. Kafka Requirements

Kafka will act as the central event-streaming platform.

Possible topics:

```text
telemetry.raw
telemetry.processed
alerts
device.events
telemetry.dlq
```

The final topic structure will be defined during architecture design.

---

## 11.1 Event Identification

Every important event should contain a unique identifier.

Example:

```text
eventId
```

This will help with deduplication and idempotency.

---

## 11.2 Partitioning

Telemetry events should normally use:

```text
deviceId
```

as the Kafka message key.

This allows telemetry for the same device to remain ordered inside the same partition.

---

## 11.3 Consumer Groups

Multiple instances of a processing service should be able to belong to the same consumer group.

This allows horizontal scaling.

---

## 11.4 Retry Strategy

Temporary processing failures should be retried.

Example:

```text
processing fails
    ↓
retry
    ↓
retry
    ↓
retry
```

The exact retry policy should be configurable.

---

## 11.5 Dead Letter Queue

Events that repeatedly fail processing should be moved to a dead letter topic.

Example:

```text
telemetry.dlq
```

This allows failed events to be inspected and potentially reprocessed.

---

## 11.6 Delivery Semantics

The project should assume that a message may be delivered more than once.

Consumers should therefore be designed to be idempotent where necessary.

The project should focus on:

```text
at-least-once delivery
+
idempotent processing
```

rather than trying to guarantee exactly-once behavior across the entire system.

---

# 12. Database Responsibilities

## 12.1 PostgreSQL

Primary use:

- companies
- users
- devices
- locations
- alert rules
- alerts
- transactional business data

Reason:

The data is relational and requires strong consistency.

---

## 12.2 MongoDB

Primary use:

- flexible device configurations
- device-type-specific metadata
- structures that may differ significantly between device types

Example:

A temperature sensor and a vehicle tracker may have very different configuration documents.

MongoDB should only be used where its flexible document model provides a real benefit.

---

## 12.3 ScyllaDB

Primary use:

- large historical telemetry volume
- write-heavy workloads
- time-oriented queries
- device telemetry history

Example query:

```text
Get telemetry for device-123
between 10:00 and 11:00.
```

The data model should be designed around expected query patterns.

---

## 12.4 Redis

Primary use:

- latest device state
- cache
- temporary counters
- temporary processing state
- rate limiting

Example:

```text
device:123:latest
```

might contain the latest known measurement.

Redis should not be treated as the primary permanent store for historical telemetry.

---

# 13. Non-Functional Requirements

## 13.1 Scalability

The system should be designed so that high-load components can later be horizontally scaled.

Examples:

- multiple ingestion instances
- multiple telemetry processing instances
- multiple Kafka consumers

---

## 13.2 Performance

The telemetry ingestion path should remain lightweight.

Expensive work should be moved to asynchronous processing where possible.

---

## 13.3 Reliability

The system should tolerate temporary failures.

Examples:

- Kafka temporarily unavailable
- database temporarily unavailable
- consumer crashes
- duplicated events
- delayed events

---

## 13.4 Idempotency

Operations that may be executed more than once should avoid producing incorrect duplicate results.

Important examples:

- Kafka message processing
- alert creation
- repeated telemetry submission

---

## 13.5 Graceful Shutdown

Services should shut down safely.

A service should:

1. stop accepting new work
2. finish or safely stop current work
3. commit or release resources correctly
4. close database connections
5. close Kafka connections
6. exit

---

## 13.6 Configuration Management

Environment-specific configuration should not be hard-coded.

Examples:

- database URLs
- Kafka brokers
- secrets
- ports
- timeouts
- retry counts

Configuration should be provided using environment variables or configuration files.

Secrets must not be committed to Git.

---

## 13.7 Error Handling

Errors should be handled consistently.

The application should distinguish between:

- validation errors
- authentication errors
- authorization errors
- business errors
- infrastructure errors
- unexpected internal errors

---

## 13.8 Timeouts

Network calls should have timeouts.

A service should not wait forever for another service.

---

## 13.9 Retries

Retries should only be used where appropriate.

Retries should normally use:

- limited attempts
- delay
- exponential backoff where appropriate

Retries must not create duplicate side effects.

---

# 14. Observability

The final system should support three main observability areas.

## 14.1 Logging

Services should produce structured logs.

Logs should include useful context such as:

- service name
- timestamp
- request ID
- trace ID
- device ID where relevant
- error details

Sensitive information should not be logged.

---

## 14.2 Metrics

The system should expose metrics.

Examples:

```text
HTTP request count
HTTP error rate
request latency
telemetry events per second
Kafka consumer lag
failed telemetry events
active alerts
database latency
```

Suggested technology:

```text
Prometheus
```

---

## 14.3 Distributed Tracing

The distributed version should support tracing requests across services.

Suggested technology:

```text
OpenTelemetry
```

Example flow:

```text
Gateway
  ↓
Device Service
  ↓
Kafka
  ↓
Telemetry Processor
```

A trace should help identify where time was spent and where failures occurred.

---

## 14.4 Visualization

Grafana may be used to display:

- application metrics
- infrastructure metrics
- Kafka metrics
- service dashboards
- alerting dashboards

---

# 15. Security Requirements

The project should include basic production-oriented security practices.

Requirements:

- authenticated user endpoints
- authenticated device ingestion
- authorization by company
- input validation
- password hashing
- secrets outside source control
- basic API rate limiting
- secure error responses
- no sensitive data in logs

HTTPS should be assumed for real deployments.

---

# 16. Testing Strategy

The project should contain several levels of testing.

## 16.1 Unit Tests

Used for:

- business rules
- validation
- transformations
- alert logic

---

## 16.2 Integration Tests

Used for:

- database interaction
- Kafka producers and consumers
- Redis
- gRPC communication
- service integrations

---

## 16.3 API Tests

Used for:

- REST endpoints
- authentication
- validation
- error handling

---

## 16.4 End-to-End Tests

A small number of end-to-end tests should cover important workflows.

Example:

```text
Simulator sends high temperature
        ↓
telemetry accepted
        ↓
telemetry processed
        ↓
rule violation detected
        ↓
alert created
        ↓
alert visible through API
```

---

## 16.5 Load Testing

The simulator should allow performance testing.

Example targets may include:

```text
100 devices
1,000 devices
10,000 devices
```

The purpose is not to meet enterprise production numbers.

The purpose is to observe system behavior under increasing load.

Metrics to observe:

- events per second
- latency
- CPU
- memory
- Kafka consumer lag
- database latency
- errors

---

# 17. Infrastructure and Deployment

## 17.1 Docker

All major components should be containerized.

The local environment should eventually include:

```text
application services
PostgreSQL
MongoDB
ScyllaDB
Redis
Kafka
Prometheus
Grafana
```

Docker Compose can be used for local development.

---

## 17.2 CI/CD

The repository should eventually include a CI pipeline.

Possible steps:

```text
checkout
    ↓
lint
    ↓
unit tests
    ↓
integration tests
    ↓
build
    ↓
Docker image
```

Automated production deployment is optional.

---

## 17.3 Health Checks

Services should expose health information.

Examples:

```text
/health
/ready
```

Possible meanings:

### Liveness

```text
Is the process alive?
```

### Readiness

```text
Is the service ready to receive traffic?
```

---

# 18. Development Phases

The project should evolve gradually.

## Phase 1 — Specification and Modeling

Create:

- system specification
- domain model
- main use cases
- modular boundaries
- initial API design
- database models

No microservices yet.

---

## Phase 2 — Modular Monolith

Implement:

- authentication
- companies
- device management
- telemetry ingestion
- telemetry storage
- basic latest state
- alert rules
- alert processing
- basic API

Use a simple database strategy first.

---

## Phase 3 — Device Simulator and Load

Implement the simulator.

Test:

- large numbers of devices
- repeated telemetry
- invalid telemetry
- offline devices
- duplicated events
- delayed events

---

## Phase 4 — Redis

Introduce Redis where it provides clear value.

Possible use cases:

- latest device state
- caching
- rate limiting
- temporary state

---

## Phase 5 — Kafka

Introduce asynchronous telemetry processing.

Change from:

```text
Device
  ↓
Application
  ↓
Database
```

to:

```text
Device
  ↓
Ingestion
  ↓
Kafka
  ↓
Processing
```

---

## Phase 6 — Service Extraction

Begin extracting modules into independent services.

A likely first candidate is telemetry ingestion because:

- it has a clear responsibility
- it can have a different scaling requirement
- it handles high traffic
- it communicates naturally through Kafka

Later candidates:

- telemetry processing
- device service
- alert service

---

## Phase 7 — gRPC

After services are extracted, introduce gRPC for synchronous service communication.

Do not introduce gRPC inside the monolith.

---

## Phase 8 — ScyllaDB

Move high-volume telemetry history to ScyllaDB.

Design its data model around required queries.

---

## Phase 9 — MongoDB

Move flexible device configuration to MongoDB if the domain model confirms that document storage is useful.

MongoDB should not be added only to increase the number of technologies.

---

## Phase 10 — Data Engineering Pipeline

Build the analytical pipeline.

Possible evolution:

```text
Kafka
 ↓
Python consumer
 ↓
Transformations
 ↓
Aggregations
 ↓
Analytics storage
```

Later:

```text
Airflow
PySpark
dbt
```

may be introduced if useful.

---

## Phase 11 — Observability

Add:

- structured logging
- Prometheus
- Grafana
- OpenTelemetry tracing
- Kafka consumer lag monitoring

---

## Phase 12 — Reliability and Failure Testing

Test scenarios such as:

- duplicate Kafka event
- consumer crash
- database unavailable
- Redis unavailable
- slow service
- telemetry arriving out of order
- invalid telemetry
- service shutdown during processing

---

# 19. Important Engineering Principles

The project should follow these principles.

## 19.1 Technology Must Have a Reason

Do not add technology only because it looks good on a CV.

Every major tool should solve a real problem.

---

## 19.2 Start Simple

The first implementation should be understandable.

Complexity should be introduced gradually.

---

## 19.3 Clear Ownership

Each module or service should have a clear responsibility.

Avoid creating services only because an entity exists.

Bad example:

```text
TemperatureService
HumidityService
BatteryService
```

Better:

```text
Telemetry Processing Service
```

---

## 19.4 Avoid Shared Databases Between Final Services

In the final distributed architecture, services should ideally own their data.

Other services should communicate through:

- APIs
- gRPC
- events

rather than directly querying another service's private tables.

---

## 19.5 Prefer Asynchronous Processing for High-Volume Telemetry

High-volume telemetry should not require a long synchronous request chain.

---

## 19.6 Design for Failure

The system should assume that:

- services can crash
- networks can fail
- messages can be duplicated
- databases can become unavailable
- events may arrive late
- consumers may fall behind

Handling these situations is part of the project.

---

# 20. Initial Out of Scope

To keep the project realistic for a small team, the first project version does not need to include:

- real IoT hardware
- Kubernetes
- complex machine learning
- real SMS providers
- real email providers
- complex payment systems
- enterprise identity providers
- multi-region deployment
- full disaster recovery
- hundreds of microservices
- exactly-once guarantees across the full system

These features may be explored later if the main system is completed.

---

# 21. Definition of a Successful Project

The project can be considered successful when it demonstrates the following end-to-end scenario:

```text
1. A company and user exist.

2. A device is registered.

3. The device simulator sends telemetry.

4. The platform receives the telemetry.

5. The telemetry is validated and processed.

6. Historical telemetry is stored.

7. The latest device state is available.

8. Monitoring rules are evaluated.

9. A sustained rule violation creates an alert.

10. Users can view the alert.

11. Telemetry is also processed through an analytical pipeline.

12. Aggregated statistics can be queried or displayed.

13. The system can handle duplicated events safely.

14. The system can recover from selected component failures.

15. Services expose logs, metrics, and health information.

16. A selected part of the original monolith has been extracted into one or more services.

17. REST is used between frontend and API Gateway.

18. gRPC is used for appropriate synchronous internal service communication.

19. Kafka is used for asynchronous events.

20. The architecture and technology decisions can be clearly explained.
```

---

# 22. Target Technology Overview

The final technology choices may evolve, but the current target is:

| Area | Technology | Purpose |
|---|---|---|
| Frontend API | REST | Communication between frontend and API Gateway |
| Internal synchronous communication | gRPC | Communication between distributed backend services |
| Event streaming | Kafka | Asynchronous events and telemetry streams |
| Relational storage | PostgreSQL | Business and transactional data |
| Document storage | MongoDB | Flexible device configuration |
| High-volume telemetry storage | ScyllaDB | Historical telemetry |
| Cache / latest state | Redis | Fast access and temporary state |
| Data engineering | Python | Data processing |
| Local transformations | Pandas | Initial data processing and exploration |
| Distributed processing | PySpark | Larger analytical workloads |
| Workflow orchestration | Airflow | Scheduled data jobs |
| Data transformations | dbt | Analytical transformations where appropriate |
| Containerization | Docker | Local development and service packaging |
| Local orchestration | Docker Compose | Running the development environment |
| Metrics | Prometheus | Application and infrastructure metrics |
| Dashboards | Grafana | Metrics visualization |
| Tracing | OpenTelemetry | Distributed tracing |
| CI | GitHub Actions or similar | Automated testing and builds |

---

# 23. Architecture Evolution Summary

The project should intentionally demonstrate architectural evolution.

```text
Modular Monolith
        ↓
Redis
        ↓
Kafka
        ↓
Async Telemetry Processing
        ↓
Extract Ingestion Service
        ↓
Extract Processing Services
        ↓
gRPC
        ↓
ScyllaDB
        ↓
MongoDB
        ↓
Data Engineering Pipeline
        ↓
Observability
        ↓
Failure Testing
        ↓
Final Distributed System
```

The final architecture is a target, not an immutable design.

Architecture decisions may change when implementation reveals better boundaries or simpler solutions.
