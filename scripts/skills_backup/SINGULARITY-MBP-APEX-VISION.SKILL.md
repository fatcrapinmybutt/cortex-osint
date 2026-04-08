---
name: SINGULARITY-MBP-APEX-VISION
description: "Document AI and OCR pipeline for litigation evidence. PaddleOCR multimodal extraction, Surya layout-aware OCR, PP-StructureV3 table and form detection, court form recognition, handwriting OCR, multi-engine ensemble with confidence voting, legal entity extraction from scanned documents, Bates stamp detection, exhibit classification, Michigan court form template matching."
version: "1.0.0"
tier: "TIER-7/APEX"
domain: "Document AI — OCR, layout analysis, form recognition, evidence extraction"
triggers:
  - OCR
  - document AI
  - scan
  - PDF extraction
  - form recognition
  - layout analysis
  - table detection
  - handwriting
  - Bates stamp
  - exhibit scan
---

# SINGULARITY-MBP-APEX-VISION v1.0

> **The all-seeing eye that turns scanned chaos into structured litigation intelligence.**
> Every page, every handwritten note, every faded court form — extracted, classified, weaponized.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    APEX-VISION Pipeline                      │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐ │
│  │ Ingest   │→ │ OCR      │→ │ Layout   │→ │ Extract    │ │
│  │ Scanner  │  │ Ensemble │  │ Analyzer │  │ Pipeline   │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘ │
│       ↓              ↓             ↓              ↓        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐ │
│  │ Form     │→ │ Lane     │→ │ Bates    │→ │ Evidence   │ │
│  │ Matcher  │  │ Router   │  │ Stamper  │  │ Persister  │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘ │
│                                                             │
│  Engines: PaddleOCR · Surya · pypdfium2 · Tesseract        │
│  Output: evidence_quotes · timeline_events · exhibit index  │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Multi-Engine OCR Ensemble

### 1.1 Engine Abstraction Layer

```python
"""
Multi-engine OCR ensemble with confidence-weighted voting.
Each engine is isolated — if one crashes, others continue.
"""
from __future__ import annotations
import re
import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@dataclass
class OCRWord:
    """Single word extracted by OCR with position and confidence."""
    text: str
    confidence: float  # 0.0 - 1.0
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    engine: str
    page: int = 0
    line_idx: int = 0

    @property
    def area(self) -> int:
        return (self.bbox[2] - self.bbox[0]) * (self.bbox[3] - self.bbox[1])


@dataclass
class OCRLine:
    """A line of text with constituent words."""
    text: str
    words: list[OCRWord]
    confidence: float
    bbox: tuple[int, int, int, int]
    page: int = 0

    @classmethod
    def from_words(cls, words: list[OCRWord], page: int = 0) -> OCRLine:
        if not words:
            return cls(text="", words=[], confidence=0.0, bbox=(0, 0, 0, 0), page=page)
        text = " ".join(w.text for w in words)
        conf = sum(w.confidence for w in words) / len(words)
        x1 = min(w.bbox[0] for w in words)
        y1 = min(w.bbox[1] for w in words)
        x2 = max(w.bbox[2] for w in words)
        y2 = max(w.bbox[3] for w in words)
        return cls(text=text, words=words, confidence=conf, bbox=(x1, y1, x2, y2), page=page)


@dataclass
class OCRPage:
    """Full page OCR result."""
    page_number: int
    lines: list[OCRLine]
    width: int
    height: int
    confidence: float
    engine: str
    raw_text: str = ""
    processing_time_ms: float = 0.0

    @property
    def text(self) -> str:
        if self.raw_text:
            return self.raw_text
        return "\n".join(line.text for line in self.lines)

    @property
    def word_count(self) -> int:
        return sum(len(line.words) for line in self.lines)


@dataclass
class OCRResult:
    """Complete document OCR result."""
    file_path: str
    pages: list[OCRPage]
    engine: str
    total_confidence: float
    processing_time_ms: float
    metadata: dict = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        return "\n\n".join(page.text for page in self.pages)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def content_hash(self) -> str:
        return hashlib.sha256(self.full_text.encode('utf-8')).hexdigest()


@runtime_checkable
class OCREngine(Protocol):
    """Protocol for OCR engine implementations."""
    name: str
    def extract(self, file_path: str, pages: list[int] | None = None) -> OCRResult: ...
    def is_available(self) -> bool: ...
    def supported_formats(self) -> list[str]: ...


class PaddleOCREngine:
    """PaddleOCR engine — best for printed text and mixed layouts."""
    name = "paddleocr"

    def __init__(self, use_gpu: bool = False, lang: str = "en"):
        self._ocr = None
        self._use_gpu = use_gpu
        self._lang = lang

    def _lazy_init(self):
        if self._ocr is None:
            try:
                from paddleocr import PaddleOCR
                self._ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang=self._lang,
                    use_gpu=self._use_gpu,
                    show_log=False,
                    det_db_thresh=0.3,
                    det_db_box_thresh=0.5,
                    rec_batch_num=16
                )
            except ImportError:
                logger.warning("PaddleOCR not installed — pip install paddleocr")
                raise

    def is_available(self) -> bool:
        try:
            self._lazy_init()
            return True
        except Exception:
            return False

    def supported_formats(self) -> list[str]:
        return [".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"]

    def extract(self, file_path: str, pages: list[int] | None = None) -> OCRResult:
        import time
        start = time.perf_counter()
        self._lazy_init()

        file_ext = Path(file_path).suffix.lower()
        ocr_pages = []

        if file_ext == ".pdf":
            ocr_pages = self._extract_pdf(file_path, pages)
        else:
            ocr_pages = [self._extract_image(file_path, page_num=0)]

        elapsed = (time.perf_counter() - start) * 1000
        total_conf = (
            sum(p.confidence for p in ocr_pages) / len(ocr_pages) if ocr_pages else 0
        )

        return OCRResult(
            file_path=file_path,
            pages=ocr_pages,
            engine=self.name,
            total_confidence=total_conf,
            processing_time_ms=elapsed
        )

    def _extract_pdf(self, file_path: str, pages: list[int] | None) -> list[OCRPage]:
        """Extract from PDF using pypdfium2 for rendering + PaddleOCR for recognition."""
        try:
            import pypdfium2 as pdfium
        except ImportError:
            logger.error("pypdfium2 required for PDF OCR")
            return []

        import tempfile
        doc = pdfium.PdfDocument(file_path)
        result_pages = []
        target_pages = pages or list(range(len(doc)))

        for pg_idx in target_pages:
            if pg_idx >= len(doc):
                continue
            page = doc[pg_idx]
            # Render at 300 DPI for OCR quality
            bitmap = page.render(scale=300 / 72)
            pil_image = bitmap.to_pil()

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                pil_image.save(tmp.name)
                ocr_page = self._extract_image(tmp.name, page_num=pg_idx)
                ocr_page.width = pil_image.width
                ocr_page.height = pil_image.height
                result_pages.append(ocr_page)
                Path(tmp.name).unlink(missing_ok=True)

        doc.close()
        return result_pages

    def _extract_image(self, img_path: str, page_num: int = 0) -> OCRPage:
        """Extract text from a single image."""
        import time
        start = time.perf_counter()
        result = self._ocr.ocr(img_path, cls=True)

        lines = []
        if result and result[0]:
            for line_data in result[0]:
                box = line_data[0]
                text = line_data[1][0]
                conf = line_data[1][1]

                x1 = int(min(p[0] for p in box))
                y1 = int(min(p[1] for p in box))
                x2 = int(max(p[0] for p in box))
                y2 = int(max(p[1] for p in box))

                word = OCRWord(
                    text=text, confidence=conf,
                    bbox=(x1, y1, x2, y2), engine=self.name,
                    page=page_num
                )
                ocr_line = OCRLine(
                    text=text, words=[word],
                    confidence=conf, bbox=(x1, y1, x2, y2),
                    page=page_num
                )
                lines.append(ocr_line)

        # Sort by Y position for reading order
        lines.sort(key=lambda ln: ln.bbox[1])
        elapsed = (time.perf_counter() - start) * 1000
        avg_conf = sum(ln.confidence for ln in lines) / len(lines) if lines else 0

        return OCRPage(
            page_number=page_num, lines=lines,
            width=0, height=0, confidence=avg_conf,
            engine=self.name, processing_time_ms=elapsed
        )


class SuryaOCREngine:
    """Surya OCR engine — layout-aware, best for complex document structures."""
    name = "surya"

    def __init__(self):
        self._model = None
        self._det_model = None

    def _lazy_init(self):
        if self._model is None:
            try:
                from surya.recognition import RecognitionPredictor
                from surya.detection import DetectionPredictor
                self._model = RecognitionPredictor()
                self._det_model = DetectionPredictor()
            except ImportError:
                logger.warning("Surya not installed — pip install surya-ocr")
                raise

    def is_available(self) -> bool:
        try:
            self._lazy_init()
            return True
        except Exception:
            return False

    def supported_formats(self) -> list[str]:
        return [".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff"]

    def extract(self, file_path: str, pages: list[int] | None = None) -> OCRResult:
        import time
        start = time.perf_counter()
        self._lazy_init()

        from PIL import Image
        images = self._load_images(file_path, pages)
        ocr_pages = []

        for pg_idx, img in enumerate(images):
            page_result = self._process_image(img, pg_idx)
            ocr_pages.append(page_result)

        elapsed = (time.perf_counter() - start) * 1000
        total_conf = sum(p.confidence for p in ocr_pages) / len(ocr_pages) if ocr_pages else 0

        return OCRResult(
            file_path=file_path, pages=ocr_pages,
            engine=self.name, total_confidence=total_conf,
            processing_time_ms=elapsed
        )

    def _load_images(self, file_path: str, pages: list[int] | None) -> list:
        from PIL import Image
        ext = Path(file_path).suffix.lower()
        if ext == ".pdf":
            try:
                import pypdfium2 as pdfium
                doc = pdfium.PdfDocument(file_path)
                target = pages or list(range(len(doc)))
                imgs = []
                for idx in target:
                    if idx < len(doc):
                        bmp = doc[idx].render(scale=300 / 72)
                        imgs.append(bmp.to_pil())
                doc.close()
                return imgs
            except ImportError:
                return []
        else:
            return [Image.open(file_path)]

    def _process_image(self, image, page_num: int) -> OCRPage:
        from surya.detection import DetectionPredictor
        from surya.recognition import RecognitionPredictor

        det_results = self._det_model([image])
        rec_results = self._model([image], det_results[0])

        lines = []
        for text_line in rec_results[0].text_lines:
            bbox = (
                int(text_line.bbox[0]), int(text_line.bbox[1]),
                int(text_line.bbox[2]), int(text_line.bbox[3])
            )
            word = OCRWord(
                text=text_line.text, confidence=text_line.confidence,
                bbox=bbox, engine=self.name, page=page_num
            )
            line = OCRLine(
                text=text_line.text, words=[word],
                confidence=text_line.confidence, bbox=bbox, page=page_num
            )
            lines.append(line)

        lines.sort(key=lambda ln: ln.bbox[1])
        avg_conf = sum(ln.confidence for ln in lines) / len(lines) if lines else 0
        return OCRPage(
            page_number=page_num, lines=lines,
            width=image.width, height=image.height,
            confidence=avg_conf, engine=self.name
        )


class PyPDFium2Engine:
    """pypdfium2 engine — fastest for native (non-scanned) PDFs."""
    name = "pypdfium2"

    def is_available(self) -> bool:
        try:
            import pypdfium2
            return True
        except ImportError:
            return False

    def supported_formats(self) -> list[str]:
        return [".pdf"]

    def extract(self, file_path: str, pages: list[int] | None = None) -> OCRResult:
        import time
        import pypdfium2 as pdfium

        start = time.perf_counter()
        doc = pdfium.PdfDocument(file_path)
        target_pages = pages or list(range(len(doc)))
        ocr_pages = []

        for pg_idx in target_pages:
            if pg_idx >= len(doc):
                continue
            page = doc[pg_idx]
            text = page.get_textpage().get_text_range()

            ocr_page = OCRPage(
                page_number=pg_idx,
                lines=[],
                width=int(page.get_width()),
                height=int(page.get_height()),
                confidence=1.0 if text.strip() else 0.0,
                engine=self.name,
                raw_text=text
            )
            ocr_pages.append(ocr_page)

        doc.close()
        elapsed = (time.perf_counter() - start) * 1000
        total_conf = sum(p.confidence for p in ocr_pages) / len(ocr_pages) if ocr_pages else 0

        return OCRResult(
            file_path=file_path, pages=ocr_pages,
            engine=self.name, total_confidence=total_conf,
            processing_time_ms=elapsed
        )


class TesseractEngine:
    """Tesseract fallback engine — widely available, lower accuracy."""
    name = "tesseract"

    def __init__(self, lang: str = "eng", psm: int = 3):
        self._lang = lang
        self._psm = psm

    def is_available(self) -> bool:
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def supported_formats(self) -> list[str]:
        return [".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"]

    def extract(self, file_path: str, pages: list[int] | None = None) -> OCRResult:
        import time
        import pytesseract
        from PIL import Image

        start = time.perf_counter()
        ext = Path(file_path).suffix.lower()
        images = []

        if ext == ".pdf":
            try:
                import pypdfium2 as pdfium
                doc = pdfium.PdfDocument(file_path)
                target = pages or list(range(len(doc)))
                for idx in target:
                    if idx < len(doc):
                        bmp = doc[idx].render(scale=300 / 72)
                        images.append((idx, bmp.to_pil()))
                doc.close()
            except ImportError:
                return OCRResult(file_path=file_path, pages=[], engine=self.name,
                               total_confidence=0, processing_time_ms=0)
        else:
            images = [(0, Image.open(file_path))]

        ocr_pages = []
        for pg_idx, img in images:
            data = pytesseract.image_to_data(
                img, lang=self._lang,
                config=f"--psm {self._psm}",
                output_type=pytesseract.Output.DICT
            )
            lines = self._parse_tesseract_data(data, pg_idx)
            avg_conf = sum(ln.confidence for ln in lines) / len(lines) if lines else 0

            ocr_pages.append(OCRPage(
                page_number=pg_idx, lines=lines,
                width=img.width, height=img.height,
                confidence=avg_conf, engine=self.name
            ))

        elapsed = (time.perf_counter() - start) * 1000
        total_conf = sum(p.confidence for p in ocr_pages) / len(ocr_pages) if ocr_pages else 0

        return OCRResult(
            file_path=file_path, pages=ocr_pages,
            engine=self.name, total_confidence=total_conf,
            processing_time_ms=elapsed
        )

    def _parse_tesseract_data(self, data: dict, page_num: int) -> list[OCRLine]:
        lines: dict[int, list[OCRWord]] = {}
        n = len(data['text'])

        for i in range(n):
            text = data['text'][i].strip()
            conf = float(data['conf'][i])
            if not text or conf < 0:
                continue

            line_num = data['line_num'][i]
            word = OCRWord(
                text=text, confidence=conf / 100.0,
                bbox=(data['left'][i], data['top'][i],
                      data['left'][i] + data['width'][i],
                      data['top'][i] + data['height'][i]),
                engine=self.name, page=page_num, line_idx=line_num
            )
            lines.setdefault(line_num, []).append(word)

        return [OCRLine.from_words(words, page_num) for words in lines.values()]
```

