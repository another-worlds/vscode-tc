import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from worker import model_registry


@pytest.fixture(autouse=True)
def clear_model_cache(monkeypatch):
    model_registry._model_cache.clear()
    yield
    model_registry._model_cache.clear()


class TestModelRegistry:
    @pytest.mark.asyncio
    async def test_load_model_from_registry_cache_hit(self, monkeypatch):
        dummy_model = MagicMock()
        model_registry._model_cache["yolov8m"] = dummy_model

        model = model_registry.get_model("yolov8m")

        assert model is dummy_model

    @pytest.mark.asyncio
    async def test_load_model_downloads_if_missing(self, monkeypatch):
        fake_home = Path("/tmp")
        monkeypatch.setattr(model_registry.Path, "home", lambda: fake_home)
        monkeypatch.setattr(model_registry.Path, "exists", lambda self: False)
        monkeypatch.setattr(model_registry.Path, "mkdir", lambda self, *args, **kwargs: None)

        fake_yolo = MagicMock()
        monkeypatch.setattr(model_registry, "YOLO", fake_yolo)

        fake_torch = MagicMock()
        fake_torch.cuda.is_available.return_value = False
        sys.modules["torch"] = fake_torch

        model = model_registry.load_model("yolov8m")

        assert model is fake_yolo.return_value
        fake_yolo.assert_called_once_with("yolov8m")
        assert "yolov8m" in model_registry._model_cache

    @pytest.mark.asyncio
    async def test_load_model_uses_existing_weights_path(self, monkeypatch):
        fake_home = Path("/tmp")
        monkeypatch.setattr(model_registry.Path, "home", lambda: fake_home)

        def fake_exists(path_self):
            return str(path_self).endswith("yolov8m.pt")

        monkeypatch.setattr(model_registry.Path, "exists", fake_exists)
        monkeypatch.setattr(model_registry.Path, "mkdir", lambda self, *args, **kwargs: None)

        fake_yolo = MagicMock()
        monkeypatch.setattr(model_registry, "YOLO", fake_yolo)

        fake_torch = MagicMock()
        fake_torch.cuda.is_available.return_value = True
        sys.modules["torch"] = fake_torch

        model = model_registry.load_model("yolov8m")

        assert model is fake_yolo.return_value
        assert fake_yolo.call_args[0][0].endswith("yolov8m.pt")

    def test_load_model_unknown_key_raises(self):
        with pytest.raises(KeyError):
            model_registry.load_model("invalid-model")
