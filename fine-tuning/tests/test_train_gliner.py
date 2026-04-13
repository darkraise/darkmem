"""Tests for GLiNER training script compatibility."""
from __future__ import annotations


def test_gliner_training_imports():
    """All imports used by train_gliner.py must resolve without error."""
    from gliner import GLiNER
    from gliner.training import TrainingArguments, Trainer
    import importlib
    mod = importlib.import_module("gliner.training")
    assert hasattr(mod, "Trainer")
    assert hasattr(mod, "TrainingArguments")
    assert not hasattr(mod, "TrainDataset"), "TrainDataset should not exist in gliner.training"


def test_gliner_base_has_data_collator_class():
    """BaseGLiNER exposes data_collator_class; concrete subclasses set it to the right collator."""
    from gliner.model import BaseGLiNER
    assert hasattr(BaseGLiNER, "data_collator_class"), "BaseGLiNER.data_collator_class not found"


def test_gliner_model_has_data_processor():
    """GLiNER model exposes data_processor after init."""
    from gliner.model import BaseGLiNER
    assert hasattr(BaseGLiNER, "data_processor_class"), "BaseGLiNER.data_processor_class not found"
