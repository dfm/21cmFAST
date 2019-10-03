"""
Various tests of the initial_conditions() function and InitialConditions class.
"""

import pytest
from py21cmfast import wrapper
import numpy as np


@pytest.fixture(scope="module")  # call this fixture once for all tests in this module
def basic_init_box():
    return wrapper.initial_conditions(
        regenerate=True, write=False, user_params=wrapper.UserParams(HII_DIM=35)
    )


def test_box_shape(basic_init_box):
    """Test basic properties of the InitialConditions struct"""
    shape = (35, 35, 35)
    assert basic_init_box.lowres_density.shape == shape
    assert basic_init_box.lowres_vx.shape == shape
    assert basic_init_box.lowres_vy.shape == shape
    assert basic_init_box.lowres_vz.shape == shape
    assert basic_init_box.lowres_vx_2LPT.shape == shape
    assert basic_init_box.lowres_vy_2LPT.shape == shape
    assert basic_init_box.lowres_vz_2LPT.shape == shape
    assert basic_init_box.hires_density.shape == tuple([4 * s for s in shape])

    assert basic_init_box.cosmo_params == wrapper.CosmoParams()


def test_modified_cosmo():
    """Test using a modified cosmology"""
    cosmo = wrapper.CosmoParams(sigma_8=0.9)
    ic = wrapper.initial_conditions(cosmo_params=cosmo, regenerate=True, write=False)

    assert ic.cosmo_params == cosmo
    assert ic.cosmo_params.SIGMA_8 == cosmo.SIGMA_8


def test_transfer_function(basic_init_box):
    """Test using a modified transfer function"""
    ic = wrapper.initial_conditions(
        regenerate=True,
        write=False,
        random_seed=basic_init_box.random_seed,
        user_params=wrapper.UserParams(HII_DIM=35),
    )

    rmsnew = np.sqrt(np.mean(ic.hires_density ** 2))
    rmsdelta = np.sqrt(np.mean((ic.hires_density - basic_init_box.hires_density) ** 2))
    assert rmsdelta < rmsnew
    assert rmsnew > 0.0
    assert not np.allclose(ic.hires_density, basic_init_box.hires_density)
