from pathlib import Path

import hydra
import nnsvs.bin.train
import pytest
import torch
from nnsvs.base import PredictionType
from nnsvs.util import init_seed
from omegaconf import OmegaConf

RECIPE_DIR = Path(__file__).parent.parent / "recipes"


def _test_model_impl(model, model_config):
    B = 4
    T = 100
    init_seed(B * T)
    x = torch.rand(B, T, model_config.netG.in_dim)
    lengths = torch.Tensor([T] * B).long()

    # warmup forward pass
    with torch.no_grad():
        y = model(x, lengths)
        y_inf = model.inference(x, lengths)

    # MDN case
    if model.prediction_type() == PredictionType.PROBABILISTIC:
        log_pi, log_sigma, mu = y
        num_gaussian = log_pi.shape[2]
        assert mu.shape == (B, T, num_gaussian, model_config.netG.out_dim)
        assert log_sigma.shape == (B, T, num_gaussian, model_config.netG.out_dim)

        # NOTE: infernece output shouldn't have num_gaussian axis
        mu_inf, sigma_inf = y_inf
        assert mu_inf.shape == (B, T, model_config.netG.out_dim)
        assert sigma_inf.shape == (B, T, model_config.netG.out_dim)
    else:
        assert y.shape == (B, T, model_config.netG.out_dim)
        assert y.shape == y_inf.shape


def _test_resf0_model_impl(model, model_config):
    B = 4
    T = 100
    init_seed(B * T)
    x = torch.rand(B, T, model_config.netG.in_dim)
    lengths = torch.Tensor([T] * B).long()

    # warmup forward pass
    with torch.no_grad():
        y, lf0_residual = model(x, lengths)
        y_inf = model.inference(x, lengths)

    # MDN case
    if model.prediction_type() == PredictionType.PROBABILISTIC:
        log_pi, log_sigma, mu = y
        num_gaussian = log_pi.shape[2]
        assert mu.shape == (B, T, num_gaussian, model_config.netG.out_dim)
        assert log_sigma.shape == (B, T, num_gaussian, model_config.netG.out_dim)
        assert lf0_residual.shape == (B, T, num_gaussian)

        # NOTE: infernece output shouldn't have num_gaussian axis
        mu_inf, sigma_inf = y_inf
        assert mu_inf.shape == (B, T, model_config.netG.out_dim)
        assert sigma_inf.shape == (B, T, model_config.netG.out_dim)
    else:
        assert lf0_residual.shape == (B, T, 1)
        assert y.shape == (B, T, model_config.netG.out_dim)
        assert y.shape == y_inf.shape


def _test_postfilter_impl(model, model_config):
    B = 4
    T = 100
    init_seed(B * T)

    in_dim = sum(model_config.netG.stream_sizes)
    x = torch.rand(B, T, in_dim)
    lengths = torch.Tensor([T] * B).long()

    # warmup forward pass
    with torch.no_grad():
        y = model(x, lengths)
        y_inf = model.inference(x, lengths)

    assert x.shape == y.shape
    assert y_inf.shape == y.shape


@pytest.mark.parametrize(
    "model_config",
    (Path(nnsvs.bin.train.__file__).parent / "conf" / "train" / "model").glob("*.yaml"),
)
def test_model_config(model_config):
    model_config = OmegaConf.load(model_config)
    model = hydra.utils.instantiate(model_config.netG)
    _test_model_impl(model, model_config)


@pytest.mark.parametrize(
    "model_config",
    (Path(nnsvs.bin.train.__file__).parent / "conf" / "train_resf0" / "model").glob(
        "*.yaml"
    ),
)
def test_resf0_acoustic_model_config(model_config):
    model_config = OmegaConf.load(model_config)

    # Dummy
    model_config.netG.in_lf0_idx = 10
    model_config.netG.in_lf0_min = 5.3936276
    model_config.netG.in_lf0_max = 6.491111
    model_config.netG.out_lf0_idx = 180
    model_config.netG.out_lf0_mean = 5.953093881972361
    model_config.netG.out_lf0_scale = 0.23435173188961034

    model = hydra.utils.instantiate(model_config.netG)
    _test_resf0_model_impl(model, model_config)


@pytest.mark.parametrize(
    "model_config", RECIPE_DIR.glob("**/conf/train/timelag/model/*.yaml")
)
def test_timelag_model_config_recipes(model_config):
    model_config = OmegaConf.load(model_config)
    model = hydra.utils.instantiate(model_config.netG)
    _test_model_impl(model, model_config)


@pytest.mark.parametrize(
    "model_config", RECIPE_DIR.glob("**/conf/train/duration/model/*.yaml")
)
def test_duration_model_config_recipes(model_config):
    model_config = OmegaConf.load(model_config)
    model = hydra.utils.instantiate(model_config.netG)
    _test_model_impl(model, model_config)


@pytest.mark.parametrize(
    "model_config", RECIPE_DIR.glob("**/conf/train/acoustic/model/*.yaml")
)
def test_acoustic_model_config_recipes(model_config):
    model_config = OmegaConf.load(model_config)
    model = hydra.utils.instantiate(model_config.netG)
    _test_model_impl(model, model_config)


@pytest.mark.parametrize(
    "model_config", RECIPE_DIR.glob("**/conf/train_resf0/acoustic/model/*.yaml")
)
def test_resf0_acoustic_model_config_recipes(model_config):
    model_config = OmegaConf.load(model_config)

    # Dummy
    model_config.netG.in_lf0_idx = 10
    model_config.netG.in_lf0_min = 5.3936276
    model_config.netG.in_lf0_max = 6.491111
    model_config.netG.out_lf0_idx = 180
    model_config.netG.out_lf0_mean = 5.953093881972361
    model_config.netG.out_lf0_scale = 0.23435173188961034

    model = hydra.utils.instantiate(model_config.netG)
    _test_resf0_model_impl(model, model_config)


@pytest.mark.parametrize(
    "model_config", RECIPE_DIR.glob("**/conf/train_postfilter/model/*.yaml")
)
def test_postfilter_config_recipes(model_config):
    model_config = OmegaConf.load(model_config)
    # Post-filter config should have netD
    hydra.utils.instantiate(model_config.netD)
    model = hydra.utils.instantiate(model_config.netG)
    _test_postfilter_impl(model, model_config)