### 1.2 Confidence-Weighted Ensemble Voter

```python
class OCREnsemble:
    """
    Multi-engine OCR with confidence-weighted voting.
    Runs available engines, fuses results at word level.
    """

    def __init__(self, engines: list[OCREngine] | None = None):
        if engines is None:
            engines = self._discover_engines()
        self.engines = [e for e in engines if e.is_available()]
        self._weights = {
            "paddleocr": 1.2,
            "surya": 1.3,
            "pypdfium2": 1.5,  # native text is highest confidence
            "tesseract": 0.8
        }
        logger.info(f"OCR Ensemble initialized: {[e.name for e in self.engines]}")

    def _discover_engines(self) -> list[OCREngine]:
        candidates: list[OCREngine] = [
            PyPDFium2Engine(),
            PaddleOCREngine(),
            SuryaOCREngine(),
            TesseractEngine(),
        ]
        return candidates

    def extract(self, file_path: str, pages: list[int] | None = None,
                min_engines: int = 1) -> OCRResult:
        """
        Run all available engines, fuse results.
        If native PDF text (pypdfium2) has >90% confidence, skip OCR engines.
        """
        results: list[OCRResult] = []
        errors: list[str] = []

        # Try native extraction first (fastest)
        native_result = self._try_native(file_path, pages)
        if native_result and native_result.total_confidence > 0.9:
            logger.info(f"Native PDF text sufficient (conf={native_result.total_confidence:.2f})")
            return native_result

        # Run OCR engines
        for engine in self.engines:
            if engine.name == "pypdfium2":
                if native_result:
                    results.append(native_result)
                continue
            ext = Path(file_path).suffix.lower()
            if ext not in engine.supported_formats():
                continue
            try:
                result = engine.extract(file_path, pages)
                results.append(result)
                logger.info(f"{engine.name}: conf={result.total_confidence:.2f}, "
                           f"time={result.processing_time_ms:.0f}ms")
            except Exception as e:
                errors.append(f"{engine.name}: {e}")
                logger.error(f"Engine {engine.name} failed: {e}")

        if not results:
            raise RuntimeError(f"All OCR engines failed: {errors}")

        # Single engine — return directly
        if len(results) == 1:
            return results[0]

        # Multi-engine fusion
        return self._fuse_results(results, file_path)

    def _try_native(self, file_path: str, pages: list[int] | None) -> OCRResult | None:
        if Path(file_path).suffix.lower() != ".pdf":
            return None
        for engine in self.engines:
            if engine.name == "pypdfium2":
                try:
                    return engine.extract(file_path, pages)
                except Exception:
                    return None
        return None

    def _fuse_results(self, results: list[OCRResult], file_path: str) -> OCRResult:
        """
        Fuse results from multiple engines using confidence-weighted voting.
        For each page position, pick the line with highest weighted confidence.
        """
        # Group by page number
        page_results: dict[int, list[tuple[OCRPage, str]]] = {}
        for result in results:
            for page in result.pages:
                page_results.setdefault(page.page_number, []).append(
                    (page, result.engine)
                )

        fused_pages = []
        for pg_num in sorted(page_results.keys()):
            candidates = page_results[pg_num]
            best_page = self._pick_best_page(candidates)
            fused_pages.append(best_page)

        total_conf = (
            sum(p.confidence for p in fused_pages) / len(fused_pages)
            if fused_pages else 0
        )
        total_time = sum(r.processing_time_ms for r in results)

        return OCRResult(
            file_path=file_path,
            pages=fused_pages,
            engine="ensemble",
            total_confidence=total_conf,
            processing_time_ms=total_time,
            metadata={"engines_used": [r.engine for r in results]}
        )

    def _pick_best_page(self, candidates: list[tuple[OCRPage, str]]) -> OCRPage:
        """Pick the best page result using weighted confidence scoring."""
        best_score = -1.0
        best_page = candidates[0][0]

        for page, engine_name in candidates:
            weight = self._weights.get(engine_name, 1.0)
            word_count_bonus = min(page.word_count / 100, 0.3)
            score = page.confidence * weight + word_count_bonus

            if score > best_score:
                best_score = score
                best_page = page

        return best_page

    def benchmark(self, file_path: str) -> dict:
        """Run all engines and compare results."""
        results = {}
        for engine in self.engines:
            ext = Path(file_path).suffix.lower()
            if ext not in engine.supported_formats():
                continue
            try:
                result = engine.extract(file_path)
                results[engine.name] = {
                    "confidence": result.total_confidence,
                    "time_ms": result.processing_time_ms,
                    "pages": result.page_count,
                    "words": sum(p.word_count for p in result.pages),
                    "text_preview": result.full_text[:200]
                }
            except Exception as e:
                results[engine.name] = {"error": str(e)}
        return results
```

---

