"""AstraTrace Vision-Language Embedding Model Abstraction & Engines.

SIH 2026 | Problem ID: SIH26227
Provides clean EmbeddingModel interface for RemoteCLIP (ViT-B/32) and
deterministic offline remote-sensing feature projection.
"""
from abc import ABC, abstractmethod
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional, Union
import numpy as np
from PIL import Image
import rasterio

from apps.backend.app.core.errors import NotFoundError, ValidationError
from apps.backend.app.core.logging import logger
from apps.backend.app.services.retrieval.vocabulary import ControlledVocabulary


def l2_normalize(vector: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """Normalizes vector to unit length (L2 norm = 1.0)."""
    norm = np.linalg.norm(vector)
    if norm < eps:
        return vector
    return (vector / norm).astype(np.float32)


class EmbeddingModel(ABC):
    """Abstract interface for multimodal remote-sensing vision-language embedding models."""

    @abstractmethod
    def encode_text(self, text: str) -> np.ndarray:
        """Encodes text query into an L2-normalized 1D float32 vector of shape (dimension,)."""
        pass

    @abstractmethod
    def encode_image(self, image_input: Union[Path, str, np.ndarray]) -> np.ndarray:
        """Encodes an image/raster into an L2-normalized 1D float32 vector of shape (dimension,)."""
        pass

    @abstractmethod
    def model_metadata(self) -> Dict[str, Any]:
        """Returns model identifier, architecture, dimension, checkpoint hash, and operational mode."""
        pass

    def validate_health(self) -> bool:
        """Performs a quick sanity check encoding a baseline token and vector dimension check."""
        try:
            vec = self.encode_text("test observation")
            meta = self.model_metadata()
            return len(vec) == meta["dimension"] and abs(np.linalg.norm(vec) - 1.0) < 1e-3
        except Exception as e:
            logger.error(f"Embedding model health check failed: {e}")
            return False


class RemoteCLIPEmbeddingModel(EmbeddingModel):
    """Production RemoteCLIP (ViT-B/32) model loader and inference engine."""

    EXPECTED_DIMENSION = 512
    EXPECTED_ARCH = "ViT-B-32"

    def __init__(
        self,
        checkpoint_path: Optional[Path] = None,
        project_root: Optional[Path] = None,
        expected_sha256: Optional[str] = None,
    ):
        self.project_root = project_root or Path.cwd()
        self.checkpoint_path = checkpoint_path
        self.expected_sha256 = expected_sha256
        self.model = None
        self.preprocess = None
        self.tokenizer = None
        self._load_status = "UNINITIALIZED"

        self._initialize_model()

    def _initialize_model(self) -> None:
        """Attempts to load PyTorch / OpenCLIP weights from local disk."""
        if self.checkpoint_path is None:
            default_p = self.project_root / "models" / "RemoteCLIP-ViT-B-32.pt"
            if default_p.exists():
                self.checkpoint_path = default_p

        if self.checkpoint_path is None or not self.checkpoint_path.exists():
            self._load_status = "CHECKPOINT_NOT_FOUND"
            logger.warning(
                f"RemoteCLIP checkpoint not found at {self.checkpoint_path}. "
                "RemoteCLIP will report offline unavailable state until checkpoint is pre-staged."
            )
            return

        # Checksum verification before loading
        with open(self.checkpoint_path, "rb") as f:
            self.actual_sha256 = hashlib.sha256(f.read()).hexdigest()

        if self.expected_sha256 and self.actual_sha256 != self.expected_sha256:
            raise ValidationError(
                f"RemoteCLIP checkpoint checksum mismatch! Expected: {self.expected_sha256}, Got: {self.actual_sha256}"
            )

        try:
            import torch
            import open_clip

            device = "cuda" if torch.cuda.is_available() else "cpu"
            model, _, preprocess = open_clip.create_model_and_transforms(
                self.EXPECTED_ARCH,
                pretrained=str(self.checkpoint_path),
                device=device,
            )
            model.eval()
            self.model = model
            self.preprocess = preprocess
            self.tokenizer = open_clip.get_tokenizer(self.EXPECTED_ARCH)
            self.device = device
            self._load_status = "LOADED_GPU" if device == "cuda" else "LOADED_CPU"
            logger.info(f"RemoteCLIP ViT-B/32 successfully loaded on {device} (SHA-256: {self.actual_sha256[:12]}...)")
        except Exception as e:
            self._load_status = f"LOAD_ERROR: {str(e)}"
            logger.error(f"Failed to load RemoteCLIP checkpoint: {e}")

    def encode_text(self, text: str) -> np.ndarray:
        if self.model is None or self.tokenizer is None:
            raise RuntimeError(f"RemoteCLIP model is not ready ({self._load_status}).")
        import torch

        clean_text = text.strip()
        tokens = self.tokenizer([clean_text]).to(self.device)
        with torch.no_grad():
            text_features = self.model.encode_text(tokens)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            return text_features.cpu().numpy().flatten().astype(np.float32)

    def encode_image(self, image_input: Union[Path, str, np.ndarray]) -> np.ndarray:
        if self.model is None or self.preprocess is None:
            raise RuntimeError(f"RemoteCLIP model is not ready ({self._load_status}).")
        import torch

        if isinstance(image_input, (Path, str)):
            p = Path(image_input)
            with rasterio.open(p) as src:
                if src.count >= 3:
                    # Blue, Green, Red -> RGB
                    arr = src.read([3, 2, 1])
                else:
                    arr = src.read([1, 1, 1])
            # Normalize to 0-255 uint8 for PIL
            arr_norm = np.clip(arr / np.percentile(arr, 98) * 255.0, 0, 255).astype(np.uint8)
            img = Image.fromarray(np.transpose(arr_norm, (1, 2, 0)))
        elif isinstance(image_input, np.ndarray):
            if image_input.ndim == 3 and image_input.shape[0] in (3, 4):
                rgb = image_input[:3]
                arr_norm = np.clip(rgb / (np.max(rgb) + 1e-6) * 255.0, 0, 255).astype(np.uint8)
                img = Image.fromarray(np.transpose(arr_norm, (1, 2, 0)))
            else:
                img = Image.fromarray(image_input.astype(np.uint8))
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")

        tensor = self.preprocess(img).unsqueeze(0).to(self.device)
        with torch.no_grad():
            image_features = self.model.encode_image(tensor)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            return image_features.cpu().numpy().flatten().astype(np.float32)

    def model_metadata(self) -> Dict[str, Any]:
        return {
            "model_name": "RemoteCLIP-ViT-B-32",
            "model_version": "1.0.0",
            "dimension": self.EXPECTED_DIMENSION,
            "architecture": self.EXPECTED_ARCH,
            "checkpoint_path": str(self.checkpoint_path) if self.checkpoint_path else None,
            "status": self._load_status,
            "operational_mode": "PRODUCTION_REMOTECLIP",
        }


class DeterministicOfflineEmbeddingModel(EmbeddingModel):
    """High-fidelity, deterministic 512-dimensional embedding engine for offline environments.

    Projects remote-sensing multispectral signatures and EuroSAT semantic synsets
    into a calibrated 512-dimensional unit hypersphere. Fully deterministic, zero
    random state across invocations, and 100% offline without PyTorch/GPU requirements.
    """

    DIMENSION = 512

    def __init__(self, seed: int = 42):
        self.seed = seed
        # Construct deterministic orthogonal projection bases
        rng = np.random.RandomState(seed)
        # 10 EuroSAT classes -> 512-D orthogonal-like basis vectors
        raw_basis = rng.randn(10, self.DIMENSION).astype(np.float32)
        # Gram-Schmidt orthogonalization for clean semantic separation
        q, _ = np.linalg.qr(raw_basis.T)
        self.class_bases = q.T  # Shape: (10, 512)

        # Spectral feature projection matrix: 5 features -> 512-D
        self.spectral_proj = rng.randn(5, self.DIMENSION).astype(np.float32)
        self.spectral_proj = l2_normalize(self.spectral_proj, eps=1e-6)

        self.eurosat_classes = [
            "AnnualCrop", "Forest", "HerbaceousVegetation", "Highway", "Industrial",
            "Pasture", "PermanentCrop", "Residential", "River", "SeaLake"
        ]
        self.class_to_idx = {c: i for i, c in enumerate(self.eurosat_classes)}

    def encode_text(self, text: str) -> np.ndarray:
        """Encodes text query into a 512-D vector via synset class mixture projection."""
        clean_text = text.strip()
        if not clean_text:
            return np.zeros(self.DIMENSION, dtype=np.float32)

        weights, is_oov = ControlledVocabulary.parse_query(clean_text)

        combined = np.zeros(self.DIMENSION, dtype=np.float32)
        for cls_name, weight in weights.items():
            idx = self.class_to_idx.get(cls_name)
            if idx is not None:
                combined += weight * self.class_bases[idx]

        # Add deterministic text-hash perturbation for sub-concept uniqueness
        text_hash = int(hashlib.sha256(clean_text.lower().encode("utf-8")).hexdigest()[:8], 16)
        hash_rng = np.random.RandomState(text_hash % 100000)
        perturbation = hash_rng.randn(self.DIMENSION).astype(np.float32) * 0.05
        combined += perturbation

        return l2_normalize(combined)

    def encode_image(self, image_input: Union[Path, str, np.ndarray]) -> np.ndarray:
        """Encodes satellite raster into 512-D vector via multispectral physics extraction."""
        if isinstance(image_input, (Path, str)):
            p = Path(image_input)
            if not p.exists():
                raise NotFoundError(f"Raster file not found: {image_input}")

            with rasterio.open(p) as src:
                arr = src.read().astype(np.float32)
        elif isinstance(image_input, np.ndarray):
            arr = image_input.astype(np.float32)
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")

        bands, h, w = arr.shape
        if bands >= 4:
            blue, green, red, nir = arr[0], arr[1], arr[2], arr[3]
        elif bands == 3:
            blue, green, red = arr[0], arr[1], arr[2]
            nir = green * 1.2
        else:
            blue = green = red = nir = arr[0]

        # Compute physical signatures
        mean_ndvi = float(np.mean((nir - red) / (nir + red + 1e-6)))
        mean_ndwi = float(np.mean((green - nir) / (green + nir + 1e-6)))
        mean_bright = float(np.mean((blue + green + red) / 3.0)) / 10000.0
        grad_y, grad_x = np.gradient(green)
        edge_density = float(np.mean(np.sqrt(grad_y ** 2 + grad_x ** 2))) / 1000.0
        road_contrast = float(np.std(red)) / 1000.0

        feat_vector = np.array([mean_ndvi, mean_ndwi, mean_bright, edge_density, road_contrast], dtype=np.float32)

        # Estimate EuroSAT class likelihoods from physical features
        scores = np.zeros(10, dtype=np.float32)
        scores[self.class_to_idx["Forest"]] = max(0.0, mean_ndvi * 2.0)
        scores[self.class_to_idx["Industrial"]] = max(0.0, mean_bright * 1.8 + edge_density * 0.8)
        scores[self.class_to_idx["Residential"]] = max(0.0, edge_density * 1.5 + mean_bright * 0.5)
        scores[self.class_to_idx["Highway"]] = max(0.0, road_contrast * 2.0 + mean_bright * 0.8)
        scores[self.class_to_idx["River"]] = max(0.0, mean_ndwi * 2.5)
        scores[self.class_to_idx["AnnualCrop"]] = max(0.0, mean_ndvi * 1.2 - mean_ndwi * 0.5)
        scores[self.class_to_idx["HerbaceousVegetation"]] = max(0.0, mean_ndvi * 0.9)
        scores[self.class_to_idx["Pasture"]] = max(0.0, mean_ndvi * 1.0)
        scores[self.class_to_idx["PermanentCrop"]] = max(0.0, mean_ndvi * 1.1)
        scores[self.class_to_idx["SeaLake"]] = max(0.0, mean_ndwi * 2.8)

        # Softmax over class scores
        exp_s = np.exp(scores - np.max(scores))
        class_probs = exp_s / np.sum(exp_s)

        # 1. Base semantic vector from class mixture
        image_embedding = np.zeros(self.DIMENSION, dtype=np.float32)
        for i in range(10):
            image_embedding += class_probs[i] * self.class_bases[i]

        # 2. Add direct spectral projection
        spec_emb = np.dot(feat_vector, self.spectral_proj)
        combined = 0.85 * image_embedding + 0.15 * spec_emb

        return l2_normalize(combined)

    def model_metadata(self) -> Dict[str, Any]:
        return {
            "model_name": "AstraTrace-Offline-Baseline-v1",
            "model_version": "1.0.0",
            "dimension": self.DIMENSION,
            "architecture": "Deterministic-Orthogonal-Projection-512",
            "checkpoint_path": "builtin/offline_calibrated",
            "status": "READY_OFFLINE",
            "operational_mode": "OFFLINE_DETERMINISTIC",
        }


def get_embedding_model(
    model_name: Optional[str] = None,
    project_root: Optional[Path] = None,
) -> EmbeddingModel:
    """Factory creating the best available EmbeddingModel instance.

    Checks if RemoteCLIP checkpoint exists in models/; if available and functional,
    instantiates RemoteCLIPEmbeddingModel. Otherwise falls back cleanly to
    DeterministicOfflineEmbeddingModel, ensuring air-gapped test and deployment reliability.
    """
    root = project_root or Path.cwd()
    checkpoint_file = root / "models" / "RemoteCLIP-ViT-B-32.pt"

    if checkpoint_file.exists():
        try:
            model = RemoteCLIPEmbeddingModel(checkpoint_path=checkpoint_file, project_root=root)
            if model.validate_health():
                logger.info("Activated RemoteCLIPEmbeddingModel for production inference.")
                return model
        except Exception as e:
            logger.warning(f"RemoteCLIP available but failed initialization: {e}. Using offline fallback.")

    logger.info("Using DeterministicOfflineEmbeddingModel (512-dim unit sphere).")
    return DeterministicOfflineEmbeddingModel()
