#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# test_big_phi.py

import pickle
import pytest
import numpy as np
from unittest.mock import patch

from pyphi import constants, config, compute, models, utils, Network, Subsystem
from pyphi.constants import Direction
from pyphi.models import Cut, _null_bigmip
from pyphi.compute import constellation
from pyphi.compute.big_phi import (_find_mip_parallel, _find_mip_sequential,
                                   big_mip_bipartitions)

# TODO: split these into `concept` and `big_phi` tests

# Answers
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

standard_answer = {
    'phi': 2.3125,
    'unpartitioned_small_phis': {
        (1,): 0.25,
        (2,): 0.5,
        (0, 1): 0.333333,
        (0, 1, 2): 0.5
    },
    'len_partitioned_constellation': 1,
    'sum_partitioned_small_phis': 0.5,
    'cut': models.Cut(severed=(1, 2), intact=(0,))
}


noised_answer = {
    'phi': 1.928592,
    'unpartitioned_small_phis': {
        (0,): 0.0625,
        (1,): 0.2,
        (2,): 0.316326,
        (0, 1): 0.319047,
        (0, 2): 0.0125,
        (1, 2): 0.263847,
        (0, 1, 2): 0.35
    },
    'len_partitioned_constellation': 7,
    'sum_partitioned_small_phis': 0.504906,
    'cut': models.Cut(severed=(1, 2), intact=(0,))
}


big_answer = {
    'phi': 10.729491,
    'unpartitioned_small_phis': {
        (0,): 0.25,
        (1,): 0.25,
        (2,): 0.25,
        (3,): 0.25,
        (4,): 0.25,
        (0, 1): 0.2,
        (0, 2): 0.2,
        (0, 3): 0.2,
        (0, 4): 0.2,
        (1, 2): 0.2,
        (1, 3): 0.2,
        (1, 4): 0.2,
        (2, 3): 0.2,
        (2, 4): 0.2,
        (3, 4): 0.2,
        (0, 1, 2): 0.2,
        (0, 1, 3): 0.257143,
        (0, 1, 4): 0.2,
        (0, 2, 3): 0.257143,
        (0, 2, 4): 0.257143,
        (0, 3, 4): 0.2,
        (1, 2, 3): 0.2,
        (1, 2, 4): 0.257143,
        (1, 3, 4): 0.257143,
        (2, 3, 4): 0.2,
        (0, 1, 2, 3): 0.185709,
        (0, 1, 2, 4): 0.185709,
        (0, 1, 3, 4): 0.185709,
        (0, 2, 3, 4): 0.185709,
        (1, 2, 3, 4): 0.185709
    },
    'len_partitioned_constellation': 17,
    'sum_partitioned_small_phis': 3.564909,
    'cut': models.Cut(severed=(2, 4), intact=(0, 1, 3))
}


big_subsys_0_thru_3_answer = {
    'phi': 0.366389,
    'unpartitioned_small_phis': {
        (0,): 0.166667,
        (1,): 0.166667,
        (2,): 0.166667,
        (3,): 0.25,
        (0, 1): 0.133333,
        (1, 2): 0.133333
    },
    'len_partitioned_constellation': 5,
    'sum_partitioned_small_phis': 0.883334,
    'cut': models.Cut(severed=(1, 3), intact=(0, 2))
}