## Layer 2: Layout-Aware Document Analysis

### 2.1 Document Zone Classifier

```python
"""
Layout analysis for legal documents.
Detects document structure: caption, body, signature block, COS, exhibits.
"""
from enum import Enum
from dataclasses import dataclass, field


class DocumentZone(Enum):
    """Legal document structural zones."""
    CAPTION = "caption"
    CASE_NUMBER = "case_number"
    TITLE = "title"
    BODY = "body"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    LIST = "list"
    SIGNATURE_BLOCK = "signature_block"
    CERTIFICATE_OF_SERVICE = "certificate_of_service"
    FOOTER = "footer"
    HEADER = "header"
    PAGE_NUMBER = "page_number"
    EXHIBIT_LABEL = "exhibit_label"
    BATES_STAMP = "bates_stamp"
    HANDWRITTEN = "handwritten"
    NOTARY = "notary"
    COURT_SEAL = "court_seal"
    UNKNOWN = "unknown"


@dataclass
class LayoutRegion:
    """A detected region within a document page."""
    zone: DocumentZone
    bbox: tuple[int, int, int, int]
    text: str
    confidence: float
    page: int
    children: list['LayoutRegion'] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class PageLayout:
    """Complete layout analysis for a single page."""
    page_number: int
    width: int
    height: int
    regions: list[LayoutRegion]
    reading_order: list[int]  # indices into regions
    column_count: int = 1
    has_table: bool = False
    has_handwriting: bool = False

    @property
    def ordered_text(self) -> str:
        return "\n".join(self.regions[i].text for i in self.reading_order
                        if i < len(self.regions))


class LegalDocumentAnalyzer:
    """
    Analyze legal document structure.
    Identifies caption, body, signature, COS, exhibits, and Bates stamps.
    """

    # Michigan court caption patterns
    CAPTION_PATTERNS = [
        r"STATE\s+OF\s+MICHIGAN",
        r"IN\s+THE\s+CIRCUIT\s+COURT",
        r"IN\s+THE\s+COURT\s+OF\s+APPEALS",
        r"IN\s+THE\s+SUPREME\s+COURT",
        r"(?:14TH|FOURTEENTH)\s+(?:JUDICIAL\s+)?CIRCUIT",
        r"COUNTY\s+OF\s+MUSKEGON",
        r"60TH\s+DISTRICT\s+COURT",
    ]

    CASE_NUMBER_PATTERNS = [
        r"(?:Case|No|File)\s*(?:No\.?)?\s*:?\s*(\d{4}[-–]\d{4,8}[-–][A-Z]{2})",
        r"(\d{4}[-–]\d{6,8}[-–][A-Z]{2,4})",
        r"COA\s*(?:No\.?)?\s*:?\s*(\d{5,6})",
        r"(\d{4}[-–]\d{5,8}(?:SM|DC|CZ|PP|FC|DM))",
    ]

    COS_PATTERNS = [
        r"CERTIFICATE\s+OF\s+SERVICE",
        r"PROOF\s+OF\s+SERVICE",
        r"I\s+(?:hereby\s+)?certify\s+that",
        r"served\s+(?:a\s+(?:true\s+)?copy|this)",
    ]

    SIGNATURE_PATTERNS = [
        r"Respectfully\s+submitted",
        r"(?:Dated|Date)\s*:\s*",
        r"_{10,}",
        r"(?:By|Signed)\s*:\s*",
        r"/s/\s+\w+",
        r"Pro\s+[Ss]e\s+(?:Plaintiff|Defendant)",
    ]

    EXHIBIT_PATTERNS = [
        r"EXHIBIT\s+[A-Z0-9]+",
        r"(?:Ex\.|Exhibit)\s+(?:No\.?\s*)?\d+",
        r"PIGORS[-–]\w[-–]\d{6}",  # Bates number
    ]

    def __init__(self):
        self._compiled_caption = [re.compile(p, re.IGNORECASE) for p in self.CAPTION_PATTERNS]
        self._compiled_case = [re.compile(p) for p in self.CASE_NUMBER_PATTERNS]
        self._compiled_cos = [re.compile(p, re.IGNORECASE) for p in self.COS_PATTERNS]
        self._compiled_sig = [re.compile(p, re.IGNORECASE) for p in self.SIGNATURE_PATTERNS]
        self._compiled_exhibit = [re.compile(p, re.IGNORECASE) for p in self.EXHIBIT_PATTERNS]

    def analyze_page(self, ocr_page: OCRPage) -> PageLayout:
        """Analyze a single page's layout and classify regions."""
        regions = []

        for line in ocr_page.lines:
            zone = self._classify_line(line, ocr_page)
            region = LayoutRegion(
                zone=zone, bbox=line.bbox, text=line.text,
                confidence=line.confidence, page=ocr_page.page_number
            )
            regions.append(region)

        # Merge adjacent regions of same type
        regions = self._merge_adjacent(regions)

        # Detect columns
        column_count = self._detect_columns(ocr_page)

        # Build reading order (top-to-bottom, left-to-right within columns)
        reading_order = self._build_reading_order(regions, column_count)

        has_table = any(r.zone == DocumentZone.TABLE for r in regions)
        has_hw = any(r.zone == DocumentZone.HANDWRITTEN for r in regions)

        return PageLayout(
            page_number=ocr_page.page_number,
            width=ocr_page.width, height=ocr_page.height,
            regions=regions, reading_order=reading_order,
            column_count=column_count,
            has_table=has_table, has_handwriting=has_hw
        )

    def analyze_document(self, ocr_result: OCRResult) -> list[PageLayout]:
        """Analyze all pages of a document."""
        layouts = []
        for page in ocr_result.pages:
            layout = self.analyze_page(page)
            layouts.append(layout)
        return layouts

    def _classify_line(self, line: OCRLine, page: OCRPage) -> DocumentZone:
        text = line.text.strip()
        if not text:
            return DocumentZone.UNKNOWN

        # Caption detection (typically top of first page)
        for pat in self._compiled_caption:
            if pat.search(text):
                return DocumentZone.CAPTION

        # Case number
        for pat in self._compiled_case:
            if pat.search(text):
                return DocumentZone.CASE_NUMBER

        # Certificate of Service
        for pat in self._compiled_cos:
            if pat.search(text):
                return DocumentZone.CERTIFICATE_OF_SERVICE

        # Signature block
        for pat in self._compiled_sig:
            if pat.search(text):
                return DocumentZone.SIGNATURE_BLOCK

        # Exhibit label / Bates stamp
        for pat in self._compiled_exhibit:
            if pat.search(text):
                if re.search(r'PIGORS[-–]\w[-–]\d{6}', text):
                    return DocumentZone.BATES_STAMP
                return DocumentZone.EXHIBIT_LABEL

        # Page number (bottom or top, short numeric)
        if page.height > 0:
            y_center = (line.bbox[1] + line.bbox[3]) / 2
            if (y_center < page.height * 0.05 or y_center > page.height * 0.95):
                if re.match(r'^\d{1,4}$', text.strip()):
                    return DocumentZone.PAGE_NUMBER

        # Heading (all caps, short, centered)
        if text.isupper() and len(text) < 100 and len(text.split()) < 15:
            return DocumentZone.HEADING

        # Table detection (multiple tab-aligned columns)
        if self._looks_like_table_row(text):
            return DocumentZone.TABLE

        # Default: body paragraph
        return DocumentZone.PARAGRAPH

    def _looks_like_table_row(self, text: str) -> bool:
        """Heuristic: table rows have multiple columns separated by whitespace."""
        parts = re.split(r'\s{3,}', text)
        if len(parts) >= 3:
            return True
        if re.match(r'^\s*\|.*\|', text):
            return True
        return False

    def _detect_columns(self, page: OCRPage) -> int:
        """Detect number of text columns by analyzing X-position distribution."""
        if not page.lines:
            return 1

        x_centers = [(ln.bbox[0] + ln.bbox[2]) / 2 for ln in page.lines]
        if not x_centers or page.width == 0:
            return 1

        # If X centers cluster into 2+ groups, it's multi-column
        from collections import Counter
        # Quantize to 10% of page width
        buckets = Counter(int(x / (page.width * 0.1)) if page.width > 0 else 0
                         for x in x_centers)
        significant = [b for b, count in buckets.items() if count >= 3]
        if len(significant) >= 2:
            spread = max(significant) - min(significant)
            if spread >= 3:
                return 2
        return 1

    def _build_reading_order(self, regions: list[LayoutRegion],
                              column_count: int) -> list[int]:
        """Build reading order indices."""
        if column_count <= 1:
            # Simple top-to-bottom
            sorted_indices = sorted(range(len(regions)),
                                   key=lambda i: regions[i].bbox[1])
            return sorted_indices

        # Multi-column: sort by column first, then Y
        page_width = max((r.bbox[2] for r in regions), default=1)
        col_width = page_width / column_count

        def sort_key(i: int):
            r = regions[i]
            col = int((r.bbox[0] + r.bbox[2]) / 2 / col_width) if col_width > 0 else 0
            return (col, r.bbox[1])

        return sorted(range(len(regions)), key=sort_key)

    def _merge_adjacent(self, regions: list[LayoutRegion]) -> list[LayoutRegion]:
        """Merge adjacent regions of the same zone type."""
        if not regions:
            return regions

        merged = [regions[0]]
        for region in regions[1:]:
            prev = merged[-1]
            if (prev.zone == region.zone and
                prev.page == region.page and
                abs(region.bbox[1] - prev.bbox[3]) < 20):
                # Merge
                prev.text += "\n" + region.text
                prev.bbox = (
                    min(prev.bbox[0], region.bbox[0]),
                    prev.bbox[1],
                    max(prev.bbox[2], region.bbox[2]),
                    region.bbox[3]
                )
                prev.confidence = (prev.confidence + region.confidence) / 2
            else:
                merged.append(region)
        return merged
```

### 2.2 Table Extraction Engine

