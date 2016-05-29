# LiPyc - a light picture manager

## Features
- Replication, and load-balancing between storage sources
- File encryption
- File deduplication at application scale
- Pictures' similarities detection

## Restriction
- Not suitable for big databases
- No restauration tool, yet
- Storage sources must be mounted in user-space

## Dependencies
- PyCrypto
- TKinter
- Pillow
- opencv

## Configuration
- pgs.json : define the placement groups use for replication and loadbalancing
