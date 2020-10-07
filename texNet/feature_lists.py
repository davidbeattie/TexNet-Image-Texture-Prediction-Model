"""Ultraleap Image Texture Prediction Model © Ultraleap Limited 2020

Licensed under the Ultraleap closed source licence agreement; you may not use this file except in compliance with the License.

A copy of this License is included with this download as a separate document. 

Alternatively, you may obtain a copy of the license from: https://www.ultraleap.com/closed-source-licence/

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License."""

import glob, itertools
import numpy as np
from image_features import ImageFeatures


class FeaturesLists:
    """This class is essentially a composite class of some functions in the ImageFeatures class. The functions in
    this class enable numerous images to be processed simultaneously, and subsequently, to generate optimal matrices for
    each image, along with additional Haralick features, and tuples of the optimal distance and angle values.
    """

    def __init__(self, image_dir, **args):
        """Initialise the class and provide a directory of images that should be processed.

        Parameters
        ----------
        image_dir: str, path
            A path that contains the associated images that should be processed.
        image_size: int, optional
            A specified image resize value.
        """
        self.image_dir = image_dir
        self.image_size = args.get('image_size')
        self.image_features = ImageFeatures()

    def create_image_list(self):
        """Function to read each image from the input directory passed to the class initialisation function.

        Returns
        -------
        image_list: ndarray
            A list of processed images in uint8 format. Calls convert_image in ImageFeatures.
        """
        image_list = []
        for image in glob.glob(self.image_dir):
            image_list.append(self.image_features.convert_image(image))
        return image_list

    def create_matrix_list(self, image_list, distances, angles):
        """This function will process the image list output from 'create_image_list' and subsequently calculate optimal
        matrices for each image, based on the list of distances and angles provided.

        Parameters
        ----------
        image_list: uint8, array_like
            A list of processed images in uint8 format.
        distances: int, array_like
            A list of integer value distances that matrices should be calculated for.
        angles: int, array_like
            A list of integer value angles in degrees, that each matrix should be computed across.

        Returns
        -------
        matrix_list: float64, 2D array
            A list of optimal matrix arrays that have captured the underlying texture in each image
            based on Chi-Square calculations.
        inputs_list: tuple of ints, array_like
            A list of tuples that contain the distance and angle combination that produced the highest Chi-Square value,
            highlighting the underlying structure in a texture image.
        haralick_list: 1d numpy array
            A list of corresponding Haralick features computed from an optimal matrix. The order of features is:
                Homogeneity
                Contrast
                Energy
                Correlation
                Mean
                Standard Deviation
                Cluster Shade
                Cluster Prominence
        """
        matrix_list = []
        inputs_list = []
        haralick_list = []
        chisum = np.zeros(shape=(len(distances), len(angles)))

        # Compute all possible permutations of distances and angles to calculate matrices.
        perms = list(itertools.product(np.arange(0, len(distances)), np.arange(0, len(angles))))

        for image in image_list:
            non_norm_mat = self.image_features.create_matrix(image, distances, angles)
            for i, perm in enumerate(perms):
                # Calculate each ChiSquare value for matrix with distance/angle combinations. Store best combination.
                chisum[perm[0], perm[1]] = self.image_features.compute_chi_sum(non_norm_mat[:, :, perm[0], perm[1]])
                max_chi = np.unravel_index(np.argmax(chisum, axis=None), chisum.shape)
                inputs_list.append(tuple((distances[max_chi[0]], angles[max_chi[1]])))

            # Calculate normalised matrix with optimal distance/angle values.
            optimal_matrix = self.image_features.create_matrix(image, distance=[distances[max_chi[0]]],
                                                               angle=[angles[max_chi[1]]], symmetric=False,
                                                               normalise=True)
            matrix_list.append(optimal_matrix)

            # Calculate haralick features from optimal matrix.
            haralick = self.image_features.create_haralick(optimal_matrix[:, :, 0, 0])
            haralick_list.append(haralick)

        # return each of the lists of optimal matrices, distance/angle combos, and haralick feature values.
        return matrix_list, inputs_list, haralick_list