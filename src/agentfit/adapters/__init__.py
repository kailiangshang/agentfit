"""Platform-neutral adapter contracts for production integrations."""

from .protocols import (CognitiveAdapter, CognitiveRequest, CognitiveResult,
                        EvidenceReference, RetrievalAdapter, RetrievalQuery,
                        RetrievedEvidence, SandboxAdapter, SandboxRequest,
                        SandboxResult)

__all__ = [
    "CognitiveAdapter", "CognitiveRequest", "CognitiveResult",
    "EvidenceReference", "RetrievalAdapter", "RetrievalQuery",
    "RetrievedEvidence", "SandboxAdapter", "SandboxRequest", "SandboxResult",
]
