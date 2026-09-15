# magiq-auth-serverless
_Captured: 2026-07-12T00:00:00Z_

## Description
Serverless Identity & Access platform for MAGIQ — supersedes the existing `magiq-auth` repo. Responsible for tenant management, authentication, RBAC, and token issuance across all MAGIQ services.

## Stack
TBD

## Modules
TBD

## Integrations
- magiq-media (upstream consumer)
- All other MAGIQ bounded context services

## ADO Board
Not yet assigned

## Priority
High

## Key Context
- Supersedes `magiq-auth` (existing Identity & Access repo)
- Responsibilities carried forward: tenants, auth, RBAC, token issuance
- Serverless architecture (cloud-native, no always-on server)
