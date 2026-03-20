# Image Processing Algorithms

## Parameters of Parameter-Adjustable Semi-Automatic Tool

### Background Radius parameter

For each pixel in the image, the **Background Radius** parameter determines a square neighborhood around the pixel based on the specified radius. The features of the pixels within this neighborhood (such as grayscale values) are then analyzed to **estimate the background characteristics**, allowing the algorithm to determine whether each pixel **belongs to the background**.

As shown in the diagram below, assume the center pixel is a "jagged protrusion" (grayscale value 200) at the edge of a cell, and the surrounding 8 pixels are background (grayscale value around 100).\
Each square represents a pixel in the image, with the number inside representing the pixel's grayscale value.&#x20;

<figure><img src="../img/assets/Background radius note.png" alt=""><figcaption></figcaption></figure>

Since the features of the neighboring region are similar to those of the background, the algorithm will classify the center pixel as belonging to the background based on the neighborhood features.

### **Use Opening by Reconstruction parameter**&#x20;

**Opening by reconstruction** is a morphology-based filtering technique used in image processing to remove isolated bright noise—pixels with significantly higher intensity than their surroundings—while preserving the true shape and size of objects. This method combines **erosion** and morphological **reconstruction**, offering superior noise suppression compared to traditional opening operations (erosion followed by dilation), by better protecting structural details.

For example, consider a 3×3 neighborhood containing eight normal pixels with grayscale values around 100 and one noise pixel with value 200:

* **Erosion step:** Each pixel is replaced by the minimum value within its 3×3 neighborhood. Since the noise pixel is surrounded by lower-intensity pixels (\~100), its value is reduced to 100, achieving preliminary noise suppression.
* **Reconstruction step:** Using the eroded image as a “seed,” morphological reconstruction is performed pixel-wise on the original image. The reconstruction dilates connected regions outward, but never beyond the original pixel intensities. The noise pixel, now at 100 and connected to surrounding pixels, can only recover up to the local maximum intensity in the original image (e.g., 107). Normal pixels that were less eroded can fully restore their original values (e.g., 101, 102).

<figure><img src="../img/assets/Use opening by reconstruction note.png" alt=""><figcaption></figcaption></figure>

This process effectively “**dilutes**” or **suppresses noise** while preserving **genuine structures**, enhancing image smoothness and structural fidelity.

### **Median Filter Radius parameter**&#x20;

The **Median Filter Radius** is a simple yet effective technique for reducing image noise, commonly used in preprocessing steps like cell segmentation. It works by sliding a **square window** (typically 3×3 or 5×5 pixels) across the image. At each position, the grayscale intensity within the window are **sorted**, and the center pixel is **replaced** by the **median value**.

The size of the window is controlled by the filter radius setting: **a larger radius means a bigger window, which results in stronger smoothing but may also blur fine details.** This method effectively removes **isolated bright or dark noise** (so-called salt-and-pepper noise) while preserving important structures such as edges and boundaries.

For instance, if the median filter radius is set to 3 pixels (corresponding to a 3×3 window), and the window contains eight pixels with grayscale values around 100 and one noisy pixel with a value of 200, the sorted values yield **a median of 104**. The **noisy center pixel** is then replaced with this **median**, effectively reducing noise while preserving edges.

<figure><img src="../img/assets/Median filter radius note.png" alt=""><figcaption></figcaption></figure>

### Sigma (**Gaussian Smoothing**) **parameter**&#x20;

For each pixel in the image, a Gaussian kernel corresponding to the specified **Sigma** value (e.g., a 3×3 kernel for sigma = 0.5) is utilized to compute a weighted average. This process smooths out minor noise and jagged edges, resulting in a **blurred image**. The gradient of this blurred image is subsequently calculated, and the **watershed algorithm** is employed for segmentation.

The sigma value determines the "**neighborhood range**," and the core of this algorithm lies in using the "voting" of **surrounding pixels** to determine the **new value** of the **central pixel**. The closer a pixel is to the center, the greater its "weight," and vice versa, achieving local smoothing of the image.

As shown in the diagram below, assume the center pixel is a "jagged protrusion" (grayscale value of 200) at the edge of a cell, and the surrounding 8 pixels are background (grayscale value of 100). Without sigma blurring, the central pixel's value is much higher than its neighbors, forming a "peak," which the watershed algorithm might interpret as a "boundary," resulting in unnecessary small regions being segmented.&#x20;

<figure><img src="../img/assets/Sigma note.png" alt=""><figcaption></figcaption></figure>

With sigma blurring, the grayscale value of the central pixel is smoothed by neighboring pixels—from 200 to 125—eliminating the "peak" shape. This helps the watershed algorithm better detect true boundaries and avoid over-segmentation.

### Threshold **parameter**

The **threshold** parameter is a fundamental tool for intelligent pixel classification in image processing. By **setting a numeric** cutoff, the algorithm separates the image into **foreground** and **background** based on pixel intensity:

* **Pixels above the threshold** typically correspond to dense regions such as cell nuclei, cytoplasm, or other relevant biological structures, and are classified as foreground.
* **Pixels below the threshold** usually represent low-intensity background areas and are classified as background.

This threshold-based binarization strategy enables flexible adaptation to different sample characteristics by adjusting the cutoff value, facilitating automatic region segmentation and identification.

For instance, in a 3×3 pixel neighborhood, if the threshold is set to 25, and three or more pixels have intensity values below 25, those pixels will be marked as background, forming distinct background areas as shown in the schematic below.

<figure><img src="../img/assets/Threshold note.png" alt=""><figcaption></figcaption></figure>

### **Smooth Boundaries parameter**

The **Smooth Boundaries** parameter works in conjunction with [Sigma](image-processing-algorithms.md#sigma-gaussian-smoothing-parameter) to **balance noise suppression** and **preservation of true boundaries** through a pixel redistribution algorithm.

* **Smooth Boundaries off:** Segmentation is based on pixel intensity differences in the **original image**. Both isolated noise pixels above the threshold and true boundaries may be detected, often resulting in jagged or fragmented edges. This setting is suitable when preserving fine cellular structures is critical.
* **Smooth Boundaries on:** The image is first smoothed by [Gaussian Smoothing](image-processing-algorithms.md#sigma-gaussian-smoothing-parameter), reducing noise intensity below the threshold. Only continuous and significant grayscale changes, corresponding to true boundaries, remain. This results in smoother segmentation outputs with more accurate and regular boundaries.

For example, in a 4×4 neighborhood with a [Threshold](image-processing-algorithms.md#threshold-parameter) set to 80:

* **Off:** Noise pixels with intensity 100 exceed the threshold, falsely identified as part of the cell region, causing abnormal protrusions on the boundary.
* **On:** Noise intensity is blurred down to 60, below the threshold, and correctly excluded. Only the central true region is segmented, producing clean and noise-free boundaries.

<figure><img src="../img/assets/Smooth boundaries note.png" alt=""><figcaption></figcaption></figure>
