import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from typing import Union
import numpy as np
import matplotlib as mpl
from matplotlib.pyplot import cm

from scipy.cluster import hierarchy
import scipy.cluster.hierarchy as shc
from sklearn.cluster import AgglomerativeClustering

from ._utils import series_to_colors
from ._utils import color_list_to_matrix_and_cmap

def k_dist(X: np.ndarray, figsize: tuple = (8,8)):
    """
    Selected signatures plot.
    --------------------------------------
    Args:
        * X: numbers to plot
        * figsize: size of figure (int,int)

    Returns:
        * fig

    Example usage:
        plot_k_dist(np.array(pd.read_hdf("nmf_output.h5","aggr").K))

    """
    fig,ax = plt.subplots(figsize=figsize)

    sns.countplot(X, ax=ax, linewidth=2, edgecolor='k', rasterized=True)
    ax.set_ylim(0,ax.get_ylim()[1]+int(ax.get_ylim()[1]*0.1))

    ax.set_title("Aggregate of ARD-NMF (n={})".format(len(X)), fontsize=20)
    ax.set_ylabel("Number of Iterations", fontsize=18)
    ax.set_xticklabels(ax.get_xticklabels(), fontsize=18)

    return fig

def consensus_matrix(
    cmatrix: pd.DataFrame,
    metric: str = 'euclidean',
    method: str = 'ward',
    n_clusters: int = 10,
    color_thresh_scale: float = 0.3,
    figsize: tuple = (8,8),
    p: int = 30,
    metas: Union[list, None] = None,
    vmax: Union[float, None] = None,
    vmin: Union[float, None] = None,
    cbar_label: str = 'ARD-NMF \nMembership',
    cmap: Union[str, None] = None,
    plot_cluster_lines: bool = False
    ):
    """
    Plot consensus matrix.
    -----------------------
    Args:
        * cmatrix: consensus matrix. This may be generated by calling:
            df, assign_p = consensus_cluster_ardnmf(filepath)
        * metric: distance metric
        * method: method of clustering
        * n_clusters: number of clusters for agglomerative clustering
        * color_thresh_scale: asthetic scale for coloring of dendrogram
        * figsize: figsize
        * p: parameter for dendrogram
        * meta: list of pd.Series that includes a variable of interest to plot
            to left of plot; must be categorical in nature

    Returns:
        * fig
    """
    # -------------
    # Heatmap
    # -------------
    fig,ax = plt.subplots(figsize=figsize)
    cbar_ax = fig.add_axes([ax.get_position().x1 + ax.get_position().x1*0.1, ax.get_position().y0, .025, .1])

    # Compute initial linkage to grab ordering
    d_linkage = shc.linkage(cmatrix, metric=metric, method=method)
    dres = shc.dendrogram(d_linkage, p=p, no_plot=True)
    dgram_idx = list(map(int, dres['ivl']))

    # Create heatmap
    if vmax is None:
        cbar_top_lim = np.max(cmatrix.values)
    else:
        cbar_top_lim = vmax

    if vmin is None:
        cbar_bottom_lim = 0
    else:
        cbar_bottom_lim = vmin

    # Create heatmap
    sns.heatmap(
        cmatrix.iloc[dgram_idx,dgram_idx].values,
        ax=ax,
        square=True,
        cbar_ax=cbar_ax,
        cbar_kws = {'ticks':[cbar_bottom_lim, cbar_top_lim]},
        rasterized=True,
        vmax=vmax,
        vmin=vmin,
        cmap=cmap
    )

    cbar_ax.set_ylabel(cbar_label, fontsize=10,rotation=90)
    ax.set_xticks([])
    ax.set_yticks([])

    x0 = ax.get_position().x0
    x1 = ax.get_position().x1
    y0 = ax.get_position().y0
    y1 = ax.get_position().y1

    buf = y1*0.015

    # -------------
    # Clustering
    # -------------
    cluster = AgglomerativeClustering(
        n_clusters=n_clusters,
        affinity=metric,
        linkage=method
    )

    clusters = cluster.fit_predict(cmatrix.iloc[dgram_idx,dgram_idx])
    cluster_color_list, _ = series_to_colors(pd.Series(clusters))

    # -------------
    # Dendrogram
    # -------------
    cmap = cm.rainbow(np.linspace(0, 1, 10))
    hierarchy.set_link_color_palette([mpl.colors.rgb2hex(rgb[:3]) for rgb in cmap])

    dax = fig.add_axes([x0, y1+buf, x1-x0, 0.15])

    dres = shc.dendrogram(
        d_linkage,
        p=p,
        ax=dax,
        above_threshold_color="grey",
        color_threshold=color_thresh_scale*max(d_linkage[:,2])
    )

    dax.set_xticks([])
    dax.set_yticks([])
    [dax.spines[x].set_visible(False) for x in ['top','right','bottom','left']]

    # -------------
    # Metadata Axes
    # -------------
    if plot_cluster_lines:
        hz_lines = np.sort(np.unique(pd.Series(clusters), return_index=True)[1])
        v,c = np.unique(clusters, return_counts=True)

        _c = hz_lines
        _c = np.roll(hz_lines, 1)
        _c[0] = 0
        _c[1] = 0

        _ci = hz_lines[1:]
        _ci = np.append(_ci, clusters.shape[0])

        for idx, hz in enumerate(hz_lines):
            ax.hlines(hz, _c[idx], _ci[idx], rasterized=True)
            ax.vlines(hz, _c[idx], _ci[idx], rasterized=True)

    # Add axes
    # Plots agglomerative clustering results
    if metas is None:
        lax = fig.add_axes([x0-3*buf, y0, 2*buf, y1-y0])
        mat, cmap = color_list_to_matrix_and_cmap(cluster_color_list)
        sns.heatmap(mat.T, cmap=cmap, ax=lax, xticklabels=False, yticklabels=False, cbar=False, rasterized=True)

        uniq, idx, num_vals = np.unique(clusters.T, return_index=True, return_counts=True)
        y_locs = idx + num_vals / 2

        for idx,u in enumerate(uniq):
            lax.text(x0-50*buf, y_locs[idx], u, ha='center')

        for idx,u in enumerate(uniq):
            ax.text(
                mat.shape[1]+0.01*mat.shape[1],
                y_locs[idx],
                "n={}".format(num_vals[idx]),
                ha='left',
                fontsize=14
            )

        for _, spine in lax.spines.items():
            spine.set_visible(True)

        lax.set_xlabel("Consensus", rotation=90)

    else:
        for idx,meta in enumerate(metas):
            new_ax = [x0-(idx+3)*buf-(idx*2)*buf, y0, 2*buf, y1-y0]
            lax = fig.add_axes(new_ax)

            if isinstance(meta, str) and meta=='aggr':
                mat, cmap = color_list_to_matrix_and_cmap(cluster_color_list)
                sns.heatmap(mat.T, cmap=cmap, ax=lax, xticklabels=False, yticklabels=False, cbar=False, rasterized=True)

                uniq, idx, num_vals = np.unique(clusters.T, return_index=True, return_counts=True)
                y_locs = idx + num_vals / 2

                for idx,u in enumerate(uniq):
                    lax.text(0.5, y_locs[idx], u, ha='center')

                for idx,u in enumerate(uniq):
                    ax.text(
                        mat.shape[1]+0.01*mat.shape[1],
                        y_locs[idx],
                        "n={}".format(num_vals[idx]),
                        ha='left',
                        fontsize=14
                    )

                lax.set_xlabel("Consensus", rotation=90)

            else:
                meta = meta.loc[cmatrix.index[dgram_idx]]

                cluster_color_list, _ = series_to_colors(meta)
                mat,cmap = color_list_to_matrix_and_cmap(cluster_color_list)
                sns.heatmap(mat.T, cmap=cmap, ax=lax, yticklabels=False, xticklabels=False, cbar=False)
                lax.set_xlabel(meta.name, rotation=90)

            for _, spine in lax.spines.items():
                spine.set_visible(True)

    rs = pd.DataFrame(clusters, index=cmatrix.index[dgram_idx]).rename(columns={0:'clusters'})

    for _, spine in ax.spines.items():
        spine.set_visible(True)

    ax.set_xlabel("Samples", fontsize=14)

    return fig, rs
