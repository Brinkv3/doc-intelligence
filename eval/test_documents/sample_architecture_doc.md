# Architecture Document — Cloud Data Platform

**System Name:** Meridian Cloud Data Platform (CDP)
**Author:** Rachel Kim, Cloud Architect
**Version:** 2.1
**Date:** May 10, 2024
**Status:** Approved

## Overview

The Meridian Cloud Data Platform (CDP) is the target state architecture for Meridian Financial Services' data warehousing and analytics capabilities. It replaces the legacy on-premises Oracle 19c data warehouse with a cloud-native architecture on AWS, providing improved scalability, cost efficiency, and support for modern analytics workloads.

## Components

### 1. Data Ingestion Layer
**Technology:** AWS Glue, Amazon S3
**Responsibility:** Ingest data from upstream source systems via batch ETL and near-real-time streaming.
- AWS Glue crawlers discover and catalog source data
- Glue ETL jobs handle transformation and loading
- S3 serves as the landing zone and staging area
- Supports CSV, Parquet, JSON, and AVRO formats

### 2. Data Storage Layer
**Technology:** Amazon Redshift (RA3 nodes), Amazon S3 (data lake)
**Responsibility:** Store structured and semi-structured data for analytics consumption.
- Redshift cluster: 4x ra3.4xlarge nodes (production), 2x ra3.xlplus (staging)
- Redshift Spectrum for querying data directly in S3
- Data lake on S3 for raw and archived data (Parquet format, partitioned by date)
- Lifecycle policies: hot data in Redshift (2 years), warm data in S3 Standard (5 years), cold data in S3 Glacier (7+ years)

### 3. Data Catalog and Governance
**Technology:** AWS Lake Formation, AWS Glue Data Catalog
**Responsibility:** Centralized metadata management, access control, and data lineage.
- Lake Formation manages fine-grained access control (column-level security)
- Glue Data Catalog provides schema registry and searchable metadata
- Data classification tags applied to PII and sensitive financial data

### 4. Analytics and Reporting
**Technology:** Amazon QuickSight, direct JDBC/ODBC connections
**Responsibility:** Serve analytics consumers with dashboards and ad-hoc query capabilities.
- QuickSight dashboards for executive and operational reporting
- JDBC/ODBC endpoints for existing BI tools (Tableau, Power BI)
- Redshift query editor for analyst self-service

### 5. Orchestration
**Technology:** AWS Step Functions, Amazon EventBridge
**Responsibility:** Coordinate ETL workflows, manage dependencies, handle retries and error states.
- Step Functions state machines for complex multi-step ETL workflows
- EventBridge schedules for time-based triggers (daily, hourly)
- SNS notifications for pipeline failures and SLA breaches

### 6. Monitoring and Observability
**Technology:** Amazon CloudWatch, AWS CloudTrail
**Responsibility:** Monitor platform health, query performance, and security events.
- CloudWatch dashboards for Redshift performance (query latency, disk usage, connection count)
- CloudWatch Alarms for resource utilization thresholds
- CloudTrail for audit logging of all API calls and data access

## Integration Points

| External System | Direction | Protocol | Data Format | Frequency |
|----------------|-----------|----------|-------------|-----------|
| Core Banking (Fiserv) | Inbound | SFTP → S3 | CSV | Daily (2 AM ET) |
| Risk Management (SAS) | Inbound | JDBC | SQL query | Daily (4 AM ET) |
| Regulatory Reporting | Outbound | S3 → SFTP | Fixed-width | Monthly |
| Customer Portal | Outbound | API Gateway | JSON | Real-time |
| Compliance (Archer) | Outbound | SFTP | CSV | Weekly |

## Technology Stack

- AWS Redshift (RA3) — primary data warehouse
- AWS Glue — ETL and data cataloging
- Amazon S3 — data lake and staging
- AWS Lake Formation — governance and access control
- AWS Step Functions — workflow orchestration
- Amazon EventBridge — event-driven scheduling
- Amazon QuickSight — business intelligence
- Amazon CloudWatch — monitoring and alerting
- AWS CloudTrail — audit logging
- AWS KMS — encryption key management
- AWS IAM — identity and access management
- Terraform — infrastructure as code

## Deployment Model

Cloud-native on AWS, single region (us-east-1), multi-AZ for high availability. All infrastructure provisioned and managed via Terraform with state stored in S3 and locked via DynamoDB. CI/CD pipeline via AWS CodePipeline deploying Glue jobs and Redshift DDL changes.

## Security Considerations

- All data encrypted at rest using AWS KMS (customer-managed keys)
- All data encrypted in transit via TLS 1.2+
- VPC with private subnets only — no public endpoints
- Lake Formation column-level access control for PII fields
- MFA required for all console access
- IAM roles follow least-privilege principle (per-service, per-environment)
- Quarterly access reviews coordinated with InfoSec
- CloudTrail logs shipped to centralized security account

## Scalability Approach

Redshift RA3 nodes with managed storage provide elastic scaling — compute and storage scale independently. Concurrency Scaling automatically adds cluster capacity during peak query periods. For data volume growth beyond 5 years, transition older data to Redshift Spectrum (query S3 directly) to maintain query performance on hot data.

## Design Decisions

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Redshift over Snowflake | Client has existing AWS Enterprise Agreement; Redshift integrates natively with Lake Formation and existing IAM model | Snowflake (better concurrency, higher cost), BigQuery (wrong cloud) |
| Glue over Airflow | Serverless, no infrastructure to manage, native integration with Glue Data Catalog | MWAA (Airflow on AWS), Step Functions only, Informatica Cloud |
| RA3 over DC2 nodes | Managed storage allows compute and storage to scale independently; RA3 pricing more favorable for 2TB+ datasets | DC2 (faster local SSD, but storage-coupled scaling) |
| Terraform over CloudFormation | Team expertise, multi-cloud portability if needed, better module ecosystem | CloudFormation (native, no additional tooling), Pulumi |

## Constraints

- Must remain within AWS due to existing Enterprise Agreement (no multi-cloud)
- All data must reside in us-east-1 per regulatory requirements
- Maximum acceptable query latency for executive dashboards: 10 seconds
- Platform must support SOC 2 Type II and FFIEC audit requirements
- Total infrastructure cost target: ≤$15,000/month (excluding data transfer)
