from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class OcrLine:
    text: str
    conf: float


@dataclass
class Field_:
    name: str
    value: str
    conf: float
    source: str = ""          # the OCR line the value came from (evidence)


@dataclass
class Issue:
    severity: str             # "error" | "warning" | "info"
    code: str
    message: str
    field: str = ""
    doc: str = ""
    conf: Optional[float] = None
    rescan: bool = False      # True => cause is scan quality, NOT forgery


@dataclass
class DocResult:
    filename: str
    doc_type: str = "unknown"
    ocr_conf: float = 0.0
    blur_score: float = 0.0
    seal_found: bool = False
    fields: dict = field(default_factory=dict)      # name -> Field_
    subjects: list = field(default_factory=list)    # [{subject, marks, max, conf}]
    issues: list = field(default_factory=list)      # list[Issue]
    text: str = ""

    def to_dict(self):
        d = asdict(self)
        d.pop("text", None)
        return d
