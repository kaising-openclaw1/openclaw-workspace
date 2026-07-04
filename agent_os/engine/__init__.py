"""
Agent OS v7.0 — Engine 核心模块
================================
ChatGPT × Gemini 融合共识架构
"""

from .core_loop import (
    AgentLoop,
    Message,
    MessagePipeline,
    MessageRole,
    ModelAdapter,
    ModelResponse,
    StopReason,
    ToolDef,
    ToolEngine,
    create_default_tools,
)

from .validator import (
    SchemaValidator,
    StructuralValidator,
    ValidationResult,
    Validator,
)

from .artifact_store import (
    Artifact,
    ArtifactStore,
)

from .permission_racer import (
    Permission,
    PermissionRacer,
    PermissionRequest,
    PermissionResult,
    PolicyEngine,
    RiskClassifier,
    RiskLevel,
    UserConfirm,
)

from .context_pipeline import (
    ContextLayer,
    ContextPipeline,
    create_project_layer,
    create_session_layer,
    create_tool_layer,
)

from .adapters import (
    OpenAIAdapter,
    AnthropicAdapter,
)

__all__ = [
    # core_loop
    "AgentLoop",
    "Message",
    "MessagePipeline",
    "MessageRole",
    "ModelAdapter",
    "ModelResponse",
    "StopReason",
    "ToolDef",
    "ToolEngine",
    "create_default_tools",
    # validator
    "SchemaValidator",
    "StructuralValidator",
    "ValidationResult",
    "Validator",
    # artifact_store
    "Artifact",
    "ArtifactStore",
    # permission_racer
    "Permission",
    "PermissionRacer",
    "PermissionRequest",
    "PermissionResult",
    "PolicyEngine",
    "RiskClassifier",
    "RiskLevel",
    "UserConfirm",
    # context_pipeline
    "ContextLayer",
    "ContextPipeline",
    "create_project_layer",
    "create_session_layer",
    "create_tool_layer",
    # adapters
    "OpenAIAdapter",
    "AnthropicAdapter",
]
