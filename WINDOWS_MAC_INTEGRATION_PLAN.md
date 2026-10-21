# Windows / Mac integration plan

**Status: READ-ONLY PLANNING ONLY.**
Nothing in this document authorises a connection, a file transfer, a remote command, or a Mac workload.

This planning pass performs no SSH, SCP, SFTP, or other remote action.

## Current operating model

- The Windows machine is the controller and the authoritative source of truth for this project.
- A Mac mini M4 Pro may later be proposed as a bounded compute worker.
- There is no blanket authorisation to use the Mac for this project or for any other project.
- Portfolio Risk X-Ray and every other existing project are outside this plan.

## V1 may not need the Mac

The proposed V1 calculations are moving averages, returns, a 21-return realised volatility, a trailing percentile, and a rule table. On a modest asset universe those steps are small. This plan does not authorise implementing them.

Remote execution is not justified until a Windows-versus-Mac benchmark on a representative finance workload shows a material benefit. If the benchmark does not show that benefit, V1 runs entirely on Windows.

## Candidate future Mac workloads

Only after the benchmark and the controls below. None of these are approved:

- historical-data transformation
- batch regime calculations
- parameter sweeps
- historical backtests
- scenario batches

Live trading, order routing, credential handling, and ad-hoc shell access are not candidate workloads.

## Required before any Mac integration

All of the following are prerequisites. Satisfying one does not imply the next.

1. **Benchmark.** Compare Windows and Mac on a representative, non-secret finance workload of the approved V1 calculations. Record runtime, hardware, input size, and software versions. The owner decides whether the difference justifies a worker.
2. **Project-specific staging folders.** Separate Windows and Mac directories used only by Market Regime Monitor. No shared drop folder with other projects.
3. **Canonical path allowlists.** The job may read and write only those staging paths. Paths outside the list fail the job before execution.
4. **Fixed approved job profiles.** A named profile lists the command, the parameters, the input schema, and the output schema. Interactive shells and arbitrary commands are not profiles.
5. **Input and output schemas.** Versioned, documented, and validated on both sides. An output that does not match the schema is rejected.
6. **Hashes.** Inputs are hashed before transfer. Outputs are hashed by the worker and checked on Windows.
7. **Dry run.** The profile is executed in a mode that validates paths, schema, and parameters without publishing results, and the owner reviews that dry run.
8. **Owner approval.** A written approval names the profile, the input hash, and the single execution being authorised.
9. **One bounded execution.** One approved profile, one input, one output location. No retries beyond what the approval names.
10. **Returned-output verification.** Windows recomputes the output hash, validates the schema, and only then accepts the result as a candidate for review. Acceptance is not automatic promotion into the authoritative project data.

## What this document does not do

- It does not authorise Mac integration.
- It does not select a transport.
- It does not create staging folders, keys, or host configuration.
- It does not permit a standing connection.