```python
class TableExtractor:
    """
    Extract structured tables from OCR results.
    Handles bordered, borderless, and partially-bordered tables.
    """

    def __init__(self, min_columns: int = 2, min_rows: int = 2):
        self.min_columns = min_columns
        self.min_rows = min_rows

    def extract_tables(self, page_layout: PageLayout) -> list[dict]:
        """Extract all tables from a page layout."""
        table_regions = [r for r in page_layout.regions
                        if r.zone == DocumentZone.TABLE]
        if not table_regions:
            return []

        # Group adjacent table rows
        groups = self._group_table_rows(table_regions)
        tables = []

        for group in groups:
            if len(group) < self.min_rows:
                continue

            table = self._parse_table(group)
            if table and len(table.get("columns", [])) >= self.min_columns:
                tables.append(table)

        return tables

    def _group_table_rows(self, regions: list[LayoutRegion]) -> list[list[LayoutRegion]]:
        """Group adjacent table-type regions into table blocks."""
        if not regions:
            return []

        groups = [[regions[0]]]
        for region in regions[1:]:
            prev = groups[-1][-1]
            gap = region.bbox[1] - prev.bbox[3]
            if gap < 30:
                groups[-1].append(region)
            else:
                groups.append([region])
        return groups

    def _parse_table(self, rows: list[LayoutRegion]) -> dict:
        """Parse a group of table rows into structured data."""
        parsed_rows = []
        for row in rows:
            cells = re.split(r'\s{3,}|\t+|\|', row.text)
            cells = [c.strip() for c in cells if c.strip()]
            if cells:
                parsed_rows.append(cells)

        if not parsed_rows:
            return {}

        max_cols = max(len(r) for r in parsed_rows)
        # Pad short rows
        for row in parsed_rows:
            while len(row) < max_cols:
                row.append("")

        columns = parsed_rows[0] if parsed_rows else []
        data_rows = parsed_rows[1:] if len(parsed_rows) > 1 else []

        return {
            "columns": columns,
            "rows": data_rows,
            "row_count": len(data_rows),
            "column_count": max_cols,
            "bbox": (
                min(r.bbox[0] for r in rows),
                rows[0].bbox[1],
                max(r.bbox[2] for r in rows),
                rows[-1].bbox[3]
            )
        }
```

---

## Layer 3: Michigan Court Form Recognition

### 3.1 SCAO Form Template Matcher

```python
"""
Michigan SCAO court form recognition.
Identifies form type, extracts filled fields, scores completeness.
"""

@dataclass
class FormField:
    """A detected field in a court form."""
    label: str
    value: str
    field_type: str  # text, checkbox, date, signature, case_number
    is_filled: bool
    confidence: float
    bbox: tuple[int, int, int, int]
    required: bool = True


@dataclass
class FormMatch:
    """Result of form template matching."""
    form_id: str           # e.g., "MC 12", "DC 100"
    form_name: str         # e.g., "Proof of Service"
    match_confidence: float
    fields: list[FormField]
    completeness_score: float
    missing_fields: list[str]
    page_range: tuple[int, int]


class MichiganFormTemplates:
    """
    Template definitions for Michigan SCAO court forms.
    Each template has characteristic text patterns and expected fields.
    """

    TEMPLATES = {
        "MC 12": {
            "name": "Proof of Service",
            "patterns": [
                r"PROOF\s+OF\s+SERVICE",
                r"MC\s*12",
                r"I\s+(?:hereby\s+)?certify",
                r"served\s+(?:a\s+)?(?:true\s+)?copy",
            ],
            "fields": [
                {"label": "Case Number", "type": "case_number", "required": True,
                 "pattern": r"Case\s*No\.?\s*:?\s*(.+)"},
                {"label": "Court", "type": "text", "required": True,
                 "pattern": r"(?:Circuit|District)\s+Court"},
                {"label": "Plaintiff", "type": "text", "required": True,
                 "pattern": r"Plaintiff.*?:\s*(.+)"},
                {"label": "Defendant", "type": "text", "required": True,
                 "pattern": r"Defendant.*?:\s*(.+)"},
                {"label": "Date Served", "type": "date", "required": True,
                 "pattern": r"(?:on|dated?)\s+(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})"},
                {"label": "Method", "type": "text", "required": True,
                 "pattern": r"(?:first.class\s+mail|personal\s+service|e.?fil)"},
                {"label": "Signature", "type": "signature", "required": True,
                 "pattern": r"(?:/s/|_{10,}|Signed)"},
            ]
        },
        "MC 20": {
            "name": "Fee Waiver Request",
            "patterns": [
                r"FEE\s+WAIVER\s+REQUEST",
                r"MC\s*20",
                r"unable\s+to\s+pay",
                r"public\s+assistance",
            ],
            "fields": [
                {"label": "Case Number", "type": "case_number", "required": True,
                 "pattern": r"Case\s*No\.?\s*:?\s*(.+)"},
                {"label": "Income", "type": "text", "required": True,
                 "pattern": r"(?:income|earn|receiv)\w*\s*:?\s*\$?([\d,.]+)"},
                {"label": "Public Assistance", "type": "checkbox", "required": False,
                 "pattern": r"(?:receiving|public\s+assistance)"},
                {"label": "Signature", "type": "signature", "required": True,
                 "pattern": r"(?:/s/|_{10,})"},
            ]
        },
        "MC 302": {
            "name": "Personal Protection Order (Domestic)",
            "patterns": [
                r"PERSONAL\s+PROTECTION\s+ORDER",
                r"MC\s*302",
                r"PPO",
                r"MCL\s+600\.2950",
            ],
            "fields": [
                {"label": "Case Number", "type": "case_number", "required": True,
                 "pattern": r"Case\s*No\.?\s*:?\s*(.+)"},
                {"label": "Petitioner", "type": "text", "required": True,
                 "pattern": r"Petitioner.*?:\s*(.+)"},
                {"label": "Respondent", "type": "text", "required": True,
                 "pattern": r"Respondent.*?:\s*(.+)"},
                {"label": "Expiration Date", "type": "date", "required": True,
                 "pattern": r"expir\w*\s*:?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})"},
            ]
        },
        "MC 375": {
            "name": "Motion",
            "patterns": [
                r"MOTION",
                r"MC\s*375",
                r"moves?\s+(?:this\s+)?(?:Honorable\s+)?Court",
            ],
            "fields": [
                {"label": "Case Number", "type": "case_number", "required": True,
                 "pattern": r"Case\s*No\.?\s*:?\s*(.+)"},
                {"label": "Moving Party", "type": "text", "required": True,
                 "pattern": r"(?:Plaintiff|Defendant|Movant).*?:\s*(.+)"},
                {"label": "Relief Requested", "type": "text", "required": True,
                 "pattern": r"(?:request|order|grant|pray)\w*"},
            ]
        },
        "DC 100": {
            "name": "Complaint",
            "patterns": [
                r"COMPLAINT",
                r"DC\s*100",
                r"COMES\s+NOW",
                r"alleges?\s+(?:as\s+follows|that)",
            ],
            "fields": [
                {"label": "Case Number", "type": "case_number", "required": True,
                 "pattern": r"Case\s*No\.?\s*:?\s*(.+)"},
                {"label": "Plaintiff", "type": "text", "required": True,
                 "pattern": r"Plaintiff.*?:\s*(.+)"},
                {"label": "Defendant", "type": "text", "required": True,
                 "pattern": r"Defendant.*?:\s*(.+)"},
                {"label": "Counts", "type": "text", "required": True,
                 "pattern": r"COUNT\s+[IVX\d]+"},
            ]
        },
        "DC 101": {
            "name": "Summons",
            "patterns": [
                r"SUMMONS",
                r"DC\s*101",
                r"YOU\s+ARE\s+(?:HEREBY\s+)?NOTIFIED",
                r"(?:answer|respond)\s+within\s+\d+\s+days",
            ],
            "fields": [
                {"label": "Case Number", "type": "case_number", "required": True,
                 "pattern": r"Case\s*No\.?\s*:?\s*(.+)"},
                {"label": "Response Deadline", "type": "date", "required": True,
                 "pattern": r"within\s+(\d+)\s+days"},
            ]
        },
        "FOC 10": {
            "name": "Uniform Child Support Order",
            "patterns": [
                r"UNIFORM\s+CHILD\s+SUPPORT\s+ORDER",
                r"FOC\s*10",
                r"child\s+support",
                r"MCL\s+552",
            ],
            "fields": [
                {"label": "Case Number", "type": "case_number", "required": True,
                 "pattern": r"Case\s*No\.?\s*:?\s*(.+)"},
                {"label": "Support Amount", "type": "text", "required": True,
                 "pattern": r"\$\s*([\d,.]+)\s*(?:per|/)\s*(?:month|week)"},
            ]
        },
        "COA 1": {
            "name": "Claim of Appeal",
            "patterns": [
                r"CLAIM\s+OF\s+APPEAL",
                r"COA\s*1",
                r"COURT\s+OF\s+APPEALS",
                r"appeal\s+(?:of|from)\s+(?:right|the)",
            ],
            "fields": [
                {"label": "COA Case Number", "type": "case_number", "required": True,
                 "pattern": r"COA\s*(?:No\.?)?\s*:?\s*(\d{5,6})"},
                {"label": "Lower Court Case", "type": "case_number", "required": True,
                 "pattern": r"(?:LC|Lower\s+Court)\s*(?:No\.?)?\s*:?\s*(.+)"},
                {"label": "Lower Court Judge", "type": "text", "required": True,
                 "pattern": r"(?:Judge|Hon\.?)\s+(.+)"},
            ]
        },
        "CC 257": {
            "name": "Civil Cover Sheet",
            "patterns": [
                r"CIVIL\s+(?:CASE\s+)?COVER\s+SHEET",
                r"CC\s*257",
            ],
            "fields": [
                {"label": "Case Number", "type": "case_number", "required": True,
                 "pattern": r"Case\s*No\.?\s*:?\s*(.+)"},
                {"label": "Case Type", "type": "text", "required": True,
                 "pattern": r"(?:type|category)\s*:?\s*(.+)"},
            ]
        },
    }

    @classmethod
    def get_template(cls, form_id: str) -> dict | None:
        return cls.TEMPLATES.get(form_id)

    @classmethod
    def all_form_ids(cls) -> list[str]:
        return list(cls.TEMPLATES.keys())


class FormRecognizer:
    """
    Recognizes Michigan court forms from OCR text.
    Matches against templates, extracts fields, scores completeness.
    """

    def __init__(self):
        self.templates = MichiganFormTemplates()
        self._compiled_templates: dict[str, list[re.Pattern]] = {}
        for form_id, template in MichiganFormTemplates.TEMPLATES.items():
            self._compiled_templates[form_id] = [
                re.compile(p, re.IGNORECASE) for p in template["patterns"]
            ]

    def identify_form(self, text: str) -> list[tuple[str, float]]:
        """
        Identify which SCAO form this document matches.
        Returns list of (form_id, confidence) sorted by confidence.
        """
        scores = []
        for form_id, patterns in self._compiled_templates.items():
            hits = sum(1 for p in patterns if p.search(text))
            if hits > 0:
                confidence = hits / len(patterns)
                scores.append((form_id, confidence))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    def extract_fields(self, text: str, form_id: str) -> FormMatch:
        """Extract form fields for a known form type."""
        template = MichiganFormTemplates.TEMPLATES.get(form_id)
        if not template:
            raise ValueError(f"Unknown form: {form_id}")

        fields = []
        missing = []

        for field_def in template["fields"]:
            pat = re.compile(field_def["pattern"], re.IGNORECASE | re.MULTILINE)
            match = pat.search(text)

            if match:
                value = match.group(1) if match.lastindex else match.group(0)
                fields.append(FormField(
                    label=field_def["label"],
                    value=value.strip(),
                    field_type=field_def["type"],
                    is_filled=bool(value.strip()),
                    confidence=0.85,
                    bbox=(0, 0, 0, 0),
                    required=field_def.get("required", True)
                ))
            else:
                if field_def.get("required", True):
                    missing.append(field_def["label"])
                fields.append(FormField(
                    label=field_def["label"],
                    value="",
                    field_type=field_def["type"],
                    is_filled=False,
                    confidence=0.0,
                    bbox=(0, 0, 0, 0),
                    required=field_def.get("required", True)
                ))

        filled = sum(1 for f in fields if f.is_filled)
        total_required = sum(1 for f in fields if f.required)
        completeness = filled / total_required if total_required > 0 else 0

        id_scores = self.identify_form(text)
        match_conf = next((s for fid, s in id_scores if fid == form_id), 0.0)

        return FormMatch(
            form_id=form_id,
            form_name=template["name"],
            match_confidence=match_conf,
            fields=fields,
            completeness_score=completeness,
            missing_fields=missing,
            page_range=(0, 0)
        )

    def auto_recognize(self, ocr_result: OCRResult) -> list[FormMatch]:
        """
        Auto-recognize all forms in a document.
        Returns matches sorted by confidence.
        """
        full_text = ocr_result.full_text
        candidates = self.identify_form(full_text)
        matches = []

        for form_id, conf in candidates:
            if conf >= 0.3:
                match = self.extract_fields(full_text, form_id)
                matches.append(match)

        return sorted(matches, key=lambda m: m.match_confidence, reverse=True)

    def score_completeness(self, match: FormMatch) -> dict:
        """Detailed completeness report for a form."""
        filled = [f for f in match.fields if f.is_filled]
        empty = [f for f in match.fields if not f.is_filled]
        required_empty = [f for f in empty if f.required]

        return {
            "form_id": match.form_id,
            "form_name": match.form_name,
            "total_fields": len(match.fields),
            "filled_fields": len(filled),
            "empty_fields": len(empty),
            "required_missing": len(required_empty),
            "completeness_pct": match.completeness_score * 100,
            "filing_ready": len(required_empty) == 0,
            "missing_required": [f.label for f in required_empty],
            "filled_details": {f.label: f.value for f in filled}
        }
```

