"""
LitigationOS Delta999 Agent Fleet + legacy agents.

Delta999 Super-Agents:
    delta999_orchestrator         — Master dispatcher and pipeline runner
    delta999_coa_agent            — COA 366810 specialist (MCR 7.212)
    delta999_evidence_chain_agent — Evidence search, chains, Bates numbering
    delta999_citation_agent       — Legal authority validator
    delta999_compliance_agent     — Filing compliance checker
    delta999_rebuttal_agent       — Adversary rebuttal specialist
    delta999_redteam_agent        — War-gaming and vulnerability assessment
"""

__all__ = [
    "delta999_orchestrator",
    "delta999_coa_agent",
    "delta999_evidence_chain_agent",
    "delta999_citation_agent",
    "delta999_compliance_agent",
    "delta999_rebuttal_agent",
    "delta999_redteam_agent",
]

# Delta999 fleet imports (lazy — only loaded when accessed)
from . import delta999_orchestrator
from . import delta999_coa_agent
from . import delta999_evidence_chain_agent
from . import delta999_citation_agent
from . import delta999_compliance_agent
from . import delta999_rebuttal_agent
from . import delta999_redteam_agent
