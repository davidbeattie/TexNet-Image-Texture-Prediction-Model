"""Ultraleap Image Texture Prediction Model © Ultraleap Limited 2020

Licensed under the Ultraleap closed source licence agreement; you may not use this file except in compliance with the License.

A copy of this License is included with this download as a separate document. 

Alternatively, you may obtain a copy of the license from: https://www.ultraleap.com/closed-source-licence/

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License."""

import numpy as np
from cv2 import imread
from skimage import transform
from skimage.feature.texture import greycomatrix


class ImageFeatures(object):
    """Feature computation class to generate optimal GLCMs and equivalent Haralick features.
    """

    def __init__(self, **args):
        """Initialise the ImageFeatures class and pass distance, angle values for computation of matrices.

        Parameters
        ----------
        distance: array_like, optional
            Integer type list of pixel pair distance offsets.
        angles: array_like, optional  - [0, 45, 90, 135]
            Integer type list of angles in degrees.
        """
        self.distance = args.get('distance')
        self.angle = args.get('angle')

    def convert_image(self, image, image_size=256, greyscale=True, resize=True):
        """Rescale images from initial input size to reduced size. Image should be square. Will be resized as square if
        optional argument 'image_size' is given.

        Parameters
        ----------
        image: path/to/file
            Image file path. .jpg, .png, or .bmp formatted.
        image_size: int, optional
            Size that image should be resized to. Default = 256.
        greyscale: bool, optional
            Sets whether image should be converted to greyscale or colour. Default = True
        resize: bool, optional
            If True, then image will be resized to the 'image_size' (w x h). Default = True.

        Returns
        -------
        converted_image: array_like, uint8
            Returns an image as a 2D array of grey level values (0 - 255) as type uint8. If greyscale is set to False,
            then returned image will be 3x2D arrays corresponding to RGB channels.
        """
        if greyscale:
            converted_image = imread(image, 0)
        else:
            converted_image = imread(image, 1)

        if resize and image_size is not None:
            converted_image = transform.resize(converted_image, output_shape=(image_size, image_size))
        else:
            print("Error: Image size not given. Please include a reshaped image size.")
        return (converted_image * 255).astype('uint8')

    def create_matrix(self, image, distance=None, angle=None, symmetric=False, normalise=False):
        """Produces a grey level co-occurence matrix based on input image, distance by which to compare pixel grey-level
        co-occurences, and corresponding angle.

        Parameters
        ----------
        image: array_like
            Having converted images into uint (preferably 256x256), pass as input to create matrix.
        distance: int, optional
            A specific distance value by which co-occurring grey-levels should be tallied across. Default = 1
        angle: int, optional
            A specific angle in degrees by which the matrix should be scanned across. Default = 0
        symmetric: bool, optional
            Determines whether output matrix is symmetric. Handled by sk-image. Default = False.
        normalise: bool, optional
            If true, matrix values are the probablities of co-occurring pixel grey-level values, where sum = 1.
            Handled by sk-image. Default = False.

        Returns
        -------
        matrix: 4D ndarray
            Output is a grey-level matrix, matrix[image_size, image_size, distance, angle] is returned. Matrix
            identifies where a given grey level value (0 - 255) occurs in comparison to an equivalent value for a given
            distance and angle. Output is uint32 if 'normalise' = True. Otherwise, float64. Handled by sk-image to
            reduce processing time.
        """
        if distance is None:
            distance = np.array([1])
        if angle is None:
            angle = np.array([0])
        return greycomatrix(image, distance, angle, symmetric=symmetric, normed=normalise)

    def create_haralick(self, matrix):
        """Function to compute 7 Haralick features used as factors to determine the level of underlying texture
        dimension contained within an image whose matrix has been calculated. We compute specific features related
        to different independent statistical properties that can be obtained from GLCMs.

        Matrices must be normalised in order to correctly calculate each Haralick feature.

        Contrast Group: This group identifies pixel co-occurrences in relation to their distance from the GLCM diagonal.
            contrast: float64, [0 - 10e6]
                'sum of squares variance'. Weights increase exponentially as values move away from diagonal. Therefore,
                an image that has a high contrast value signifies co-occurring pixel values occur far from the diagonal.
            homogeneity: float64, [0 - 1]
                Weights decrease exponentially away from the diagonal, meaning a matrix's homogeneity value is higher
                when its contrast is very low (close to diagonal). Therefore, images with very little variance will
                produce a homogeneity value that approaches 1.

        Orderliness Group: This group explains how 'regular' the pixel value differences are within a matrix.
            asm: float64, [0 - >1]
                'Angular Second Moment', if a matrix contains large numbers for only a few pixel co-occurrences, then
                asm will be high, indicating that the underlying texture is some repeated pattern (orderly). Conversely,
                if asm is low, then the underlying texture will be very randomised in changes in grey level.
            energy: float64, [0 - 1]
                This is the square root of asm.

        Descriptives Group: This group calculates descriptive statistics such as mean, stdev on the matrix entries, not
                            the image values themselves.
                mean: float64
                    matrix mean demonstrates the frequency of occurrence of one pixel value (j) being found across a
                    distance, and angle input value, at its (i) neighbour. For symmetric matrices, calculating mean
                    for i will be identical to j mean.
                stdev: float64
                    square root of the variance in terms of the dispersion of values around the calculated mean for
                    pixel co-occurrences.
                corr: float64
                    Correlation that identifies the linear dependency of grey levels on those of neighbouring pixels.
                    0 (uncorrelated) and 1 (perfectly correlated). This measure is independent of all other Haralick
                    features. High values denote high predictability of pixel relationships.
                cls_shade: float64
                    Cluster Shade measures the skewness and uniformity in the computed matrix. Higher values suggest
                    more asymmetry around the mean.
                cls_prom: float64
                    Cluster Prominence measures asymmetry in the matrix. Similar characteristics to Cluster Shade
                    (cls_shade).

        Refer to:
            R. M. Haralick, K. Shanmugam and I. Dinstein, "Textural Features for Image Classification,"
            in IEEE Transactions on Systems, Man, and Cybernetics, vol. SMC-3, no. 6, pp. 610-621, Nov. 1973,
            doi: 10.1109/TSMC.1973.4309314.

        Parameters
        ----------
        matrix: ndarray - 2D
            An input matrix array containing co-occurring grey-level values for an image. Must first be normalised.

        Returns
        -------
        features: ndarray
            Outputs a list of 9 Haralick features calculated from the input matrix.
        """
        # Initialise a mesh grid
        level = matrix.shape[0]
        I, J = np.ogrid[0:level, 0:level]
        ij = I * J

        # Compute Homogeneity weights and apply to matrix for homogeneity calculation.
        homo_weight = 1. / (1. + (I - J) ** 2)
        homo = np.apply_over_axes(np.sum, (matrix * homo_weight), axes=(0, 1))[0, 0]

        # Compute Contrast weights. Apply to matrix.
        con_weight = (I - J) ** 2
        contrast = np.apply_over_axes(np.sum, (matrix * con_weight), axes=(0, 1))[0, 0]

        # Compute ASM (angular second moment). Take square root for energy calculation.
        asm = np.apply_over_axes(np.sum, (matrix ** 2), axes=(0, 1))[0, 0]
        energy = np.sqrt(asm)

        k = np.arange(len(matrix))
        tk = np.arange(2 * (len(matrix)))
        p = matrix / matrix.sum()
        pravel = p.ravel()
        px = p.sum(0)
        py = p.sum(1)

        ux = np.dot(px, k)
        uy = np.dot(py, k)
        vx = np.dot(px, k ** 2) - ux ** 2
        vy = np.dot(py, k ** 2) - uy ** 2
        sx = np.sqrt(vx)
        sy = np.sqrt(vy)

        if sx == 0.0 or sy == 0.0:
            corr = 1.0
        else:
            # Compute Correlation value across matrix
            corr = (1. / sx / sy) * (np.dot(ij.ravel(), pravel) - ux * uy)

        px_plus_y = np.zeros(2 * len(matrix), np.double)
        px_minus_y = np.zeros(len(matrix), np.double)

        idx1 = np.arange(0, level * 2)
        idx2 = np.arange(0, level)

        tmp1 = np.array([np.array(I + J).reshape(-1, 1), np.array(matrix).reshape(-1, 1)])
        tmp2 = np.array([np.abs(I - J).reshape(-1, 1), np.array(matrix).reshape(-1, 1)])

        for i in idx1:
            px_plus_y[i] = tmp1[1][tmp1[0] == i].sum()

        for i in idx2:
            px_minus_y[i] = tmp2[1][tmp2[0] == i].sum()

        # Compute mean and standard deviation of matrix.
        mean = np.dot(tk, px_plus_y)
        stdev = np.sqrt(np.dot(tk ** 2, px_plus_y) - mean ** 2)

        # Calculate Cluster Shade and Prominence weights, then obtain values by applying across matrix.
        shade_weight = np.power((I + J - ux - uy), 3)
        prom_weight = np.power((I + J - ux - uy), 4)

        cls_shade = np.apply_over_axes(np.sum, (matrix * shade_weight), axes=(0, 1))[0, 0]
        cls_prom = np.apply_over_axes(np.sum, (matrix * prom_weight), axes=(0, 1))[0, 0]

        return np.array([homo, asm, contrast, energy, corr, mean, stdev, cls_shade, cls_prom])

    def compute_chi_sum(self, matrix):
        """This function computes a Chi-Square value for an input matrix. This value can be used to ascertain which
        particular distance value and angle used to calculate the matrix has enabled the underlying structure to be
        captured. High Chi-Square values will indicate that the input matrix has more succesfully captured the texture
        structure within an image.

        Parameters
        ----------
        matrix: ndarray - 2D
            An input matrix array containing co-occurring grey-level values for an image. Should be non-normalised.

        Returns
        -------
        chi_sum: float64
            Provides a float64 value of the computed Chi-Square value that indicates the goodness of fit of the matrix
            computed over a specific distance and angle, in relation to the underlying texture structure in the
            corresponding image.

        Refer to:
            Zucker, Steven W., and Demetri Terzopoulos. "Finding structure in co-occurrence matrices
            for texture analysis." Computer graphics and image processing 12, no. 3 (1980): 286-308.
        """

        # Calculate matrix row and column totals.
        row_matrix = np.repeat(matrix.sum(axis=0), matrix.shape[0], axis=0).reshape(matrix.shape[0], matrix.shape[1])
        col_matrix = np.repeat(matrix.sum(axis=1), matrix.shape[0], axis=0).reshape(matrix.shape[0], matrix.shape[1]).T

        # Calculate multiplied row and column totals then divide by the sum of the non-normalised matrix.
        matrix_rc_totals = (row_matrix * col_matrix) / matrix.sum()

        # Obtain the expected values for each cell in the matrix
        expected_values = (matrix - matrix_rc_totals) ** 2

        # Return the sum of all values where rows and columns sums are non zero.
        return np.sum(np.divide(expected_values, matrix_rc_totals, where=(matrix_rc_totals != 0)))