---

## Layer 4: Evidence Extraction Pipeline

### 4.1 Legal Entity Extractor

```python
"""
Extract legal entities from OCR text:
case numbers, judge names, party names, dates, dollar amounts, citations.
"""

@dataclass
class LegalEntity:
    """An extracted legal entity."""
    entity_type: str  # case_number, judge, party, date, amount, citation, statute
    value: str
    raw_text: str
    confidence: float
    page: int
    position: int  # character offset
    context: str  # surrounding text (±50 chars)


class LegalEntityExtractor:
    """
    Extract structured legal entities from OCR text.
    Tuned for Michigan family/custody/civil rights litigation.
    """

    ENTITY_PATTERNS = {
        "case_number": [
            (r'\b(\d{4}[-–]\d{4,8}[-–][A-Z]{2,4})\b', 0.95),
            (r'\bCOA\s*(?:No\.?)?\s*:?\s*(\d{5,6})\b', 0.90),
            (r'\b(\d{4}[-–]\d{8}(?:SM|DC))\b', 0.85),
        ],
        "judge": [
            (r'\b(?:Hon(?:orable)?\.?\s+)([\w\s.]+?)(?:\s*,|\s+(?:Circuit|District|Chief))', 0.90),
            (r'\b(?:Judge|Justice)\s+([\w\s.]+?)(?:\s*,|\s+presid)', 0.85),
            (r'\b(McNeill|Hoopes|Ladas[-–]Hoopes|Kostrzewa)\b', 0.95),
        ],
        "party": [
            (r'\b(?:Plaintiff|Petitioner)\s*[,:]?\s*([\w\s.]+?)(?:\s*,|\s+v\.?)', 0.80),
            (r'\b(?:Defendant|Respondent)\s*[,:]?\s*([\w\s.]+?)(?:\s*,|\s+\))', 0.80),
            (r'\b(Andrew\s+(?:James\s+)?Pigors)\b', 0.95),
            (r'\b(Emily\s+A\.?\s+Watson)\b', 0.95),
        ],
        "date": [
            (r'\b(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})\b', 0.85),
            (r'\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b', 0.90),
            (r'\b(\d{4}[-–]\d{2}[-–]\d{2})\b', 0.85),
        ],
        "dollar_amount": [
            (r'\$\s*([\d,]+\.?\d{0,2})\b', 0.90),
            (r'\b([\d,]+\.?\d{0,2})\s*dollars?\b', 0.80),
        ],
        "mcr_citation": [
            (r'\b(MCR\s+\d+\.\d+(?:\([A-Za-z0-9]+\))*)\b', 0.95),
            (r'\b(MCL\s+\d+\.\d+[a-z]?(?:\([0-9]+\))?)\b', 0.95),
            (r'\b(MRE\s+\d+(?:\([a-z]\))?)\b', 0.95),
        ],
        "case_law": [
            (r'\b([\w\s]+v\.?\s+[\w\s]+,\s*\d+\s+(?:Mich|Mich\s*App|F\.\d[a-z]*d?|US)\s+\d+)', 0.85),
            (r'\b(\d+\s+(?:Mich|Mich\s*App)\s+\d+\s*\(\d{4}\))', 0.80),
        ],
        "federal_statute": [
            (r'\b(\d+\s+U\.?S\.?C\.?\s+§?\s*\d+[a-z]?)\b', 0.90),
            (r'\b(42\s+USC\s+§?\s*1983)\b', 0.95),
            (r'\b(28\s+USC\s+§?\s*1343)\b', 0.95),
        ],
        "bates_number": [
            (r'\b(PIGORS[-–][A-Z][-–]\d{6})\b', 0.98),
            (r'\b([A-Z]{2,10}[-–]\d{4,8})\b', 0.70),
        ],
    }

    def __init__(self):
        self._compiled: dict[str, list[tuple[re.Pattern, float]]] = {}
        for etype, patterns in self.ENTITY_PATTERNS.items():
            self._compiled[etype] = [
                (re.compile(p, re.IGNORECASE), conf) for p, conf in patterns
            ]

    def extract(self, text: str, page: int = 0) -> list[LegalEntity]:
        """Extract all legal entities from text."""
        entities = []

        for etype, compiled_pats in self._compiled.items():
            for pattern, base_conf in compiled_pats:
                for match in pattern.finditer(text):
                    value = match.group(1) if match.lastindex else match.group(0)
                    start = match.start()
                    ctx_start = max(0, start - 50)
                    ctx_end = min(len(text), match.end() + 50)
                    context = text[ctx_start:ctx_end]

                    entities.append(LegalEntity(
                        entity_type=etype,
                        value=value.strip(),
                        raw_text=match.group(0),
                        confidence=base_conf,
                        page=page,
                        position=start,
                        context=context.strip()
                    ))

        # Deduplicate by value within same type
        seen = set()
        unique = []
        for e in entities:
            key = (e.entity_type, e.value.lower())
            if key not in seen:
                seen.add(key)
                unique.append(e)

        return unique

    def extract_from_ocr(self, ocr_result: OCRResult) -> dict[str, list[LegalEntity]]:
        """Extract entities from full OCR result, grouped by type."""
        all_entities: dict[str, list[LegalEntity]] = {}

        for page in ocr_result.pages:
            entities = self.extract(page.text, page.page_number)
            for entity in entities:
                all_entities.setdefault(entity.entity_type, []).append(entity)

        return all_entities


class BatesStampDetector:
    """Detect and read Bates stamps from OCR results."""

    BATES_PATTERNS = [
        re.compile(r'PIGORS[-–]([A-Z])[-–](\d{6})', re.IGNORECASE),
        re.compile(r'([A-Z]{2,8})[-–](\d{4,8})'),
        re.compile(r'Bates\s*(?:No\.?)?\s*:?\s*(\w+[-–]\d+)', re.IGNORECASE),
    ]

    def detect(self, ocr_page: OCRPage) -> list[dict]:
        """Detect Bates stamps on a page, including position."""
        stamps = []
        text = ocr_page.text

        for pattern in self.BATES_PATTERNS:
            for match in pattern.finditer(text):
                # Check if stamp is near page edges (typical Bates position)
                stamp_text = match.group(0)
                stamps.append({
                    "stamp": stamp_text,
                    "page": ocr_page.page_number,
                    "prefix": match.group(1) if match.lastindex >= 1 else "",
                    "number": match.group(2) if match.lastindex >= 2 else "",
                    "position": match.start(),
                    "confidence": 0.95 if "PIGORS" in stamp_text.upper() else 0.70
                })

        return stamps


class QualityScorer:
    """Score OCR quality per page and overall."""

    def score_page(self, page: OCRPage) -> dict:
        """Score a single page's OCR quality."""
        conf = page.confidence
        word_count = page.word_count
        text = page.text

        # Garbled text detection
        garbled_ratio = self._garbled_ratio(text)
        # Whitespace ratio
        ws_ratio = text.count(' ') / max(len(text), 1)
        # Average word length (very short = likely OCR errors)
        words = text.split()
        avg_word_len = sum(len(w) for w in words) / max(len(words), 1)

        quality = conf * 0.5 + (1 - garbled_ratio) * 0.3 + min(avg_word_len / 5, 1) * 0.2

        return {
            "page": page.page_number,
            "overall_quality": round(quality, 3),
            "ocr_confidence": round(conf, 3),
            "word_count": word_count,
            "garbled_ratio": round(garbled_ratio, 3),
            "avg_word_length": round(avg_word_len, 1),
            "needs_review": quality < 0.7,
            "grade": "A" if quality > 0.9 else "B" if quality > 0.8 else
                     "C" if quality > 0.7 else "D" if quality > 0.5 else "F"
        }

    def score_document(self, ocr_result: OCRResult) -> dict:
        """Score entire document's OCR quality."""
        page_scores = [self.score_page(p) for p in ocr_result.pages]
        avg_quality = sum(s["overall_quality"] for s in page_scores) / max(len(page_scores), 1)
        pages_needing_review = [s["page"] for s in page_scores if s["needs_review"]]

        return {
            "file": ocr_result.file_path,
            "pages": len(page_scores),
            "avg_quality": round(avg_quality, 3),
            "min_quality": round(min((s["overall_quality"] for s in page_scores), default=0), 3),
            "pages_needing_review": pages_needing_review,
            "grade": "A" if avg_quality > 0.9 else "B" if avg_quality > 0.8 else
                     "C" if avg_quality > 0.7 else "D" if avg_quality > 0.5 else "F",
            "per_page": page_scores
        }

    def _garbled_ratio(self, text: str) -> float:
        """Estimate ratio of garbled/non-English characters."""
        if not text:
            return 0.0
        non_ascii = sum(1 for c in text if ord(c) > 127 and not c.isspace())
        garbage_patterns = len(re.findall(r'[^\w\s.,;:!?\-\'\"()/\[\]@#$%&*+=<>{}|\\~`^]', text))
        total = len(text)
        return (non_ascii + garbage_patterns) / max(total, 1)
