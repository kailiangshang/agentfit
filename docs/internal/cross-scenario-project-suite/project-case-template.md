# ProjectCase Contract

This document defines the required sections of an AgentFit cross-scenario project package. It is a contract, not a completed project case.

## source_evidence

Lists accepted evidence IDs, claim boundaries, source dates, licenses, and reproducibility status.

## raw_materials

Describes the original task material, its provenance, authorization, redaction, and version.

## task_semantic_spec

Defines objective, input space, expected output, examples, distribution, metrics, trade-offs, thresholds, budgets, risks, failure costs, human boundaries, and evidence requirements.

## capability_semantic_registry

Defines the available rule, model, Skill, tool, MCP, human, state, and non-LLM analytical capabilities with contracts and constraints.

## task_capability_alignment

Records covered, partially covered, missing, conflicting, permission-limited, and unverifiable task requirements.

## candidate_space

Defines legal Agentless, fixed Workflow, single-Agent, multi-Agent, human-hybrid, degraded, and rejection candidates without presupposing the winner.

## adaptation_set

Contains the samples and feedback available to the inner loop.

## validation_set

Contains the samples available for candidate and architecture selection.

## holdout_set

Contains the independently protected samples used only for final audit.

## stress_and_failure_set

Contains malformed inputs, tool failures, permission denials, conflicting evidence, timeouts, unsafe actions, and recovery cases.

## budgets

Defines cost, latency, step, token, compute, and human-review limits.

## safety_constraints

Defines data, permission, approval, rollback, audit, refusal, and human-responsibility boundaries.

## evaluation_protocol

Defines baselines, metrics, hard gates, Pareto comparisons, ablations, statistical or human review, stopping, and rejection rules.

## expected_artifacts

Defines the required CandidateGraph, Trace, reports, decisions, deployment or rejection bundle, and reusable project asset.

## provenance_and_license

Records data lineage, source versions, licenses, third-party dependencies, commercial services, and redistribution constraints.