rule152_answer = {
    'phi': 6.952286,
    'unpartitioned_small_phis': {
        (0,): 0.125,
        (1,): 0.125,
        (2,): 0.125,
        (3,): 0.125,
        (4,): 0.125,
        (0, 1): 0.25,
        (0, 2): 0.184614,
        (0, 3): 0.184614,
        (0, 4): 0.25,
        (1, 2): 0.25,
        (1, 3): 0.184614,
        (1, 4): 0.184614,
        (2, 3): 0.25,
        (2, 4): 0.184614,
        (3, 4): 0.25,
        (0, 1, 2): 0.25,
        (0, 1, 3): 0.316666,
        (0, 1, 4): 0.25,
        (0, 2, 3): 0.316666,
        (0, 2, 4): 0.316666,
        (0, 3, 4): 0.25,
        (1, 2, 3): 0.25,
        (1, 2, 4): 0.316666,
        (1, 3, 4): 0.316666,
        (2, 3, 4): 0.25,
        (0, 1, 2, 3): 0.25,
        (0, 1, 2, 4): 0.25,
        (0, 1, 3, 4): 0.25,
        (0, 2, 3, 4): 0.25,
        (1, 2, 3, 4): 0.25,
        (0, 1, 2, 3, 4): 0.25
    },
    'len_partitioned_constellation': 24,
    'sum_partitioned_small_phis': 4.185363,
    'cuts': [
        models.Cut(severed=(0, 1, 2, 3), intact=(4,)),
        models.Cut(severed=(0, 1, 2, 4), intact=(3,)),
        models.Cut(severed=(0, 1, 3, 4), intact=(2,)),
        models.Cut(severed=(0, 2, 3, 4), intact=(1,)),
        models.Cut(severed=(1, 2, 3, 4), intact=(0,)),
        # TODO: are there other possible cuts?
    ]
}


micro_answer = {
    'phi': 0.974411,
    'unpartitioned_small_phis': {
        (0,): 0.175,
        (1,): 0.175,
        (2,): 0.175,
        (3,): 0.175,
        (0, 1): 0.348114,
        (2, 3): 0.348114,
    },
    'cuts': [
        models.Cut(severed=(0, 2), intact=(1, 3)),
        models.Cut(severed=(1, 2), intact=(0, 3)),
        models.Cut(severed=(0, 3), intact=(1, 2)),
        models.Cut(severed=(1, 3), intact=(0, 2)),
    ]
}

macro_answer = {
    'phi': 0.86905,
    'unpartitioned_small_phis': {
        (0,): 0.455,
        (1,): 0.455,
    },
    'cuts': [
        models.Cut(severed=(0,), intact=(1,)),
        models.Cut(severed=(1,), intact=(0,)),
    ]
}


# Helpers
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def check_unpartitioned_small_phis(small_phis, unpartitioned_constellation):
    assert len(small_phis) == len(unpartitioned_constellation)
    for c in unpartitioned_constellation:
        assert c.phi == small_phis[c.mechanism]


def check_partitioned_small_phis(answer, partitioned_constellation):
    if 'len_partitioned_constellation' in answer:
        assert (answer['len_partitioned_constellation'] ==
                len(partitioned_constellation))
    if 'sum_partitioned_small_phis' in answer:
        assert (round(sum(c.phi for c in partitioned_constellation),
                      config.PRECISION) ==
                answer['sum_partitioned_small_phis'])


def check_mip(mip, answer):
    # Check big phi value.
    assert mip.phi == answer['phi']
    # Check small phis of unpartitioned constellation.
    check_unpartitioned_small_phis(answer['unpartitioned_small_phis'],
                                   mip.unpartitioned_constellation)
    # Check sum of small phis of partitioned constellation if answer is
    # available.
    check_partitioned_small_phis(answer, mip.partitioned_constellation)
    # Check cut.
    if 'cut' in answer:
        assert mip.cut == answer['cut']
    elif 'cuts' in answer:
        assert mip.cut in answer['cuts']


# Tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_null_concept(s, flushcache, restore_fs_cache):
    flushcache()
    cause = models.Mice(models.Mip(
        unpartitioned_repertoire=s.unconstrained_cause_repertoire(()),
        phi=0, direction=Direction.PAST, mechanism=(), purview=(),
        partition=None, partitioned_repertoire=None))
    effect = models.Mice(models.Mip(
        unpartitioned_repertoire=s.unconstrained_effect_repertoire(()),
        phi=0, direction=Direction.FUTURE, mechanism=(), purview=(),
        partition=None, partitioned_repertoire=None))
    assert (s.null_concept ==
            models.Concept(mechanism=(), phi=0, cause=cause, effect=effect,
                           subsystem=s))


