from anndata import AnnData
import scanpy as sc
import numpy as np
import pandas as pd
import sys
import os
import torch
from typing import Union

sys.path.append(os.path.join(os.path.dirname(__file__), '.', 'SignatureAnalyzer-GPU'))
from ARD_NMF import ARD_NMF, run_method_engine

# Relative Imports
from .utils import compute_phi, transfer_weights, select_signatures, select_markers

# ---------------------------------
# NMF Wrapper
# ---------------------------------
def ardnmf(X: pd.DataFrame, \
           K0: Union[int, None] = None, \
           objective: str = 'poisson', \
           max_iter: int = 10000, \
           del_: int = 1, \
           tolerance: float = 1e-6, \
           phi: Union[float, None] = None, \
           a: float = 10.0, \
           b: Union[float, None] = None , \
           prior_on_W: str = 'L1', \
           prior_on_H: str = 'L1', \
           report_frequency: int = 100, \
           active_thresh: float = 1e-5, \
           cut_norm: float = 0.5, \
           cut_diff: float = 1.0
       ) -> (pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame):
        """
        Wrapper for ARD-NMF. Wraps core algorithm from:
        https://github.com/broadinstitute/SignatureAnalyzer-GPU
        ------------------------------------------------------------------------
        Args:
            * X: input matrix (features x samples)
            * K0: starting number of latent components
            * objective: objective function for optimizaiton
            * max_iter: maximum number of iterations for algorithm
            * del_: n/a
            * tolerance: stop point for optimization
            * phi: dispersion parameter
            * a: shape parameter
            * b: shape parameter
            * prior_on_W: L1 or L2
            * prior_on_H: L1 or L2
            * report_frequency: how often to print stats
            * parameters: parameters file
            * cut_norm: min normalized value for mean signature
            * cut_diff: difference between mean signature and rest of signatures
                for marker selction
            * active_thresh: threshold for a latent component's impact on
                signature if the latent factor is less than this, it does not contribute

        Returns:
            * H: (samples x K)
            * W: (K x features)
            * markers
            * signatures
        """

        assert objective in ['poisson','gaussian'], \
            "Unable to use {}; specify either poisson or gaussian objective.".format(objective)

        if objective == 'poisson': Beta = 1
        if objective == 'gaussian': Beta = 2

        assert prior_on_W in ['L1','L2'], \
            "Unable to use {}; use either L1 or L2 prior on W.".format(prior_on_W)
        assert prior_on_H in ['L1','L2'], \
            "Unable to use {}; use either L1 or L2 prior on H.".format(prior_on_H)

        if phi is None:
            phi = compute_phi(np.mean(X.values), np.var(X.values), Beta)
            print("Using computed phi of {}".format(phi))

        # ---------------------------------
        # Load data into tensors
        # ---------------------------------
        data = ARD_NMF(X, objective)
        channel_names = data.channel_names
        sample_names = data.sample_names

        # ---------------------------------
        # Run NMF
        # ---------------------------------
        W, H, cost = run_method_engine(
            data, \
            a, \
            phi, \
            b, \
            Beta, \
            prior_on_W, \
            prior_on_H, \
            K0, \
            tolerance, \
            max_iter \
        )

        W,H,nsig = transfer_weights(W, H, active_thresh=active_thresh)
        sig_names = [str(i) for i in range(1,nsig+1)]
        W = pd.DataFrame(data=W, index=channel_names, columns=sig_names)
        H = pd.DataFrame(data=H, index=sig_names, columns=sample_names)

        W,H = select_signatures(W,H)
        markers, signatures = select_markers(X, W, H, cut_norm=cut_norm, cut_diff=cut_diff)

        return H,W,markers,signatures
