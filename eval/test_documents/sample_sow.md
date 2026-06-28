# Statement of Work — Data Platform Modernization

**SOW Number:** SOW-2024-0042
**Effective Date:** March 1, 2024
**End Date:** August 31, 2024

## Parties

This Statement of Work ("SOW") is entered into between:
- **Client:** Meridian Financial Services, Inc. ("Client")
- **Service Provider:** Apex Consulting Group, LLC ("Provider")

This SOW is issued under and governed by the Master Services Agreement dated January 15, 2023 between Client and Provider (the "MSA").

## Project Overview

Provider will assist Client in modernizing its legacy data platform, migrating from on-premises Oracle data warehouse to a cloud-native architecture on AWS. The engagement covers assessment, architecture design, migration execution, and knowledge transfer.

## Scope of Work

### In Scope
- Current state assessment of existing Oracle data warehouse (schema, ETL, reports)
- Target state architecture design on AWS (Redshift, Glue, S3, Lake Formation)
- Data migration for 47 production schemas (~2.3TB total)
- Rewrite of 12 critical ETL pipelines from Informatica to AWS Glue
- Parallel run validation for 30 business days
- Knowledge transfer to Client's data engineering team (4 sessions)

### Out of Scope
- Migration of non-production or archived data
- Modifications to upstream source systems
- End-user training on BI tools
- Ongoing managed services post-migration

## Deliverables

1. Current State Assessment Report
2. Target State Architecture Document
3. Migration Runbook and Rollback Plan
4. Migrated schemas and ETL pipelines (in AWS)
5. Parallel Run Validation Report
6. Knowledge Transfer Materials and Session Recordings

## Milestones

| Milestone | Target Date | Payment |
|-----------|-------------|---------|
| SOW Execution | March 1, 2024 | $75,000 |
| Assessment Complete | April 15, 2024 | $50,000 |
| Architecture Approved | May 15, 2024 | $75,000 |
| Migration Complete | July 31, 2024 | $125,000 |
| Parallel Run Sign-off | August 31, 2024 | $75,000 |

## Total Engagement Value

$400,000 (Four Hundred Thousand Dollars), payable upon milestone completion as described above.

## Team and Rates

- Engagement Lead: $275/hour
- Senior Data Engineer (2): $225/hour each
- Cloud Architect: $250/hour
- Project Manager: $175/hour

## Assumptions

- Client will provide VPN access within 5 business days of SOW execution
- Client DBA team will be available for 8 hours/week for schema documentation
- AWS accounts and IAM roles will be provisioned by Client prior to architecture phase
- Source system freezes during migration windows will be coordinated 2 weeks in advance

## Payment Terms

Net 30 from invoice date. Invoices submitted upon milestone completion with supporting documentation.

## Termination

Either party may terminate this SOW with 30 days written notice. In the event of termination, Client will pay for all work completed through the termination date plus any non-cancelable expenses.