def test_concept_nonexistent(s, flushcache, restore_fs_cache):
    flushcache()
    assert not compute.concept(s, (0, 2))


@patch('pyphi.compute.distance._constellation_distance_simple')
@patch('pyphi.compute.distance._constellation_distance_emd')
def test_constellation_distance_uses_simple_vs_emd(mock_emd_distance,
                                                   mock_simple_distance, s):
    """Quick check that we use the correct constellation distance function.

    If the two constellations differ only in that some concepts have
    moved to the null concept and all other concepts are the same then
    we use the simple constellation distance. Otherwise, use the EMD.
    """
    make_mice = lambda: models.Mice(models.Mip(
        phi=None, direction=None, mechanism=None,
        purview=None, partition=None,
        unpartitioned_repertoire=None,
        partitioned_repertoire=None))

    lone_concept = models.Concept(cause=make_mice(), effect=make_mice(),
                                  mechanism=(0, 1))
    # lone concept -> null concept
    compute.constellation_distance((lone_concept,), ())
    assert mock_emd_distance.called is False
    assert mock_simple_distance.called is True
    mock_simple_distance.reset_mock()

    other_concept = models.Concept(cause=make_mice(), effect=make_mice(),
                                   mechanism=(0, 1, 2))
    # different concepts in constellation
    compute.constellation_distance((lone_concept,), (other_concept,))
    assert mock_emd_distance.called is True
    assert mock_simple_distance.called is False


@config.override(MEASURE='KLD')
def test_kld_distance_no_inf():
    a = np.array([1.0, 0])
    b = np.array([0, 1.0])

    d = compute.distance.measure(a, b)
    assert not np.isinf(d)
    assert d == compute.distance.BIG_NUMBER


@config.override(CACHE_BIGMIPS=True)
def test_big_mip_cache_key_includes_config_dependencies(s, flushcache,
                                                        restore_fs_cache):
    flushcache()

    with config.override(MEASURE='EMD'):
        emd_big_phi = compute.big_phi(s)

    with config.override(MEASURE='KLD'):
        kld_big_phi = compute.big_phi(s)

    assert kld_big_phi != emd_big_phi


def test_conceptual_information(s, flushcache, restore_fs_cache):
    flushcache()
    assert compute.conceptual_information(s) == 2.8125


def test_big_mip_empty_subsystem(s_empty, flushcache, restore_fs_cache):
    flushcache()
    assert (compute.big_mip(s_empty) ==
            models.BigMip(phi=0.0,
                          unpartitioned_constellation=(),
                          partitioned_constellation=(),
                          subsystem=s_empty,
                          cut_subsystem=s_empty))


def test_big_mip_disconnected_network(reducible, flushcache, restore_fs_cache):
    flushcache()
    assert (compute.big_mip(reducible) ==
            models.BigMip(subsystem=reducible, cut_subsystem=reducible,
                          phi=0.0, unpartitioned_constellation=[],
                          partitioned_constellation=[]))


def test_big_mip_wrappers(reducible, flushcache, restore_fs_cache):
    flushcache()
    assert (compute.big_mip(reducible) ==
            models.BigMip(subsystem=reducible, cut_subsystem=reducible,
                          phi=0.0, unpartitioned_constellation=[],
                          partitioned_constellation=[]))
    assert compute.big_phi(reducible) == 0.0


@config.override(SINGLE_NODES_WITH_SELFLOOPS_HAVE_PHI=True)
def test_big_mip_single_node_selfloops_have_phi(s_single, flushcache,
                                                restore_fs_cache):
    flushcache()
    assert compute.big_mip(s_single).phi == 0.5


