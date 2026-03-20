# Stereo-CITE T FF

Spatial multi-omics data enables researchers to explore cellular processes across different omics layers. Despite the limitations of RNA expression in predicting protein levels, integrating spatial transcriptomics and proteomics provides valuable complementary insights, revolutionizing our understanding of complex biological activities.

## Explore Tissue Context through Spatial Multi-omics Data

The linked windows can manipulate multiple views of the same dataset simultaneously based on spot coordinates.&#x20;

{% hint style="info" %}
The spots that require manipulation based on the coordinates rely heavily on the initiator of the action. Therefore, **only the primary window can serve as the initiator**, and the result will be reflected in all other linked windows.&#x20;
{% endhint %}

### By clusters

To view the gene and protein cluster results side by side, open the [layer menu](../navigation-for-visual-explore.md#layer-menu-and-bin-sizes). Click on the <img src="../../img/assets/new_linked_window.png" alt="" data-size="line"> in front of `Cluster` under Proteomics to open the protein cluster result in a new linked window. You are also allowed to switch the initiative party in the main window.&#x20;

<div><figure><img src="../../img/assets/open protein cluster layer in new linked window.png" alt=""><figcaption></figcaption></figure> <figure><img src="../../img/assets/gene cluster protein cluster side by side.png" alt=""><figcaption></figcaption></figure></div>

Clustering based on spatial gene expression or protein level leads to different classifications for spots with the same coordinates. The primary window (left) displays the clusters based on the spatial gene expression matrix. When a cluster is selected, the corresponding spots within the cluster will be highlighted. In the linked window (right), only the selected spots are displayed on the canvas and are color-coded based on the protein clusters.

<figure><img src="../../img/assets/linked by coordinates-select cluster.png" alt=""><figcaption><p>Spot coordinates in cluster 1 of spatial gene clustering result (left) have different classifications in spatial protein clustering (right)</p></figcaption></figure>

The functionality of linking spots between windows also extends to linking UMAP and spatial cluster view.

<div><figure><img src="../../img/assets/umap layer.png" alt=""><figcaption><p>Gene clusters in UMAP (left) and protein clusters in spatial view (right)</p></figcaption></figure> <figure><img src="../../img/assets/umap spots linked by coordinates-select cluster.png" alt=""><figcaption><p>Spots linking between gene's UMAP (left) and protein's spatial clustering (right)</p></figcaption></figure></div>

### By lasso

{% hint style="info" %}
The lasso function is currently only available in the spatial view, so it cannot be used to link spots in UMAP or any other spatial views.
{% endhint %}

In addition to selecting a cluster, you can also use the [lasso function](../navigation-for-visual-explore.md#mouse-tools) to choose specific regions of interest. After saving the lasso region, you can switch to any spatial view, including gene heatmap, protein heatmap, gene cluster, and protein cluster.

<div><figure><img src="../../img/assets/linked by coordinates-lasso cluster.png" alt=""><figcaption></figcaption></figure> <figure><img src="../../img/assets/linked by coordinates-lasso heatmap.png" alt=""><figcaption></figcaption></figure></div>

## Spatial Distribution of Protein and its Corresponding Marker Gene

{% hint style="info" %}
This function is only applicable to square bins such as bin 20, 50, 100, etc.&#x20;
{% endhint %}

For Stereo-CITE data analysis, SAW (>= 8.1) displays gene vs. protein correlations in the HTML analysis report, refer to [**SAW User Manual**](https://en.stomics.tech/service/new-saw-operation-manual.html) -**Analysis**-**Outputs**-**HTML Report**-**Gene : protein correlations** for more information. In StereoMap (>= 4.1), you can visualize the spatial distribution of protein-marker gene pairs and gain a better understanding of the correlations.&#x20;

To view the protein heatmap alongside the gene heatmap, open the [layer menu](../navigation-for-visual-explore.md#layer-menu-and-bin-sizes). Click on the <img src="../../img/assets/new_linked_window.png" alt="" data-size="line"> in front of `Protein_Heatmap_tissue` to open the protein heatmap in a new linked window. This will allow you to see both heatmaps side by side. You are also allowed to view the protein heatmap first, and open the gene heatmap in a new linked window.

<div><figure><img src="../../img/assets/open protein layer in new linked window.png" alt=""><figcaption></figcaption></figure> <figure><img src="../../img/assets/gene protein side by side.png" alt=""><figcaption></figcaption></figure></div>

In SAW HTML report, protein _**IgM\_Ms**_ and its pre-defined marker gene _**Ighm**_ show a positive correlation (Pearson's _r_ = 0.4957) which agrees with previous reports [\[1\]](stereo-cite-t-ff.md#reference). In the StereoMap, you can click on the <img src="../../img/assets/link.svg" alt="" data-size="original"> icon located behind the feature name to observe if the expression of the pair same or different across gene or protein maps. Clicking on the <img src="../../img/assets/link.svg" alt="" data-size="original"> of protein _**IgM\_Ms**_ will display its protein distribution in the protein window and show the gene _**Ighm**_ distribution in the gene window at the same time.&#x20;

<div><figure><img src="../../img/assets/gene-protein correlation.png" alt=""><figcaption><p>Correlation in SAW HTML report</p></figcaption></figure> <figure><img src="../../img/assets/spatial distribution of IgM_Ms and Ighm marker gene.png" alt=""><figcaption><p>Spatial distributions of Ighm (left: gene) and IgM_Ms (right: protein)</p></figcaption></figure></div>

If you want to see multiple pairs, you may click on the <img src="../../img/assets/checkboxOutline.svg" alt="" data-size="original"> in front of the feature name to select them.&#x20;

<figure><img src="../../img/assets/select multiple pairs.png" alt=""><figcaption><p>Select multiple feature pairs</p></figcaption></figure>

The large bin size may blur the pattern. You can switch to other square bin sizes in the main window, and the linked window will be manipulated simultaneously.

<figure><img src="../../img/assets/change bin size for both window.png" alt=""><figcaption></figcaption></figure>

## Reference

1. Niu, X., Swett, A. D., Sotelo, J., Jiao, M. S., Stewart, C. M., Potenski, C., Mielinis, P., Roelli, P., Stoeckius, M., & Landau, D. A. (2023). Integration of whole transcriptome spatial profiling with protein markers. _Nature Biotechnology_, _41_(6), 788-793. https://doi.org/10.1038/s41587-022-01536-3
