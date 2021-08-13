import planar
import numpy as np


def get_plotting_zoom_level_and_center_coordinates_from_lonlat_tuples(
        longitudes=None, latitudes=None, lonlat_pairs=None):
    """Function documentation:\n
    Basic framework adopted from Krichardson under the following thread:
    https://community.plotly.com/t/dynamic-zoom-for-mapbox/32658/7

    # NOTE:
    # THIS IS A TEMPORARY SOLUTION UNTIL THE DASH TEAM IMPLEMENTS DYNAMIC ZOOM
    # in their plotly-functions associated with mapbox, such as go.Densitymapbox() etc.

    Returns the appropriate zoom-level for these plotly-mapbox-graphics along with
    the center coordinate tuple of all provided coordinate tuples.
    """

    # Check whether the list hasn't already be prepared outside this function
    if lonlat_pairs is None:
        # Check whether both latitudes and longitudes have been passed,
        # or if the list lenghts don't match
        if ((latitudes is None or longitudes is None)
                or (len(latitudes) != len(longitudes))):
            # Otherwise, return the default values of 0 zoom and the coordinate origin as center point
            return 0, (0, 0)

        # Instantiate collator list for all coordinate-tuples
        lonlat_pairs = [(longitudes[i], latitudes[i])
                        for i in range(len(longitudes))]

    # Get the boundary-box via the planar-module
    b_box = planar.BoundingBox(lonlat_pairs)

    # In case the resulting b_box is empty, return the default 0-values as well
    if b_box.is_empty:
        return 0, (0, 0)

    # Otherwise, get the area of the bounding box in order to calculate a zoom-level
    area = b_box.height * b_box.width

    # * 1D-linear interpolation with numpy:
    # - Pass the area as the only x-value and not as a list, in order to return a scalar as well
    # - The x-points "xp" should be in parts in comparable order of magnitude of the given area
    # - The zpom-levels are adapted to the areas, i.e. start with the smallest area possible of 0
    # which leads to the highest possible zoom value 20, and so forth decreasing with increasing areas
    # as these variables are antiproportional
    zoom = np.interp(x=area,
                     xp=[0, 5**-10, 4**-10, 3**-10, 2**-10, 1**-10, 1**-5],
                     fp=[20, 17, 16, 15, 14, 7, 5])

    # Finally, return the zoom level and the associated boundary-box center coordinates
    return zoom, b_box.center