@config.override(SINGLE_NODES_WITH_SELFLOOPS_HAVE_PHI=False)
def test_big_mip_single_node_selfloops_dont_have_phi(s_single, flushcache,
                                                     restore_fs_cache):
    flushcache()
    assert compute.big_mip(s_single).phi == 0.0


@config.override(PARALLEL_CUT_EVALUATION=False)
def test_find_mip_sequential_standard_example(s, flushcache, restore_fs_cache):
    flushcache()
    unpartitioned_constellation = constellation(s)
    bipartitions = utils.directed_bipartition(s.node_indices)[1:-1]
    cuts = [Cut(bipartition[0], bipartition[1])
            for bipartition in bipartitions]
    min_mip = _null_bigmip(s)
    min_mip.phi = float('inf')
    mip = _find_mip_sequential(s, cuts, unpartitioned_constellation, min_mip)
    check_mip(mip, standard_answer)


@config.override(PARALLEL_CUT_EVALUATION=True, NUMBER_OF_CORES=-2)
def test_find_mip_parallel_standard_example(s, flushcache, restore_fs_cache):
    flushcache()
    unpartitioned_constellation = constellation(s)
    bipartitions = utils.directed_bipartition(s.node_indices)[1:-1]
    cuts = [Cut(bipartition[0], bipartition[1])
            for bipartition in bipartitions]
    min_mip = _null_bigmip(s)
    min_mip.phi = float('inf')
    mip = _find_mip_parallel(s, cuts, unpartitioned_constellation, min_mip)
    check_mip(mip, standard_answer)


@config.override(PARALLEL_CUT_EVALUATION=False)
def test_find_mip_sequential_noised_example(s_noised, flushcache,
                                            restore_fs_cache):
    flushcache()
    unpartitioned_constellation = constellation(s_noised)
    bipartitions = utils.directed_bipartition(s_noised.node_indices)[1:-1]
    cuts = [Cut(bipartition[0], bipartition[1])
            for bipartition in bipartitions]
    min_mip = _null_bigmip(s_noised)
    min_mip.phi = float('inf')
    mip = _find_mip_sequential(s_noised, cuts, unpartitioned_constellation, min_mip)

    check_mip(mip, noised_answer)


@config.override(PARALLEL_CUT_EVALUATION=True, NUMBER_OF_CORES=-2)
def test_find_mip_parallel_noised_example(s_noised, flushcache,
                                          restore_fs_cache):
    flushcache()
    unpartitioned_constellation = constellation(s_noised)
    bipartitions = utils.directed_bipartition(s_noised.node_indices)[1:-1]
    cuts = [Cut(bipartition[0], bipartition[1])
            for bipartition in bipartitions]
    min_mip = _null_bigmip(s_noised)
    min_mip.phi = float('inf')
    mip = _find_mip_parallel(s_noised, cuts, unpartitioned_constellation, min_mip)
    check_mip(mip, noised_answer)


def test_possible_complexes(s):
    assert list(compute.possible_complexes(s.network, s.state)) == [
        Subsystem(s.network, s.state, (1,)),
        Subsystem(s.network, s.state, (0, 1)),
        Subsystem(s.network, s.state, (0, 2)),
        Subsystem(s.network, s.state, (1, 2)),
        Subsystem(s.network, s.state, (0, 1, 2)),
    ]


def test_complexes_standard(s, flushcache, restore_fs_cache):
    flushcache()
    complexes = list(compute.complexes(s.network, s.state))
    check_mip(complexes[2], standard_answer)


# TODO!! add more assertions for the smaller subsystems
def test_all_complexes_standard(s, flushcache, restore_fs_cache):
    flushcache()
    complexes = list(compute.all_complexes(s.network, s.state))
    check_mip(complexes[-1], standard_answer)


def test_big_mip_complete_graph_standard_example(s_complete):
    mip = compute.big_mip(s_complete)
    check_mip(mip, standard_answer)


