# Project Plan — Data Platform Modernization

**Project Name:** Data Platform Modernization
**Project Manager:** Marcus Chen
**Start Date:** March 4, 2024
**Target End Date:** August 31, 2024
**Client:** Meridian Financial Services, Inc.
**Provider:** Apex Consulting Group, LLC

## Project Objectives

Migrate Meridian's legacy Oracle data warehouse to a cloud-native architecture on AWS, including all production schemas, ETL pipelines, and downstream reporting integrations.

## Team Roles

| Role | Name | Allocation |
|------|------|------------|
| Engagement Lead | David Park | 50% |
| Project Manager | Marcus Chen | 100% |
| Senior Data Engineer | Priya Sharma | 100% |
| Senior Data Engineer | Alex Thompson | 100% |
| Cloud Architect | Rachel Kim | 75% |

## Phases

### Phase 1: Assessment (March 4 – April 12, 2024)
**Duration:** 6 weeks
**Key Activities:**
- Inventory all Oracle schemas, tables, views, and stored procedures
- Document existing ETL pipelines (Informatica mappings, schedules, dependencies)
- Catalog downstream consumers (BI reports, data feeds, APIs)
- Assess data quality and identify transformation requirements
- Produce Current State Assessment Report

### Phase 2: Architecture Design (April 15 – May 17, 2024)
**Duration:** 5 weeks
**Key Activities:**
- Design target state architecture (Redshift, Glue, S3, Lake Formation)
- Define data model mapping from Oracle to Redshift
- Design ETL pipeline architecture in AWS Glue
- Define security model (IAM, encryption, VPC configuration)
- Produce Target State Architecture Document
- Architecture review with Client technical leadership

### Phase 3: Migration Execution (May 20 – July 26, 2024)
**Duration:** 10 weeks
**Key Activities:**
- Set up AWS infrastructure (Redshift cluster, Glue jobs, S3 buckets)
- Migrate schemas in priority order: Finance → Risk → Operations → HR → Compliance
- Rewrite 12 ETL pipelines from Informatica to AWS Glue
- Unit test each migrated schema and pipeline
- Produce Migration Runbook and Rollback Plan

### Phase 4: Validation and Transition (July 29 – August 30, 2024)
**Duration:** 5 weeks
**Key Activities:**
- Execute parallel run (30 business days)
- Compare Oracle and Redshift outputs for all critical reports
- Conduct 4 knowledge transfer sessions with Client data engineering team
- Resolve any discrepancies identified during parallel run
- Produce Parallel Run Validation Report
- Obtain Client sign-off

## Milestones

| Milestone | Target Date | Gate Criteria |
|-----------|-------------|---------------|
| Assessment Complete | April 12, 2024 | Assessment report delivered and accepted |
| Architecture Approved | May 17, 2024 | Architecture document approved by Client CTO |
| Migration 50% Complete | June 28, 2024 | 24 of 47 schemas migrated and tested |
| Migration Complete | July 26, 2024 | All 47 schemas and 12 pipelines migrated |
| Parallel Run Start | July 29, 2024 | All migration artifacts deployed to production |
| Final Sign-off | August 30, 2024 | Parallel run report accepted, knowledge transfer complete |

## Dependencies

- Client DBA team availability for schema documentation (8 hours/week minimum)
- AWS account provisioning and IAM role creation by Client Cloud team
- VPN access for Provider team members
- Source system freeze windows coordinated with business owners
- Client InfoSec approval of security architecture before Phase 3

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Undocumented Oracle stored procedures delay assessment | Medium | Medium | Allocate additional discovery time; engage Oracle DBA contractors if needed |
| Schema complexity exceeds estimate | Low | High | Architecture phase includes complexity scoring; will flag if >20% over estimate |
| Parallel run reveals data discrepancies | Medium | High | Build in 2-week buffer before final sign-off; define acceptable variance thresholds upfront |
| Client resource availability during migration | Medium | Medium | Secure named Client resources at SOW signing; escalation path to Engagement Lead |

## Communication Plan

- **Weekly Status Report:** Every Friday, distributed to Steering Committee
- **Bi-weekly Steering Committee:** Every other Wednesday, 60 minutes
- **Daily Standup (during Phase 3):** 15 minutes, Provider team + Client DBA lead
- **Ad-hoc Escalation:** Via Teams channel #data-migration, response within 4 hours

## Success Criteria

- All 47 production schemas migrated with zero data loss
- All 12 ETL pipelines operational in AWS Glue with performance within 20% of Oracle baseline
- Parallel run demonstrates <0.01% variance in critical report outputs
- Client data engineering team rated "confident" in post-KT survey (≥4/5 average)
- Project completed within budget ($400,000) and timeline (August 31, 2024)