```

---

## Layer 5: Evidence Classification & Lane Routing

### 5.1 MEEK Lane Router

```python
"""
MEEK (Michigan Evidence Extraction Keywords) lane routing.
Routes OCR'd documents to case lanes A-F based on content.
Detection priority: E → D → F → C → A → B
"""

@dataclass
class LaneAssignment:
    """Lane routing result for a document."""
    primary_lane: str
    lane_name: str
    confidence: float
    signals: list[str]
    secondary_lanes: list[tuple[str, float]]
    document_type: str
    priority_score: float
    smoking_gun: bool


class MEEKLaneRouter:
    """
    Route documents to litigation lanes using keyword signals.
    Priority order: E (judicial) → D (PPO) → F (appellate) → C (federal) → A (custody) → B (housing)
    """

    LANE_SIGNALS = {
        "E": {
            "name": "Judicial Misconduct",
            "priority": 6,
            "keywords": [
                "mcneill", "jenny l. mcneill", "judicial misconduct", "JTC",
                "judicial tenure", "canon", "ex parte", "benchbook",
                "bias", "prejudice", "disqualification", "MCR 2.003",
                "hoopes", "ladas-hoopes", "ladas hoopes", "cavan berry",
                "990 terrace", "judicial cartel", "abuse of discretion",
            ],
            "case_numbers": ["2024-001507-DC"],
        },
        "D": {
            "name": "PPO",
            "priority": 5,
            "keywords": [
                "PPO", "personal protection", "protection order",
                "5907", "2023-5907-PP", "stalking", "MCL 600.2950",
                "MC 302", "contempt", "show cause", "jail",
                "MCL 764.15b",
            ],
            "case_numbers": ["2023-5907-PP"],
        },
        "F": {
            "name": "Appellate",
            "priority": 4,
            "keywords": [
                "COA", "court of appeals", "366810", "appeal",
                "appellant", "appellee", "MCR 7.212", "MCR 7.204",
                "MCR 7.205", "claim of appeal", "appendix",
                "MSC", "supreme court", "MCR 7.305", "MCR 7.306",
                "superintending control", "mandamus", "habeas corpus",
            ],
            "case_numbers": ["366810"],
        },
        "C": {
            "name": "Federal / Civil Rights",
            "priority": 3,
            "keywords": [
                "§1983", "section 1983", "42 USC", "28 USC 1343",
                "civil rights", "color of law", "federal",
                "qualified immunity", "monell", "deliberate indifference",
                "RICO", "conspiracy",
            ],
            "case_numbers": [],
        },
        "A": {
            "name": "Custody",
            "priority": 2,
            "keywords": [
                "custody", "parenting time", "001507", "2024-001507-DC",
                "watson", "best interest", "MCL 722.23", "MCR 3.206",
                "FOC", "friend of court", "visitation",
                "established custodial", "Vodvarka", "factor",
                "parental alienation", "withholding",
            ],
            "case_numbers": ["2024-001507-DC"],
        },
        "B": {
            "name": "Housing",
            "priority": 1,
            "keywords": [
                "shady oaks", "eviction", "housing", "trailer",
                "002760", "2025-002760-CZ", "habitability",
                "landlord", "tenant", "mobile home", "lot rent",
            ],
            "case_numbers": ["2025-002760-CZ"],
        },
    }

    DOCUMENT_TYPES = {
        "motion": [r"MOTION\s+(?:TO|FOR)", r"moves?\s+(?:this\s+)?Court"],
        "order": [r"ORDER\s+(?:GRANTING|DENYING|OF\s+THE\s+COURT)", r"IT\s+IS\s+(?:HEREBY\s+)?ORDERED"],
        "brief": [r"BRIEF\s+(?:IN\s+SUPPORT|OF)", r"MEMORANDUM\s+(?:OF|IN)"],
        "transcript": [r"TRANSCRIPT\s+OF", r"THE\s+COURT\s*:", r"Q\.\s+.*\nA\.\s+"],
        "letter": [r"Dear\s+(?:Judge|Sir|Madam|Mr|Ms)", r"Sincerely"],
        "police_report": [r"INCIDENT\s+REPORT", r"NSPD", r"OFFICER\s+\w+\s+\w+", r"COMPLAINANT"],
        "medical": [r"DIAGNOSIS", r"PATIENT", r"PHYSICIAN", r"TREATMENT\s+PLAN"],
        "affidavit": [r"AFFIDAVIT\s+OF", r"under\s+penalty\s+of\s+perjury", r"VERIFICATION"],
        "complaint": [r"COMPLAINT\s+(?:FOR|AND)", r"COMES\s+NOW", r"COUNT\s+[IVX\d]+"],
        "exhibit": [r"EXHIBIT\s+[A-Z0-9]+", r"PIGORS[-–]\w[-–]\d{6}"],
    }

    SMOKING_GUN_KEYWORDS = [
        "premeditated", "admitted", "confession", "recant",
        "nothing was physical", "meth", "fabricat", "false allegation",
        "documented so emily", "ex parte order for full custody",
        "albert watson", "NS2505044", "HealthWest",
    ]

    def __init__(self):
        self._compiled_types = {}
        for doc_type, patterns in self.DOCUMENT_TYPES.items():
            self._compiled_types[doc_type] = [
                re.compile(p, re.IGNORECASE | re.MULTILINE) for p in patterns
            ]
        self._smoking_gun_pats = [
            re.compile(kw, re.IGNORECASE) for kw in self.SMOKING_GUN_KEYWORDS
        ]

    def route(self, text: str, file_path: str = "") -> LaneAssignment:
        """Route document to a litigation lane."""
        text_lower = text.lower()
        lane_scores: dict[str, tuple[float, list[str]]] = {}

        for lane, config in self.LANE_SIGNALS.items():
            hits = []
            for kw in config["keywords"]:
                count = text_lower.count(kw.lower())
                if count > 0:
                    hits.append(f"{kw} ({count})")

            for cn in config["case_numbers"]:
                if cn.lower() in text_lower:
                    hits.append(f"case:{cn}")

            if hits:
                score = len(hits) * config["priority"]
                lane_scores[lane] = (score, hits)

        if not lane_scores:
            return LaneAssignment(
                primary_lane="A", lane_name="Custody (default)",
                confidence=0.1, signals=[], secondary_lanes=[],
                document_type=self._classify_type(text),
                priority_score=0.0, smoking_gun=False
            )

        # Sort by score descending (highest priority lane with most signals wins)
        sorted_lanes = sorted(lane_scores.items(), key=lambda x: x[1][0], reverse=True)
        primary = sorted_lanes[0]
        max_score = primary[1][0]

        secondary = [(lane, score / max_score)
                     for lane, (score, _) in sorted_lanes[1:] if score > 0]

        # Smoking gun detection
        smoking_gun = any(p.search(text) for p in self._smoking_gun_pats)

        doc_type = self._classify_type(text)
        priority = self._priority_score(primary[0], primary[1][0], smoking_gun, doc_type)

        return LaneAssignment(
            primary_lane=primary[0],
            lane_name=self.LANE_SIGNALS[primary[0]]["name"],
            confidence=min(primary[1][0] / 20, 1.0),
            signals=primary[1][1],
            secondary_lanes=secondary,
            document_type=doc_type,
            priority_score=priority,
            smoking_gun=smoking_gun
        )

    def _classify_type(self, text: str) -> str:
        """Classify document type from content."""
        best_type = "unknown"
        best_hits = 0

        for doc_type, patterns in self._compiled_types.items():
            hits = sum(1 for p in patterns if p.search(text))
            if hits > best_hits:
                best_hits = hits
                best_type = doc_type

        return best_type

    def _priority_score(self, lane: str, raw_score: float,
                         smoking_gun: bool, doc_type: str) -> float:
        """Calculate priority score for evidence triage."""
        base = raw_score / 10
        if smoking_gun:
            base *= 2.0
        if doc_type in ("police_report", "transcript", "order"):
            base *= 1.5
        if lane == "E":
            base *= 1.3  # Judicial misconduct is always high priority
        return min(round(base, 2), 10.0)

    def batch_route(self, documents: list[tuple[str, str]]) -> list[LaneAssignment]:
        """Route multiple documents. Input: [(file_path, text), ...]"""
        return [self.route(text, path) for path, text in documents]