def test_big_mip_complete_graph_s_noised(s_noised_complete):
    mip = compute.big_mip(s_noised_complete)
    check_mip(mip, noised_answer)


@pytest.mark.slow
def test_big_mip_complete_graph_big_subsys_all(big_subsys_all_complete):
    mip = compute.big_mip(big_subsys_all_complete)
    check_mip(mip, big_answer)


@pytest.mark.slow
def test_big_mip_complete_graph_rule152_s(rule152_s_complete):
    mip = compute.big_mip(rule152_s_complete)
    check_mip(mip, rule152_answer)


@pytest.mark.slow
def test_big_mip_big_network(big_subsys_all, flushcache, restore_fs_cache):
    flushcache()
    mip = compute.big_mip(big_subsys_all)
    check_mip(mip, big_answer)


def test_big_mip_big_network_0_thru_3(big_subsys_0_thru_3, flushcache,
                                      restore_fs_cache):
    flushcache()
    mip = compute.big_mip(big_subsys_0_thru_3)
    check_mip(mip, big_subsys_0_thru_3_answer)


@pytest.mark.slow
def test_big_mip_rule152(rule152_s, flushcache, restore_fs_cache):
    flushcache()
    mip = compute.big_mip(rule152_s)
    check_mip(mip, rule152_answer)


# TODO fix this horribly outdated mess that never worked in the first place :P
@pytest.mark.veryslow
def test_rule152_complexes_no_caching(rule152):
    net = rule152
    # Mapping from index of a PyPhi subsystem in network.subsystems to the
    # index of the corresponding subsystem in the Matlab list of subsets
    perm = {0: 0, 1: 1, 2: 3, 3: 7, 4: 15, 5: 2, 6: 4, 7: 8, 8: 16, 9: 5, 10:
            9, 11: 17, 12: 11, 13: 19, 14: 23, 15: 6, 16: 10, 17: 18, 18: 12,
            19: 20, 20: 24, 21: 13, 22: 21, 23: 25, 24: 27, 25: 14, 26: 22, 27:
            26, 28: 28, 29: 29, 30: 30}
    with open('test/data/rule152_results.pkl', 'rb') as f:
        results = pickle.load(f)

    # Don't use concept caching for this test.
    constants.CACHE_CONCEPTS = False

    for state, result in results.items():
        # Empty the DB.
        _flushdb()
        # Unpack the state from the results key.
        # Generate the network with the state we're testing.
        net = Network(rule152.tpm, state,
                      connectivity_matrix=rule152.connectivity_matrix)
        # Comptue all the complexes, leaving out the first (empty) subsystem
        # since Matlab doesn't include it in results.
        complexes = list(compute.complexes(net))[1:]
        # Check the phi values of all complexes.
        zz = [(bigmip.phi, result['subsystem_phis'][perm[i]]) for i, bigmip in
            list(enumerate(complexes))]
        diff = [utils.phi_eq(bigmip.phi, result['subsystem_phis'][perm[i]]) for
                i, bigmip in list(enumerate(complexes))]
        assert all(utils.phi_eq(bigmip.phi, result['subsystem_phis'][perm[i]])
                for i, bigmip in list(enumerate(complexes))[:])
        # Check the main complex in particular.
        main = compute.main_complex(net)
        # Check the phi value of the main complex.
        assert utils.phi_eq(main.phi, result['phi'])
        # Check that the nodes are the same.
        assert (main.subsystem.node_indices ==
                complexes[result['main_complex'] - 1].subsystem.node_indices)
        # Check that the concept's phi values are the same.
        result_concepts = [c for c in result['concepts'] if c['is_irreducible']]
        z = list(zip([c.phi for c in main.unpartitioned_constellation],
                    [c['phi'] for c in result_concepts]))
        diff = [i for i in range(len(z)) if not utils.phi_eq(z[i][0], z[i][1])]
        assert all(list(utils.phi_eq(c.phi, result_concepts[i]['phi']) for i, c
                        in enumerate(main.unpartitioned_constellation)))
        # Check that the minimal cut is the same.
        assert main.cut == result['cut']


