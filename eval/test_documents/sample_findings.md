# Cloud Infrastructure Security Assessment — Findings Report

**Assessment Title:** Annual Cloud Infrastructure Security Assessment
**Assessment Date:** May 15, 2024
**Prepared By:** Pinnacle Security Advisors, LLC
**Client:** Meridian Financial Services, Inc.

## Executive Summary

Pinnacle Security Advisors conducted a comprehensive security assessment of Meridian Financial Services' AWS cloud infrastructure during the period April 15–May 10, 2024. The assessment covered 3 production accounts, 2 staging accounts, and the centralized networking account. Overall, Meridian's cloud security posture is rated **Moderate Risk** — foundational controls are in place, but several gaps in IAM governance, network segmentation, and data encryption practices require remediation before the upcoming regulatory examination.

## Scope

The assessment covered the following areas:
- Identity and Access Management (IAM policies, roles, MFA enforcement)
- Network architecture and segmentation (VPCs, security groups, NACLs)
- Data protection (encryption at rest and in transit, key management)
- Logging and monitoring (CloudTrail, GuardDuty, Config Rules)
- Incident response readiness
- Compliance alignment with FFIEC IT Examination Handbook and NIST CSF

## Methodology

The assessment was conducted using a combination of automated scanning (Prowler, ScoutSuite), manual configuration review, and interviews with Meridian's Cloud Engineering and InfoSec teams. Findings are rated using a four-level severity scale: Critical, High, Medium, Low.

## Findings

### Finding 1: Overly Permissive IAM Policies
**Severity:** Critical
**Description:** 14 IAM roles across production accounts use wildcard (*) permissions for S3 and Lambda actions. Three roles have full AdministratorAccess attached, including one used by an automated deployment pipeline.
**Evidence:** IAM policy analysis via Prowler identified 14 roles with overly broad permissions. The deployment pipeline role (role: cicd-deploy-prod) has AdministratorAccess with no condition keys or resource restrictions.
**Recommendation:** Implement least-privilege policies for all production roles. Replace AdministratorAccess on the CI/CD role with scoped permissions limited to the specific services and resources required for deployment. Target remediation: 30 days.

### Finding 2: Unencrypted S3 Buckets Containing Customer Data
**Severity:** High
**Description:** 3 of 28 production S3 buckets do not have default encryption enabled. Two of these buckets contain customer PII based on naming conventions and sample object inspection.
**Evidence:** ScoutSuite scan identified buckets meridian-customer-exports, meridian-reports-archive, and meridian-temp-processing without default encryption. Object-level inspection confirmed PII presence in the first two buckets.
**Recommendation:** Enable SSE-S3 or SSE-KMS default encryption on all production buckets immediately. Implement an SCP (Service Control Policy) to prevent creation of unencrypted buckets. Target remediation: 14 days.

### Finding 3: Incomplete CloudTrail Coverage
**Severity:** Medium
**Description:** CloudTrail is enabled in all production accounts but data event logging is not enabled for S3 object-level operations or Lambda invocations. This limits the ability to investigate data access incidents.
**Evidence:** CloudTrail configuration review confirmed that only management events are being logged. S3 data events and Lambda data events are not captured.
**Recommendation:** Enable S3 data event logging for all buckets containing sensitive data. Enable Lambda data event logging for production functions. Estimated additional cost: ~$200/month based on current event volume. Target remediation: 30 days.

### Finding 4: Security Groups Allow Unrestricted SSH Access
**Severity:** Medium
**Description:** 7 security groups in the production VPC allow inbound SSH (port 22) from 0.0.0.0/0. While no EC2 instances currently have public IPs, this represents a latent risk if instances are later assigned public IPs or if VPC peering is modified.
**Evidence:** Security group analysis identified sg-0a1b2c3d4e, sg-1f2g3h4i5j, and 5 others with inbound rule allowing TCP 22 from 0.0.0.0/0.
**Recommendation:** Restrict SSH access to specific CIDR ranges (corporate VPN and bastion host IPs only). Implement AWS Systems Manager Session Manager as the primary remote access method. Target remediation: 14 days.

### Finding 5: No Formal Incident Response Runbook for Cloud
**Severity:** Low
**Description:** Meridian has a general incident response plan but lacks cloud-specific runbooks for common scenarios (compromised credentials, unauthorized data access, resource hijacking).
**Evidence:** Interview with InfoSec team confirmed that the existing IR plan references on-premises procedures. Cloud-specific playbooks have not been developed despite 18 months of production cloud usage.
**Recommendation:** Develop cloud-specific IR runbooks for the top 5 incident scenarios. Conduct a tabletop exercise within 60 days. Target remediation: 60 days.

## Recommendations Summary

| # | Finding | Severity | Remediation Target |
|---|---------|----------|-------------------|
| 1 | Overly Permissive IAM Policies | Critical | 30 days |
| 2 | Unencrypted S3 Buckets with PII | High | 14 days |
| 3 | Incomplete CloudTrail Coverage | Medium | 30 days |
| 4 | Unrestricted SSH Security Groups | Medium | 14 days |
| 5 | No Cloud IR Runbooks | Low | 60 days |

## Overall Risk Rating

**Moderate Risk** — Foundational security controls are in place (GuardDuty active, Config Rules deployed, MFA enforced for console access), but the combination of overly permissive IAM policies and unencrypted customer data buckets presents material risk that should be addressed prior to the Q3 regulatory examination.

## Standards Referenced

- FFIEC IT Examination Handbook — Information Security
- NIST Cybersecurity Framework (CSF) v2.0
- CIS AWS Foundations Benchmark v3.0
- AWS Well-Architected Framework — Security Pillar