```

---

## Layer 6: Handwriting & Degraded Document Recovery

### 6.1 Image Preprocessing Pipeline

```python
"""
Image preprocessing for degraded document recovery.
Deskew, denoise, contrast enhancement, binarization.
"""

class ImagePreprocessor:
    """
    Multi-stage image preprocessing for OCR quality improvement.
    Handles skewed, noisy, faded, and partially damaged documents.
    """

    def __init__(self, target_dpi: int = 300):
        self.target_dpi = target_dpi

    def preprocess(self, image, stages: list[str] | None = None) -> 'Image':
        """
        Apply preprocessing stages to an image.
        Stages: deskew, denoise, contrast, binarize, sharpen, border_remove
        """
        from PIL import Image, ImageFilter, ImageEnhance, ImageOps
        import numpy as np

        if stages is None:
            stages = ["deskew", "contrast", "denoise", "sharpen"]

        img = image.copy() if hasattr(image, 'copy') else Image.open(image)

        for stage in stages:
            try:
                if stage == "deskew":
                    img = self._deskew(img)
                elif stage == "denoise":
                    img = self._denoise(img)
                elif stage == "contrast":
                    img = self._enhance_contrast(img)
                elif stage == "binarize":
                    img = self._adaptive_binarize(img)
                elif stage == "sharpen":
                    img = self._sharpen(img)
                elif stage == "border_remove":
                    img = self._remove_borders(img)
                elif stage == "upscale":
                    img = self._upscale(img)
            except Exception as e:
                logger.warning(f"Preprocessing stage '{stage}' failed: {e}")
                continue

        return img

    def _deskew(self, img):
        """Correct document skew using projection profile."""
        import numpy as np
        from PIL import Image

        gray = img.convert('L')
        arr = np.array(gray)

        # Simple skew detection via row variance
        best_angle = 0
        best_score = 0

        for angle_tenth in range(-30, 31):
            angle = angle_tenth / 10.0
            rotated = img.rotate(angle, fillcolor=255, expand=False)
            row_sums = np.sum(np.array(rotated.convert('L')) < 128, axis=1)
            score = np.var(row_sums)
            if score > best_score:
                best_score = score
                best_angle = angle

        if abs(best_angle) > 0.1:
            img = img.rotate(best_angle, fillcolor=255, expand=True)
            logger.debug(f"Deskewed by {best_angle:.1f}°")

        return img

    def _denoise(self, img):
        """Remove noise using median filter."""
        from PIL import ImageFilter
        return img.filter(ImageFilter.MedianFilter(size=3))

    def _enhance_contrast(self, img):
        """Enhance contrast for faded documents."""
        from PIL import ImageEnhance, ImageOps
        img = ImageOps.autocontrast(img, cutoff=2)
        enhancer = ImageEnhance.Contrast(img)
        return enhancer.enhance(1.5)

    def _adaptive_binarize(self, img):
        """Adaptive thresholding for mixed lighting conditions."""
        import numpy as np
        from PIL import Image

        gray = np.array(img.convert('L'))
        # Block-based adaptive threshold
        block_size = 31
        h, w = gray.shape
        binary = np.zeros_like(gray)

        for y in range(0, h, block_size):
            for x in range(0, w, block_size):
                block = gray[y:y+block_size, x:x+block_size]
                if block.size == 0:
                    continue
                threshold = np.mean(block) - 10
                binary[y:y+block_size, x:x+block_size] = (
                    (block < threshold).astype(np.uint8) * 255
                )

        return Image.fromarray(255 - binary)

    def _sharpen(self, img):
        """Sharpen text edges."""
        from PIL import ImageFilter
        return img.filter(ImageFilter.SHARPEN)

    def _remove_borders(self, img):
        """Remove black borders from scanned documents."""
        from PIL import ImageOps
        return ImageOps.crop(img, border=10)

    def _upscale(self, img):
        """Upscale low-resolution images for better OCR."""
        from PIL import Image
        w, h = img.size
        if w < 1000 or h < 1000:
            scale = max(2000 / w, 2000 / h)
            new_size = (int(w * scale), int(h * scale))
            return img.resize(new_size, Image.LANCZOS)
        return img

    def auto_select_stages(self, img) -> list[str]:
        """
        Auto-detect which preprocessing stages are needed.
        Analyzes image quality metrics to decide.
        """
        import numpy as np
        arr = np.array(img.convert('L'))
        stages = []

        # Check contrast
        std = np.std(arr)
        if std < 50:
            stages.append("contrast")

        # Check noise (high-frequency energy)
        if arr.shape[0] > 10 and arr.shape[1] > 10:
            laplacian_var = np.var(arr[1:-1, 1:-1].astype(float) * 4 -
                                   arr[:-2, 1:-1].astype(float) -
                                   arr[2:, 1:-1].astype(float) -
                                   arr[1:-1, :-2].astype(float) -
                                   arr[1:-1, 2:].astype(float))
            if laplacian_var > 1000:
                stages.append("denoise")

        # Always try deskew and sharpen
        stages.extend(["deskew", "sharpen"])

        return stages


class HandwritingDetector:
    """
    Detect handwritten regions in documents.
    Uses stroke analysis and texture features.
    """

    def detect_handwriting(self, img) -> list[dict]:
        """
        Detect handwritten regions in an image.
        Returns bounding boxes of handwritten areas.
        """
        import numpy as np
        from PIL import Image

        gray = np.array(img.convert('L'))
        # Edge detection for stroke analysis
        edges = self._sobel_edges(gray)

        # Sliding window handwriting detection
        regions = []
        window_size = 100
        stride = 50

        for y in range(0, gray.shape[0] - window_size, stride):
            for x in range(0, gray.shape[1] - window_size, stride):
                window = edges[y:y+window_size, x:x+window_size]
                if self._is_handwritten(window):
                    regions.append({
                        "bbox": (x, y, x + window_size, y + window_size),
                        "confidence": self._handwriting_confidence(window),
                        "type": "handwritten"
                    })

        # Merge overlapping regions
        return self._merge_regions(regions)

    def _sobel_edges(self, gray) -> 'np.ndarray':
        """Simple Sobel edge detection."""
        import numpy as np
        gx = gray[:, 2:].astype(float) - gray[:, :-2].astype(float)
        gy = gray[2:, :].astype(float) - gray[:-2, :].astype(float)
        min_h, min_w = min(gx.shape[0], gy.shape[0]), min(gx.shape[1], gy.shape[1])
        return np.sqrt(gx[:min_h, :min_w]**2 + gy[:min_h, :min_w]**2)

    def _is_handwritten(self, edge_window) -> bool:
        """Heuristic: handwriting has irregular stroke patterns."""
        import numpy as np
        edge_density = np.mean(edge_window > 30)
        # Handwriting has moderate edge density (5-40%) with high variance
        if 0.05 < edge_density < 0.40:
            variance = np.var(edge_window)
            return variance > 500
        return False

    def _handwriting_confidence(self, window) -> float:
        """Estimate confidence that a region is handwritten."""
        import numpy as np
        edge_density = np.mean(window > 30)
        variance = np.var(window)
        score = min(edge_density * 2, 1.0) * min(variance / 2000, 1.0)
        return round(score, 3)

    def _merge_regions(self, regions: list[dict]) -> list[dict]:
        """Merge overlapping handwriting regions."""
        if not regions:
            return []

        merged = [regions[0]]
        for region in regions[1:]:
            bbox = region["bbox"]
            did_merge = False
            for existing in merged:
                eb = existing["bbox"]
                if (bbox[0] < eb[2] and bbox[2] > eb[0] and
                    bbox[1] < eb[3] and bbox[3] > eb[1]):
                    existing["bbox"] = (
                        min(bbox[0], eb[0]), min(bbox[1], eb[1]),
                        max(bbox[2], eb[2]), max(bbox[3], eb[3])
                    )
                    existing["confidence"] = max(existing["confidence"],
                                                  region["confidence"])
                    did_merge = True
                    break
            if not did_merge:
                merged.append(region)

        return merged


