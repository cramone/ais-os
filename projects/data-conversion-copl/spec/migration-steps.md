# Migration Steps
_Captured: 2026-07-07_

Plan for executing the COPL data conversion end to end.

1. Copy the database from the development server
2. Restore to local server
3. Run path update scripts
```sql
UPDATE MAGIQ_DOCS_VERSIONS
SET PhysicalPath = REPLACE(PhysicalPath, '\\COPL\Live\', 's3://mgq-conversions/COPL/Live/')
WHERE PhysicalPath LIKE '%\\COPL\Live\%';

UPDATE MAGIQ_DOCS_VERSIONS
SET PhysicalPath = REPLACE(PhysicalPath, '\','/')
```
4. Export to JSON
5. Import from JSON
6. Verify