@config.override(PARALLEL_CUT_EVALUATION=True)
def test_find_mip_parallel_micro(micro_s, flushcache, restore_fs_cache):
    flushcache()

    unpartitioned_constellation = constellation(micro_s)
    bipartitions = utils.directed_bipartition(micro_s.node_indices)[1:-1]
    cuts = [Cut(bipartition[0], bipartition[1])
            for bipartition in bipartitions]
    min_mip = _null_bigmip(micro_s)
    min_mip.phi = float('inf')
    mip = _find_mip_parallel(micro_s, cuts, unpartitioned_constellation,
                             min_mip)
    check_mip(mip, micro_answer)


@config.override(PARALLEL_CUT_EVALUATION=False)
def test_find_mip_sequential_micro(micro_s, flushcache, restore_fs_cache):
    flushcache()

    unpartitioned_constellation = constellation(micro_s)
    bipartitions = utils.directed_bipartition(micro_s.node_indices)[1:-1]
    cuts = [Cut(bipartition[0], bipartition[1])
            for bipartition in bipartitions]
    min_mip = _null_bigmip(micro_s)
    min_mip.phi = float('inf')
    mip = _find_mip_sequential(micro_s, cuts, unpartitioned_constellation,
                               min_mip)
    check_mip(mip, micro_answer)


@pytest.mark.dev
def test_big_mip_macro(macro_s, flushcache, restore_fs_cache):
    flushcache()
    mip = compute.big_mip(macro_s)
    check_mip(mip, macro_answer)


def test_parallel_and_sequential_constellations_are_equal(s, micro_s, macro_s):
    with config.override(PARALLEL_CONCEPT_EVALUATION=False):
        c = compute.constellation(s)
        c_micro = compute.constellation(micro_s)
        c_macro = compute.constellation(macro_s)

    with config.override(PARALLEL_CONCEPT_EVALUATION=True):
        assert set(c) == set(compute.constellation(s))
        assert set(c_micro) == set(compute.constellation(micro_s))
        assert set(c_macro) == set(compute.constellation(macro_s))


def test_big_mip_bipartitions():
    with config.override(CUT_ONE_APPROXIMATION=False):
        answer = [models.Cut((1,), (2, 3, 4)),
                  models.Cut((2,), (1, 3, 4)),
                  models.Cut((1, 2), (3, 4)),
                  models.Cut((3,), (1, 2, 4)),
                  models.Cut((1, 3), (2, 4)),
                  models.Cut((2, 3), (1, 4)),
                  models.Cut((1, 2, 3), (4,)),
                  models.Cut((4,), (1, 2, 3)),
                  models.Cut((1, 4), (2, 3)),
                  models.Cut((2, 4), (1, 3)),
                  models.Cut((1, 2, 4), (3,)),
                  models.Cut((3, 4), (1, 2)),
                  models.Cut((1, 3, 4), (2,)),
                  models.Cut((2, 3, 4), (1,))]
        assert big_mip_bipartitions((1, 2, 3, 4)) == answer

    with config.override(CUT_ONE_APPROXIMATION=True):
        answer = [models.Cut((1,), (2, 3, 4)),
                  models.Cut((2,), (1, 3, 4)),
                  models.Cut((3,), (1, 2, 4)),
                  models.Cut((1, 2, 3), (4,)),
                  models.Cut((4,), (1, 2, 3)),
                  models.Cut((1, 2, 4), (3,)),
                  models.Cut((1, 3, 4), (2,)),
                  models.Cut((2, 3, 4), (1,))]
        assert big_mip_bipartitions((1, 2, 3, 4)) == answer