class MRE901AuthenticationGenerator:
    """
    Generate MRE 901 authentication metadata for evidence exhibits.
    Tracks chain of custody, extraction method, and verification.
    """

    def generate(self, file_path: str, ocr_result: OCRResult,
                 lane: LaneAssignment, quality: dict) -> dict:
        """Generate authentication metadata for an exhibit."""
        import os
        from datetime import datetime

        file_stat = os.stat(file_path) if os.path.exists(file_path) else None

        return {
            "exhibit_source": file_path,
            "file_size_bytes": file_stat.st_size if file_stat else 0,
            "file_modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                            if file_stat else None,
            "content_hash_sha256": ocr_result.content_hash(),
            "extraction_method": ocr_result.engine,
            "extraction_date": datetime.now().isoformat(),
            "ocr_confidence": ocr_result.total_confidence,
            "quality_grade": quality.get("grade", "?"),
            "page_count": ocr_result.page_count,
            "lane_assignment": lane.primary_lane,
            "document_type": lane.document_type,
            "authentication_basis": self._determine_basis(ocr_result, lane),
            "chain_of_custody": [
                {
                    "action": "extracted",
                    "timestamp": datetime.now().isoformat(),
                    "method": f"OCR ensemble ({ocr_result.engine})",
                    "operator": "LitigationOS APEX-VISION pipeline"
                }
            ],
            "mre_901_grounds": self._mre_grounds(lane),
            "is_authenticated": quality.get("grade", "F") in ("A", "B", "C"),
            "needs_affidavit": True,
            "sullivan_v_gray_applicable": self._is_recording(file_path)
        }

    def _determine_basis(self, ocr_result: OCRResult, lane: LaneAssignment) -> str:
        if lane.document_type == "police_report":
            return "MRE 901(b)(7) — Public record"
        if lane.document_type == "order":
            return "MRE 901(b)(7) — Public record / court document"
        if lane.document_type == "transcript":
            return "MRE 901(b)(1) — Testimony of witness with knowledge"
        return "MRE 901(b)(1) — Testimony of witness with knowledge"

    def _mre_grounds(self, lane: LaneAssignment) -> list[str]:
        grounds = ["MRE 901(b)(1) — Testimony of custodian"]
        if lane.document_type in ("police_report", "order"):
            grounds.append("MRE 901(b)(7) — Public record or report")
            grounds.append("MRE 902(1) — Self-authenticating public documents")
        if lane.document_type == "transcript":
            grounds.append("MRE 901(b)(5) — Voice identification")
        return grounds

    def _is_recording(self, path: str) -> bool:
        ext = Path(path).suffix.lower()
        return ext in (".mp3", ".mp4", ".wav", ".m4a", ".avi", ".mov", ".mkv")
```

---

## Complete Pipeline Orchestrator

```python
class APEXVisionPipeline:
    """
    Master orchestrator for the APEX-VISION document AI pipeline.
    Chains: Ingest → OCR → Layout → Extract → Route → Persist
    """

    def __init__(self, db_path: str = "litigation_context.db"):
        self.ensemble = OCREnsemble()
        self.layout_analyzer = LegalDocumentAnalyzer()
        self.table_extractor = TableExtractor()
        self.form_recognizer = FormRecognizer()
        self.entity_extractor = LegalEntityExtractor()
        self.bates_detector = BatesStampDetector()
        self.quality_scorer = QualityScorer()
        self.lane_router = MEEKLaneRouter()
        self.preprocessor = ImagePreprocessor()
        self.handwriting_detector = HandwritingDetector()
        self.auth_generator = MRE901AuthenticationGenerator()
        self.db_path = db_path

    def process_file(self, file_path: str,
                     preprocess: bool = True) -> dict:
        """
        Full pipeline for a single file.
        Returns comprehensive extraction result.
        """
        logger.info(f"Processing: {file_path}")

        # Step 1: OCR extraction
        ocr_result = self.ensemble.extract(file_path)

        # Step 2: Quality scoring
        quality = self.quality_scorer.score_document(ocr_result)

        # Step 3: Layout analysis
        layouts = self.layout_analyzer.analyze_document(ocr_result)

        # Step 4: Table extraction
        tables = []
        for layout in layouts:
            tables.extend(self.table_extractor.extract_tables(layout))

        # Step 5: Form recognition
        forms = self.form_recognizer.auto_recognize(ocr_result)

        # Step 6: Entity extraction
        entities = self.entity_extractor.extract_from_ocr(ocr_result)

        # Step 7: Bates stamp detection
        bates = []
        for page in ocr_result.pages:
            bates.extend(self.bates_detector.detect(page))

        # Step 8: Lane routing
        lane = self.lane_router.route(ocr_result.full_text, file_path)

        # Step 9: Authentication metadata
        auth = self.auth_generator.generate(file_path, ocr_result, lane, quality)

        result = {
            "file_path": file_path,
            "ocr": {
                "engine": ocr_result.engine,
                "pages": ocr_result.page_count,
                "confidence": ocr_result.total_confidence,
                "processing_ms": ocr_result.processing_time_ms,
                "content_hash": ocr_result.content_hash(),
            },
            "quality": quality,
            "layout": {
                "pages": len(layouts),
                "zones": sum(len(l.regions) for l in layouts),
                "has_tables": len(tables) > 0,
                "has_handwriting": any(l.has_handwriting for l in layouts),
            },
            "tables": tables,
            "forms": [
                self.form_recognizer.score_completeness(f) for f in forms
            ],
            "entities": {
                etype: [{"value": e.value, "confidence": e.confidence, "page": e.page}
                       for e in elist]
                for etype, elist in entities.items()
            },
            "bates_stamps": bates,
            "lane": {
                "primary": lane.primary_lane,
                "name": lane.lane_name,
                "confidence": lane.confidence,
                "signals": lane.signals[:10],
                "document_type": lane.document_type,
                "priority": lane.priority_score,
                "smoking_gun": lane.smoking_gun,
            },
            "authentication": auth,
            "full_text": ocr_result.full_text,
        }

        return result

    def process_batch(self, file_paths: list[str],
                      max_workers: int = 4) -> list[dict]:
        """Process multiple files with progress tracking."""
        results = []
        total = len(file_paths)

        for i, path in enumerate(file_paths):
            try:
                result = self.process_file(path)
                results.append(result)
                logger.info(f"[{i+1}/{total}] ✅ {Path(path).name} "
                           f"→ Lane {result['lane']['primary']} "
                           f"(conf={result['ocr']['confidence']:.2f})")
            except Exception as e:
                logger.error(f"[{i+1}/{total}] ❌ {Path(path).name}: {e}")
                results.append({"file_path": path, "error": str(e)})

        return results

    def persist_to_db(self, result: dict, conn=None) -> int:
        """Persist extraction results to evidence_quotes table."""
        import sqlite3

        if conn is None:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA busy_timeout = 60000")
            conn.execute("PRAGMA journal_mode = WAL")

        full_text = result.get("full_text", "")
        lane = result.get("lane", {})
        quality = result.get("quality", {})
        rows_inserted = 0

        # Insert as evidence quote
        try:
            conn.execute("""
                INSERT OR IGNORE INTO evidence_quotes
                (quote_text, source_file, category, lane, confidence, page_number)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                full_text[:5000],
                result["file_path"],
                lane.get("document_type", "unknown"),
                lane.get("primary", "A"),
                quality.get("avg_quality", 0),
                1
            ))
            rows_inserted += conn.total_changes
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"DB persist error: {e}")

        return rows_inserted
```

---

## Anti-Patterns (25 Rules)

1. NEVER trust OCR output below 60% confidence without human review flag
2. NEVER OCR password-protected PDFs without explicit user authorization
3. NEVER skip native text extraction (pypdfium2) — it's 10× faster and more accurate
4. NEVER run PaddleOCR and Surya simultaneously — GPU memory overflow risk
5. NEVER store raw OCR text as evidence without quality scoring
6. NEVER assume single-column layout — always detect columns first
7. NEVER merge table regions with paragraph regions during layout analysis
8. NEVER trust handwriting OCR above 80% confidence without verification
9. NEVER skip Bates stamp detection — existing stamps indicate prior legal processing
10. NEVER route a document to multiple primary lanes — one lane only, with secondary signals
11. NEVER apply binarization to color-critical evidence (photos, highlighted documents)
12. NEVER upscale already high-DPI images — wastes memory and processing time
13. NEVER OCR at resolution below 200 DPI — accuracy drops exponentially
14. NEVER cache OCR results without content hashing — file may have been modified
15. NEVER run OCR on video files — extract frames first, then OCR individual frames
16. NEVER ignore Surya's layout detection when available — it outperforms heuristics
17. NEVER process more than 50 pages in a single OCR batch — memory and timeout risk
18. NEVER persist entities without deduplication — same entity found multiple times per page
19. NEVER skip MRE 901 authentication metadata — exhibits need provenance chain
20. NEVER allow OCR errors to silently propagate — log and flag every engine failure
21. NEVER use Tesseract as primary engine when PaddleOCR is available
22. NEVER apply aggressive denoising to handwriting — destroys stroke detail
23. NEVER assume English-only — court documents may contain foreign names/text
24. NEVER skip form completeness scoring — incomplete forms should not be filed
25. NEVER generate smoking gun alerts without verifying keyword context (avoid false positives)

## Performance Budgets

| Operation | Budget | Technique |
|-----------|--------|-----------|
| Native PDF extraction | <100ms/page | pypdfium2 direct text |
| OCR (printed text) | <2s/page | PaddleOCR with 300 DPI |
| OCR (handwriting) | <5s/page | Surya with preprocessing |
| Layout analysis | <200ms/page | Regex + heuristic classification |
| Form recognition | <100ms/document | Template pattern matching |
| Entity extraction | <50ms/page | Compiled regex patterns |
| Lane routing | <10ms/document | Keyword scoring |
| Quality scoring | <50ms/page | Statistical analysis |
| Image preprocessing | <500ms/page | PIL/NumPy operations |
| Batch processing | <3s/page average | Ensemble with early exit |
| DB persistence | <20ms/document | Single INSERT with WAL |

## Research Citations

- **PaddleOCR** — Baidu, 2024. Multi-language OCR with angle classification
- **PaddleOCR-VL-1.5** — Vision-language multimodal OCR (2025)
- **Surya** — Layout-aware OCR with reading order detection (VikParuchuri, 2024)
- **PP-StructureV3** — Table and form structure extraction (Baidu, 2024)
- **DocTR** — Document Text Recognition (Mindee, 2024)
- **TrOCR** — Transformer-based OCR (Microsoft, 2023)
- **LayoutLMv3** — Pre-trained multimodal document AI model (Microsoft, 2022)
- **pypdfium2** — Python bindings for PDFium (Google's PDF engine)
- **Sullivan v Gray** — 117 Mich App 476 (1982) — one-party recording consent

## Cross-Links

- **APEX-AUTOMATON** — Receives OCR output for legal reasoning pipeline
- **APEX-MEMORY** — Persists extraction results to episodic/semantic memory
- **COMBAT-EVIDENCE** — Evidence density visualization from OCR findings
- **DOCUMENT-FORGE** — Court-ready PDF generation from extracted content
- **INTEGRATION-FILING** — Filing pipeline receives lane-routed evidence
- **APEX-GRAPHML** — Entity relationships fed into knowledge graph
