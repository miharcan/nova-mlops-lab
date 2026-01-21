from __future__ import annotations

from typing import Dict, Literal, Optional

try:
    # pydantic v2
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover
    # pydantic v1 fallback
    from pydantic import BaseModel, Field  # type: ignore


class Resources(BaseModel):
    cloud: Literal["local", "openstack"] = "local"
    flavor: Optional[str] = None
    image: Optional[str] = None
    network: Optional[str] = None
    security_group: Optional[str] = None
    volume_gb: Optional[int] = None
    keypair: Optional[str] = None


class RunSpec(BaseModel):
    entrypoint: str
    args: Dict[str, object] = Field(default_factory=dict)


class ArtifactSpec(BaseModel):
    output_dir: str = "artifacts"


class JobSpec(BaseModel):
    name: str
    resources: Resources = Field(default_factory=Resources)
    run: RunSpec
    artifacts: ArtifactSpec = Field(default_factory=ArtifactSpec)

    # compatibility helper
    @classmethod
    def from_dict(cls, data: dict) -> "JobSpec":
        # pydantic v2 uses model_validate, v1 uses parse_obj
        if hasattr(cls, "model_validate"):
            return cls.model_validate(data)  # type: ignore[attr-defined]
        return cls.parse_obj(data)  # type: ignore[attr-defined]
