## Team 71 Jiejun Xie 1418316 Anqi Liao 1578312 Xinhe Liu 1477404 Yifu Chen 1609437 Kexing Ma 1697372

This directory contains unit tests for verifying the functionality and API routing of the Fission-based YouTube data processing system.

## Files

- **test_route_api.py**  
  Tests the REST API routes for querying processed YouTube data from Elasticsearch. Includes parameterized date range tests and response validation.

- **test_route_harvester.py**  
  Tests the Fission harvester routes that collect and send YouTube video data into the Elasticsearch backend. Verifies endpoint behavior and ingestion logs.

- **.gitkeep**  
  Keeps the `logs/` directory in version control even when empty.

- **logs/**  
  Contains API and harvester logs generated during test execution. Useful for debugging and historical reference.