# Processing — Business Scenarios

_Context: `Processing`_

> **Scenarios now live under each aggregate.** This file is an index only.

---

## Index

| # | Scenario | Key Aggregates | File |
|---|---|---|---|
| P-1 | Full Processing Pipeline (Image Asset) | ProcessingJob, Asset | [processingjob.scenarios.md](aggregates/ProcessingJob/processingjob.scenarios.md) |
| P-2 | Document Asset — Fast Exit (No Processing Capability) | ProcessingJob, Asset | [processingjob.scenarios.md](aggregates/ProcessingJob/processingjob.scenarios.md) |
| P-3 | Processing Pipeline Failure Recovery (Saga Timeout) | ProcessingJob, Asset, AssetIngestionSaga | [processingjob.scenarios.md](aggregates/ProcessingJob/processingjob.scenarios.md) |

---

## Related

- [ProcessingJob Scenarios](aggregates/ProcessingJob/processingjob.scenarios.md)
- [AssetManagement Business Scenarios](../AssetManagement/business-scenarios.md)

<!-- Scenario bodies removed — see aggregate scenario files above -->
